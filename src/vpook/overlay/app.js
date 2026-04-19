const avatarEl = document.getElementById("avatar");

let avatarConfig = null;
let currentSource = "";

function applyState(state) {
  if (!avatarConfig) {
    return;
  }

  const volume = Number(state.volume || 0);
  const talking = Boolean(state.talking);
  const stretch = Math.min(volume, 1);
  const translateY = talking ? -8 - stretch * 14 : -stretch * 4;
  const scaleX = talking ? 1 + stretch * 0.05 : 1 - stretch * 0.01;
  const scaleY = talking ? 1 - stretch * 0.07 : 1 + stretch * 0.02;
  const brightness = talking ? 1 + stretch * 0.18 : 1;

  const targetSource = talking ? avatarConfig.talking : avatarConfig.idle;
  if (currentSource !== targetSource) {
    avatarEl.src = targetSource;
    currentSource = targetSource;
  }

  avatarEl.style.transform = `translateY(${translateY}px) scaleX(${scaleX}) scaleY(${scaleY})`;
  avatarEl.style.filter = `brightness(${brightness}) drop-shadow(0 10px 24px rgba(0, 0, 0, 0.22))`;
  avatarEl.style.opacity = talking ? "1" : "0.98";
}

async function loadConfig() {
  const response = await fetch("/config.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load config: ${response.status}`);
  }
  return response.json();
}

function connectSocket(websocketUrl) {
  const socket = new WebSocket(websocketUrl);

  socket.addEventListener("message", (event) => {
    const payload = JSON.parse(event.data);
    if (payload.type !== "state") {
      return;
    }
    applyState(payload);
  });

  socket.addEventListener("close", () => {
    window.setTimeout(() => connectSocket(websocketUrl), 1000);
  });
}

async function bootstrap() {
  const config = await loadConfig();
  avatarConfig = config.avatar;
  avatarEl.src = avatarConfig.idle;
  currentSource = avatarConfig.idle;
  connectSocket(config.websocketUrl);
}

bootstrap().catch((error) => {
  console.error(error);
});
