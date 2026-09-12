(function () {
  function siteKey() {
    if (location.protocol === "file:") return "file://";
    return location.hostname || location.origin;
  }

  async function publish() {
    const {
      interceptEnabled = true,
      enabled = true,
      skipHosts = [],
    } = await chrome.storage.local.get({
      interceptEnabled: true,
      enabled: true,
      skipHosts: [],
    });
    const skip = skipHosts.includes(siteKey());
    const on = interceptEnabled !== false && enabled !== false;
    try {
      document.documentElement.setAttribute(
        "data-tab-stereo-fix",
        JSON.stringify({ enabled: on, skip }),
      );
    } catch {
      // Ignore detached documents.
    }
  }

  publish();
  chrome.storage.onChanged.addListener((changes, area) => {
    if (area === "local" && (changes.enabled || changes.interceptEnabled || changes.skipHosts)) {
      publish();
    }
  });

  document.addEventListener("tab-stereo-fix-hit", (event) => {
    const detail = event.detail || {};
    chrome.runtime.sendMessage({
      type: "hit",
      host: siteKey(),
      kind: detail.kind || "getUserMedia",
      hits: Number(detail.hits) || 1,
    }).catch(() => {});
  });
})();
