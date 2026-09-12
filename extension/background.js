const HOST = "com.tabstereofix.host";
const DEFAULTS = { enabled: false, gainPercent: 200 };

async function setBadge(enabled) {
  await chrome.action.setBadgeBackgroundColor({ color: enabled ? "#1d4ed8" : "#64748b" });
  await chrome.action.setBadgeText({ text: enabled ? "开" : "" });
  await chrome.action.setTitle({
    title: enabled
      ? "Wide AEC 已关 · 声音可进 VoiceMeeter / AUX / CABLE / Line 1"
      : "Wide AEC 开着 · 点开关后会重启这个浏览器用户",
  });
}

function native(message) {
  return new Promise((resolve) => {
    try {
      chrome.runtime.sendNativeMessage(HOST, message, (response) => {
        const error = chrome.runtime.lastError && chrome.runtime.lastError.message;
        if (error) {
          resolve({ ok: false, error });
          return;
        }
        resolve(response || { ok: false, error: "本机开关没有返回" });
      });
    } catch (error) {
      resolve({ ok: false, error: error.message || String(error) });
    }
  });
}

async function refreshStatus() {
  const result = await native({ type: "status" });
  if (result && result.ok) {
    await chrome.storage.local.set({ enabled: Boolean(result.enabled) });
    await setBadge(Boolean(result.enabled));
  }
  return result;
}

async function setEnabled(enabled) {
  const result = await native({ type: "set", enabled });
  if (result && result.ok) {
    await chrome.storage.local.set({ enabled });
    await setBadge(enabled);
  }
  return result;
}

async function toggle() {
  const { enabled } = await chrome.storage.local.get(DEFAULTS);
  return setEnabled(!enabled);
}

chrome.runtime.onInstalled.addListener(async () => {
  await chrome.storage.local.set({
    enabled: false,
    gainPercent: 200,
    extensionId: chrome.runtime.id,
  });
  await refreshStatus();
});

chrome.runtime.onStartup.addListener(refreshStatus);
chrome.commands.onCommand.addListener(async (command) => {
  if (command === "toggle-relay") await toggle();
});

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (!message || typeof message !== "object") return;
  if (message.type === "get-state") {
    Promise.all([chrome.storage.local.get(DEFAULTS), refreshStatus()]).then(([local, host]) => {
      sendResponse({
        enabled: Boolean((host && host.enabled) ?? local.enabled),
        gainPercent: Number(local.gainPercent) || 200,
        host,
        extensionId: chrome.runtime.id,
      });
    });
    return true;
  }
  if (message.type === "SET_ENABLED") {
    setEnabled(Boolean(message.enabled)).then(sendResponse);
    return true;
  }
  if (message.type === "SET_GAIN") {
    const gainPercent = Math.max(100, Math.min(400, Number(message.gainPercent) || 200));
    chrome.storage.local.set({ gainPercent }).then(() => {
      native({ type: "volume", level: 1 });
      sendResponse({ ok: true, gainPercent });
    });
    return true;
  }
});

refreshStatus();
