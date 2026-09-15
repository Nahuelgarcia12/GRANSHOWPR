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

const p1Nombre = document.getElementById("podio-p1-nombre");
const p1Pts = document.getElementById("podio-p1-pts");
const p2Nombre = document.getElementById("podio-p2-nombre");
const p2Pts = document.getElementById("podio-p2-pts");
const p3Nombre = document.getElementById("podio-p3-nombre");
const p3Pts = document.getElementById("podio-p3-pts");

async function obtenerPin() {
  try {
    const res = await fetch("/api/pin?t=" + Date.now());
    const data = await res.json();
    if (data && data.pin) {
      if (pinTxt) pinTxt.innerText = data.pin;
      if (pinMiniTxt) pinMiniTxt.innerText = data.pin;
    }
  } catch (e) {}
}

function conectarPantalla() {
  const wsProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

  socket = new WebSocket(wsUrl);

  socket.onopen = () => {
    socket.send(JSON.stringify({ action: "register", role: "screen" }));
    obtenerPin();
  };

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    procesarEventoPantalla(data);
  };

  socket.onclose = () => {
    setTimeout(conectarPantalla, 2000);
  };
}

function cambiarVista(vistaActiva) {
  [vistaLobby, vistaJuego, vistaRanking, vistaPodio].forEach(v => {
    if (v) v.classList.add("oculta");
  });
  if (vistaActiva) vistaActiva.classList.remove("oculta");
}

function procesarEventoPantalla(data) {
  switch (data.event) {
    case "sync_screen":
    case "tanda_ready":
      obtenerPin();
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
      animarBarra(data.reading_time || 6);
      break;

    case "buzzers_unlocked":
      detenerBarra();
      break;

    case "buzzer_won":
      detenerBarra();
      turnoNombre.innerText = data.winner_name.toUpperCase();
      cartelTurno.classList.remove("oculta");
      break;

    // FIX: faltaba este caso. Sin él, cuando alguien pulsaba y fallaba,
    // la pantalla grande seguía mostrando el nombre del jugador que ya
    // perdió su turno, en vez de avisar que el rebote está abierto.
    case "rebote_active":
      turnoNombre.innerText = "¡REBOTE! ¿QUIÉN LA ROBA?";
      cartelTurno.classList.remove("oculta");
      animarBarra(data.rebote_time || 7);
      break;

    case "round_result":
      cartelTurno.classList.add("oculta");
      if (data.status === "correct") {
        consignaPantalla.innerText = `¡PUNTO PARA ${data.winner_name.toUpperCase()}! Era: ${data.respuesta_correcta}`;
      } else {
        consignaPantalla.innerText = `Ronda finalizada. Era: ${data.respuesta_correcta}`;
      }
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