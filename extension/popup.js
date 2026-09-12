const toggleEl = document.getElementById("toggle");
const statusEl = document.getElementById("status");
const pillEl = document.getElementById("state-pill");
const masterLabel = document.getElementById("master-label");
const extIdEl = document.getElementById("ext-id");
const gainEl = document.getElementById("gain");
const gainLabel = document.getElementById("gain-label");

function setStatus(text, kind) {
  statusEl.textContent = text;
  statusEl.className = `status ${kind}`;
}

function render(state) {
  const enabled = Boolean(state.enabled);
  toggleEl.checked = enabled;
  pillEl.textContent = enabled ? "开" : "关";
  masterLabel.textContent = enabled ? "声音传播：开" : "声音传播：关";
  extIdEl.textContent = state.extensionId ? `插件 ID：${state.extensionId}` : "";
  const gain = Number(state.gainPercent) || 200;
  gainEl.value = String(gain);
  gainLabel.textContent = `${gain}%`;

  const host = state.host || {};
  if (host.error && /Specified native messaging host not found|Access to the specified native messaging host is forbidden/i.test(host.error)) {
    setStatus("还没接通本机开关。请先双击「安装开关.bat」，然后到扩展页点重新加载。", "bad");
    return;
  }
  if (host.error) {
    setStatus(host.error, "bad");
    return;
  }
  if (enabled) {
    setStatus("已打开。这个浏览器用户的 Wide AEC 已关，声音应能进 VoiceMeeter / CABLE。再关一次会重启并恢复。", "ok");
    return;
  }
  setStatus("现在关着。打开后只重启当前这个浏览器，其它浏览器不动。", "warn");
}

async function refresh() {
  const state = await chrome.runtime.sendMessage({ type: "get-state" });
  render(state || {});
  return state;
}

toggleEl.addEventListener("change", async () => {
  toggleEl.disabled = true;
  setStatus("正在重启这个浏览器用户…", "warn");
  const result = await chrome.runtime.sendMessage({
    type: "SET_ENABLED",
    enabled: toggleEl.checked,
  });
  if (result && result.restarting) {
    setStatus("浏览器即将重启，请等它重新打开。", "warn");
  } else if (result && result.error) {
    setStatus(result.error, "bad");
    toggleEl.checked = !toggleEl.checked;
  } else {
    render({ enabled: toggleEl.checked, host: result, extensionId: chrome.runtime.id });
  }
  toggleEl.disabled = false;
});

document.getElementById("open-privacy").addEventListener("click", () => {
  chrome.tabs.create({ url: chrome.runtime.getURL("privacy.html") });
});

gainEl.addEventListener("input", () => {
  gainLabel.textContent = `${gainEl.value}%`;
});
gainEl.addEventListener("change", async () => {
  await chrome.runtime.sendMessage({ type: "SET_GAIN", gainPercent: Number(gainEl.value) });
});

refresh();
