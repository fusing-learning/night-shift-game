"""Core DSP + synthesis building blocks for the procedural audio pipeline.

Everything is numpy float64, sample rate SR. Signals are 1-D (mono) or
shape (2, n) (stereo). Functions operate along the last axis.

Loop-safety conventions ("periodic" flags):
  * colored() noise is generated in the frequency domain -> exactly periodic.
  * periodic=True filters run over two tiled periods and keep the second,
    so IIR state wraps around the loop seam.
  * reverb_circ() is an exact circular convolution.
  * fix_cycles() rescales a frequency trajectory so that it completes an
    integer number of cycles over the loop -> phase continuous at the seam.
  * place(..., wrap=True) wraps event tails around to the loop start.
"""
import subprocess
import numpy as np
from scipy import signal

SR = 44100
TAU = 2.0 * np.pi
FFMPEG = "/opt/homebrew/bin/ffmpeg"


# ----------------------------------------------------------------- basics
def N(d):
    return max(1, int(round(d * SR)))


def T(n):
    return np.arange(n) / SR


def db(x):
    return 10.0 ** (x / 20.0)


def rms(x):
    return float(np.sqrt(np.mean(np.square(x)) + 1e-20))


def cents(c):
    return 2.0 ** (c / 1200.0)


def mtof(m):
    return 440.0 * 2.0 ** ((m - 69) / 12.0)


def _farr(f, n):
    return np.array(np.broadcast_to(np.asarray(f, float), (n,)), dtype=float)


def norm(x, peak=1.0):
    m = np.max(np.abs(x))
    return x * (peak / m) if m > 0 else x


def unit(x):
    """Scale to unit RMS."""
    return x / rms(x)


# ------------------------------------------------------------- envelopes
def env(points, n, shape="smooth"):
    """Piecewise envelope through (time_s, value) points.
    shape: 'smooth' (raised-cosine segments) or 'lin'."""
    ts = np.array([p[0] for p in points], float)
    vs = np.array([p[1] for p in points], float)
    t = T(n)
    if len(ts) == 1:
        return np.full(n, vs[0])
    idx = np.clip(np.searchsorted(ts, t, side="right") - 1, 0, len(ts) - 2)
    t0, t1, v0, v1 = ts[idx], ts[idx + 1], vs[idx], vs[idx + 1]
    u = np.clip((t - t0) / np.maximum(t1 - t0, 1e-9), 0.0, 1.0)
    if shape == "smooth":
        u = 0.5 - 0.5 * np.cos(np.pi * u)
    out = v0 + (v1 - v0) * u
    out[t < ts[0]] = vs[0]
    return out


def env_db(points, n, floor=-90.0):
    """Envelope interpolated in dB (exponential-feeling curves)."""
    pts = [(t, max(v, floor)) for t, v in points]
    e = db(env(pts, n, "lin"))
    return np.where(e <= db(floor) * 1.0001, 0.0, e)


def ad(n, a, tau, hold=0.0):
    """Curved attack (sin^2) then exponential decay with time-constant tau."""
    t = T(n)
    att = np.sin(0.5 * np.pi * np.clip(t / max(a, 1e-5), 0, 1)) ** 2
    dec = np.exp(-np.maximum(t - a - hold, 0) / max(tau, 1e-5))
    return att * dec


def fade(x, fin=0.003, fout=0.02):
    x = np.array(x, float)
    n = x.shape[-1]
    a = min(N(fin), n // 2) if fin > 0 else 0
    b = min(N(fout), n // 2) if fout > 0 else 0
    if a > 0:
        x[..., :a] *= np.sin(0.5 * np.pi * np.arange(a) / a) ** 2
    if b > 0:
        x[..., n - b:] *= np.cos(0.5 * np.pi * (np.arange(b) + 1) / b) ** 2
    return x


def bump(t, center, width, period=None):
    """Raised-cosine bump (1 at centre, 0 beyond +-width). Circular if period."""
    d = t - center
    if period:
        d = (d + period / 2) % period - period / 2
    u = np.clip(np.abs(d) / width, 0, 1)
    return 0.5 + 0.5 * np.cos(np.pi * u)


# --------------------------------------------------------------- filters
def _apply_sos(sos, x, periodic=False):
    if periodic:
        n = x.shape[-1]
        y = signal.sosfilt(sos, np.concatenate([x, x], axis=-1), axis=-1)
        return y[..., n:]
    return signal.sosfilt(sos, x, axis=-1)


def _apply_ba(b, a, x, periodic=False):
    if periodic:
        n = x.shape[-1]
        y = signal.lfilter(b, a, np.concatenate([x, x], axis=-1), axis=-1)
        return y[..., n:]
    return signal.lfilter(b, a, x, axis=-1)


def lp(x, f, order=2, periodic=False):
    f = float(np.clip(f, 5, SR * 0.47))
    return _apply_sos(signal.butter(order, f, "lowpass", fs=SR, output="sos"), x, periodic)


def hp(x, f, order=2, periodic=False):
    f = float(np.clip(f, 3, SR * 0.47))
    return _apply_sos(signal.butter(order, f, "highpass", fs=SR, output="sos"), x, periodic)


def bp(x, lo, hi, order=2, periodic=False):
    lo = float(np.clip(lo, 5, SR * 0.45))
    hi = float(np.clip(hi, lo * 1.05, SR * 0.47))
    return _apply_sos(signal.butter(order, [lo, hi], "bandpass", fs=SR, output="sos"), x, periodic)


def rbj(kind, f, q=0.707, gain_db=0.0):
    f = min(max(f, 5.0), SR * 0.45)
    w = TAU * f / SR
    c, s = np.cos(w), np.sin(w)
    al = s / (2 * q)
    A = 10 ** (gain_db / 40)
    if kind == "lp":
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
        a = [1 + al, -2 * c, 1 - al]
    elif kind == "hp":
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
        a = [1 + al, -2 * c, 1 - al]
    elif kind == "bp":
        b = [al, 0.0, -al]
        a = [1 + al, -2 * c, 1 - al]
    elif kind == "peak":
        b = [1 + al * A, -2 * c, 1 - al * A]
        a = [1 + al / A, -2 * c, 1 - al / A]
    else:
        raise ValueError(kind)
    b = np.array(b) / a[0]
    a = np.array(a) / a[0]
    return b, a


def peq(x, f, gain_db, q=1.0, periodic=False):
    b, a = rbj("peak", f, q, gain_db)
    return _apply_ba(b, a, x, periodic)


def reson(x, f, q, periodic=False):
    b, a = rbj("bp", f, q)
    return _apply_ba(b, a, x, periodic)


def tvf(x, f, q=0.707, kind="lp", block=64, periodic=False):
    """Time-varying RBJ biquad (coefficients updated every `block` samples)."""
    x = np.asarray(x, float)
    if x.ndim == 2:
        return np.stack([tvf(c, f, q, kind, block, periodic) for c in x])
    n = len(x)
    f = _farr(f, n)
    q = _farr(q, n)
    if periodic:
        x = np.concatenate([x, x])
        f = np.concatenate([f, f])
        q = np.concatenate([q, q])
    m = len(x)
    y = np.empty(m)
    zi = np.zeros(2)
    for i in range(0, m, block):
        j = min(m, i + block)
        c = (i + j) // 2
        b, a = rbj(kind, float(f[c]), float(max(q[c], 0.05)))
        y[i:j], zi = signal.lfilter(b, a, x[i:j], zi=zi)
    return y[n:] if periodic else y


def resbank(x, freqs, qs, gains=None, periodic=False):
    y = np.zeros_like(x)
    qs = np.broadcast_to(qs, (len(freqs),))
    gains = np.ones(len(freqs)) if gains is None else gains
    for f, q, g in zip(freqs, qs, gains):
        if f < SR * 0.45:
            y += g * reson(x, f, q, periodic)
    return y


def comb(x, delay_s, fb, periodic=False):
    d = max(1, N(delay_s))
    b = np.zeros(d + 1); b[0] = 1
    a = np.zeros(d + 1); a[0] = 1; a[d] = -fb
    return _apply_ba(b, a, x, periodic)


def sat(x, drive=2.0):
    return np.tanh(drive * x) / np.tanh(drive)


def softclip(x, drive=2.0, bias=0.0):
    y = np.tanh(drive * (x + bias)) - np.tanh(drive * bias)
    return y / max(np.max(np.abs(y)), 1e-9)


# ------------------------------------------------------------------ noise
def colored(n, r, slope=0.0, lo=None, hi=None):
    """Exactly periodic colored noise, unit RMS. slope in dB/octave."""
    k = n // 2 + 1
    X = r.standard_normal(k) + 1j * r.standard_normal(k)
    fr = np.fft.rfftfreq(n, 1 / SR)
    fr[0] = 1.0
    g = (fr / 1000.0) ** (slope / 6.0206)
    if lo:
        g = g / np.sqrt(1 + (lo / fr) ** 4)
    if hi:
        g = g / np.sqrt(1 + (fr / hi) ** 4)
    g[0] = 0.0
    y = np.fft.irfft(X * g, n)
    return y / (np.std(y) + 1e-20)


def white(n, r):
    return r.standard_normal(n)


def smooth_rand(n, r, rate, periodic=False):
    """Slowly varying random control signal in roughly [-1,1]."""
    y = colored(n, r, 0, hi=rate) if periodic else lp(r.standard_normal(n), rate, 2)
    return y / (3 * np.std(y) + 1e-20)


# ------------------------------------------------------------ oscillators
def phase(f, n, ph0=0.0):
    f = _farr(f, n)
    p = np.empty(n)
    p[0] = 0.0
    np.cumsum(f[:-1] / SR, out=p[1:])
    return p + ph0


def fix_cycles(f, n):
    """Scale a frequency trajectory so it spans an integer number of cycles."""
    f = _farr(f, n)
    tot = f.sum() / SR
    k = max(1, round(tot))
    return f * (k / tot)


def qf(f, period):
    """Quantise a constant frequency to an integer number of cycles per period."""
    return max(1, round(f * period)) / period


def _blep_saw(p, dt):
    p = np.mod(p, 1.0)
    y = 2 * p - 1
    m = p < dt
    u = p[m] / dt[m]
    y[m] -= u + u - u * u - 1
    m = p > 1 - dt
    u = (p[m] - 1) / dt[m]
    y[m] -= u * u + u + u + 1
    return y


def osc(kind, f, n, ph0=0.0, pw=0.5):
    f = _farr(f, n)
    p = phase(f, n, ph0)
    dt = np.clip(np.abs(f) / SR, 1e-9, 0.49)
    if kind == "sine":
        return np.sin(TAU * p)
    if kind == "saw":
        return _blep_saw(p, dt)
    if kind == "square":
        return 0.5 * (_blep_saw(p, dt) - _blep_saw(p + pw, dt))
    if kind == "tri":
        q = np.mod(p, 1.0)
        return 2 * np.abs(2 * q - 1) - 1
    raise ValueError(kind)


def supersaw(f, n, r, voices=5, detune=12.0, periodic_len=None):
    """Detuned saw stack. Returns unit-ish mono."""
    y = np.zeros(n)
    for v in range(voices):
        c = detune * (2 * v / max(voices - 1, 1) - 1) + r.uniform(-2, 2)
        fv = _farr(f, n) * cents(c)
        if periodic_len:
            fv = fix_cycles(fv, n)
        y += osc("saw", fv, n, r.random())
    return y / np.sqrt(voices)


# --------------------------------------------------------- modal / impacts
RATIOS = {
    "bar": [1, 2.756, 5.404, 8.933, 13.34, 18.64],
    "bell": [0.5, 1, 1.183, 1.506, 2.0, 2.514, 2.662, 3.011, 4.166, 5.433],
    "pipe": [1, 2.32, 4.25, 6.63, 9.38, 12.5, 16.1],
    "plate": [1, 1.59, 2.14, 2.30, 2.65, 2.92, 3.16, 3.50, 3.60, 4.06, 4.15, 4.6, 5.1, 5.4],
}


def rand_ratios(r, k, lo=0.12, hi=0.7):
    x, out = 1.0, [1.0]
    for _ in range(k - 1):
        x += r.uniform(lo, hi)
        out.append(x)
    return out


def modal(n, r, f0, ratios, tau, decay_pow=0.7, tilt=0.5, jit=0.01, amps=None):
    """Sum of exponentially damped sinusoids (struck object)."""
    t = T(n)
    y = np.zeros(n)
    for i, ra in enumerate(ratios):
        f = f0 * ra * (1 + jit * r.standard_normal())
        if f > SR * 0.45 or f < 15:
            continue
        tk = tau * (ra / ratios[0]) ** (-decay_pow)
        a = (amps[i] if amps is not None else (ra / ratios[0]) ** (-tilt)) * r.uniform(0.5, 1.0)
        m = min(n, int(tk * SR * 8) + 1)
        y[:m] += a * np.exp(-t[:m] / tk) * np.sin(TAU * f * t[:m] + r.uniform(0, TAU))
    return y * (1 - np.exp(-t / 0.0004))


def metal_hit(n, r, f0, tau, kind="plate", k=14, bright=0.5, noise=0.3):
    ratios = RATIOS[kind] if kind in RATIOS else rand_ratios(r, k)
    y = modal(n, r, f0, ratios[:k], tau, tilt=bright)
    y = unit(y)
    if noise:
        nb = hp(r.standard_normal(n), 1500) * ad(n, 0.0005, 0.006)
        y += noise * 4 * nb
    return y


def thump(n, f0, f1, ptau, atau, a=0.002):
    t = T(n)
    f = f1 + (f0 - f1) * np.exp(-t / ptau)
    return np.sin(TAU * phase(f, n)) * ad(n, a, atau)


def burst(n, r, tau, lo=None, hi=None, a=0.001, slope=0.0):
    x = r.standard_normal(n)
    if slope:
        x = colored(n, r, slope)
    if lo and hi:
        x = bp(x, lo, hi)
    elif lo:
        x = hp(x, lo)
    elif hi:
        x = lp(x, hi)
    return unit(x) * ad(n, a, tau)


def click(n, r, lo=2000, hi=9000, tau=0.002):
    return burst(n, r, tau, lo, hi, a=0.0002)


def bubble(n, r, f0, dur, rise=1.5, tau=None):
    t = T(n)
    m = min(n, N(dur))
    tau = tau or dur / 4
    f = f0 * (1 + rise * np.clip(t / dur, 0, 1))
    y = np.sin(TAU * phase(f, n)) * ad(n, 0.001, tau)
    y[m:] *= np.exp(-(t[m:] - t[m]) / 0.004)
    return y


def pulses(rate, n, r, jitter=0.0, shimmer=0.0, sub=0.0, amp=None):
    """Impulse train (fractional placement) following a rate trajectory (Hz)."""
    rate = _farr(rate, n)
    amp = None if amp is None else _farr(amp, n)
    y = np.zeros(n + 2)
    pos, k = 0.0, 0
    while pos < n:
        i = int(pos)
        rt = rate[i]
        if rt < 1.0:
            pos += 32
            continue
        a = max(0.0, 1.0 + shimmer * r.standard_normal())
        if sub and (k & 1):
            a *= 1 - sub
        if amp is not None:
            a *= amp[i]
        fr = pos - i
        y[i] += a * (1 - fr)
        y[i + 1] += a * fr
        pos += max(1.5, SR / rt * (1 + jitter * r.standard_normal()))
        k += 1
    return y[:n]


def poisson_times(r, dur, density):
    """Event times for a (possibly time varying) Poisson process. density: fn(t) or float."""
    times, t = [], 0.0
    if callable(density):
        dmax = max(density(x) for x in np.linspace(0, dur, 200)) + 1e-9
        while True:
            t += r.exponential(1 / dmax)
            if t >= dur:
                break
            if r.random() < density(t) / dmax:
                times.append(t)
    else:
        while True:
            t += r.exponential(1 / density)
            if t >= dur:
                break
            times.append(t)
    return times


def crackle(n, r, density, lo=1200, hi=7000, amp_pow=2.5):
    """Sparse heavy-tailed pops (fire, sparks, sizzle)."""
    y = np.zeros(n)
    for t in poisson_times(r, n / SR, density):
        i = int(t * SR)
        if i < n:
            y[i] += r.choice([-1, 1]) * r.random() ** amp_pow
    y = bp(y, lo, hi, 2)
    return y


def wet_clicks(n, r, density, fmin=300, fmax=3000, gl=(0.002, 0.012)):
    """Granular wet clicks: tiny pitch-dropping windowed sines."""
    y = np.zeros(n)
    for t in poisson_times(r, n / SR, density):
        i = int(t * SR)
        L = N(r.uniform(*gl))
        if i + L >= n:
            continue
        f0 = np.exp(r.uniform(np.log(fmin), np.log(fmax)))
        tt = T(L)
        f = f0 * (1 + r.uniform(-0.5, 0.8) * tt / tt[-1])
        g = np.sin(TAU * phase(f, L)) * np.hanning(L) * r.uniform(0.2, 1.0)
        y[i:i + L] += g
    return y


# ------------------------------------------------------------------ voice
VOWELS = {
    "a": [(730, 90, 1.0), (1090, 110, 0.5), (2440, 170, 0.25), (3400, 250, 0.1)],
    "o": [(570, 80, 1.0), (840, 100, 0.45), (2410, 170, 0.15), (3400, 250, 0.06)],
    "u": [(300, 60, 1.0), (870, 90, 0.3), (2240, 150, 0.1), (3300, 250, 0.04)],
    "e": [(530, 70, 1.0), (1840, 120, 0.5), (2480, 170, 0.3), (3500, 250, 0.1)],
    "i": [(270, 60, 1.0), (2290, 140, 0.4), (3010, 200, 0.3), (3600, 250, 0.1)],
    "uh": [(640, 80, 1.0), (1190, 110, 0.5), (2390, 160, 0.2), (3400, 250, 0.08)],
    "ae": [(660, 90, 1.0), (1720, 120, 0.5), (2410, 170, 0.3), (3400, 250, 0.1)],
}


def vowel_track(seq, n, fscale=1.0, bwscale=1.0):
    """seq: vowel name or list of (time_s, name). -> list of (f, bw, g) arrays."""
    if isinstance(seq, str):
        seq = [(0.0, seq)]
    out = []
    for k in range(4):
        fpts = [(t, VOWELS[v][k][0] * fscale) for t, v in seq]
        bpts = [(t, VOWELS[v][k][1] * bwscale * max(fscale, 0.5)) for t, v in seq]
        gpts = [(t, VOWELS[v][k][2]) for t, v in seq]
        out.append((env(fpts, n), env(bpts, n), env(gpts, n)))
    return out


def formant_filter(x, form, block=64):
    y = np.zeros_like(x)
    for f, bw, g in form:
        y += tvf(x, f, f / bw, "bp", block) * g
    return y


def glottal(f0, n, r, jitter=0.02, shimmer=0.1, sub=0.0, tilt=500):
    y = pulses(f0, n, r, jitter, shimmer, sub)
    y = lp(y, tilt, 1)
    y = hp(y, 25)
    return unit(y)


def voice(n, r, f0, vowels="a", fscale=1.0, jitter=0.02, shimmer=0.1, sub=0.0,
          breath=0.3, tilt=500, bwscale=1.0, body=0.15):
    src = glottal(f0, n, r, jitter, shimmer, sub, tilt)
    pe = lp(np.abs(src), 60)
    pe = pe / (np.max(pe) + 1e-9)
    exc = src + breath * r.standard_normal(n) * (0.35 + 0.65 * pe)
    y = formant_filter(exc, vowel_track(vowels, n, fscale, bwscale))
    y += body * lp(exc, 250)
    return unit(y)


def whisper(n, r, vowels, fscale=1.0):
    exc = r.standard_normal(n)
    return unit(formant_filter(exc, vowel_track(vowels, n, fscale, 1.6)))


def screech(n, r, f0, rough=0.03, ring=1.41, ring_amt=0.5, bright=3000, pw=0.3):
    f0 = _farr(f0, n)
    wob = smooth_rand(n, r, 35)
    f = f0 * (1 + rough * 3 * wob)
    s = 0.6 * osc("saw", f, n) + 0.4 * osc("square", f, n, pw=pw)
    rm = s * osc("sine", f * ring + 37, n)
    y = (1 - ring_amt) * s + ring_amt * rm
    y = peq(y, bright, 8, 1.2)
    return unit(y)


def bowed(n, r, freqs, q=300, flutter=0.4, periodic=False, amps=None):
    """Noise-excited high-Q resonators: bowed metal / glass tones."""
    exc = colored(n, r, 0) if periodic else r.standard_normal(n)
    y = np.zeros(n)
    for i, f in enumerate(freqs):
        if f > SR * 0.45:
            continue
        b = reson(exc, f, q, periodic)
        b = b / (np.std(b) + 1e-20)
        a = 1.0 if amps is None else amps[i]
        if flutter:
            a = a * (1 + flutter * smooth_rand(n, r, 3, periodic))
        y += a * b
    return unit(y)


def creak(n, r, rate, freqs, q=12, jitter=0.35, amp=None, slip=0.04):
    """Stick-slip creak: jittery impulse train into resonances."""
    imp = pulses(rate, n, r, jitter, 0.6, 0.0, amp)
    # occasional big slips
    for t in poisson_times(r, n / SR, 3.0):
        i = int(t * SR)
        if i < n:
            imp[i] += r.uniform(1, 3) * (1 if r.random() < 0.5 else -1) * slip * 25
    y = resbank(imp, freqs, q, np.array([1.0 / (1 + 0.3 * k) for k in range(len(freqs))]))
    y += 0.3 * hp(imp, 2500)
    return unit(y)


def whoosh(n, r, fc, q=1.2, slope=-1.0):
    x = colored(n, r, slope)
    return unit(tvf(x, fc, q, "bp"))


# ----------------------------------------------------------------- reverb
_IR_CACHE = {}


def make_ir(dur, rt_low, rt_high, seed, stereo=True, predelay=0.012, er=10,
            lpf=9000, metallic=None):
    key = (dur, rt_low, rt_high, seed, stereo, predelay, er, lpf, str(metallic))
    if key in _IR_CACHE:
        return _IR_CACHE[key]
    r = np.random.default_rng(seed)
    n = N(dur)
    t = T(n)
    rt_mid = 0.5 * (rt_low + rt_high)
    chans = []
    for ch in range(2 if stereo else 1):
        w = r.standard_normal(n)
        lo = lp(w, 350, 2)
        hi = hp(w, 2800, 2)
        mid = w - lo - hi
        ir = (lo * np.exp(-6.91 * t / rt_low) + mid * np.exp(-6.91 * t / rt_mid)
              + hi * np.exp(-6.91 * t / rt_high))
        ir *= 1 - np.exp(-t / 0.012)
        for _ in range(er):
            i = int(r.uniform(0.002, 0.07) * SR)
            ir[i] += r.choice([-1, 1]) * r.uniform(2, 6)
        ir = lp(ir, lpf, 2)
        if metallic:
            for f in metallic:
                ir = peq(ir, f * r.uniform(0.97, 1.03), 9, 7)
        ir = np.concatenate([np.zeros(N(predelay)), ir])
        ir *= np.concatenate([np.ones(len(ir) - N(0.05)), np.cos(0.5 * np.pi * np.arange(N(0.05)) / N(0.05)) ** 2])
        ir /= np.sqrt(np.sum(ir ** 2))
        chans.append(ir)
    ir = np.array(chans) if stereo else chans[0]
    _IR_CACHE[key] = ir
    return ir


def ir_hall(stereo=True):
    return make_ir(5.0, 5.5, 2.2, 101, stereo, predelay=0.03, lpf=7000)


def ir_room(stereo=False):
    return make_ir(0.9, 0.7, 0.35, 202, stereo, predelay=0.004, lpf=9000)


def ir_metal(stereo=False):
    return make_ir(1.4, 1.1, 0.6, 303, stereo, predelay=0.006, lpf=10000,
                   metallic=[180, 420, 870, 1630, 2950])


def ir_big(stereo=False):
    return make_ir(3.5, 3.2, 1.4, 404, stereo, predelay=0.02, lpf=7000)


def reverb(x, ir, wet=0.3, dry=1.0):
    """Linear (non-circular) reverb; output extends by len(ir)-1."""
    x = np.asarray(x, float)
    n = x.shape[-1]
    m = ir.shape[-1]
    if ir.ndim == 2 and x.ndim == 1:
        w = np.stack([signal.oaconvolve(x, ir[c]) for c in range(2)])
        d = np.stack([x, x])
    elif ir.ndim == 2:
        w = np.stack([signal.oaconvolve(x[c], ir[c]) for c in range(2)])
        d = x
    elif x.ndim == 2:
        w = np.stack([signal.oaconvolve(x[c], ir) for c in range(2)])
        d = x
    else:
        w = signal.oaconvolve(x, ir)
        d = x
    out = wet * w
    out[..., :n] += dry * d
    return out


def reverb_circ(x, ir, wet=0.3, dry=1.0):
    """Exact circular convolution reverb for seamless loops."""
    x = np.asarray(x, float)
    L = x.shape[-1]

    def fold(h):
        m = len(h)
        k = -(-m // L)
        hp_ = np.zeros(k * L)
        hp_[:m] = h
        return hp_.reshape(k, L).sum(0)

    def cconv(a, h):
        return np.fft.irfft(np.fft.rfft(a) * np.fft.rfft(fold(h)), L)

    if ir.ndim == 2:
        xs = x if x.ndim == 2 else np.stack([x, x])
        w = np.stack([cconv(xs[c], ir[c]) for c in range(2)])
        d = xs
    else:
        if x.ndim == 2:
            w = np.stack([cconv(x[c], ir) for c in range(2)])
        else:
            w = cconv(x, ir)
        d = x
    return dry * d + wet * w


# ----------------------------------------------------------------- stereo
def pan(x, p):
    p = np.clip(p, -1, 1)
    a = (p + 1) * np.pi / 4
    return np.stack([x * np.cos(a), x * np.sin(a)])


def mono_bass(st, fc=120.0, periodic=False):
    m = 0.5 * (st[0] + st[1])
    s = 0.5 * (st[0] - st[1])
    s = hp(s, fc, 4, periodic)
    return np.stack([m + s, m - s])


def place(buf, sig, t, gain=1.0, wrap=False, p=None):
    """Add sig into buf at time t. Mono sig into stereo buf is panned (p)."""
    if buf.ndim == 2 and sig.ndim == 1:
        sig = pan(sig, 0.0 if p is None else p)
    L = buf.shape[-1]
    m = sig.shape[-1]
    pos = int(round(t * SR))
    if wrap:
        pos %= L
        k = 0
        while k < m:
            c = min(m - k, L - pos)
            buf[..., pos:pos + c] += gain * sig[..., k:k + c]
            k += c
            pos = 0
    else:
        if pos >= L:
            return buf
        if pos < 0:
            sig = sig[..., -pos:]
            m = sig.shape[-1]
            pos = 0
        c = min(m, L - pos)
        buf[..., pos:pos + c] += gain * sig[..., :c]
    return buf


def wrap_add(x, L):
    """Fold a long rendering onto a loop of length L (tails wrap to head)."""
    out = np.zeros(x.shape[:-1] + (L,))
    n = x.shape[-1]
    for s in range(0, n, L):
        c = min(L, n - s)
        out[..., :c] += x[..., s:s + c]
    return out


# ---------------------------------------------------------------- dynamics
def limit(x, reduce_db=4.0, win=0.025, periodic=False):
    """Smooth peak limiter: pulls the top `reduce_db` of peaks down to a ceiling.
    Gain = box-smoothed (twice) min-filtered gain curve, which is guaranteed to stay
    at or below the instantaneous required gain (no overs) and has no steps.
    periodic=True wraps the filters around the loop."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    a = np.max(np.abs(x), axis=0) if x.ndim == 2 else np.abs(x)
    thr = a.max() * db(-reduce_db)
    g = np.minimum(1.0, thr / np.maximum(a, 1e-12))
    w = N(win)
    mode = "wrap" if periodic else "nearest"
    g = minimum_filter1d(g, 2 * w + 1, mode=mode)
    g = uniform_filter1d(g, w, mode=mode)
    g = uniform_filter1d(g, w, mode=mode)
    return x * g


# ---------------------------------------------------------------- finish
def finish_oneshot(x, peak_db=-1.0, fin=0.003, fout=None, hpf=25.0, lpf=14000.0,
                   trim_db=-70.0):
    x = np.asarray(x, float)
    if hpf:
        x = hp(x, hpf, 2)
    if lpf:
        x = lp(x, lpf, 4)
    env_ = np.max(np.abs(x), axis=0) if x.ndim == 2 else np.abs(x)
    thr = env_.max() * db(trim_db)
    idx = np.nonzero(env_ > thr)[0]
    end = min(x.shape[-1], idx[-1] + N(0.01)) if len(idx) else x.shape[-1]
    x = x[..., :end]
    n = x.shape[-1]
    if fout is None:
        fout = min(0.06, 0.2 * n / SR)
    x = fade(x, fin, fout)
    # DC removal with a smooth window after fading (hann ends at 0 -> ends stay silent)
    w = np.hanning(n)
    x = x - np.multiply.outer(x.sum(-1) / w.sum(), w) if x.ndim == 2 else x - w * (x.sum() / w.sum())
    return norm(x, db(peak_db))


def finish_loop(x, peak_db=-1.0, hpf=20.0, lpf=None):
    x = np.asarray(x, float)
    if hpf:
        x = hp(x, hpf, 2, periodic=True)
    if lpf:
        x = lp(x, lpf, 4, periodic=True)
    x = x - x.mean(axis=-1, keepdims=True)
    return norm(x, db(peak_db))


# ------------------------------------------------------------------- I/O
def write_flac(path, x):
    x = np.asarray(x, float)
    ch = 1 if x.ndim == 1 else x.shape[0]
    pcm = np.clip(np.round(x * 32767.0), -32768, 32767).astype("<i2")
    if ch == 2:
        pcm = pcm.T.copy()
    cmd = [FFMPEG, "-y", "-loglevel", "error", "-f", "s16le", "-ar", str(SR), "-ac", str(ch),
           "-i", "pipe:0", "-c:a", "flac", "-compression_level", "8", "-sample_fmt", "s16", path]
    subprocess.run(cmd, input=pcm.tobytes(), check=True)
