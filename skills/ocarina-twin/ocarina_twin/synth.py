"""Subtractive-then-physical synthesizer for one ocarina chamber."""
from __future__ import annotations

import numpy as np
from scipy.signal import butter, sosfilt, lfilter

from .air import dry_mid_frac, effective_noise_q, mid_hi_hz, mid_lo_hz
from .model import TwinModel, NoteFit, ChamberGlobals


def _biquad_bandpass(sr: float, f0: float, Q: float):
    """RBJ bandpass (peak 0 dB at f0), returned as (b, a)."""
    f0 = float(np.clip(f0, 20.0, sr * 0.45))
    Q = float(np.clip(Q, 0.5, 200.0))
    w0 = 2 * np.pi * f0 / sr
    alpha = np.sin(w0) / (2 * Q)
    b0 = alpha
    b1 = 0.0
    b2 = -alpha
    a0 = 1 + alpha
    a1 = -2 * np.cos(w0)
    a2 = 1 - alpha
    b = np.array([b0 / a0, b1 / a0, b2 / a0])
    a = np.array([1.0, a1 / a0, a2 / a0])
    return b, a


def _interp_note(model: TwinModel, f0: float) -> NoteFit:
    notes = sorted(model.notes, key=lambda n: n.f0)
    if not notes:
        return NoteFit(note=None, f0=f0)
    if f0 <= notes[0].f0:
        return notes[0]
    if f0 >= notes[-1].f0:
        return notes[-1]
    for a, b in zip(notes, notes[1:]):
        if a.f0 <= f0 <= b.f0:
            t = 0 if b.f0 == a.f0 else (np.log(f0) - np.log(a.f0)) / (np.log(b.f0) - np.log(a.f0))
            def lerp(x, y):
                return (1 - t) * x + t * y
            hlen = max(len(a.h), len(b.h))
            ha = list(a.h) + [0] * (hlen - len(a.h))
            hb = list(b.h) + [0] * (hlen - len(b.h))
            return NoteFit(
                note=None,
                f0=f0,
                open_holes=a.open_holes if t < 0.5 else b.open_holes,
                level=lerp(a.level, b.level),
                h=[lerp(x, y) for x, y in zip(ha, hb)],
                Q=lerp(a.Q, b.Q),
                noise_Q=lerp(a.noise_Q, b.noise_Q),
                noise_res_db=lerp(a.noise_res_db, b.noise_res_db),
                noise_mid_db=lerp(getattr(a, "noise_mid_db", -40), getattr(b, "noise_mid_db", -40)),
                noise_hiss_db=lerp(a.noise_hiss_db, b.noise_hiss_db),
                noise_slope_db_oct=lerp(a.noise_slope_db_oct, b.noise_slope_db_oct),
                atk_pre_s=lerp(a.atk_pre_s, b.atk_pre_s),
                atk_speak_s=lerp(a.atk_speak_s, b.atk_speak_s),
                overshoot_db=lerp(a.overshoot_db, b.overshoot_db),
                chiff_peak=lerp(a.chiff_peak, b.chiff_peak),
                chiff_len_s=lerp(a.chiff_len_s, b.chiff_len_s),
                rel_s=lerp(a.rel_s, b.rel_s),
                wander_cents_std=lerp(a.wander_cents_std, b.wander_cents_std),
                wobble_pct=lerp(a.wobble_pct, b.wobble_pct),
                wobble_hz=lerp(a.wobble_hz, b.wobble_hz),
            )
    return notes[-1]


def _breath_env(n: int, sr: float, nf: NoteFit, hold_s: float) -> np.ndarray:
    pre = int(max(0, nf.atk_pre_s) * sr)
    speak = max(8, int(max(0.004, nf.atk_speak_s) * sr))
    rel = max(8, int(max(0.02, nf.rel_s) * sr))
    hold_n = max(1, int(hold_s * sr))
    env = np.zeros(n)
    # raised-cosine speak after pre
    i0 = pre
    i1 = min(n, pre + speak)
    if i1 > i0:
        t = np.linspace(0, 1, i1 - i0, endpoint=True)
        env[i0:i1] = 0.5 - 0.5 * np.cos(np.pi * t)
    os = 10 ** (nf.overshoot_db / 20.0)
    if os != 1 and i1 > i0:
        env[i0:i1] *= 1 + (os - 1) * np.sin(np.pi * t)
    i2 = min(n, max(i1, hold_n - rel))
    env[i1:i2] = 1.0
    # settle overshoot into 1
    i3 = min(n, hold_n)
    if i3 > i2:
        t = np.linspace(0, 1, i3 - i2, endpoint=True)
        env[i2:i3] = 1.0 * (1 - t)  # will overwrite below if release
    # release from hold_n
    r0 = min(n, max(i1, hold_n - rel))
    env[i1:r0] = 1.0
    r1 = min(n, r0 + rel)
    if r1 > r0:
        t = np.linspace(0, 1, r1 - r0, endpoint=True)
        env[r0:r1] = 0.5 + 0.5 * np.cos(np.pi * t)
    return env


def _match_rms(x: np.ndarray, target: float) -> np.ndarray:
    rms = float(np.sqrt(np.mean(x ** 2) + 1e-20))
    return x * (target / rms) if rms > 0 else x


def _band(x, sr, lo, hi):
    ny = sr / 2
    lo, hi = max(40.0, lo), min(ny - 40.0, hi)
    if hi <= lo + 20:
        return np.zeros_like(x)
    return sosfilt(butter(2, [lo / ny, hi / ny], btype="band", output="sos"), x)


def _colored_noise(n: int, sr: float, slope_db_oct: float, rng: np.random.Generator) -> np.ndarray:
    """Approximately f^(slope/6) amplitude tilt, unit RMS."""
    w = rng.standard_normal(n)
    spec = np.fft.rfft(w)
    freqs = np.fft.rfftfreq(n, 1 / sr)
    scale = np.ones_like(freqs)
    nz = freqs > 20
    scale[nz] = (freqs[nz] / 1000.0) ** (slope_db_oct / 6.0)
    spec *= scale
    y = np.fft.irfft(spec, n=n)
    y /= np.sqrt(np.mean(y ** 2) + 1e-20)
    return y


def render_note(model: TwinModel, f0: float, dur_s: float, sr: int = 44100,
                seed: int = 0, hold_s: float | None = None) -> np.ndarray:
    """Render one note. dur_s includes release tail."""
    nf = _interp_note(model, f0)
    g = model.globals
    hold = dur_s if hold_s is None else hold_s
    n = int(sr * dur_s)
    rng = np.random.default_rng(seed)

    env = _breath_env(n, sr, nf, hold)
    # slow wander / wobble
    t = np.arange(n) / sr
    # two slow components so it is not a metronome LFO
    w1 = rng.standard_normal()
    phase = 2 * np.pi * (nf.wobble_hz * (0.85 + 0.3 * abs(w1))) * t + rng.uniform(0, 2 * np.pi)
    wander = (nf.wander_cents_std / 1200.0) * np.log(2) * np.sin(phase * 0.35 + 0.4)
    wob = (nf.wobble_pct / 100.0) * 0.5 * (1 + np.sin(phase))
    inst_f = f0 * (1 + wander)
    amp_wob = 1 + 0.5 * (wob - np.mean(wob))

    # phase accumulator
    phi = np.cumsum(2 * np.pi * inst_f / sr)
    # Cavity sees a near-sine volume-velocity. Weak H2/H3 are labium
    # radiation that does NOT pass through the Helmholtz filter — putting
    # them through the bandpass would erase them, which is exactly the
    # "too pure / no bite" failure mode.
    sine = np.sin(phi)
    direct = np.zeros(n)
    for k, hk in enumerate(nf.h[1:], start=2):
        if hk > 1e-5:
            direct = direct + hk * np.sin(k * phi)
    if g.drive_gain > 0:
        # tiny extra fold on the DIRECT path only
        direct = direct + 0.15 * (np.tanh(g.drive_gain * sine) - sine)

    # period-synchronous turbulence
    raw = _colored_noise(n, sr, nf.noise_slope_db_oct, rng)
    sync = 0.35 + g.sync_amt * 0.65 * (0.5 - 0.5 * np.cos(phi))
    turb = raw * sync

    nq = effective_noise_q(nf.noise_Q, nf.open_holes, f0)
    tone_q = min(float(nf.Q), 30.0 + f0 * 0.035)
    helm_tone = lfilter(*_biquad_bandpass(sr, f0, tone_q), sine * env * amp_wob)
    halo = lfilter(*_biquad_bandpass(sr, f0, nq), turb)
    halo = _match_rms(halo, 10 ** (nf.noise_res_db / 20.0)) * env * amp_wob
    body = helm_tone + halo

    mid_lo, mid_hi = mid_lo_hz(f0), mid_hi_hz(sr)
    mid_db = getattr(nf, "noise_mid_db", None)
    if mid_db is None:
        mid_db = nf.noise_hiss_db + 6.0
    dry = dry_mid_frac(f0)
    mid_src = (1.0 - dry) * turb + dry * raw
    mid = _band(mid_src, sr, mid_lo, mid_hi)
    # same low-note presence as helmholtz-voice.js (C5×2.4 → A5×1)
    lift = 2.4 + (1.0 - 2.4) * min(1.0, max(0.0, (f0 - 500.0) / 400.0))
    mid = _match_rms(mid, lift * 10 ** (mid_db / 20.0)) * env * amp_wob

    hiss = _band(raw, sr, 4000.0, min(sr / 2 - 40, 12000.0))
    hiss = _match_rms(hiss, 10 ** (nf.noise_hiss_db / 20.0)) * env * amp_wob

    # chiff: extra wide-Q burst of turbulence at onset
    chiff_env = np.zeros(n)
    c0 = int(nf.atk_pre_s * sr)
    c1 = int((nf.atk_pre_s + nf.chiff_len_s) * sr)
    c1 = min(n, max(c0 + 4, c1))
    if c1 > c0:
        tt = np.linspace(0, 1, c1 - c0, endpoint=True)
        chiff_env[c0:c1] = np.sin(np.pi * tt) * max(0.0, nf.chiff_peak - 1.0)
    b2, a2 = _biquad_bandpass(sr, f0, g.chiff_q)
    chiff = lfilter(b2, a2, turb)
    chiff = _match_rms(chiff, 10 ** (nf.noise_res_db / 20.0)) * chiff_env

    y = body + mid + hiss + chiff + direct * env * amp_wob

    # normalize sustain H1-ish level
    # take a window after speak
    a0 = min(n - 8, int((nf.atk_pre_s + nf.atk_speak_s + 0.05) * sr))
    a1 = min(n, max(a0 + int(0.1 * sr), int(hold * 0.7 * sr)))
    if a1 > a0 + 16:
        rms = np.sqrt(np.mean(y[a0:a1] ** 2) + 1e-20)
        y = y / rms * nf.level
    else:
        y = y * nf.level

    peak = np.max(np.abs(y)) + 1e-12
    if peak > 0.95:
        y = y * (0.95 / peak)
    return y.astype(np.float32)


def render_model_scale(model: TwinModel, sr: int = 44100, note_s: float = 0.9,
                       gap_s: float = 0.15) -> np.ndarray:
    chunks = []
    gap = np.zeros(int(sr * gap_s), dtype=np.float32)
    for i, nf in enumerate(sorted(model.notes, key=lambda n: n.f0)):
        chunks.append(render_note(model, nf.f0, note_s + nf.rel_s, sr=sr,
                                  seed=1000 + i, hold_s=note_s))
        chunks.append(gap)
    return np.concatenate(chunks) if chunks else np.zeros(1, dtype=np.float32)
