"""
Ocarina digital-twin model
==========================

Physical picture
----------------
An ocarina is a fipple-driven Helmholtz resonator, not a pipe.

  f0 ≈ (c / 2π) * sqrt(A_eff / (V * L_eff))

A_eff is the voicing window plus every open finger-hole (holes in
parallel). V is chamber volume. L_eff is wall thickness + end
correction (~0.6 r per hole). Placement of a hole barely changes
pitch; its area does. That is why interpolation MUST stay inside
one chamber: a second chamber is a different V.

The cavity has one isolated acoustic mode near f0. The first
standing-wave / "pipe" modes sit many octaves up (egg-shaped body).
So the *resonator does not generate a harmonic series*. The faint
H2/H3 you measure come from the jet, not from the body:

  * the oscillating jet at the labium is a weakly nonlinear switch
  * radiation at the window/holes has a weak quadratic term
  * hard blow can start to tickle a distant cavity mode ("shriek")

Q of a ceramic alto is typically 30–70. That Q is the physical
attack/decay of the *tone*: τ ≈ Q / (π f0) ≈ 15–50 ms. Player
breath-onset is usually slower than that, so recorded attacks are
breath-limited except on tongued notes.

What you hear as "timbre" after the near-sine fundamental is mostly
**Helmholtz-filtered jet turbulence**: the same bandpass that
selects f0 also colors the noise, so the hiss peaks *at the note*,
not at a fixed 273 Hz shelf. Open holes add a second, brighter
path: windway + hole-edge turbulence that radiates without passing
through the cavity (2–8 kHz "air").

Onset ("chiff"): before the feedback loop locks, the labium
radiates a short unfiltered / low-Q burst. Then the Helmholtz mode
rings up and swallows most of that bandwidth. Decay is the reverse
if the player stops the jet; a tongue-stop dumps the jet and the
cavity rings for ~τ.

Therefore a twin is NOT "PeriodicWave + three fixed noise shelves".
It is:

  jet oscillator (weakly folded sine)
    + period-synchronous turbulence
        → Helmholtz biquad (f0, Q)
  + direct-radiated hole/windway hiss (highpass)
  + onset chiff (wider-Q burst of the same sources)
  + slow breath wander on f0 and gain

Fitting is subtractive and per-chamber, against a frequency axis
(log f0 or open-area), never against the written note name.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any


SCHEMA = "ocarina-twin-v2"


@dataclass
class ChamberGlobals:
    """Shared by every note in one cavity."""
    volume_hint_ml: float | None = None
    Q_prior: float = 45.0
    # hiss_hp_hz is a FALLBACK only. Playback cutoff is hiss_hp_ratio × f0.
    hiss_hp_hz: float = 2800.0
    hiss_hp_ratio: float = 1.6
    chiff_q: float = 2.2
    sync_amt: float = 0.65
    drive_gain: float = 0.55
    dry_hiss_lo: float = 0.15
    dry_hiss_hi: float = 0.70
    dry_hiss_f_lo: float = 520.0
    dry_hiss_f_hi: float = 1400.0


@dataclass
class NoteFit:
    # identity
    note: str | None
    f0: float                      # measured, not nominal
    open_holes: int | None = None  # count proxy when areas unknown
    # core tone
    level: float = 1.0             # linear, relative to chamber peak
    h: list[float] = field(default_factory=lambda: [1, 0, 0, 0, 0, 0])
    Q: float = 45.0                # tone ring (attack/decay, pitch lock)
    noise_Q: float = 12.0          # wider: residual bump around f0 is not a whistle
    # residual split (dB re H1 RMS)
    noise_res_db: float = -28.0    # energy that belongs IN the resonator
    noise_hiss_db: float = -50.0   # energy that bypasses the resonator
    noise_slope_db_oct: float = -8.0
    # envelopes (seconds)
    atk_pre_s: float = 0.008
    atk_speak_s: float = 0.025
    overshoot_db: float = 0.0
    chiff_peak: float = 1.6        # × sustain noise during chiff
    chiff_len_s: float = 0.045
    rel_s: float = 0.070
    # slow wander (sustain)
    wander_cents_std: float = 3.0
    wobble_pct: float = 6.0
    wobble_hz: float = 4.0


@dataclass
class TwinModel:
    schema: str = SCHEMA
    instrument: str = ""
    chamber: str = "1"
    globals: ChamberGlobals = field(default_factory=ChamberGlobals)
    notes: list[NoteFit] = field(default_factory=list)
    recorded: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "instrument": self.instrument,
            "chamber": self.chamber,
            "globals": asdict(self.globals),
            "notes": [asdict(n) for n in self.notes],
            "recorded": self.recorded,
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "TwinModel":
        g = ChamberGlobals(**{k: v for k, v in d.get("globals", {}).items()
                              if k in ChamberGlobals.__dataclass_fields__})
        notes = []
        for n in d.get("notes", []):
            fields = NoteFit.__dataclass_fields__
            notes.append(NoteFit(**{k: v for k, v in n.items() if k in fields}))
        return TwinModel(
            schema=d.get("schema", SCHEMA),
            instrument=d.get("instrument", ""),
            chamber=str(d.get("chamber", "1")),
            globals=g,
            notes=notes,
            recorded=d.get("recorded", {}),
        )
