let socket = null;
let currentQuestion = null;
let miSalaPin = null;

// Elementos DOM
const txtEstado = document.getElementById("txt-estado");
const txtCategoria = document.getElementById("txt-categoria");
const txtConsigna = document.getElementById("txt-consigna");
const txtSolucion = document.getElementById("txt-solucion");
const txtGanador = document.getElementById("txt-ganador");
const turnoBox = document.getElementById("turno-box");
const txtTotalJugadores = document.getElementById("txt-total-jugadores");
const tablaBody = document.getElementById("tabla-body");

const boxOpcionesHost = document.getElementById("box-opciones-host");
const listaOpcionesHost = document.getElementById("lista-opciones-host");

const txtPinSala = document.getElementById("txt-pin-sala");

const btnLanzar = document.getElementById("btn-siguiente");
const btnLanzarMC = document.getElementById("btn-siguiente-mc");
const btnAbrirBuzzers = document.getElementById("btn-abrir-buzzers");
const btnCorrecto = document.getElementById("btn-correcto");
const btnIncorrecto = document.getElementById("btn-incorrecto");
const btnAnular = document.getElementById("btn-anular");
const btnPodio = document.getElementById("btn-finalizar-juego");
const btnCambiarPin = document.getElementById("btn-cambiar-pin");
const btnVerRanking = document.getElementById("btn-ver-ranking");

btnVerRanking.onclick = () => {
  socket.send(JSON.stringify({ action: "show_leaderboard" }));
};

function obtenerRoomDeLaURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get("room");
}

function conectarHost() {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const roomExistente = obtenerRoomDeLaURL();
  const query = roomExistente ? `?room=${roomExistente}` : "";
  const wsUrl = `${wsProtocol}//${window.location.host}/ws${query}`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    socket.send(JSON.stringify({ action: "register", role: "host" }));
    txtEstado.innerText = "ESTADO: CONECTADO - LISTO PARA JUGAR";
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    procesarEventoHost(data);
  };

  socket.onclose = () => {
    txtEstado.innerText = "ESTADO: DESCONECTADO (REINTENTANDO...)";
    setTimeout(conectarHost, 2000);
  };
}

function actualizarInfoSala(pin) {
  miSalaPin = pin;
  txtPinSala.innerText = pin;

  const nuevaUrl = `${window.location.pathname}?room=${pin}`;
  window.history.replaceState({}, "", nuevaUrl);
}

function procesarEventoHost(data) {
  switch (data.event) {
    case "sync_state":
      if (data.room_pin) actualizarInfoSala(data.room_pin);
      actualizarRanking(data.leaderboard);
      break;

    case "room_reset":
      actualizarInfoSala(data.new_pin);
      txtEstado.innerText = "ESTADO: SALA NUEVA CREADA";
      actualizarRanking([]);
      break;

    case "player_joined":
    case "player_left":
      actualizarRanking(data.players);
      break;

    case "new_question":
      txtCategoria.innerText = data.categoria.toUpperCase();
      txtConsigna.innerText = data.consigna;
      txtSolucion.innerText = data.respuesta_correcta;

      if (data.tipo === "multiple") {
        txtEstado.innerText = "ESTADO: MULTIPLE CHOICE - ESPERANDO RESPUESTAS...";
        turnoBox.className = "turno-box espera";
        txtGanador.innerText = "0 respondieron...";
        btnAbrirBuzzers.disabled = true;
        btnCorrecto.disabled = true;
        btnIncorrecto.disabled = true;

        if (boxOpcionesHost && data.opciones) {
          boxOpcionesHost.style.display = "flex";
          listaOpcionesHost.innerHTML = data.opciones.map((opc, idx) => {
            const letras = ["A", "B", "C", "D"];
            const esCorrecta = (opc === data.respuesta_correcta);
            return `<li style="padding: 6px 10px; border-radius: 6px; background: ${esCorrecta ? '#064e3b' : '#1e294b'}; color: ${esCorrecta ? '#34d399' : '#fff'}; border: 1px solid ${esCorrecta ? '#10b981' : '#334155'}; font-size: 0.9rem;">
              <strong>${letras[idx]}:</strong> ${opc} ${esCorrecta ? '✔' : ''}
            </li>`;
          }).join("");
        }
      } else {
        txtEstado.innerText = "ESTADO: LEYENDO CONSIGNAS (AUTO-ACTIVACIÓN EN 6s)";
        turnoBox.className = "turno-box espera";
        txtGanador.innerText = "ESPERANDO PULSADOR...";
        btnAbrirBuzzers.disabled = false;
        btnCorrecto.disabled = true;
        btnIncorrecto.disabled = true;

        if (boxOpcionesHost) boxOpcionesHost.style.display = "none";
      }
      break;

    case "buzzers_unlocked":
      txtEstado.innerText = "ESTADO: PULSADORES ABIERTOS";
      break;

    case "buzzer_won":
      txtEstado.innerText = `ESTADO: RESPONDIENDO ${data.winner_name.toUpperCase()}`;
      turnoBox.className = "turno-box activo";
      txtGanador.innerText = `🎤 ${data.winner_name.toUpperCase()}`;
      btnCorrecto.disabled = false;
      btnIncorrecto.disabled = false;
      break;

    case "rebote_active":
      txtEstado.innerText = `ESTADO: REBOTE HABILITADO (EXCLUIDO: ${data.excluded_player})`;
      turnoBox.className = "turno-box espera";
      txtGanador.innerText = "ESPERANDO REBOTE...";
      btnCorrecto.disabled = true;
      btnIncorrecto.disabled = true;
      break;

    case "round_result":
      txtEstado.innerText = `ESTADO: RONDA TERMINADA (${data.status})`;
      turnoBox.className = "turno-box espera";
      txtGanador.innerText = "RONDA FINALIZADA";
      txtSolucion.innerText = data.respuesta_correcta || "---";
      btnCorrecto.disabled = true;
      btnIncorrecto.disabled = true;
      if (data.leaderboard) actualizarRanking(data.leaderboard);
      break;

    case "mc_progress":
      txtGanador.innerText = `${data.respondieron} / ${data.total_jugadores} respondieron`;
      break;

    case "mc_result":
      txtEstado.innerText = "ESTADO: RONDA MULTIPLE CHOICE TERMINADA";
      turnoBox.className = "turno-box espera";
      txtGanador.innerText = "RONDA FINALIZADA";
      txtSolucion.innerText = data.respuesta_correcta || "---";
      btnAbrirBuzzers.disabled = false;
      if (data.leaderboard) actualizarRanking(data.leaderboard);
      break;

    case "game_over":
      txtEstado.innerText = "ESTADO: PODIO FINAL MOSTRADO";
      break;
  }
}

function actualizarRanking(lista) {
  if (!lista) return;
  txtTotalJugadores.innerText = `${lista.length} Jugadores`;
  if (lista.length === 0) {
    tablaBody.innerHTML = '<tr><td colspan="3" class="sin-datos">No hay jugadores conectados</td></tr>';
    return;
  }

  tablaBody.innerHTML = lista.map((p, index) => `
    <tr>
      <td>#${index + 1}</td>
      <td>${p.name}</td>
      <td>${p.score} pts</td>
    </tr>
  `).join("");
}

// Mandos del Host
btnLanzar.onclick = () => socket.send(JSON.stringify({ action: "next_question", tipo: "abierta" }));
if (btnLanzarMC) {
  btnLanzarMC.onclick = () => socket.send(JSON.stringify({ action: "next_question", tipo: "multiple" }));
}
btnAbrirBuzzers.onclick = () => socket.send(JSON.stringify({ action: "open_buzzers" }));
btnCorrecto.onclick = () => socket.send(JSON.stringify({ action: "answer_correct" }));
btnIncorrecto.onclick = () => socket.send(JSON.stringify({ action: "answer_incorrect" }));
btnAnular.onclick = () => socket.send(JSON.stringify({ action: "round_null" }));
btnPodio.onclick = () => socket.send(JSON.stringify({ action: "finish_game" }));
btnCambiarPin.onclick = () => {
  if (confirm("¿Seguro que querés crear una sala nueva? Los jugadores actuales quedarán en la sala vieja.")) {
    socket.send(JSON.stringify({ action: "reset_room" }));
  }
};

conectarHost();