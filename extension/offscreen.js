const players = new Map();
let currentKinds = [];

function connectKeepAlive() {
  try {
    const port = chrome.runtime.connect({ name: "sw-keepalive" });
    port.onDisconnect.addListener(() => setTimeout(connectKeepAlive, 1000));
  } catch {
    setTimeout(connectKeepAlive, 2000);
  }
}

function normalizeKinds(kinds) {
  const list = Array.isArray(kinds) ? kinds.filter((item) => item && item !== "default") : [];
  return list.length ? [...new Set(list)] : ["default"];
}

function matchDeviceId(kind, devices) {
  const outputs = devices.filter((item) => item.kind === "audiooutput" && item.label);
  if (kind === "default") return "";
  if (kind === "cable") {
    const found = outputs.find((item) => /cable/i.test(item.label) && !/voicemeeter/i.test(item.label));
    return found ? found.deviceId : "";
  }
  if (kind === "voicemeeter-aux") {
    const found = outputs.find((item) => /voicemeeter/i.test(item.label) && /aux/i.test(item.label));
    return found ? found.deviceId : "";
  }
  if (kind === "line1") {
    const found = outputs.find((item) => /line\s*1/i.test(item.label) && !/voicemeeter/i.test(item.label));
    return found ? found.deviceId : "";
  }
  if (kind === "voicemeeter") {
    const found =
      outputs.find((item) => /voicemeeter/i.test(item.label) && !/aux|vaio3|insert/i.test(item.label)) ||
      outputs.find((item) => /voicemeeter/i.test(item.label));
    return found ? found.deviceId : "";
  }
  return "";
}

async function resolveSinkIds(kinds) {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return normalizeKinds(kinds).map((kind) => matchDeviceId(kind, devices));
}

async function makePlayer(stream, sinkId) {
  const audio = new Audio();
  audio.srcObject = stream;
  audio.autoplay = true;
  audio.volume = 1;
  if (audio.setSinkId) {
    try {
      await audio.setSinkId(sinkId || "");
    } catch {
      await audio.setSinkId("");
    }
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
  const sinkIds = await resolveSinkIds(message.sinkKinds);
  const audios = [];
  for (const sinkId of sinkIds) {
    audios.push(await makePlayer(stream, sinkId));
  }
  players.set(message.tabId, { audios, stream });
  return { ok: true };
}

function stopTab(tabId) {
  const player = players.get(tabId);
  if (!player) return;
  releaseAudios(player);
  player.stream.getTracks().forEach((track) => track.stop());
  players.delete(tabId);
}

function stopAll() {
  for (const tabId of [...players.keys()]) stopTab(tabId);
}

async function setSinks(sinkKinds) {
  currentKinds = normalizeKinds(sinkKinds);
  const sinkIds = await resolveSinkIds(currentKinds);
  for (const player of players.values()) {
    releaseAudios(player);
    for (const sinkId of sinkIds) {
      player.audios.push(await makePlayer(player.stream, sinkId));
    }
  }
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") return;

  if (message.type === "START_TAB") {
    startTab(message).then(sendResponse).catch((error) => {
      sendResponse({ ok: false, error: error && error.message ? error.message : String(error) });
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
    setSinks(message.sinkKinds).then(() => sendResponse({ ok: true })).catch((error) => {
      sendResponse({ ok: false, error: error.message });
    });
    return true;
  }
});

connectKeepAlive();
chrome.storage.local.get({ sinkKinds: [] }).then((state) => {
  currentKinds = normalizeKinds(state.sinkKinds);
});
