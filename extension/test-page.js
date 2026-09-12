const lib = globalThis.TabStereoFixConstraints;
const sample = {
  audio: {
    echoCancellation: { exact: true },
    noiseSuppression: true,
    autoGainControl: true,
    deviceId: "default",
  },
  video: false,
};

const stripped = lib.stripConstraints(sample);
const dryOk =
  stripped.audio.echoCancellation === false &&
  stripped.audio.noiseSuppression === false &&
  stripped.audio.autoGainControl === false &&
  stripped.audio.deviceId === "default";

document.getElementById("dry-status").textContent = dryOk
  ? "约束改写正常：回声消除 / 噪声抑制 / 自动增益都已关掉，其它参数仍保留。"
  : "约束改写异常，请重新加载扩展。";
document.getElementById("dry-status").className = dryOk ? "ok" : "bad";
document.getElementById("dry-out").textContent = JSON.stringify(
  { before: sample, after: stripped },
  null,
  2,
);

document.getElementById("live").addEventListener("click", async () => {
  const status = document.getElementById("live-status");
  const out = document.getElementById("live-out");
  status.textContent = "正在申请麦克风…";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    const settings = stream.getAudioTracks()[0].getSettings();
    stream.getTracks().forEach((track) => track.stop());
    const liveOk = settings.echoCancellation === false;
    status.textContent = liveOk
      ? "真实申请也被改掉了：echoCancellation = false。Wide Echo Cancellation 不应再被这次麦克风申请触发。"
      : "浏览器仍返回了 echoCancellation = true。请确认扩展已开启，或再关掉 chrome://flags 里的 Chrome Wide Echo Cancellation。";
    status.className = liveOk ? "ok" : "bad";
    out.textContent = JSON.stringify(settings, null, 2);
  } catch (error) {
    status.className = "bad";
    status.textContent = error && error.message ? error.message : String(error);
  }
});
