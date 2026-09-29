"""
Canonical air bands — Grok 2026-09-28.

E6/F6 air is a pedestal from just above f0 to ~4 kHz, ~−32 dB re tone.
It is NOT 5–12 kHz fizz. Do not add a highshelf to "make air".

Bands (residual after tracked H1–H8, dB re sustain RMS):
  noise_res_db  : [0.70 f0, 1.25 f0]     cavity breath halo
  noise_mid_db  : [1.25 f0, 4000 Hz]     hole-rush (the 12-hole top)
  noise_hiss_db : [4000 Hz, 12000 Hz]    true high hiss (stay quiet)
"""

RES_LO_RATIO = 0.70
RES_HI_RATIO = 1.25
MID_LO_RATIO = 1.25
MID_HI_HZ = 4000.0
HISS_LO_HZ = 4000.0
HISS_HI_HZ = 12000.0

NOISE_Q_CLOSED = 12.0
NOISE_Q_OPEN_SCALE = 0.60   # F6 12/12 → Q ≈ 4.8
NOISE_Q_MIN = 3.8

DRY_HISS_F_LO = 520.0
DRY_HISS_F_HI = 1400.0
DRY_MID_LO = 0.20
DRY_MID_HI = 0.75


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def mid_lo_hz(f0: float) -> float:
    return max(200.0, float(f0) * MID_LO_RATIO)


def mid_hi_hz(sr: float = 44100.0) -> float:
    return min(MID_HI_HZ, sr * 0.45)


def dry_mid_frac(f0: float) -> float:
    t = clamp((float(f0) - DRY_HISS_F_LO) / max(1.0, DRY_HISS_F_HI - DRY_HISS_F_LO), 0.0, 1.0)
    return DRY_MID_LO + (DRY_MID_HI - DRY_MID_LO) * t


def effective_noise_q(noise_q, open_holes, f0, hole_count: int = 12) -> float:
    q = max(3.5, float(noise_q or NOISE_Q_CLOSED))
    if open_holes is None:
        t = clamp((float(f0) - 880.0) / 520.0, 0.0, 1.0)
        return max(NOISE_Q_MIN, q * (1.0 - 0.55 * t))
    open_frac = clamp(open_holes / max(1, hole_count), 0.0, 1.0)
    return max(NOISE_Q_MIN, q * (1.0 - NOISE_Q_OPEN_SCALE * open_frac))


def fitted_noise_q(open_holes, hole_count: int = 12) -> float:
    return effective_noise_q(NOISE_Q_CLOSED, open_holes, 880.0, hole_count)


def pink_hp_rms(hp_hz: float) -> float:
    """Unit-RMS leaky-pink through 2nd-order HP. Used as JS compensation."""
    return clamp(0.40 * (839.0 / max(200.0, hp_hz)) ** 0.5, 0.08, 0.55)
