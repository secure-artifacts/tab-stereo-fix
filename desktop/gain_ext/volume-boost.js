(function () {
  function restore(el) {
    if (!el || (el.tagName !== "VIDEO" && el.tagName !== "AUDIO")) return;
    try {
      el.muted = false;
      if (el.volume < 1) el.volume = 1;
    } catch {
      // Ignore locked media elements.
    }
  }

  function scan() {
    document.querySelectorAll("video, audio").forEach(restore);
  }

  document.addEventListener("play", (event) => restore(event.target), true);
  scan();
})();
