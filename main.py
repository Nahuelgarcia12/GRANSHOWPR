import json
import asyncio
import random
import time
import io
from typing import Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import qrcode
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
    # El banco de preguntas es compartido por todas las salas (no es por evento).
    nuevo_id = insert_question(
        data.consigna, data.respuesta_correcta, data.categoria, data.tipo, data.opciones
    )
    return {"status": "ok", "id": nuevo_id, "mensaje": "Pregunta guardada"}


# --- UNA SALA = UNA PARTIDA/EVENTO, CON SU PROPIO ESTADO AISLADO ---
class GameManager:
    def __init__(self, room_pin: str):
        self.room_pin: str = room_pin
        self.connections: List[WebSocket] = []
        self.players: Dict[WebSocket, dict] = {}
        self.host_socket: Optional[WebSocket] = None
        self.screen_socket: Optional[WebSocket] = None

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
        self.mc_round_start: Optional[float] = None

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
        """Manda el mismo mensaje a TODOS los conectados de ESTA sala (host, screen, jugadores)."""
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
            p["mc_elapsed"] = None

    # ---------- LÓGICA PREGUNTAS ABIERTAS (pulsador) ----------
    async def auto_open_buzzers(self, seconds: int = 6):
        try:
            await asyncio.sleep(seconds)
            if self.state == "READING":
                self.state = "BUZZER_OPEN"
                await self.broadcast({"event": "buzzers_unlocked", "time_limit": 10})
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

    def calcular_puntos_mc(self, elapsed: float) -> int:
        """10 a 20 puntos según velocidad de respuesta. Mínimo garantizado: 10."""
        if elapsed is None:
            elapsed = self.mc_time_limit
        fraccion_restante = max(0.0, 1 - (elapsed / self.mc_time_limit))
        bonus_velocidad = round(10 * fraccion_restante)
        return 10 + bonus_velocidad

    async def reveal_mc_results(self):
        if not self.current_question:
            return

        correcta = self.current_question["respuesta_correcta"]
        conteo_opciones: Dict[str, int] = {}
        puntos_ronda: Dict[str, int] = {}

        for p in self.players.values():
            elegida = p.get("mc_answer")
            if elegida is not None:
                conteo_opciones[elegida] = conteo_opciones.get(elegida, 0) + 1
                if elegida == correcta:
                    ganados = self.calcular_puntos_mc(p.get("mc_elapsed"))
                    p["score"] += ganados
                    puntos_ronda[p["name"]] = ganados

        self.state = "ROUND_OVER"
        await self.broadcast({
            "event": "mc_result",
            "respuesta_correcta": correcta,
            "conteo_opciones": conteo_opciones,
            "puntos_ronda": puntos_ronda,
            "leaderboard": self.get_leaderboard()
        })


# --- REGISTRO DE SALAS ACTIVAS (esto es lo que habilita multi-sala) ---
class RoomRegistry:
    def __init__(self):
        self.rooms: Dict[str, GameManager] = {}

    def generar_pin_unico(self) -> str:
        while True:
            pin = str(random.randint(1000, 9999))
            if pin not in self.rooms:
                return pin

    def crear_sala(self) -> GameManager:
        pin = self.generar_pin_unico()
        sala = GameManager(pin)
        self.rooms[pin] = sala
        return sala

    def obtener_sala(self, pin: str) -> Optional[GameManager]:
        return self.rooms.get(pin)

    def eliminar_sala_si_vacia(self, pin: str):
        """Si una sala se queda sin nadie conectado (host, screen y jugadores),
        la limpiamos para no acumular memoria con salas fantasma."""
        sala = self.rooms.get(pin)
        if sala and not sala.connections:
            del self.rooms[pin]


registry = RoomRegistry()


@app.get("/api/qr")
def generar_qr(request: Request, room: str):
    """
    Genera un QR que apunta directo a la sala indicada, usando la misma
    dirección (IP local o dominio) que el navegador usó para pedir esta
    página. El jugador que escanea entra directo a esa sala, sin tener
    que tipear el PIN a mano.
    """
    host = request.headers.get("host")
    esquema = "https" if request.url.scheme == "https" else "http"
    player_url = f"{esquema}://{host}/static/player/?room={room}"

    img = qrcode.make(player_url)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return StreamingResponse(buffer, media_type="image/png")


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()

    # Si la URL trae ?room=XXXX (por ejemplo, el host recargó la página, o la
    # pantalla/jugador llegaron con un link que ya incluye la sala), lo usamos.
    room_param = ws.query_params.get("room")
    sala: Optional[GameManager] = None

    try:
        while True:
            text_data = await ws.receive_text()
            data = json.loads(text_data)
            action = data.get("action")

            # 1. IDENTIFICACIÓN Y AUTENTICACIÓN (acá es donde se elige/crea la sala)
            if action == "register":
                role = data.get("role")

                if role == "host":
                    # Si la URL ya traía una sala activa válida, reconectamos ahí
                    # (por ejemplo, recargó la página sin querer). Si no, sala nueva.
                    existente = registry.obtener_sala(room_param) if room_param else None
                    sala = existente or registry.crear_sala()

                    sala.connections.append(ws)
                    sala.host_socket = ws

                    await ws.send_text(json.dumps({
                        "event": "sync_state",
                        "room_pin": sala.room_pin,
                        "state": sala.state,
                        "modulo_actual": sala.modulo_actual,
                        "leaderboard": sala.get_leaderboard()
                    }))

                elif role == "screen":
                    if not room_param:
                        await ws.send_text(json.dumps({
                            "event": "auth_error",
                            "message": "Falta el código de sala en el link de la pantalla."
                        }))
                        continue

                    sala = registry.obtener_sala(room_param)
                    if not sala:
                        await ws.send_text(json.dumps({
                            "event": "auth_error",
                            "message": "Esa sala ya no existe. Pedile al host el link actualizado."
                        }))
                        continue

                    sala.connections.append(ws)
                    sala.screen_socket = ws

                    await ws.send_text(json.dumps({
                        "event": "sync_screen",
                        "room_pin": sala.room_pin,
                        "state": sala.state,
                        "modulo_actual": sala.modulo_actual,
                        "leaderboard": sala.get_leaderboard()
                    }))

                elif role == "player":
                    pin_ingresado = str(data.get("pin", "")).strip()
                    encontrada = registry.obtener_sala(pin_ingresado)

                    if not encontrada:
                        await ws.send_text(json.dumps({
                            "event": "auth_error",
                            "message": "Código incorrecto o la sala ya no está activa."
                        }))
                        continue

                    sala = encontrada
                    name = data.get("name", "Anónimo").strip()
                    sala.connections.append(ws)
                    sala.players[ws] = {
                        "name": name,
                        "score": 0,
                        "blocked_this_round": False,
                        "mc_answer": None,
                        "mc_elapsed": None
                    }
                    await ws.send_text(json.dumps({"event": "auth_ok"}))
                    await sala.broadcast({
                        "event": "player_joined",
                        "players": sala.get_leaderboard()
                    })

                continue  # el resto de las acciones necesita ya tener `sala` asignada

            # A partir de acá, todas las acciones son sobre la sala ya identificada.
            if sala is None:
                continue

            # 2. REINICIAR SALA (CAMBIO DE PIN): en multi-sala esto no tiene sentido
            # tal como antes (¿"la" sala? ¿cuál?). Lo reemplazamos por "crear sala nueva"
            # desde cero para este host, dejando la vieja disponible hasta que quede vacía.
            if action == "reset_room":
                vieja = sala
                nueva = registry.crear_sala()
                nueva.connections.append(ws)
                nueva.host_socket = ws
                if vieja.host_socket == ws:
                    vieja.host_socket = None
                if ws in vieja.connections:
                    vieja.connections.remove(ws)
                registry.eliminar_sala_si_vacia(vieja.room_pin)
                sala = nueva
                await ws.send_text(json.dumps({
                    "event": "room_reset",
                    "new_pin": sala.room_pin
                }))

            # 3. LANZAR PREGUNTA (abierta O multiple choice, según 'tipo')
            elif action == "next_question":
                if not sala.questions_queue:
                    sala.questions_queue = get_random_questions(limit=30)

                if sala.reading_task and not sala.reading_task.done():
                    sala.reading_task.cancel()
                if sala.mc_deadline_task and not sala.mc_deadline_task.done():
                    sala.mc_deadline_task.cancel()

                sala.current_question = sala.questions_queue.pop(0)
                sala.buzzer_winner = None
                sala.rebote_disponible = True
                sala.reset_player_round_state()

                tipo = sala.current_question.get("tipo", "abierta")

                if tipo == "multiple":
                    opciones = sala.current_question.get("opciones") or []
                    opciones_mezcladas = opciones.copy()
                    random.shuffle(opciones_mezcladas)

                    sala.state = "MC_OPEN"

                    await sala.broadcast_split(
                        data_public={
                            "event": "new_question",
                            "tipo": "multiple",
                            "categoria": sala.current_question["categoria"],
                            "consigna": sala.current_question["consigna"],
                            "opciones": opciones_mezcladas,
                            "time_limit": sala.mc_time_limit
                        },
                        data_host_extra={
                            "respuesta_correcta": sala.current_question["respuesta_correcta"]
                        }
                    )

                    sala.mc_round_start = time.time()
                    sala.mc_deadline_task = asyncio.create_task(
                        sala.auto_reveal_mc(sala.mc_time_limit)
                    )

                else:
                    sala.state = "READING"
                    await sala.broadcast_split(
                        data_public={
                            "event": "new_question",
                            "tipo": "abierta",
                            "categoria": sala.current_question["categoria"],
                            "consigna": sala.current_question["consigna"],
                            "reading_time": 6
                        },
                        data_host_extra={
                            "respuesta_correcta": sala.current_question["respuesta_correcta"]
                        }
                    )
                    sala.reading_task = asyncio.create_task(sala.auto_open_buzzers(6))

            # 4. ABRIR PULSADORES ANTES DE TIEMPO (solo preguntas abiertas)
            elif action == "open_buzzers":
                if sala.state == "READING":
                    if sala.reading_task and not sala.reading_task.done():
                        sala.reading_task.cancel()
                    sala.state = "BUZZER_OPEN"
                    await sala.broadcast({"event": "buzzers_unlocked", "time_limit": 10})

            # 5. PULSADOR PRESIONADO (solo preguntas abiertas)
            elif action == "press_buzzer":
                if sala.state == "BUZZER_OPEN":
                    player = sala.players.get(ws)
                    if player and not player["blocked_this_round"]:
                        sala.state = "ANSWERING"
                        sala.buzzer_winner = player["name"]
                        await sala.broadcast({
                            "event": "buzzer_won",
                            "winner_name": player["name"],
                            "speaking_time": 10
                        })

            # 5b. RESPUESTA DE MULTIPLE CHOICE (todos responden a la vez)
            elif action == "submit_answer":
                if sala.state == "MC_OPEN":
                    player = sala.players.get(ws)
                    if player and player["mc_answer"] is None:
                        selected = data.get("selected")
                        player["mc_answer"] = selected
                        player["mc_elapsed"] = time.time() - (sala.mc_round_start or time.time())

                        respondieron = sum(
                            1 for p in sala.players.values() if p["mc_answer"] is not None
                        )
                        await sala.broadcast({
                            "event": "mc_progress",
                            "respondieron": respondieron,
                            "total_jugadores": len(sala.players)
                        })

                        if sala.players and respondieron == len(sala.players):
                            if sala.mc_deadline_task and not sala.mc_deadline_task.done():
                                sala.mc_deadline_task.cancel()
                            await sala.reveal_mc_results()

            # 6. RESPUESTA CORRECTA (solo preguntas abiertas)
            elif action == "answer_correct":
                if sala.state == "ANSWERING":
                    for p in sala.players.values():
                        if p["name"] == sala.buzzer_winner:
                            p["score"] += 10
                            break

                    sala.state = "ROUND_OVER"
                    await sala.broadcast({
                        "event": "round_result",
                        "status": "correct",
                        "winner_name": sala.buzzer_winner,
                        "respuesta_correcta": sala.current_question["respuesta_correcta"],
                        "leaderboard": sala.get_leaderboard()
                    })

            # 7. RESPUESTA INCORRECTA (solo preguntas abiertas)
            elif action == "answer_incorrect":
                if sala.state == "ANSWERING":
                    for p in sala.players.values():
                        if p["name"] == sala.buzzer_winner:
                            p["blocked_this_round"] = True
                            break

                    if sala.rebote_disponible:
                        sala.rebote_disponible = False
                        sala.state = "BUZZER_OPEN"
                        await sala.broadcast({
                            "event": "rebote_active",
                            "excluded_player": sala.buzzer_winner,
                            "rebote_time": 7
                        })
                    else:
                        sala.state = "ROUND_OVER"
                        await sala.broadcast({
                            "event": "round_result",
                            "status": "null_round",
                            "respuesta_correcta": sala.current_question["respuesta_correcta"],
                            "leaderboard": sala.get_leaderboard()
                        })

            # 8. ANULAR RONDA
            elif action == "round_null":
                if sala.reading_task and not sala.reading_task.done():
                    sala.reading_task.cancel()
                if sala.mc_deadline_task and not sala.mc_deadline_task.done():
                    sala.mc_deadline_task.cancel()
                sala.state = "ROUND_OVER"
                await sala.broadcast({
                    "event": "round_result",
                    "status": "null_round",
                    "respuesta_correcta": sala.current_question["respuesta_correcta"] if sala.current_question else "",
                    "leaderboard": sala.get_leaderboard()
                })

            # 9. MOSTRAR TABLA DE POSICIONES A DEMANDA
            elif action == "show_leaderboard":
                sala.state = "LEADERBOARD"
                await sala.broadcast({
                    "event": "show_leaderboard",
                    "leaderboard": sala.get_leaderboard()
                })

            # 10. PODIO FINAL
            elif action == "finish_game":
                sala.state = "PODIUM"
                await sala.broadcast({
                    "event": "game_over",
                    "podium": sala.get_leaderboard()[:3],
                    "full_ranking": sala.get_leaderboard()
                })

    except WebSocketDisconnect:
        if sala:
            sala.disconnect(ws)
            await sala.broadcast({
                "event": "player_left",
                "players": sala.get_leaderboard()
            })
            registry.eliminar_sala_si_vacia(sala.room_pin)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)