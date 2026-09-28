"""Shared air-band definition. Fit, offline synth and JS must use this."""

# Playback highpass for hole-rush (not a fixed 2800 Hz).
HISS_HP_RATIO = 1.6
HISS_HP_MIN_HZ = 700.0
HISS_HP_MAX_HZ = 3500.0
HISS_TOP_HZ = 12000.0

# Dry (unsynced) hiss fraction vs f0.
DRY_HISS_F_LO = 520.0
DRY_HISS_F_HI = 1400.0
DRY_HISS_LO = 0.15
DRY_HISS_HI = 0.70

NOISE_Q_CLOSED = 12.0
NOISE_Q_OPEN_SCALE = 0.45   # F6 12/12 holes → Q ≈ 6.6
NOISE_Q_MIN = 4.5


def hiss_hp_hz(f0: float) -> float:
    f = float(f0) * HISS_HP_RATIO
    return max(HISS_HP_MIN_HZ, min(HISS_HP_MAX_HZ, f))


def dry_hiss_frac(f0: float) -> float:
    t = (float(f0) - DRY_HISS_F_LO) / max(1.0, DRY_HISS_F_HI - DRY_HISS_F_LO)
    t = max(0.0, min(1.0, t))
    return DRY_HISS_LO + (DRY_HISS_HI - DRY_HISS_LO) * t


def effective_noise_q(noise_q: float | None, open_holes: int | None, f0: float,
                      hole_count: int = 12) -> float:
    q = max(4.0, float(noise_q or NOISE_Q_CLOSED))
    if open_holes is None:
        t = max(0.0, min(1.0, (float(f0) - 880.0) / 520.0))
        return max(NOISE_Q_MIN, q * (1.0 - 0.45 * t))
    open_frac = max(0.0, min(1.0, open_holes / max(1, hole_count)))
    return max(NOISE_Q_MIN, q * (1.0 - NOISE_Q_OPEN_SCALE * open_frac))


def fitted_noise_q(open_holes: int | None, hole_count: int = 12) -> float:
    """Write this into JSON so JS/Python do not have to guess."""
    return effective_noise_q(NOISE_Q_CLOSED, open_holes, 880.0, hole_count)
