const assert = require("assert");
const {
  stripConstraints,
  stripAudioConstraints,
  wouldEnableAec,
} = require("../extension/constraints.js");

const meetLike = stripConstraints({
  audio: {
    echoCancellation: { exact: true },
    noiseSuppression: true,
    autoGainControl: { ideal: true },
    deviceId: { ideal: "mic-1" },
  },
});

assert.strictEqual(meetLike.audio.echoCancellation, false);
assert.strictEqual(meetLike.audio.noiseSuppression, false);
assert.strictEqual(meetLike.audio.autoGainControl, false);
assert.deepStrictEqual(meetLike.audio.deviceId, { ideal: "mic-1" });

const fromTrue = stripAudioConstraints(true);
assert.strictEqual(fromTrue.echoCancellation, false);

assert.strictEqual(wouldEnableAec({ audio: true }), true);
assert.strictEqual(wouldEnableAec({ audio: { echoCancellation: true } }), true);
assert.strictEqual(wouldEnableAec({ audio: { echoCancellation: false } }), false);
assert.strictEqual(wouldEnableAec({ audio: { deviceId: "default" } }, true), true);
assert.strictEqual(wouldEnableAec({ video: true }), false);

const mandatory = stripConstraints({
  audio: {
    mandatory: { googEchoCancellation: true, sourceId: "abc" },
    optional: [{ googNoiseSuppression: true }],
  },
});
assert.strictEqual(mandatory.audio.mandatory.googEchoCancellation, false);
assert.strictEqual(mandatory.audio.mandatory.sourceId, "abc");
assert.strictEqual(mandatory.audio.optional[0].googNoiseSuppression, false);

const apply = stripAudioConstraints({ echoCancellation: { exact: true } });
assert.strictEqual(apply.echoCancellation, false);

console.log("constraints tests passed");
