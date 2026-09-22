let socket = null;
let readingInterval = null;

const vistaLobby = document.getElementById("vista-lobby");
const vistaJuego = document.getElementById("vista-juego");
const vistaRanking = document.getElementById("vista-ranking");
const vistaPodio = document.getElementById("vista-podio");

const pinTxt = document.getElementById("pin-txt");
const pinMiniTxt = document.getElementById("pin-mini-txt");
const countJugadores = document.getElementById("count-jugadores");
const listaParticipantes = document.getElementById("lista-participantes");

const categoriaTag = document.getElementById("categoria-tag");
const consignaPantalla = document.getElementById("consigna-pantalla");
const barraProgreso = document.getElementById("barra-progreso");
const cartelTurno = document.getElementById("cartel-turno");
const turnoNombre = document.getElementById("turno-nombre");
const leaderboardPantalla = document.getElementById("leaderboard-pantalla");

const opcionesPantalla = document.getElementById("opciones-pantalla");
const opcionItems = Array.from(document.querySelectorAll(".opcion-pantalla-item"));

const qrImg = document.getElementById("qr-img");

const p1Nombre = document.getElementById("podio-p1-nombre");
const p1Pts = document.getElementById("podio-p1-pts");
const p2Nombre = document.getElementById("podio-p2-nombre");
const p2Pts = document.getElementById("podio-p2-pts");
const p3Nombre = document.getElementById("podio-p3-nombre");
const p3Pts = document.getElementById("podio-p3-pts");

function obtenerRoomDeLaURL() {
  const params = new URLSearchParams(window.location.search);
  return params.get("room");
}

function cambiarVista(vistaActiva) {
  [vistaLobby, vistaJuego, vistaRanking, vistaPodio].forEach(v => {
    if (v) v.classList.add("oculta");
  });
  if (vistaActiva) vistaActiva.classList.remove("oculta");
}

function conectarPantalla() {
  const roomPin = obtenerRoomDeLaURL();
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";

  const query = roomPin ? `?room=${roomPin}` : "";
  const wsUrl = `${wsProtocol}//${window.location.host}/ws${query}`;

  if (roomPin && qrImg) {
    qrImg.src = `/api/qr?room=${roomPin}`;
  }

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    socket.send(JSON.stringify({ action: "register", role: "screen" }));
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    procesarEventoPantalla(data);
  };

  socket.onclose = () => {
    setTimeout(conectarPantalla, 2000);
  };
}

function actualizarSalaEnPantalla(nuevoPin) {
  if (pinTxt) pinTxt.innerText = nuevoPin;
  if (pinMiniTxt) pinMiniTxt.innerText = nuevoPin;

  if (qrImg) qrImg.src = `/api/qr?room=${nuevoPin}&t=${Date.now()}`;

  actualizarLobbyJugadores([]);
  window.history.replaceState({}, "", `${window.location.pathname}?room=${nuevoPin}`);
  cambiarVista(vistaLobby);
}

// Limpia textos que tengan letras prefijadas tipo "AWhitney" o "A) Whitney"
function limpiarTextoOpcion(texto) {
  if (!texto) return "";
  return String(texto).replace(/^[A-Da-d][\)\.\:\-\s]+|^[A-Da-d](?=[A-ZÁÉÍÓÚa-záéíóú])/, "").trim();
}

function mostrarOpcionesPantalla(opciones) {
  if (!opcionesPantalla) return;
  opcionesPantalla.classList.remove("oculta");

  opcionItems.forEach((item, i) => {
    item.classList.remove("correcta", "opaca");
    const textoEl = item.querySelector(".opcion-texto");
    if (textoEl) {
      textoEl.innerText = limpiarTextoOpcion(opciones[i] || "");
    }
  });
}

function revelarOpcionesPantalla(respuestaCorrecta) {
  const correctaLimpia = limpiarTextoOpcion(respuestaCorrecta).toLowerCase();

  opcionItems.forEach((item) => {
    const textoEl = item.querySelector(".opcion-texto");
    const valor = textoEl ? textoEl.innerText.trim().toLowerCase() : "";

    if (valor === correctaLimpia) {
      item.classList.add("correcta");
      item.classList.remove("opaca");
    } else {
      item.classList.add("opaca");
      item.classList.remove("correcta");
    }
  });
}

function procesarEventoPantalla(data) {
  switch (data.event) {
    case "sync_screen":
      actualizarSalaEnPantalla(data.room_pin);
      break;

    case "room_reset":
      actualizarSalaEnPantalla(data.new_pin);
      break;

    case "player_joined":
    case "player_left":
      actualizarLobbyJugadores(data.players);
      break;

    case "new_question":
      cambiarVista(vistaJuego);
      cartelTurno.classList.add("oculta");

      categoriaTag.innerText = data.categoria.toUpperCase();
      consignaPantalla.innerText = data.consigna;

      if (data.tipo === "multiple") {
        mostrarOpcionesPantalla(data.opciones || []);
        animarBarra(data.time_limit || 15);
      } else {
        opcionesPantalla.classList.add("oculta");
        animarBarra(data.reading_time || 6);
      }
      break;

    case "buzzers_unlocked":
      detenerBarra();
      break;

    case "buzzer_won":
      detenerBarra();
      turnoNombre.innerText = data.winner_name.toUpperCase();
      cartelTurno.classList.remove("oculta");
      break;

    case "rebote_active":
      turnoNombre.innerText = "¡REBOTE! ¿QUIÉN LA ROBA?";
      cartelTurno.classList.remove("oculta");
      animarBarra(data.rebote_time || 7);
      break;

    case "round_result":
      cartelTurno.classList.add("oculta");
      if (data.status === "correct") {
        consignaPantalla.innerText = `¡PUNTO PARA ${data.winner_name.toUpperCase()}! Era: ${limpiarTextoOpcion(data.respuesta_correcta)}`;
      } else {
        consignaPantalla.innerText = `Ronda finalizada. Era: ${limpiarTextoOpcion(data.respuesta_correcta)}`;
      }
      break;

    case "mc_result":
      detenerBarra();
      revelarOpcionesPantalla(data.respuesta_correcta);
      consignaPantalla.innerText = `¡RESPUESTA CORRECTA: ${limpiarTextoOpcion(data.respuesta_correcta).toUpperCase()}!`;
      break;

    case "show_leaderboard":
      cambiarVista(vistaRanking);
      renderLeaderboardCompleto(data.leaderboard || []);
      break;

    case "game_over":
      cambiarVista(vistaPodio);
      const podium = data.podium || data.full_ranking || [];

      if (podium.length > 0 && podium[0]) {
        p1Nombre.innerText = podium[0].name.toUpperCase();
        p1Pts.innerText = `${podium[0].score} pts`;
      } else {
        p1Nombre.innerText = "VACÍO";
        p1Pts.innerText = "0 pts";
      }

      if (podium.length > 1 && podium[1]) {
        p2Nombre.innerText = podium[1].name.toUpperCase();
        p2Pts.innerText = `${podium[1].score} pts`;
      } else {
        p2Nombre.innerText = "---";
        p2Pts.innerText = "0 pts";
      }

      if (podium.length > 2 && podium[2]) {
        p3Nombre.innerText = podium[2].name.toUpperCase();
        p3Pts.innerText = `${podium[2].score} pts`;
      } else {
        p3Nombre.innerText = "---";
        p3Pts.innerText = "0 pts";
      }
      break;
  }
}

function actualizarLobbyJugadores(players) {
  if (!players) return;
  countJugadores.innerText = players.length;
  listaParticipantes.innerHTML = players.map(p => `
    <div class="badge-jugador">👤 ${p.name}</div>
  `).join("");
}

function renderLeaderboardCompleto(leaderboard) {
  if (!leaderboardPantalla) return;
  leaderboardPantalla.innerHTML = leaderboard.map((p, index) => `
    <li class="ranking-item ${index === 0 ? 'top-1' : ''}">
      <span>#${index + 1} &nbsp; <strong>${p.name.toUpperCase()}</strong></span>
      <span class="puntos">${p.score} pts</span>
    </li>
  `).join("");
}

function animarBarra(segundos) {
  clearInterval(readingInterval);
  let restante = segundos * 10;
  const total = restante;
  barraProgreso.style.width = "100%";

  readingInterval = setInterval(() => {
    restante--;
    const pct = (restante / total) * 100;
    barraProgreso.style.width = `${pct}%`;
    if (restante <= 0) clearInterval(readingInterval);
  }, 100);
}

function detenerBarra() {
  clearInterval(readingInterval);
  barraProgreso.style.width = "0%";
}

conectarPantalla();