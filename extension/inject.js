(function () {
  if (globalThis.__tabStereoFixInjected) return;
  globalThis.__tabStereoFixInjected = true;

  const lib = globalThis.TabStereoFixConstraints;
  if (!lib) return;

  let hits = 0;

  function isEnabled() {
    try {
      const raw = document.documentElement.getAttribute("data-tab-stereo-fix");
      if (!raw) return true;
      const cfg = JSON.parse(raw);
      if (cfg.enabled === false || cfg.skip === true) return false;
      return true;
    } catch {
      return true;
    }
  }

  function report(kind) {
    hits += 1;
    try {
      document.documentElement.setAttribute("data-tab-stereo-fix-hits", String(hits));
      document.dispatchEvent(
        new CustomEvent("tab-stereo-fix-hit", {
          detail: { hits, kind },
        }),
      );
    } catch {
      // Ignore pages that block custom events.
    }
  }

  function wrapGetUserMedia(original) {
    return function patchedGetUserMedia(constraints, ...rest) {
      if (!isEnabled()) return original.call(this, constraints, ...rest);
      const next = lib.stripConstraints(constraints);
      if (constraints && constraints.audio) report("getUserMedia");
      return original.call(this, next, ...rest);
    };
  }

  function wrapGetDisplayMedia(original) {
    return function patchedGetDisplayMedia(constraints, ...rest) {
      if (!isEnabled() || !constraints || !constraints.audio) {
        return original.call(this, constraints, ...rest);
      }
      const next = lib.stripConstraints(constraints);
      if (lib.wouldEnableAec(constraints)) report("getDisplayMedia");
      return original.call(this, next, ...rest);
    };
  }

  function patchMediaDevices(proto) {
    if (!proto || proto.__tabStereoFix) return;
    if (typeof proto.getUserMedia === "function") {
      proto.getUserMedia = wrapGetUserMedia(proto.getUserMedia);
    }
    if (typeof proto.getDisplayMedia === "function") {
      proto.getDisplayMedia = wrapGetDisplayMedia(proto.getDisplayMedia);
    }
    proto.__tabStereoFix = true;
  }

  function patchLegacy(owner, name) {
    const original = owner[name];
    if (typeof original !== "function" || original.__tabStereoFix) return;
    const wrapped = function (constraints, success, failure) {
      const next = isEnabled() ? lib.stripConstraints(constraints) : constraints;
      if (isEnabled() && (lib.wouldEnableAec(constraints) || (constraints && constraints.audio === true))) {
        report(name);
      }
      return original.call(this, next, success, failure);
    };
    wrapped.__tabStereoFix = true;
    try {
      owner[name] = wrapped;
    } catch {
      // Some pages freeze navigator.
    }
  }

  function patchApplyConstraints() {
    const proto = globalThis.MediaStreamTrack && MediaStreamTrack.prototype;
    if (!proto || typeof proto.applyConstraints !== "function" || proto.__tabStereoFix) {
      return;
    }
    const original = proto.applyConstraints;
    proto.applyConstraints = function patchedApplyConstraints(constraints) {
      if (!isEnabled() || this.kind !== "audio") {
        return original.call(this, constraints);
      }
      const next = lib.stripAudioConstraints(constraints);
      if (lib.wouldEnableAec(constraints)) report("applyConstraints");
      return original.call(this, next);
    };
    proto.__tabStereoFix = true;
  }

  if (globalThis.MediaDevices) patchMediaDevices(MediaDevices.prototype);
  if (navigator.mediaDevices) patchMediaDevices(Object.getPrototypeOf(navigator.mediaDevices));
  patchLegacy(navigator, "getUserMedia");
  patchLegacy(navigator, "webkitGetUserMedia");
  patchLegacy(navigator, "mozGetUserMedia");
  patchApplyConstraints();
})();
