// Jet-drive AudioWorklet: a 2-pole Helmholtz resonator driven by a delayed
// sigmoid jet, with turbulence noise gated by the jet oscillation. The
// parameters come from instruments/<id>/jet_model.json (the Python fit in
// skills/ocarina-twin/fit_jet.py); the noise input is the chamber's fitted
// slope-colored buffer. The processor owns the whole voice in ?jet=1 mode.
class JetDriveProcessor extends AudioWorkletProcessor {
  static get parameterDescriptors() {
    return [
      { name: "f0", defaultValue: 440, minValue: 20, maxValue: 5000, automationRate: "a-rate" },
      { name: "breath", defaultValue: 0, minValue: 0, maxValue: 2, automationRate: "a-rate" },
      { name: "q", defaultValue: 30, minValue: 1, maxValue: 200, automationRate: "k-rate" },
      { name: "delayRatio", defaultValue: 0.5, minValue: 0.1, maxValue: 2, automationRate: "k-rate" },
      { name: "jetK", defaultValue: 1, minValue: 0.01, maxValue: 20, automationRate: "k-rate" },
      { name: "jetH2", defaultValue: 0, minValue: 0, maxValue: 4, automationRate: "k-rate" },
      { name: "jetH3", defaultValue: 0, minValue: 0, maxValue: 4, automationRate: "k-rate" },
      { name: "jetDrive", defaultValue: 0.5, minValue: 0, maxValue: 2, automationRate: "k-rate" },
      { name: "jetFeedback", defaultValue: 0.1, minValue: 0, maxValue: 1, automationRate: "k-rate" },
      { name: "turbGain", defaultValue: 0, minValue: 0, maxValue: 2, automationRate: "k-rate" },
      { name: "turbGate", defaultValue: 0.5, minValue: 0, maxValue: 1, automationRate: "k-rate" },
      { name: "turbBypass", defaultValue: 0.2, minValue: 0, maxValue: 1, automationRate: "k-rate" },
      { name: "outGain", defaultValue: 1, minValue: 0, maxValue: 1000, automationRate: "k-rate" },
    ];
  }

  constructor() {
    super();
    this.ring = new Float32Array(4096);
    this.ringPos = 0;
    this.phase = 0;
    this.y1 = 0;
    this.y2 = 0;
    this.stopFrame = -1;
    this.port.onmessage = (e) => {
      if (e.data && e.data.stopAt != null) {
        this.stopFrame = Math.max(0, Math.round(e.data.stopAt * sampleRate));
      }
    };
  }

  process(inputs, outputs, parameters) {
    if (this.stopFrame >= 0 && currentFrame >= this.stopFrame) return false;
    const out = outputs[0] && outputs[0][0];
    if (!out) return true;
    const noise = (inputs[0] && inputs[0][0]) || null;
    const f0s = parameters.f0;
    const breaths = parameters.breath;
    const q = Math.max(1, parameters.q[0]);
    const delayRatio = parameters.delayRatio[0];
    const jetK = parameters.jetK[0];
    const jetH2 = parameters.jetH2[0];
    const jetH3 = parameters.jetH3[0];
    const jetDrive = parameters.jetDrive[0];
    const jetFeedback = parameters.jetFeedback[0];
    const turbGain = parameters.turbGain[0];
    const turbGate = parameters.turbGate[0];
    const turbBypass = parameters.turbBypass[0];
    const outGain = parameters.outGain[0];
    const ring = this.ring;
    const ringLen = ring.length;
    for (let i = 0; i < out.length; i++) {
      const f0 = f0s.length > 1 ? f0s[i] : f0s[0];
      const breath = breaths.length > 1 ? breaths[i] : breaths[0];
      const r = Math.exp(-Math.PI * f0 / q / sampleRate);
      const th = 2 * Math.PI * f0 / sampleRate;
      const a1 = 2 * r * Math.cos(th);
      const a2 = -r * r;
      const b0 = 1 - a1 + r * r;
      const delay = Math.max(1, Math.min(ringLen - 2,
        Math.round(sampleRate * delayRatio / f0)));
      this.phase += 2 * Math.PI * f0 / sampleRate;
      if (this.phase > 2 * Math.PI) this.phase -= 2 * Math.PI;
      // Breath gates the whole jet excitation: with breath 0 the node is
      // silent even while it sits ahead of its note on the graph (the A4
      // default before the first f0 event must never leak).
      const j = Math.tanh(jetK * breath * (1
        + jetDrive * Math.sin(this.phase)
        + jetH2 * Math.sin(2 * this.phase)
        + jetH3 * Math.sin(3 * this.phase)
        + jetFeedback * this.y1));
      ring[this.ringPos] = j;
      const idx = (this.ringPos - delay + ringLen * 2) % ringLen;
      const idxPrev = (idx - 1 + ringLen) % ringLen;
      const edge = ring[idx] - ring[idxPrev];
      const nz = noise ? noise[i] : 0;
      const turb = turbGain * nz * breath * (1 - turbGate + turbGate * Math.abs(j));
      const y = b0 * (edge + turb) + a1 * this.y1 + a2 * this.y2;
      this.y2 = this.y1;
      this.y1 = y;
      this.ringPos = (this.ringPos + 1) % ringLen;
      out[i] = (y + turbBypass * turbGain * nz) * outGain;
    }
    return true;
  }
}

registerProcessor("jet-drive", JetDriveProcessor);
