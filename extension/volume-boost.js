(function () {
  let context;
  let gainNode;

  function level() {
    const value = Number(document.documentElement.dataset.stereoGain || "1");
    return Number.isFinite(value) && value > 0 ? Math.min(4, value) : 1;
  }

  function ensure() {
    const Ctor = window.AudioContext || window.webkitAudioContext;
    if (!Ctor) return null;
    if (!context) {
      context = new Ctor();
      gainNode = context.createGain();
      gainNode.connect(context.destination);
    }
    gainNode.gain.value = level();
    if (context.state === "suspended") void context.resume();
    return gainNode;
  }

  function hook(el) {
    if (!el || el.__stereoBoost) return;
    if (el.tagName !== "VIDEO" && el.tagName !== "AUDIO") return;
    el.__stereoBoost = true;
    try {
      el.muted = false;
      if (el.volume < 1) el.volume = 1;
    } catch {
      // Ignore locked media elements.
    }
    const node = ensure();
    if (!node || !context) return;
    try {
      context.createMediaElementSource(el).connect(node);
    } catch {
      // Page already took this element.
    }
  }

  function scan() {
    document.querySelectorAll("video, audio").forEach(hook);
    if (gainNode) gainNode.gain.value = level();
  }

  document.addEventListener("play", (event) => hook(event.target), true);
  const observer = new MutationObserver(scan);
  observer.observe(document.documentElement, {
    subtree: true,
    childList: true,
    attributes: true,
    attributeFilter: ["data-stereo-gain"],
  });
  setInterval(scan, 2000);
  scan();
})();
