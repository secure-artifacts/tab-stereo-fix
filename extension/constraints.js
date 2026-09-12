(function (root) {
  const PROCESSING_KEYS = [
    "echoCancellation",
    "noiseSuppression",
    "autoGainControl",
    "googEchoCancellation",
    "googEchoCancellation2",
    "googAutoGainControl",
    "googAutoGainControl2",
    "googNoiseSuppression",
    "googNoiseSuppression2",
    "googHighpassFilter",
    "googTypingNoiseDetection",
    "googAudioMirroring",
  ];

  const ALWAYS_OFF = [
    "echoCancellation",
    "noiseSuppression",
    "autoGainControl",
  ];

  function cloneValue(value) {
    if (!value || typeof value !== "object") return value;
    if (Array.isArray(value)) return value.map(cloneValue);
    const out = {};
    for (const key of Object.keys(value)) {
      out[key] = cloneValue(value[key]);
    }
    return out;
  }

  function forceOffMap(source) {
    if (!source || typeof source !== "object") return source;
    const next = cloneValue(source);
    for (const key of PROCESSING_KEYS) {
      if (key in next) next[key] = false;
    }
    return next;
  }

  function stripAudioConstraints(audio) {
    if (audio === undefined || audio === null || audio === false) return audio;
    if (audio === true) {
      const next = {};
      for (const key of ALWAYS_OFF) next[key] = false;
      return next;
    }
    if (typeof audio !== "object") return audio;

    const next = cloneValue(audio);
    for (const key of ALWAYS_OFF) next[key] = false;
    for (const key of PROCESSING_KEYS) {
      if (key in next) next[key] = false;
    }
    if (next.mandatory && typeof next.mandatory === "object") {
      next.mandatory = forceOffMap(next.mandatory);
      next.mandatory.echoCancellation = false;
      next.mandatory.googEchoCancellation = false;
    }
    if (Array.isArray(next.optional)) {
      next.optional = next.optional.map(forceOffMap);
    }
    if (Array.isArray(next.advanced)) {
      next.advanced = next.advanced.map(forceOffMap);
    }
    return next;
  }

  function stripConstraints(constraints) {
    if (!constraints || typeof constraints !== "object") return constraints;
    if (!("audio" in constraints)) return constraints;
    const next = cloneValue(constraints);
    next.audio = stripAudioConstraints(next.audio);
    return next;
  }

  function constraintOn(value) {
    if (value === true) return true;
    if (value && typeof value === "object") {
      return value.exact === true || value.ideal === true;
    }
    return false;
  }

  function constraintOff(value) {
    return value === false || (value && typeof value === "object" && value.exact === false);
  }

  function wouldEnableAec(constraints, assumeDefaultOn) {
    if (!constraints) return false;
    const audio =
      constraints.audio !== undefined ? constraints.audio : constraints;
    if (audio === true) return true;
    if (!audio || typeof audio !== "object") return false;
    const values = [audio, audio.mandatory, ...(audio.optional || []), ...(audio.advanced || [])];
    if (values.some((item) => item && typeof item === "object" && PROCESSING_KEYS.some((key) => constraintOn(item[key])))) {
      return true;
    }
    if (values.some((item) => item && typeof item === "object" && constraintOff(item.echoCancellation))) {
      return false;
    }
    return Boolean(assumeDefaultOn);
  }

  const api = {
    PROCESSING_KEYS,
    cloneValue,
    stripAudioConstraints,
    stripConstraints,
    wouldEnableAec,
  };

  root.TabStereoFixConstraints = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
