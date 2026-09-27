"""Fit an ocarina-twin model from held-note recordings of ONE chamber."""
from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.fft import rfft, rfftfreq
from scipy.signal import butter, get_window, sosfilt

from .model import ChamberGlobals, NoteFit, TwinModel


NOTE_RE = re.compile(r"([A-G]s?\d+)", re.I)
NOM = {
    "A4": 440.00, "As4": 466.16, "B4": 493.88,
    "C5": 523.25, "Cs5": 554.37, "D5": 587.33, "Ds5": 622.25,
    "E5": 659.26, "F5": 698.46, "Fs5": 739.99, "G5": 783.99,
    "Gs5": 830.61, "A5": 880.00, "As5": 932.33, "B5": 987.77,
    "C6": 1046.50, "Cs6": 1108.73, "D6": 1174.66, "Ds6": 1244.51,
    "E6": 1318.51, "F6": 1396.91,
}


def load_mono(path: Path):
    x, sr = sf.read(path)
    if x.ndim > 1:
        x = x.mean(axis=1)
    return x.astype(np.float64), int(sr)


def rms_env(x, sr, ms=8):
    n = max(1, int(sr * ms / 1000))
    pad = (-len(x)) % n
    y = np.pad(x, (0, pad))
    e = np.sqrt(np.mean(y.reshape(-1, n) ** 2, axis=1) + 1e-20)
    t = (np.arange(len(e)) + 0.5) * n / sr
    return t, e


def sounding_span(x, sr):
    """Longest region above ~8% of peak RMS. Tolerates leading/trailing
    silence. The median leg guards human takes against low-level noise, but
    must never rise above half the peak: flat SYNTHETIC sustains (the offline
    render bench) sit AT the median, and an unclamped median*4 threshold
    exceeds the peak, collapsing the span onto the 0.15/0.85 fallback that
    reads release+silence as sustain."""
    t, e = rms_env(x, sr, 10)
    peak = e.max()
    # One peak-relative leg: these held takes show 20+ dB headroom between
    # the mic floor and peak*0.08 (measured -39..-51 vs floors -41..-61), so
    # the old median*4 noise guard never guarded anything - its threshold
    # EXCEEDED the peak on every take (med4/peak 2.3-3.7) and the span fell
    # onto the 0.15/0.85 fallback, fitting release+silence as sustain. The
    # flat synthetic sustains of the render bench read correctly under the
    # same rule, so one leg serves both sides of the stage gate.
    thr = peak * 0.08
    act = e > thr
    best = None
    i = 0
    while i < len(act):
        if act[i]:
            j = i
            while j < len(act) and act[j]:
                j += 1
            if j - i >= 6:
                cand = (float(t[i]), float(t[min(j, len(t) - 1)]))
                if best is None or cand[1] - cand[0] > best[1] - best[0]:
                    best = cand
            i = j
        else:
            i += 1
    if best is None:
        return 0.15 * len(x) / sr, 0.85 * len(x) / sr
    return best


def refine_f0(x, sr, guess, lo=0.88, hi=1.14):
    n = len(x)
    if n < 256:
        return float(guess)
    w = get_window("hann", n, fftbins=True)
    spec = np.abs(rfft(x * w))
    fr = rfftfreq(n, 1 / sr)
    m = (fr > guess * lo) & (fr < guess * hi)
    if not np.any(m):
        return float(guess)
    idx = np.where(m)[0][int(np.argmax(spec[m]))]
    if 1 <= idx < len(spec) - 1:
        a, b, c = spec[idx - 1], spec[idx], spec[idx + 1]
        den = a - 2 * b + c
        delta = 0.5 * (a - c) / den if abs(den) > 1e-18 else 0.0
        return float(fr[idx] + np.clip(delta, -1, 1) * (fr[1] - fr[0]))
    return float(fr[idx])


def fit_harmonics(x, sr, f0, n_h=8):
    t = np.arange(len(x)) / sr
    cols = [np.ones_like(t)]
    for k in range(1, n_h + 1):
        cols.append(np.cos(2 * np.pi * k * f0 * t))
        cols.append(np.sin(2 * np.pi * k * f0 * t))
    A = np.column_stack(cols)
    coef, *_ = np.linalg.lstsq(A, x, rcond=None)
    rec = A @ coef
    amps = [np.hypot(coef[1 + 2 * (k - 1)], coef[2 + 2 * (k - 1)]) for k in range(1, n_h + 1)]
    return np.array(amps), rec, x - rec


def subtract_tracked(x, sr, f_guess, n_h=8, win_ms=40, hop_ms=8):
    win = int(sr * win_ms / 1000)
    hop = int(sr * hop_ms / 1000)
    w = get_window("hann", win, fftbins=True)
    recon = np.zeros_like(x)
    weight = np.zeros_like(x)
    frames = []
    f = f_guess
    for start in range(0, max(1, len(x) - win), hop):
        sl = slice(start, start + win)
        frame = x[sl]
        try:
            f = refine_f0(frame, sr, f, 0.97, 1.03)
        except ValueError:
            pass
        amps, rec, _ = fit_harmonics(frame, sr, f, n_h)
        recon[sl] += rec * w
        weight[sl] += w
        frames.append({
            "t": (start + win / 2) / sr,
            "f0": f,
            "amps": amps,
            "rms": float(np.sqrt(np.mean(frame ** 2) + 1e-20)),
        })
    recon = recon / np.maximum(weight, 1e-6)
    residual = np.zeros_like(x)
    mask = weight > 0.25
    residual[mask] = x[mask] - recon[mask]
    return recon, residual, frames


def band_rms(x, sr, lo, hi):
    ny = sr / 2
    lo = max(30.0, lo)
    hi = min(ny - 30.0, hi)
    if hi <= lo + 15:
        return 0.0
    y = sosfilt(butter(2, [lo / ny, hi / ny], btype="band", output="sos"), x)
    return float(np.sqrt(np.mean(y ** 2) + 1e-20))


def residual_slope(res, sr, f0):
    n = min(len(res), 8192)
    w = get_window("hann", n, fftbins=True)
    spec = np.abs(rfft(res[:n] * w))
    fr = rfftfreq(n, 1 / sr)
    db = 20 * np.log10(spec + 1e-20)
    keep = np.ones_like(db, dtype=bool)
    for k in range(1, 8):
        keep &= np.abs(1200 * np.log2(np.maximum(fr, 1) / (k * f0))) > 45
    m = keep & (fr > 250) & (fr < 8000)
    if m.sum() < 16:
        return -8.0
    return float(np.polyfit(np.log2(fr[m]), db[m], 1)[0])


def rise_ms(x, sr, ms=4):
    t, e = rms_env(x, sr, ms)
    if e.max() <= 0:
        return 25.0
    p = e.max()
    try:
        t10 = t[np.where(e >= 0.10 * p)[0][0]]
        t90 = t[np.where(e >= 0.90 * p)[0][0]]
        return float(max(4.0, (t90 - t10) * 1000))
    except Exception:
        return 25.0


def overshoot_db(x, sr):
    t, e = rms_env(x, sr, 6)
    if len(e) < 8:
        return 0.0
    peak = e.max()
    # later half as sustain proxy
    sus = np.median(e[len(e) // 2 :])
    return float(20 * np.log10((peak + 1e-12) / (sus + 1e-12)))


def guess_note_from_name(path: Path, f0: float) -> str | None:
    m = NOTE_RE.search(path.stem)
    if m:
        raw = m.group(1)
        raw = raw[0].upper() + raw[1:]
        return raw
    # nearest nominal
    best, bd = None, 1e9
    for k, v in NOM.items():
        d = abs(np.log2(f0 / v))
        if d < bd:
            best, bd = k, d
    return best


def open_holes_from_fingerings(fingerings: dict | None, note: str | None) -> int | None:
    if not fingerings or not note:
        return None
    total = len(fingerings.get("holes", {}))
    for n in fingerings.get("notes", []):
        if n.get("id") == note:
            return total - len(n.get("covered", []))
    return None


def fit_take(path: Path, fingerings: dict | None = None) -> NoteFit:
    x, sr = load_mono(path)
    t0, t1 = sounding_span(x, sr)
    # sustain: skip onset and the last bit (human release / room)
    sa = t0 + 0.11
    sb = max(sa + 0.18, t1 - 0.10)
    if sb <= sa + 0.12:
        sa, sb = t0 + 0.07, t1 - 0.05
    xs = x[int(sa * sr): int(sb * sr)]
    xo = x[int(t0 * sr): int(min(t1, t0 + 0.08) * sr)]

    name = guess_note_from_name(path, 500)
    f_guess = NOM.get(name or "", 500.0)
    f0 = refine_f0(xs, sr, f_guess)
    name = guess_note_from_name(path, f0)

    recon, residual, frames = subtract_tracked(xs, sr, f0)
    amps = np.median(np.stack([fr["amps"] for fr in frames]), axis=0)
    h = (amps / (amps[0] + 1e-12)).tolist()

    sig = float(np.sqrt(np.mean(xs ** 2) + 1e-20))
    res_rms = float(np.sqrt(np.mean(residual ** 2) + 1e-20))
    near = band_rms(residual, sr, 0.65 * f0, 1.35 * f0)
    hiss = band_rms(residual, sr, 2800.0, min(sr / 2 - 40, 12000))
    slope = residual_slope(residual, sr, f0)

    ftrack = np.array([fr["f0"] for fr in frames])
    cents = 1200 * np.log2(ftrack / np.median(ftrack))
    # wobble from harmonic RMS
    e = np.array([fr["rms"] for fr in frames])
    wob = float(np.std(e) / (np.mean(e) + 1e-12) * 100)

    # onset residual vs sustain residual → chiff multiplier
    if len(xo) > 400:
        _, ores, _ = subtract_tracked(xo, sr, f0, win_ms=24, hop_ms=6)
        o_rms = float(np.sqrt(np.mean(ores ** 2) + 1e-20))
        o_sig = float(np.sqrt(np.mean(xo ** 2) + 1e-20))
        chiff = float(np.clip((o_rms / (o_sig + 1e-12)) / (res_rms / (sig + 1e-12) + 1e-6), 1.0, 4.0))
        speak = rise_ms(xo, sr) / 1000.0
        os_db = float(np.clip(overshoot_db(xo, sr), 0, 6))
    else:
        chiff, speak, os_db = 1.3, 0.025, 0.0

    # Q: tone 3 dB width on a mid-length window, clamped to ocarina range
    n = min(len(xs), int(sr * 0.35))
    w = get_window("hann", n, fftbins=True)
    spec = np.abs(rfft(xs[:n] * w)) ** 2
    fr = rfftfreq(n, 1 / sr)
    m = (fr > f0 - 60) & (fr < f0 + 60)
    Q = 45.0
    if np.any(m):
        peak = spec[m].max()
        idx = np.where(m)[0][int(np.argmax(spec[m]))]
        half = peak / 2
        i = idx
        while i > 0 and spec[i] > half:
            i -= 1
        j = idx
        while j < len(spec) - 1 and spec[j] > half:
            j += 1
        bw = max(fr[1], fr[j] - fr[i])
        Q = float(np.clip(f0 / bw, 18.0, 80.0))

    return NoteFit(
        note=name,
        f0=float(f0),
        open_holes=open_holes_from_fingerings(fingerings, name),
        level=sig,
        h=h[:6],
        Q=Q,
        noise_Q=12.0,
        noise_res_db=float(20 * np.log10(near / (sig + 1e-12) + 1e-12)),
        noise_hiss_db=float(20 * np.log10(hiss / (sig + 1e-12) + 1e-12)),
        noise_slope_db_oct=float(np.clip(slope, -16, -2)),
        atk_pre_s=0.006,
        atk_speak_s=float(np.clip(speak, 0.008, 0.08)),
        overshoot_db=os_db,
        chiff_peak=chiff,
        chiff_len_s=0.045,
        rel_s=0.07,
        wander_cents_std=float(np.clip(np.std(cents), 0.4, 12)),
        wobble_pct=float(np.clip(wob, 1.0, 20)),
        wobble_hz=4.0,
    )


def normalize_levels(notes: list[NoteFit]) -> list[NoteFit]:
    """Recording gain is a mic-chain artifact. Peak note in the chamber = 1."""
    peak = max((n.level for n in notes), default=1.0)
    for n in notes:
        n.level = float(n.level / (peak + 1e-12))
    return notes


def fit_chamber(wav_paths: list[Path], instrument: str, chamber: str = "1",
                fingerings: dict | None = None) -> TwinModel:
    notes = [fit_take(p, fingerings=fingerings) for p in wav_paths]
    notes = normalize_levels(notes)
    notes.sort(key=lambda n: n.f0)
    qs = [n.Q for n in notes]
    return TwinModel(
        instrument=instrument,
        chamber=str(chamber),
        globals=ChamberGlobals(Q_prior=float(np.median(qs))),
        notes=notes,
        recorded={
            "takes": [str(p.name) for p in wav_paths],
            "rule": "per-chamber log-f interpolation only; never cross a chamber boundary",
            "level": "relative to loudest fitted take in this chamber (mic gain discarded)",
        },
    )


def load_fingerings(path: Path | None) -> dict | None:
    if path is None or not path.exists():
        return None
    return json.loads(path.read_text())
