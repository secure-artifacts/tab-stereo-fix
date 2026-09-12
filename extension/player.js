const players = new Map();
const sinksEl = document.getElementById("sinks");
const foundEl = document.getElementById("found");
const statusEl = document.getElementById("status");
const listEl = document.getElementById("list");
let currentKinds = ["cable", "voicemeeter"];

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = `status ${kind}`;
}

function selectedKinds() {
  const kinds = [...sinksEl.querySelectorAll("button.on")]
    .map((button) => button.dataset.kind)
    .filter((kind) => kind && kind !== "default");
  return kinds;
}

function paintSinks(kinds) {
  const selected = new Set(kinds && kinds.length ? kinds : ["default"]);
  for (const button of sinksEl.querySelectorAll("button[data-kind]")) {
    const kind = button.dataset.kind;
    button.classList.toggle("on", kind === "default" ? selected.has("default") || !kinds.length : selected.has(kind));
  }
}

async function unlockOutputs() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: false,
        noiseSuppression: false,
        autoGainControl: false,
      },
      video: false,
    });
    stream.getTracks().forEach((track) => track.stop());
  } catch {
    // User can still try named devices if Chrome already exposed them.
  }
}

function matchDeviceId(kind, devices) {
  const outputs = devices.filter((item) => item.kind === "audiooutput" && item.label);
  if (kind === "default") return { id: "", label: "默认设备" };
  if (kind === "cable") {
    const found = outputs.find((item) => /cable/i.test(item.label) && !/voicemeeter/i.test(item.label));
    return found ? { id: found.deviceId, label: found.label } : null;
  }
  if (kind === "voicemeeter-aux") {
    const found = outputs.find((item) => /voicemeeter/i.test(item.label) && /aux/i.test(item.label));
    return found ? { id: found.deviceId, label: found.label } : null;
  }
  if (kind === "voicemeeter") {
    const found =
      outputs.find((item) => /voicemeeter/i.test(item.label) && !/aux|vaio3|insert/i.test(item.label)) ||
      outputs.find((item) => /voicemeeter/i.test(item.label));
    return found ? { id: found.deviceId, label: found.label } : null;
  }
  return null;
}

async function resolveTargets(kinds) {
  const devices = await navigator.mediaDevices.enumerateDevices();
  const wanted = kinds && kinds.length ? kinds : ["default"];
  const targets = [];
  const missing = [];
  for (const kind of wanted) {
    const found = matchDeviceId(kind, devices);
    if (found) targets.push({ kind, ...found });
    else missing.push(kind);
  }
  if (!targets.length) targets.push({ kind: "default", id: "", label: "默认设备" });
  return { targets, missing, devices };
}

async function makePlayer(stream, sinkId) {
  const audio = new Audio();
  audio.srcObject = stream;
  audio.autoplay = true;
  audio.volume = 1;
  if (audio.setSinkId) {
    await audio.setSinkId(sinkId || "");
  }
  await audio.play();
  return audio;
}

function releaseAudios(player) {
  for (const audio of player.audios || []) {
    audio.pause();
    audio.srcObject = null;
  }
  player.audios = [];
}

async function applyTargets(targets) {
  for (const player of players.values()) {
    releaseAudios(player);
    for (const target of targets) {
      player.audios.push(await makePlayer(player.stream, target.id));
    }
  }
}

function renderFound(targets, missing) {
  const ok = targets.map((item) => `已接到：${item.label}`).join("<br>");
  const no = missing.length
    ? `<div>没找到：${missing.join("、")}。请确认已安装，并允许一次麦克风权限用来列出设备（不录音）。</div>`
    : "";
  foundEl.innerHTML = `<div>${ok}</div>${no}`;
}

async function applySinks(kinds) {
  currentKinds = kinds && kinds.length ? kinds : ["default"];
  paintSinks(currentKinds);
  const { targets, missing } = await resolveTargets(currentKinds);
  renderFound(targets, missing);
  await applyTargets(targets);
  await chrome.storage.local.set({ sinkKinds: currentKinds.filter((item) => item !== "default") });
  setStatus(
    missing.length
      ? "已尽量输出。有设备没找到，先看下面红色提示。"
      : `声音正在打到：${targets.map((item) => item.label).join(" + ")}`,
    missing.length ? "warn" : "ok",
  );
  return { targets, missing };
}

async function startTab(message) {
  stopTab(message.tabId);
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      mandatory: {
        chromeMediaSource: "tab",
        chromeMediaSourceId: message.streamId,
      },
    },
    video: false,
  });
  const { targets } = await resolveTargets(currentKinds);
  const audios = [];
  for (const target of targets) {
    audios.push(await makePlayer(stream, target.id));
  }
  players.set(message.tabId, { audios, stream, title: message.title || "" });
  renderTabs();
  return { ok: true };
}

function stopTab(tabId) {
  const player = players.get(tabId);
  if (!player) return;
  releaseAudios(player);
  player.stream.getTracks().forEach((track) => track.stop());
  players.delete(tabId);
  renderTabs();
}

function stopAll() {
  for (const tabId of [...players.keys()]) stopTab(tabId);
}

function renderTabs() {
  const items = [...players.entries()];
  listEl.innerHTML = items.length
    ? items.map(([, player]) => `<div class="item"><strong>${player.title || "标签页"}</strong><span>已接入</span></div>`).join("")
    : '<div class="empty">还没有接到出声的标签。</div>';
}

sinksEl.addEventListener("click", (event) => {
  const button = event.target.closest("button[data-kind]");
  if (!button) return;
  button.classList.toggle("on");
  if (button.dataset.kind === "default" && button.classList.contains("on")) {
    for (const other of sinksEl.querySelectorAll("button[data-kind]")) {
      if (other !== button) other.classList.remove("on");
    }
  } else {
    sinksEl.querySelector('[data-kind="default"]')?.classList.remove("on");
  }
  if (![...sinksEl.querySelectorAll("button.on")].length) {
    sinksEl.querySelector('[data-kind="default"]')?.classList.add("on");
  }
});

document.getElementById("apply").addEventListener("click", async () => {
  setStatus("正在接到 CABLE / VoiceMeeter…", "warn");
  await unlockOutputs();
  try {
    await applySinks(selectedKinds());
  } catch (error) {
    setStatus(error.message || String(error), "bad");
  }
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") return;
  if (message.type === "START_TAB") {
    startTab(message).then(sendResponse).catch((error) => {
      sendResponse({ ok: false, error: error.message || String(error) });
    });
    return true;
  }
  if (message.type === "STOP_TAB") {
    stopTab(message.tabId);
    sendResponse({ ok: true });
    return true;
  }
  if (message.type === "STOP_ALL") {
    stopAll();
    sendResponse({ ok: true });
    return true;
  }
  if (message.type === "SET_SINKS") {
    applySinks(message.sinkKinds).then(() => sendResponse({ ok: true })).catch((error) => {
      sendResponse({ ok: false, error: error.message });
    });
    return true;
  }
});

window.addEventListener("beforeunload", () => {
  stopAll();
  chrome.runtime.sendMessage({ type: "PLAYER_CLOSED" }).catch(() => {});
});

(async function init() {
  const state = await chrome.storage.local.get({ sinkKinds: ["cable", "voicemeeter"] });
  currentKinds = state.sinkKinds && state.sinkKinds.length ? state.sinkKinds : ["cable", "voicemeeter"];
  paintSinks(currentKinds);
  await unlockOutputs();
  await applySinks(currentKinds);
  chrome.runtime.sendMessage({ type: "PLAYER_READY" }).catch(() => {});
})();
