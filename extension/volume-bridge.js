(function () {
  async function publish() {
    const { enabled = false, gainPercent = 200 } = await chrome.storage.local.get({
      enabled: false,
      gainPercent: 200,
    });
    const gain = enabled ? Math.max(1, Number(gainPercent) || 200) / 100 : 1;
    try {
      document.documentElement.dataset.stereoGain = String(gain);
    } catch {
      // Ignore detached documents.
    }
  }

  publish();
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && (changes.enabled || changes.gainPercent)) publish();
  });
})();
