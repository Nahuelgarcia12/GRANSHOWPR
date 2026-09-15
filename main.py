import json
import asyncio
import random
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


@app.post("/api/preguntas")
def api_nueva_pregunta(data: PreguntaIn):
    nuevo_id = insert_question(data.consigna, data.respuesta_correcta, data.categoria, data.tipo)
    return {"status": "ok", "id": nuevo_id, "mensaje": "Pregunta guardada"}


# --- GESTOR DE ESTADO DEL JUEGO Y WEBSOCKETS ---
class GameManager:
    def __init__(self):
        self.room_pin: str = self.generate_new_pin()
        self.connections: List[WebSocket] = []
        self.players: Dict[WebSocket, dict] = {}
        self.host_socket: Optional[WebSocket] = None
        self.screen_socket: Optional[WebSocket] = None

        # NUEVO: qué módulo/juego está activo ahora mismo.
        # None = sin módulo activo (pantalla de selección / espera)
        self.modulo_actual: Optional[str] = None

        self.questions_queue: List[dict] = []
        self.current_question: Optional[dict] = None
        self.state: str = "LOBBY"
        self.buzzer_winner: Optional[str] = None
        self.rebote_disponible: bool = True
        self.reading_task: Optional[asyncio.Task] = None

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

        msg = json.dumps(data)
        for ws in self.connections:
            try:
                await ws.send_text(msg)
            except Exception:
                pass

    async def broadcast_split(self, data_public: dict, data_host_extra: dict):

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
                        "blocked_this_round": False
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

            # 2. INICIAR PARTIDA / TANDA
            elif action == "start_tanda":
                manager.questions_queue = get_random_questions(limit=15)
                manager.state = "LOBBY"
                await manager.broadcast({
                    "event": "tanda_ready",
                    "room_pin": manager.room_pin,
                    "total_questions": len(manager.questions_queue),
                    "leaderboard": manager.get_leaderboard()
                })

            # 3. REINICIAR SALA (CAMBIO DE PIN)
            elif action == "reset_room":
                manager.room_pin = manager.generate_new_pin()
                manager.players.clear()
                manager.modulo_actual = None
                manager.state = "LOBBY"
                await manager.broadcast({
                    "event": "room_reset",
                    "new_pin": manager.room_pin
                })

            # 4. LANZAR PREGUNTA
            elif action == "next_question":
                if not manager.questions_queue:
                    manager.questions_queue = get_random_questions(limit=10)

                if manager.reading_task and not manager.reading_task.done():
                    manager.reading_task.cancel()

                manager.current_question = manager.questions_queue.pop(0)
                manager.state = "READING"
                manager.buzzer_winner = None
                manager.rebote_disponible = True

                for p in manager.players.values():
                    p["blocked_this_round"] = False


                await manager.broadcast_split(
                    data_public={
                        "event": "new_question",
                        "categoria": manager.current_question["categoria"],
                        "consigna": manager.current_question["consigna"],
                        "reading_time": 6
                    },
                    data_host_extra={
                        "respuesta_correcta": manager.current_question["respuesta_correcta"]
                    }
                )

                manager.reading_task = asyncio.create_task(manager.auto_open_buzzers(6))

            # 5. ABRIR PULSADORES ANTES DE TIEMPO
            elif action == "open_buzzers":
                if manager.state == "READING":
                    if manager.reading_task and not manager.reading_task.done():
                        manager.reading_task.cancel()
                    manager.state = "BUZZER_OPEN"
                    await manager.broadcast({
                        "event": "buzzers_unlocked",
                        "time_limit": 10
                    })

            # 6. PULSADOR PRESIONADO
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

            # 7. RESPUESTA CORRECTA
            elif action == "answer_correct":
                if manager.state == "ANSWERING":
                    for p in manager.players.values():
                        if p["name"] == manager.buzzer_winner:
                            p["score"] += 10
                            break

                    manager.state = "ROUND_OVER"
                    # Acá SÍ se revela la respuesta correcta a todos: la ronda ya terminó.
                    await manager.broadcast({
                        "event": "round_result",
                        "status": "correct",
                        "winner_name": manager.buzzer_winner,
                        "respuesta_correcta": manager.current_question["respuesta_correcta"],
                        "leaderboard": manager.get_leaderboard()
                    })

            # 8. RESPUESTA INCORRECTA
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

            # 12. NUEVO: INICIAR UN MÓDULO/JUEGO ESPECÍFICO
            # El animador elige desde el dropdown del panel: "trivia", "bingo_musical",
            # "minuto_ganar", "pasapalabra", "100_argentinos", etc.
            elif action == "iniciar_modulo":
                nuevo_modulo = data.get("modulo")
                manager.modulo_actual = nuevo_modulo
                manager.state = "LOBBY"
                manager.current_question = None

                # Cancelar cualquier tarea de lectura pendiente del módulo anterior
                if manager.reading_task and not manager.reading_task.done():
                    manager.reading_task.cancel()

                await manager.broadcast({
                    "event": "modulo_iniciado",
                    "modulo": nuevo_modulo
                })

            # 13. NUEVO: FINALIZAR EL MÓDULO ACTUAL (vuelve a la pantalla de selección)
            elif action == "finalizar_modulo":
                if manager.reading_task and not manager.reading_task.done():
                    manager.reading_task.cancel()

                manager.modulo_actual = None
                manager.state = "LOBBY"

                await manager.broadcast({
                    "event": "modulo_finalizado",
                    "leaderboard": manager.get_leaderboard()
                })

    except WebSocketDisconnect:
        manager.disconnect(ws)
        await manager.broadcast({
            "event": "player_left",
            "players": manager.get_leaderboard()
        })


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)