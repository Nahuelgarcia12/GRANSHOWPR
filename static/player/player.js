let socket = null;
let playerName = "";
let roomPin = "";
let currentScore = 0;
let readingInterval = null;

let preguntaActualTipo = "abierta";
let opcionSeleccionada = null;
let yaRespondioMC = false;

const screenLogin = document.getElementById("pantalla-login");
const screenGame = document.getElementById("pantalla-juego");
const formLogin = document.getElementById("form-login");
const inputNombre = document.getElementById("input-nombre");
const inputPin = document.getElementById("input-pin");
const loginError = document.getElementById("login-error");

const txtName = document.getElementById("player-name");
const txtScore = document.getElementById("player-score");
const badgeCat = document.getElementById("badge-categoria");
const readingMsg = document.getElementById("reading-msg");
const readingBar = document.getElementById("reading-bar");

const buzzerWrapper = document.getElementById("buzzer-wrapper");
const buzzerBtn = document.getElementById("buzzer-btn");

const opcionesWrapper = document.getElementById("opciones-wrapper");
const opcionBtns = Array.from(document.querySelectorAll(".opcion-btn"));

const boxPregunta = document.getElementById("pregunta-player-box");
const playerQuestionTxt = document.getElementById("player-question-txt");

const fbCard = document.getElementById("feedback-card");
const fbIcon = document.getElementById("feedback-icon");
const fbTitle = document.getElementById("feedback-title");
const fbSub = document.getElementById("feedback-sub");

const displayRoomPin = document.getElementById("display-room-pin");

function obtenerRoomDeLaURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get("room");
}

async function precargarRoomDesdeURL() {
  let room = obtenerRoomDeLaURL();

  if (!room) {
    try {
      const resp = await fetch("/api/sala-activa");
      if (resp.ok) {
        const data = await resp.json();
        if (data.room_pin) {
          room = data.room_pin;
        }
      }
    } catch (e) {
      console.warn("No se pudo autodetectar la sala activa:", e);
    }
  }

  if (room) {
    if (displayRoomPin) displayRoomPin.innerText = room;
    if (inputPin) inputPin.value = room;
  } else {
    if (displayRoomPin) displayRoomPin.innerText = "----";
  }

  if (inputNombre) inputNombre.focus();
}

precargarRoomDesdeURL();

formLogin.addEventListener("submit", (e) => {
  e.preventDefault();
  playerName = inputNombre.value.trim();
  roomPin = inputPin.value.trim();
  loginError.classList.add("oculta");

  if (!playerName || !roomPin) return;

  iniciarConexion();
});

function iniciarConexion() {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    socket.send(JSON.stringify({
      action: "register",
      role: "player",
      name: playerName,
      pin: roomPin
    }));
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.event === "auth_ok") {
      solicitarWakeLock();
      screenLogin.classList.add("oculta");
      screenGame.classList.remove("oculta");
      txtName.innerText = playerName;
      return;
    }

    if (data.event === "auth_error") {
      loginError.innerText = data.message || "Código incorrecto";
      loginError.classList.remove("oculta");
      socket.close();
      return;
    }

    procesarEvento(data);
  };

  socket.onerror = () => {
    loginError.innerText = "Error al conectar con el servidor.";
    loginError.classList.remove("oculta");
  };

  socket.onclose = () => {
    if (!screenGame.classList.contains("oculta")) {
      setFeedback("perdiste", "❌", "DESCONECTADO", "Se perdió el enlace con el show.");
      bloquearBuzzer();
    }
  };
}

// Acción del pulsador (preguntas abiertas)
buzzerBtn.addEventListener("pointerdown", () => {
  if (buzzerBtn.disabled) return;
  socket.send(JSON.stringify({ action: "press_buzzer" }));
  if (navigator.vibrate) navigator.vibrate(80);
});

// Acción de votar una opción en el celular (multiple choice)
opcionBtns.forEach((btn) => {
  btn.addEventListener("pointerdown", () => {
    if (yaRespondioMC || btn.disabled) return;

    const textoSpan = btn.querySelector(".opcion-texto");
    opcionSeleccionada = textoSpan ? textoSpan.innerText.trim() : btn.innerText.trim();
    yaRespondioMC = true;

    opcionBtns.forEach((b) => {
      b.disabled = true;
      b.classList.remove("seleccionada");
    });
    btn.classList.add("seleccionada");

    socket.send(JSON.stringify({ action: "submit_answer", selected: opcionSeleccionada }));
    if (navigator.vibrate) navigator.vibrate(60);

    setFeedback("ganaste", "🗳️", "¡VOTO REGISTRADO!", "Esperando que termine el tiempo...");
  });
});

function procesarEvento(data) {
  switch (data.event) {

    case "new_question":
      preguntaActualTipo = data.tipo || "abierta";
      badgeCat.innerText = data.categoria.toUpperCase();
      playerQuestionTxt.innerText = data.consigna;
      boxPregunta.classList.remove("oculta");
      fbCard.classList.add("oculta");

      if (preguntaActualTipo === "multiple") {
        mostrarModoMultiple(data.opciones || [], data.time_limit || 15);
      } else {
        mostrarModoAbierta(data.reading_time || 6);
      }
      break;

    case "buzzers_unlocked":
      detenerBarra();
      desbloquearBuzzer();
      fbCard.classList.add("oculta");
      break;

    case "buzzer_won":
      bloquearBuzzer();
      if (data.winner_name === playerName) {
        if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
        setFeedback("ganaste", "🎤", "¡TENÉS LA PALABRA!", "Respondé por el micrófono ahora.");
      } else {
        setFeedback("perdiste", "🛑", `PULSÓ ${data.winner_name.toUpperCase()}`, "Esperá la resolución.");
      }
      break;

    case "rebote_active":
      if (data.excluded_player === playerName) {
        bloquearBuzzer();
        setFeedback("perdiste", "🚫", "FUERA DE RONDA", "Erraste en la respuesta previa.");
      } else {
        desbloquearBuzzer();
        setFeedback("ganaste", "↩️", "¡REBOTE ACTIVO!", "¡Pulsá rápido para robar el punto!");
      }
      break;

    case "round_result":
      bloquearBuzzer();
      cerrarRonda();

      if (data.leaderboard) actualizarScorePropio(data.leaderboard);

      fbCard.classList.add("oculta");
      readingMsg.innerText = "Esperando la próxima pregunta...";
      break;

    case "mc_result":
      detenerBarra();
      revelarResultadoMC(data.respuesta_correcta);
      cerrarRonda();

      if (data.leaderboard) actualizarScorePropio(data.leaderboard);

      const puntosGanados = (data.puntos_ronda && data.puntos_ronda[playerName]) || 0;

      if (opcionSeleccionada === null) {
        setFeedback("perdiste", "⌛", "NO RESPONDIÓ", `La correcta era: ${data.respuesta_correcta}`);
      } else if (opcionSeleccionada === data.respuesta_correcta) {
        if (navigator.vibrate) navigator.vibrate([80, 40, 80]);
        setFeedback("ganaste", "✅", `¡CORRECTO! +${puntosGanados} pts`, "Puntos sumados a tu marcador.");
      } else {
        setFeedback("perdiste", "❌", "RESPUESTA INCORRECTA", `La correcta era: ${data.respuesta_correcta}`);
      }
      break;

    case "game_over":
      bloquearBuzzer();
      if (boxPregunta) boxPregunta.classList.add("oculta");
      badgeCat.innerText = "FIN DEL SHOW";

      const ranking = data.full_ranking || [];
      const posicion = ranking.findIndex(p => p.name === playerName) + 1;

      if (posicion === 1) {
        setFeedback("ganaste", "👑", "¡SOS EL CAMPEÓN!", `Ganaste el show con ${currentScore} pts.`);
      } else if (posicion > 1 && posicion <= 3) {
        setFeedback("ganaste", "🥈", `¡ENTRASTE AL PODIO! (#${posicion})`, `Gran partida. Terminaste con ${currentScore} pts.`);
      } else if (posicion > 3) {
        setFeedback("estado-espera", "🎖️", `PUESTO #${posicion}`, `Completaste el juego con ${currentScore} pts.`);
      } else {
        setFeedback("ganaste", "🏆", "¡FIN DEL JUEGO!", "Mirá el podio en la pantalla principal.");
      }
      break;
  }
}

function mostrarModoAbierta(segundos) {
  if (opcionesWrapper) opcionesWrapper.classList.add("oculta");
  if (buzzerWrapper) buzzerWrapper.classList.remove("oculta");
  bloquearBuzzer();
  animarBarra(segundos, "Leyendo consigna...", "¡Pulsadores abiertos!");
}

function mostrarModoMultiple(opciones, segundos) {
  if (buzzerWrapper) buzzerWrapper.classList.add("oculta");
  if (opcionesWrapper) opcionesWrapper.classList.remove("oculta");

  opcionSeleccionada = null;
  yaRespondioMC = false;

  opcionBtns.forEach((btn, i) => {
    const txtSpan = btn.querySelector(".opcion-texto");
    if (txtSpan) txtSpan.innerText = opciones[i] || "";
    btn.disabled = false;
    btn.classList.remove("seleccionada", "correcta", "incorrecta");
  });

  animarBarra(segundos, "¡Elegí tu respuesta!", "¡Tiempo agotado!");
}

function revelarResultadoMC(respuestaCorrecta) {
  opcionBtns.forEach((btn) => {
    btn.disabled = true;
    const txtSpan = btn.querySelector(".opcion-texto");
    const valor = txtSpan ? txtSpan.innerText.trim() : btn.innerText.trim();

    if (valor === respuestaCorrecta.trim()) {
      btn.classList.add("correcta");
    } else if (btn.classList.contains("seleccionada")) {
      btn.classList.add("incorrecta");
    }
  });
}

function cerrarRonda() {
  boxPregunta.classList.add("oculta");
  badgeCat.innerText = "SALA CONECTADA";
}

function actualizarScorePropio(leaderboard) {
  const yo = leaderboard.find(p => p.name === playerName);
  if (yo) {
    currentScore = yo.score;
    txtScore.innerText = `⭐ ${currentScore} pts`;
  }
}

function animarBarra(segundos, mensajeInicial, mensajeFinal) {
  clearInterval(readingInterval);
  readingMsg.innerText = mensajeInicial;
  let restante = segundos * 10;
  const total = restante;

  readingBar.style.width = "100%";

  readingInterval = setInterval(() => {
    restante--;
    const pct = (restante / total) * 100;
    readingBar.style.width = `${pct}%`;

    if (restante <= 0) {
      clearInterval(readingInterval);
      readingMsg.innerText = mensajeFinal;
    }
  }, 100);
}

function detenerBarra() {
  clearInterval(readingInterval);
  readingBar.style.width = "0%";
}

function desbloquearBuzzer() {
  buzzerBtn.disabled = false;
  buzzerBtn.classList.remove("disabled");
  buzzerBtn.classList.add("active");
}

function bloquearBuzzer() {
  buzzerBtn.disabled = true;
  buzzerBtn.classList.add("disabled");
  buzzerBtn.classList.remove("active");
}

function setFeedback(clase, icono, titulo, sub) {
  fbCard.className = `feedback-card ${clase}`;
  fbIcon.innerText = icono;
  fbTitle.innerText = titulo;
  fbSub.innerText = sub;
  fbCard.classList.remove("oculta");
}

async function solicitarWakeLock() {
  try {
    if ('wakeLock' in navigator) {
      await navigator.wakeLock.request('screen');
    }
  } catch (err) {}
}