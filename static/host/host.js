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

const txtPinSala = document.getElementById("txt-pin-sala");
const inputLinkPantalla = document.getElementById("input-link-pantalla");
const btnCopiarLink = document.getElementById("btn-copiar-link");

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

btnCopiarLink.onclick = () => {
  inputLinkPantalla.select();
  navigator.clipboard.writeText(inputLinkPantalla.value).then(() => {
    btnCopiarLink.innerText = "✅ COPIADO";
    setTimeout(() => { btnCopiarLink.innerText = "📋 COPIAR"; }, 1500);
  }).catch(() => {
    // Si el navegador bloquea el clipboard (ej. sin HTTPS), al menos queda seleccionado.
  });
};

// Si el panel se recarga con ?room=XXXX en su propia URL, reconectamos a esa
// misma sala en vez de crear una nueva sin querer.
function obtenerRoomDeLaURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get("room");
}

// Conectar con el WebSocket del backend
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

  // Dejamos la sala guardada en la propia URL del host, para poder
  // recargar la página sin perder la partida en curso.
  const nuevaUrl = `${window.location.pathname}?room=${pin}`;
  window.history.replaceState({}, "", nuevaUrl);

  const linkPantalla = `${window.location.origin}/static/screen/?room=${pin}`;
  inputLinkPantalla.value = linkPantalla;
}

// Escuchador de eventos del servidor
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
      } else {
        txtEstado.innerText = "ESTADO: LEYENDO CONSIGNAS (AUTO-ACTIVACIÓN EN 6s)";
        turnoBox.className = "turno-box espera";
        txtGanador.innerText = "ESPERANDO PULSADOR...";
        btnAbrirBuzzers.disabled = false;
        btnCorrecto.disabled = true;
        btnIncorrecto.disabled = true;
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
btnLanzar.onclick = () => socket.send(JSON.stringify({ action: "next_question" }));
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

// Iniciar al cargar
conectarHost();