let socket = null;
let playerName = "";
let roomPin = "";
let currentScore = 0;
let readingInterval = null;

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
const buzzerBtn = document.getElementById("buzzer-btn");

const boxPregunta = document.getElementById("pregunta-player-box");
const playerQuestionTxt = document.getElementById("player-question-txt");

const fbCard = document.getElementById("feedback-card");
const fbIcon = document.getElementById("feedback-icon");
const fbTitle = document.getElementById("feedback-title");
const fbSub = document.getElementById("feedback-sub");

const displayRoomPin = document.getElementById("display-room-pin");

// 1. CARGA INMEDIATA DEL PIN AL ABRIR LA PÁGINA
async function obtenerPinActivo() {
  try {
    const res = await fetch("/api/pin?t=" + Date.now());
    const data = await res.json();
    if (data && data.pin) {
      if (displayRoomPin) displayRoomPin.innerText = data.pin;
      if (inputPin) inputPin.value = data.pin;
      if (inputNombre) inputNombre.focus();
    }
  } catch (err) {
    if (displayRoomPin) displayRoomPin.innerText = "----";
  }
}

// Ejecutar inmediatamente
obtenerPinActivo();

// 2. INGRESO A LA SALA
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

// 3. ACCIÓN DEL PULSADOR
buzzerBtn.addEventListener("pointerdown", () => {
  if (buzzerBtn.disabled) return;
  socket.send(JSON.stringify({ action: "press_buzzer" }));
  if (navigator.vibrate) navigator.vibrate(80);
});

// 4. EVENTOS EN VIVO
function procesarEvento(data) {
  switch (data.event) {

    case "new_question":
      badgeCat.innerText = data.categoria.toUpperCase();
      playerQuestionTxt.innerText = data.consigna;
      boxPregunta.classList.remove("oculta");
      fbCard.classList.add("oculta");
      bloquearBuzzer();
      animarBarraLectura(data.reading_time || 6);
      break;

    case "buzzers_unlocked":
      detenerBarraLectura();
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
      boxPregunta.classList.add("oculta");
      badgeCat.innerText = "SALA CONECTADA";

      if (data.leaderboard) {
        const yo = data.leaderboard.find(p => p.name === playerName);
        if (yo) {
          currentScore = yo.score;
          txtScore.innerText = `⭐ ${currentScore} pts`;
        }
      }

      fbCard.classList.add("oculta");
      readingMsg.innerText = "Esperando la próxima pregunta...";
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

// 5. HELPERS
function animarBarraLectura(segundos) {
  clearInterval(readingInterval);
  readingMsg.innerText = "Leyendo consigna...";
  let restante = segundos * 10;
  const total = restante;

  readingBar.style.width = "100%";

  readingInterval = setInterval(() => {
    restante--;
    const pct = (restante / total) * 100;
    readingBar.style.width = `${pct}%`;

    if (restante <= 0) {
      clearInterval(readingInterval);
      readingMsg.innerText = "¡Pulsadores abiertos!";
    }
  }, 100);
}

function detenerBarraLectura() {
  clearInterval(readingInterval);
  readingBar.style.width = "0%";
  readingMsg.innerText = "¡Pulsadores abiertos!";
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