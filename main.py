import json
import asyncio
import random
import time
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
from database import init_db, get_random_questions, insert_question


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="El Gran Show - Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


# --- MODELOS PARA EL PANEL DE PREGUNTAS ---
class PreguntaIn(BaseModel):
    consigna: str
    respuesta_correcta: str
    categoria: str
    tipo: str = "abierta"
    opciones: Optional[List[str]] = None  # solo se usa si tipo == "multiple"


@app.post("/api/preguntas")
def api_nueva_pregunta(data: PreguntaIn):
    nuevo_id = insert_question(
        data.consigna, data.respuesta_correcta, data.categoria, data.tipo, data.opciones
    )
    return {"status": "ok", "id": nuevo_id, "mensaje": "Pregunta guardada"}


# --- GESTOR DE ESTADO DEL JUEGO Y WEBSOCKETS ---
class GameManager:
    def __init__(self):
        self.room_pin: str = self.generate_new_pin()
        self.connections: List[WebSocket] = []
        self.players: Dict[WebSocket, dict] = {}
        self.host_socket: Optional[WebSocket] = None
        self.screen_socket: Optional[WebSocket] = None

        # Qué módulo/juego está activo. Por ahora solo "trivia" (abiertas + multiple).
        self.modulo_actual: Optional[str] = "trivia"

        self.questions_queue: List[dict] = []
        self.current_question: Optional[dict] = None
        self.state: str = "LOBBY"

        # Estado específico de preguntas ABIERTAS (pulsador)
        self.buzzer_winner: Optional[str] = None
        self.rebote_disponible: bool = True
        self.reading_task: Optional[asyncio.Task] = None

        # Estado específico de preguntas MULTIPLE CHOICE
        self.mc_deadline_task: Optional[asyncio.Task] = None
        self.mc_time_limit: int = 15

    def generate_new_pin(self) -> str:
        return str(random.randint(1000, 9999))

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)
        if ws in self.players:
            del self.players[ws]
        if ws == self.host_socket:
            self.host_socket = None
        if ws == self.screen_socket:
            self.screen_socket = None

    async def broadcast(self, data: dict):
        """Manda el mismo mensaje a TODOS (host, screen, jugadores)."""
        msg = json.dumps(data)
        for ws in self.connections:
            try:
                await ws.send_text(msg)
            except Exception:
                pass

    async def broadcast_split(self, data_public: dict, data_host_extra: dict):
        """Versión sin datos sensibles a jugadores/pantalla; versión completa solo al host."""
        msg_public = json.dumps(data_public)
        msg_host = json.dumps({**data_public, **data_host_extra})

        for ws in self.connections:
            try:
                if ws == self.host_socket:
                    await ws.send_text(msg_host)
                else:
                    await ws.send_text(msg_public)
            except Exception:
                pass

    def get_leaderboard(self) -> List[dict]:
        board = [{"name": p["name"], "score": p["score"]} for p in self.players.values()]
        return sorted(board, key=lambda x: x["score"], reverse=True)

    def reset_player_round_state(self):
        for p in self.players.values():
            p["blocked_this_round"] = False
            p["mc_answer"] = None
            p["mc_answer_time"] = None

    # ---------- LÓGICA PREGUNTAS ABIERTAS (pulsador) ----------
    async def auto_open_buzzers(self, seconds: int = 6):
        try:
            await asyncio.sleep(seconds)
            if self.state == "READING":
                self.state = "BUZZER_OPEN"
                await self.broadcast({
                    "event": "buzzers_unlocked",
                    "time_limit": 10
                })
        except asyncio.CancelledError:
            pass

    # ---------- LÓGICA MULTIPLE CHOICE (todos responden a la vez) ----------
    async def auto_reveal_mc(self, seconds: int):
        try:
            await asyncio.sleep(seconds)
            if self.state == "MC_OPEN":
                await self.reveal_mc_results()
        except asyncio.CancelledError:
            pass

    async def reveal_mc_results(self):
        """Corta las respuestas, suma puntos y revela la correcta a todos."""
        if not self.current_question:
            return

        correcta = self.current_question["respuesta_correcta"]
        conteo_opciones: Dict[str, int] = {}

        for p in self.players.values():
            elegida = p.get("mc_answer")
            if elegida is not None:
                conteo_opciones[elegida] = conteo_opciones.get(elegida, 0) + 1
                if elegida == correcta:
                    p["score"] += 10

        self.state = "ROUND_OVER"
        await self.broadcast({
            "event": "mc_result",
            "respuesta_correcta": correcta,
            "conteo_opciones": conteo_opciones,
            "leaderboard": self.get_leaderboard()
        })


manager = GameManager()


@app.get("/api/pin")
def get_current_pin():
    return {"pin": manager.room_pin}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        while True:
            text_data = await ws.receive_text()
            data = json.loads(text_data)
            action = data.get("action")

            # 1. IDENTIFICACIÓN Y AUTENTICACIÓN
            if action == "register":
                role = data.get("role")

                if role == "player":
                    pin_ingresado = str(data.get("pin", "")).strip()

                    if pin_ingresado != manager.room_pin:
                        await ws.send_text(json.dumps({
                            "event": "auth_error",
                            "message": "Código incorrecto. El PIN actual es de 4 dígitos."
                        }))
                        continue

                    name = data.get("name", "Anónimo").strip()
                    manager.players[ws] = {
                        "name": name,
                        "score": 0,
                        "blocked_this_round": False,
                        "mc_answer": None,
                        "mc_answer_time": None
                    }
                    await ws.send_text(json.dumps({"event": "auth_ok"}))
                    await manager.broadcast({
                        "event": "player_joined",
                        "players": manager.get_leaderboard()
                    })

                elif role == "screen":
                    manager.screen_socket = ws
                    await ws.send_text(json.dumps({
                        "event": "sync_screen",
                        "room_pin": manager.room_pin,
                        "state": manager.state,
                        "modulo_actual": manager.modulo_actual,
                        "leaderboard": manager.get_leaderboard()
                    }))

                elif role == "host":
                    manager.host_socket = ws
                    await ws.send_text(json.dumps({
                        "event": "sync_state",
                        "room_pin": manager.room_pin,
                        "state": manager.state,
                        "modulo_actual": manager.modulo_actual,
                        "leaderboard": manager.get_leaderboard()
                    }))

            # 2. REINICIAR SALA (CAMBIO DE PIN)
            elif action == "reset_room":
                manager.room_pin = manager.generate_new_pin()
                manager.players.clear()
                manager.state = "LOBBY"
                await manager.broadcast({
                    "event": "room_reset",
                    "new_pin": manager.room_pin
                })

            # 4. LANZAR PREGUNTA (abierta O multiple choice, según 'tipo')
            elif action == "next_question":
                if not manager.questions_queue:
                    # Se autocompleta sola: no hace falta ningún botón de "cargar tanda".
                    manager.questions_queue = get_random_questions(limit=30)

                if manager.reading_task and not manager.reading_task.done():
                    manager.reading_task.cancel()
                if manager.mc_deadline_task and not manager.mc_deadline_task.done():
                    manager.mc_deadline_task.cancel()

                manager.current_question = manager.questions_queue.pop(0)
                manager.buzzer_winner = None
                manager.rebote_disponible = True
                manager.reset_player_round_state()

                tipo = manager.current_question.get("tipo", "abierta")

                if tipo == "multiple":
                    opciones = manager.current_question.get("opciones") or []
                    opciones_mezcladas = opciones.copy()
                    random.shuffle(opciones_mezcladas)

                    manager.state = "MC_OPEN"

                    # La respuesta correcta sigue yendo SOLO al host, igual que en abiertas.
                    await manager.broadcast_split(
                        data_public={
                            "event": "new_question",
                            "tipo": "multiple",
                            "categoria": manager.current_question["categoria"],
                            "consigna": manager.current_question["consigna"],
                            "opciones": opciones_mezcladas,
                            "time_limit": manager.mc_time_limit
                        },
                        data_host_extra={
                            "respuesta_correcta": manager.current_question["respuesta_correcta"]
                        }
                    )

                    manager.mc_deadline_task = asyncio.create_task(
                        manager.auto_reveal_mc(manager.mc_time_limit)
                    )

                else:
                    manager.state = "READING"
                    await manager.broadcast_split(
                        data_public={
                            "event": "new_question",
                            "tipo": "abierta",
                            "categoria": manager.current_question["categoria"],
                            "consigna": manager.current_question["consigna"],
                            "reading_time": 6
                        },
                        data_host_extra={
                            "respuesta_correcta": manager.current_question["respuesta_correcta"]
                        }
                    )
                    manager.reading_task = asyncio.create_task(manager.auto_open_buzzers(6))

            # 5. ABRIR PULSADORES ANTES DE TIEMPO (solo preguntas abiertas)
            elif action == "open_buzzers":
                if manager.state == "READING":
                    if manager.reading_task and not manager.reading_task.done():
                        manager.reading_task.cancel()
                    manager.state = "BUZZER_OPEN"
                    await manager.broadcast({
                        "event": "buzzers_unlocked",
                        "time_limit": 10
                    })

            # 6. PULSADOR PRESIONADO (solo preguntas abiertas)
            elif action == "press_buzzer":
                if manager.state == "BUZZER_OPEN":
                    player = manager.players.get(ws)
                    if player and not player["blocked_this_round"]:
                        manager.state = "ANSWERING"
                        manager.buzzer_winner = player["name"]

                        await manager.broadcast({
                            "event": "buzzer_won",
                            "winner_name": player["name"],
                            "speaking_time": 10
                        })

            # 6b. NUEVO: RESPUESTA DE MULTIPLE CHOICE (todos responden a la vez)
            elif action == "submit_answer":
                if manager.state == "MC_OPEN":
                    player = manager.players.get(ws)
                    if player and player["mc_answer"] is None:
                        selected = data.get("selected")  # texto exacto de la opción elegida
                        player["mc_answer"] = selected
                        player["mc_answer_time"] = time.time()

                        respondieron = sum(
                            1 for p in manager.players.values() if p["mc_answer"] is not None
                        )
                        await manager.broadcast({
                            "event": "mc_progress",
                            "respondieron": respondieron,
                            "total_jugadores": len(manager.players)
                        })

                        # Si ya contestaron todos, cerramos antes de que se cumpla el tiempo.
                        if manager.players and respondieron == len(manager.players):
                            if manager.mc_deadline_task and not manager.mc_deadline_task.done():
                                manager.mc_deadline_task.cancel()
                            await manager.reveal_mc_results()

            # 7. RESPUESTA CORRECTA (solo preguntas abiertas)
            elif action == "answer_correct":
                if manager.state == "ANSWERING":
                    for p in manager.players.values():
                        if p["name"] == manager.buzzer_winner:
                            p["score"] += 10
                            break

                    manager.state = "ROUND_OVER"
                    await manager.broadcast({
                        "event": "round_result",
                        "status": "correct",
                        "winner_name": manager.buzzer_winner,
                        "respuesta_correcta": manager.current_question["respuesta_correcta"],
                        "leaderboard": manager.get_leaderboard()
                    })

            # 8. RESPUESTA INCORRECTA (solo preguntas abiertas)
            elif action == "answer_incorrect":
                if manager.state == "ANSWERING":
                    for p in manager.players.values():
                        if p["name"] == manager.buzzer_winner:
                            p["blocked_this_round"] = True
                            break

                    if manager.rebote_disponible:
                        manager.rebote_disponible = False
                        manager.state = "BUZZER_OPEN"
                        await manager.broadcast({
                            "event": "rebote_active",
                            "excluded_player": manager.buzzer_winner,
                            "rebote_time": 7
                        })
                    else:
                        manager.state = "ROUND_OVER"
                        await manager.broadcast({
                            "event": "round_result",
                            "status": "null_round",
                            "respuesta_correcta": manager.current_question["respuesta_correcta"],
                            "leaderboard": manager.get_leaderboard()
                        })

            # 9. ANULAR RONDA
            elif action == "round_null":
                if manager.reading_task and not manager.reading_task.done():
                    manager.reading_task.cancel()
                if manager.mc_deadline_task and not manager.mc_deadline_task.done():
                    manager.mc_deadline_task.cancel()
                manager.state = "ROUND_OVER"
                await manager.broadcast({
                    "event": "round_result",
                    "status": "null_round",
                    "respuesta_correcta": manager.current_question["respuesta_correcta"] if manager.current_question else "",
                    "leaderboard": manager.get_leaderboard()
                })

            # 10. MOSTRAR TABLA DE POSICIONES A DEMANDA
            elif action == "show_leaderboard":
                manager.state = "LEADERBOARD"
                await manager.broadcast({
                    "event": "show_leaderboard",
                    "leaderboard": manager.get_leaderboard()
                })

            # 11. PODIO FINAL
            elif action == "finish_game":
                manager.state = "PODIUM"
                await manager.broadcast({
                    "event": "game_over",
                    "podium": manager.get_leaderboard()[:3],
                    "full_ranking": manager.get_leaderboard()
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast({
            "event": "player_left",
            "players": manager.get_leaderboard()
        })


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)