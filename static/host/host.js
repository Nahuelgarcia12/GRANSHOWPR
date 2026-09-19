let socket = null;
let currentQuestion = null;

// Elementos DOM
const txtEstado = document.getElementById("txt-estado");
const txtCategoria = document.getElementById("txt-categoria");
const txtConsigna = document.getElementById("txt-consigna");
const txtSolucion = document.getElementById("txt-solucion");
const txtGanador = document.getElementById("txt-ganador");
const turnoBox = document.getElementById("turno-box");
const txtTotalJugadores = document.getElementById("txt-total-jugadores");
const tablaBody = document.getElementById("tabla-body");

const btnLanzar = document.getElementById("btn-siguiente");
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

// Conectar con el WebSocket del backend
function conectarHost() {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

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

// Escuchador de eventos del servidor
function procesarEventoHost(data) {
  switch (data.event) {
    case "player_joined":
    case "player_left":
      actualizarRanking(data.players);
      break;

    case "sync_state":
      txtEstado.innerText = `ESTADO: ${data.state}`;
      actualizarRanking(data.leaderboard);
      break;

   case "new_question":
      txtEstado.innerText = "ESTADO: LEYENDO CONSIGNAS (AUTO-ACTIVACIÓN EN 6s)";
      txtCategoria.innerText = data.categoria.toUpperCase();
      txtConsigna.innerText = data.consigna; // Muestra la pregunta
      txtSolucion.innerText = data.respuesta_correcta; // Muestra la solución al host
      turnoBox.className = "turno-box espera";
      txtGanador.innerText = "ESPERANDO PULSADOR...";
      btnCorrecto.disabled = true;
      btnIncorrecto.disabled = true;
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
btnLanzar.onclick = () => socket.send(JSON.stringify({ action: "next_question" }));
btnAbrirBuzzers.onclick = () => socket.send(JSON.stringify({ action: "open_buzzers" }));
btnCorrecto.onclick = () => socket.send(JSON.stringify({ action: "answer_correct" }));
btnIncorrecto.onclick = () => socket.send(JSON.stringify({ action: "answer_incorrect" }));
btnAnular.onclick = () => socket.send(JSON.stringify({ action: "round_null" }));
btnPodio.onclick = () => socket.send(JSON.stringify({ action: "finish_game" }));
btnCambiarPin.onclick = () => {
  if (confirm("¿Seguro que querés cambiar el PIN? Esto desconectará a los jugadores actuales.")) {
    socket.send(JSON.stringify({ action: "reset_room" }));
  }
};

// Iniciar al cargar
conectarHost();