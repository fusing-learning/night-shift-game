"""Music + ambience loops (stereo) and mono ambience loops.

All loops are built periodic by construction (see dsp.py docstring):
quantised oscillator frequencies, circular filters / reverbs, wrapped events.
Tonal centre: D (D1 36.71 Hz / D2 73.42 Hz), phrygian/locrian colours.
"""
import numpy as np
from dsp import *
from registry import snd
from sfx_world import small_hits
from sfx_monsters import bubbles

D1, D2 = 36.708, 73.416


def lfo(t, P, k, ph=0.0):
    return np.sin(TAU * (k * t / P + ph))


# ============================================================ instruments
def mbox_note(f, r, vel=1.0, dur=None):
    tau0 = 1.9 * (523.25 / f) ** 0.6
    dur = dur or min(6.0, tau0 * 5)
    n = N(dur)
    t = T(n)
    sag = 1 + 0.004 * np.exp(-t / 0.02)
    ratios = [1, 2.0, 3.0, 5.93, 9.7, 14.3]
    amps = [1, 0.22, 0.06, 0.16, 0.06, 0.025]
    taus = [tau0, tau0 * 0.45, tau0 * 0.3, 0.18, 0.08, 0.04]
    y = np.zeros(n)
    for ra, a, tk in zip(ratios, amps, taus):
        if f * ra > 15000:
            continue
        y += a * np.exp(-t / tk) * np.sin(TAU * phase(f * ra * sag, n) + r.uniform(0, TAU))
    y *= 1 - np.exp(-t / 0.0007)
    y += 0.10 * click(n, r, 3000, 10000, 0.0015)
    return y * vel


def wow(x, P=None, depth=0.0015, rate=0.35, ph=0.0, flutter=0.00015):
    n = len(x)
    t = T(n)
    if P:
        rate = qf(rate, P)
        fr = qf(7.3, P)
    else:
        fr = 7.3
    d = depth * (1 + np.sin(TAU * (rate * t + ph))) + flutter * (1 + np.sin(TAU * fr * t))
    pos = np.arange(n) - d * SR
    if P:
        return np.interp(np.mod(pos, n), np.arange(n + 1), np.concatenate([x, x[:1]]))
    return np.interp(pos, np.arange(n), x, left=0.0)


def kick(r, f0=150, f1=45, drive=3.0, dur=0.45):
    n = N(dur)
    y = thump(n, f0, f1, 0.035, 0.16) + 0.25 * click(n, r, 1500, 8000, 0.003) + 0.2 * burst(n, r, 0.03, None, 300)
    return sat(y, drive)


def anvil(r, f0=None):
    n = N(0.9)
    y = 0.7 * metal_hit(n, r, f0 or r.uniform(380, 460), 0.3, "bar", noise=0.5) * ad(n, 0.0005, 0.35)
    y += 0.6 * burst(n, r, 0.05, 800, 6000) + 0.5 * thump(n, 220, 140, 0.01, 0.05)
    return sat(y, 1.5)


def pipe(r, f0):
    return metal_hit(N(0.6), r, f0, 0.2, "pipe", noise=0.2) * 0.5


def hat(r, tau=0.03):
    n = N(0.15)
    y = unit(hp(r.standard_normal(n), 7000)) * ad(n, 0.0005, tau)
    y += 0.4 * unit(modal(n, r, 3500, rand_ratios(r, 8, 0.2, 0.9), tau * 1.5))
    return lp(y, 12000)


def tom(r, f0):
    n = N(0.8)
    y = thump(n, f0 * 1.9, f0, 0.04, 0.3) + 0.3 * burst(n, r, 0.04, None, 900)
    return sat(y, 2)


def bass(f, dur, r, drive=3.0):
    n = N(dur + 0.05)
    t = T(n)
    y = osc("saw", f, n) + 0.6 * osc("square", f / 2, n) + 0.3 * osc("saw", f * cents(8), n)
    y = tvf(y, 180 + 1800 * np.exp(-t / 0.06), 2.0, "lp")
    y = sat(unit(y) * 0.8, drive)
    return y * env([(0, 0), (0.003, 1), (dur, 0.8), (dur + 0.04, 0)], n)


def stab(freqs, dur, r):
    n = N(dur + 0.4)
    t = T(n)
    y = sum(supersaw(f, n, r, 3, 10) for f in freqs)
    y = tvf(y, 400 + 3000 * (1 - np.exp(-t / 0.02)) * np.exp(-t / 0.25), 1.0, "lp")
    y = sat(unit(y) * 0.7, 1.8)
    return y * env([(0, 0), (0.015, 1), (dur, 0.6), (dur + 0.35, 0)], n)


def riser(r, dur):
    n = N(dur)
    t = T(n)
    fc = 300 * (6000 / 300) ** (t / dur)
    y = whoosh(n, r, fc, 2.5, -1) * env_db([(0, -40), (dur, 0)], n)
    return fade(y, 0.01, 0.01)


def crash(r):
    n = N(2.5)
    y = unit(hp(r.standard_normal(n), 3000)) + 0.5 * unit(modal(n, r, 3100, rand_ratios(r, 20, 0.05, 0.3), 0.8))
    y = lp(y, 10000) * ad(n, 0.001, 0.6)
    dn = whoosh(n, r, 6000 * (300 / 6000) ** np.clip(T(n) / 1.5, 0, 1), 1.5, -1) * ad(n, 0.01, 0.5)
    return 0.6 * y + 0.5 * dn


def strings(freqs, dur, r, rise=35.0):
    n = N(dur)
    t = T(n)
    rs = cents(rise * (t / dur) ** 1.5)
    out = np.zeros((2, n))
    for ch in range(2):
        y = np.zeros(n)
        for f in freqs:
            vib = 1 + 0.004 * np.sin(TAU * phase(5 + r.uniform(-0.5, 0.5), n) + r.random() * TAU) * np.clip(t / 2, 0, 1)
            for k in range(3):
                y += osc("saw", f * rs * vib * cents(r.uniform(-7, 7)), n, r.random())
        y = lp(y, 1800, 2)
        y = hp(peq(y, 700, 3, 1), 120)
        out[ch] = unit(y)
    return out


def choir(freqs, dur, r, vowel="a", fscale=1.0):
    n = N(dur)
    t = T(n)
    out = np.zeros((2, n))
    for ch in range(2):
        src = np.zeros(n)
        for f in freqs:
            for k in range(3):
                vib = 1 + 0.006 * np.sin(TAU * phase(5.2 + r.uniform(-0.6, 0.6), n) + r.random() * TAU)
                vib *= 1 + 0.002 * smooth_rand(n, r, 4)
                src += osc("saw", f * cents(r.uniform(-10, 10)) * vib, n, r.random())
        src += 0.15 * r.standard_normal(n) * np.sqrt(len(freqs))
        fr = [(f * fscale, bw, g) for f, bw, g in VOWELS[vowel]]
        y = resbank(src, [a for a, _, _ in fr], [a / b for a, b, _ in fr], np.array([g for _, _, g in fr]))
        out[ch] = unit(lp(y, 5000))
    return out * env([(0, 0), (min(1.5, dur / 3), 1), (dur - min(1.5, dur / 3), 1), (dur, 0)], n)


def siren(fpath, n, r):
    t = T(n)
    f = fpath * (1 + 0.012 * np.sin(TAU * 5.5 * t))
    y = osc("tri", f, n) + 0.3 * osc("saw", f, n) + 0.5 * osc("sine", f, n)
    y = sat(y, 2)
    y = bp(y, 300, 5000)
    return unit(peq(y, 1200, 4, 1))


def heart(r, lp_f=180):
    n = N(0.5)
    y = thump(n, 70, 42, 0.03, 0.1) + 0.3 * burst(n, r, 0.03, None, 150)
    return lp(y, lp_f)


def tick(r, f=None):
    n = N(0.08)
    return unit(modal(n, r, f or r.uniform(2800, 5000), rand_ratios(r, 4), 0.008)) + 0.4 * click(n, r, 3000, 10000)


def rev_swell(r, dur=2.5, f0=98):
    n = N(1.2)
    hit = metal_hit(n, r, f0, 0.8, "bell", noise=0.3) + 0.5 * bowed(n, r, [f0 * 2, f0 * 2.12, f0 * 2.83], 200)
    hit = hit * ad(n, 0.001, 0.4)
    w = reverb(hit, ir_hall(True), 1.0, 0.4)[:, :N(dur)]
    w = w[:, ::-1] * np.linspace(0, 1, N(dur)) ** 1.5
    return fade(w, 0.005, 0.004)


def glass_cluster(freqs, dur, r, att, rel):
    n = N(dur)
    t = T(n)
    y = np.zeros(n)
    for f in freqs:
        for dc in (-5, 5):
            y += np.sin(TAU * f * cents(dc + r.uniform(-2, 2)) * t + r.random() * TAU)
    y *= 1 + 0.25 * np.sin(TAU * r.uniform(3, 5) * t)
    return unit(y) * env([(0, 0), (att, 1), (dur - rel, 0.8), (dur, 0)], n)


def finish_music(out, P=None, reduce_db=4.0):
    out = mono_bass(out, 120, periodic=bool(P))
    out = lp(out, 14000, 2, periodic=bool(P))
    return limit(out, reduce_db, periodic=bool(P))


# ============================================================== AMBIENCE
@snd("amb_factory", 1, gain=0.45, loop=True, folder="music")
def amb_factory(v, r):
    P = 60.0
    L = N(P)
    t = T(L)
    out = np.zeros((2, L))
    for ch in range(2):
        rum = colored(L, r, -6, lo=22, hi=180) * (0.75 + 0.25 * lfo(t, P, 2, 0.3 * ch) + 0.1 * lfo(t, P, 7, 0.1))
        air = colored(L, r, -3, lo=250, hi=2200) * (0.6 + 0.4 * lfo(t, P, 3, 0.5 * ch))
        air = tvf(air, 600 * 2 ** (1.2 * lfo(t, P, 1, 0.2 + 0.3 * ch)), 0.8, "lp", periodic=True)
        out[ch] = 0.5 * rum + 0.12 * air
    hum = np.zeros(L)
    for k, a in [(1, 1), (2, 0.5), (3, 0.35), (4, 0.2), (6, 0.08)]:
        hum += a * osc("sine", qf(D2 * k, P), L, r.random()) + a * 0.8 * osc("sine", qf(D2 * k * 1.0037, P), L, r.random())
    hum += 0.25 * osc("sine", qf(110.0, P), L) + 0.2 * osc("sine", qf(110.35, P), L)
    hum *= 0.7 + 0.3 * lfo(t, P, 1, 0.6)
    out += pan(0.09 * unit(hum), -0.1)
    bz = hp(osc("saw", qf(146.83, P), L) + 0.5 * osc("square", qf(293.66, P), L), 900, 2, periodic=True)
    bz = lp(bz, 5000, 2, periodic=True)
    bz *= np.clip(0.5 + 0.5 * lfo(t, P, 4, 0.2) + 0.4 * smooth_rand(L, r, 3, periodic=True), 0, 1) ** 2
    out += pan(0.02 * unit(bz), 0.6)

    ev = np.zeros((2, L))
    # far metallic groans
    for tt in [7.0, 23.5, 41.0, 53.0]:
        gn = N(r.uniform(2.0, 3.2))
        g = creak(gn, r, env([(0, 15), (gn / SR / 2, r.uniform(40, 70)), (gn / SR, 12)], gn),
                  list(np.array([110, 230, 410, 690]) * r.uniform(0.8, 1.2)), 10)
        g += 0.7 * bowed(gn, r, list(np.array([97, 151, 233, 337]) * r.uniform(0.85, 1.15)), 70)
        g = lp(g, 2500) * env([(0, 0), (0.4, 1), (gn / SR - 0.5, 0.6), (gn / SR, 0)], gn)
        place(ev, unit(g) * 0.5, tt, wrap=True, p=r.uniform(-0.8, 0.8))
    # single clanks
    for tt in [15.2, 34.7, 48.3]:
        cn = N(1.2)
        c = metal_hit(cn, r, r.uniform(140, 320), 0.5, "pipe" if r.random() < 0.5 else "plate", noise=0.3)
        place(ev, lp(c, 3000) * 0.6, tt, wrap=True, p=r.uniform(-0.9, 0.9))
    # sparse drips (some clustered)
    for tt in [3.1, 3.9, 11.4, 19.8, 20.35, 29.0, 37.2, 45.6, 46.1, 46.9, 57.5]:
        dn = N(0.15)
        d = bubble(dn, r, r.uniform(900, 1500), 0.05, 2.0, 0.015) + 0.2 * unit(modal(dn, r, r.uniform(2200, 3200), [1, 2.4, 3.9], 0.03))
        place(ev, d * r.uniform(0.4, 0.7), tt, wrap=True, p=r.uniform(-1, 1))
    ev = reverb_circ(ev, ir_hall(True), 1.0, 0.15)
    out += lp(ev, 6000, 2, periodic=True)
    return finish_music(out, P)


@snd("amb_furnace", 1, gain=0.4, loop=True, folder="music")
def amb_furnace(v, r):
    P = 20.0
    L = N(P)
    t = T(L)
    breath = 1 + 0.3 * lfo(t, P, 5) + 0.15 * lfo(t, P, 13, 0.3) + 0.2 * smooth_rand(L, r, 2, periodic=True)
    roar = colored(L, r, -4, lo=40, hi=1500)
    roar = tvf(roar, 700 * 2 ** (0.8 * smooth_rand(L, r, 1.5, periodic=True) * 3), 0.9, "lp", periodic=True)
    rum = colored(L, r, -6, lo=22, hi=140)
    hs = colored(L, r, -1, lo=1500, hi=6000)
    y = unit(roar) * breath + 0.7 * unit(rum) * (0.8 + 0.2 * lfo(t, P, 3)) + 0.1 * hs * breath
    cr = np.zeros(L)
    for tt in poisson_times(r, P, 22):
        cn = N(r.uniform(0.003, 0.012))
        p_ = bp(r.standard_normal(cn + 200), 1000, 6000)[:cn] * ad(cn, 0.0003, cn / SR / 4)
        place(cr, p_ * r.random() ** 2.5, tt, wrap=True)
    y += 0.5 * unit(cr) * 0.4
    return finish_loop(y)


@snd("amb_alarm", 1, gain=0.35, loop=True, folder="music")
def amb_alarm(v, r):
    P = 4.0
    L = N(P)
    t = T(L)
    fa, fb = 293.66, 415.30
    sel = 0.5 + 0.5 * np.tanh(np.sin(TAU * t / P) * 12)
    f = fix_cycles(fb + (fa - fb) * sel, L)
    y = osc("saw", f, L) + 0.7 * osc("square", f * 1.003, L, pw=0.4)
    y = sat(y * 1.2, 4)
    y = peq(y, 800, 6, 1.5, periodic=True)
    y = peq(y, 1600, 4, 2, periodic=True)
    y = lp(y, 3500, 2, periodic=True)
    a = 0.55 + 0.45 * np.abs(np.sin(TAU * t / P)) ** 0.6
    y = unit(y) * a
    y = reverb_circ(y, ir_big(False), 0.9, 0.45)
    y = lp(y, 2500, 2, periodic=True)
    return finish_loop(y, hpf=80)


@snd("amb_boss_breath", 1, gain=0.55, loop=True, folder="music")
def amb_boss_breath(v, r):
    P = 8.0
    L = N(P)
    y = np.zeros(L)
    inn = N(3.2)
    ti = T(inn)
    ie = env([(0, 0), (1.2, 0.7), (2.8, 1), (3.2, 0)], inn)
    ins = tvf(colored(inn, r, -2), 400 + 500 * ti / 3.2, 1.2, "bp") + 0.6 * whisper(inn, r, "o", 0.55)
    ins = unit(ins) * ie
    ins *= 0.75 + 0.25 * (0.5 + 0.5 * np.sin(TAU * 22 * ti))
    ins += 0.3 * bubbles(inn, r, 8, 100, 300) * ie
    place(y, ins * 0.6, 0.3, wrap=True)
    exn = N(3.6)
    te = T(exn)
    ee = env([(0, 0), (0.3, 1), (2.6, 0.7), (3.6, 0)], exn)
    f0 = 32 * (1 + 0.1 * smooth_rand(exn, r, 4))
    ex = voice(exn, r, f0, [(0, "a"), (3.6, "o")], 0.5, 0.2, 0.4, 0.5, 1.5, 600)
    ex = unit(ex) + 0.8 * unit(lp(r.standard_normal(exn), 900))
    rat = resbank(pulses(24 * (1 + 0.1 * smooth_rand(exn, r, 3)), exn, r, 0.2, 0.5), [430, 1180, 2210, 3170], 25)
    ex = unit(ex) + 0.4 * unit(rat) + 0.3 * unit(wet_clicks(exn, r, 60, 200, 1500))
    place(y, unit(ex) * ee, 4.0, wrap=True)
    y = reverb_circ(y, ir_big(False), 0.25)
    return finish_loop(y, hpf=25)


@snd("heartbeat", 1, gain=0.6, loop=True, folder="sfx")
def heartbeat(v, r):
    P = 1.2
    L = N(P)
    y = np.zeros(L)
    place(y, heart(r), 0.25, wrap=True)
    place(y, heart(r) * 0.75, 0.53, wrap=True)
    return finish_loop(y, hpf=25)


# ================================================================= MUSIC
def drone_bed(P, r, level=1.0, bright=1.0):
    L = N(P)
    t = T(L)
    out = np.zeros((2, L))
    sub = osc("sine", qf(D1, P), L) * (0.75 + 0.25 * lfo(t, P, 2, 0.1))
    out += pan(0.5 * sub, 0)
    for ch in range(2):
        s = np.zeros(L)
        for f, a in [(D2, 1), (110.0, 0.45), (146.83, 0.3)]:
            for k in range(3):
                s += a * osc("saw", qf(f * cents(r.uniform(-9, 9)), P), L, r.random())
        cut = 160 * 2 ** (2.4 * bright * (0.5 + 0.5 * lfo(t, P, 1, 0.25 + 0.1 * ch))) * (1 + 0.15 * lfo(t, P, 3, 0.2 * ch))
        s = tvf(s, cut, 1.4, "lp", periodic=True)
        out[ch] += 0.35 * unit(s)
    return out * level


@snd("mus_drone", 1, gain=0.4, loop=True, folder="music")
def mus_drone(v, r):
    P = 64.0
    L = N(P)
    t = T(L)
    out = drone_bed(P, r)
    send = np.zeros((2, L))
    tones = [(146.83, 0, 20, 0.5, -0.3), (220.0, 8, 16, 0.35, 0.4), (311.13, 20, 12, 0.4, 0.5),
             (155.56, 22, 10, 0.3, -0.5), (207.65, 40, 12, 0.4, -0.4), (415.30, 42, 10, 0.25, 0.3),
             (349.23, 52, 10, 0.3, 0.2), (130.81, 56, 10, 0.3, -0.2)]
    for f, c, w, a, p in tones:
        b = bowed(L, r, [f, f * 2.005, f * 3.01], q=350, periodic=True, amps=[1, 0.4, 0.15])
        b = b * bump(t, c, w, P) * a
        send += pan(b, p) * 0.5
        out += pan(b, p) * 0.25
    for c, fr, p in [(12, [1174.66, 1244.51, 1760.0], -0.5), (33, [1244.51, 1661.22, 2349.3], 0.5),
                     (52, [1174.66, 1661.22, 2489.0], 0.0)]:
        g = glass_cluster(fr, 9.0, r, 3.5, 5.0)
        place(send, g * 0.1, c - 3.5, wrap=True, p=p)
    for tt in (6.0, 38.0):
        bn = N(3.0)
        bm = lp(thump(bn, 55, 34, 0.1, 0.8) + 0.5 * burst(bn, r, 0.4, None, 200), 300)
        place(send, bm * 0.5, tt, wrap=True)
    for ch in range(2):
        out[ch] += 0.06 * colored(L, r, -6, lo=40, hi=500) * (0.6 + 0.4 * lfo(t, P, 3, 0.3 * ch))
    out += reverb_circ(send, ir_hall(True), 1.0, 0.0) * 0.8 + send * 0.3
    return finish_music(out, P)


@snd("mus_tension", 1, gain=0.5, loop=True, folder="music")
def mus_tension(v, r):
    P = 36.0
    L = N(P)
    t = T(L)
    beat = 0.75
    bar = 3.0
    out = np.zeros((2, L))
    send = np.zeros((2, L))
    # sub + low bowed drone glue
    out += pan(0.25 * osc("sine", qf(D1, P), L) * (0.8 + 0.2 * lfo(t, P, 3)), 0)
    dr = bowed(L, r, [D2, 110.0], 300, periodic=True)
    out += pan(0.12 * dr, 0)
    # heartbeat pulse
    for b in range(48):
        tb = b * beat
        acc = 1.0 if b % 4 == 0 else 0.8
        place(out, heart(r) * 0.8 * acc, tb, wrap=True)
        place(out, heart(r) * 0.55 * acc, tb + 0.22, wrap=True)
    # ticking / scraping metallic rhythm
    for br in range(12):
        rb = np.random.default_rng(1000 + br % 4)
        for s in range(16):
            ts = br * bar + s * bar / 16
            reg = (br % 4 == 3 and s % 4 == 0)
            if rb.random() < 0.38 or reg or s in (2, 10):
                g = (0.35 if s % 4 == 2 else 0.2) * (1.3 if reg else 1)
                place(out, tick(r) * g * 0.35, ts + r.uniform(-0.004, 0.004), wrap=True, p=0.5 if s % 2 else -0.5)
        if br % 2 == 1:
            sn = N(1.4)
            sc = creak(sn, r, env([(0, 30), (0.7, 90), (1.4, 40)], sn), list(np.array([900, 1500, 2600]) * r.uniform(0.85, 1.15)), 12)
            sc = sc * env([(0, 0), (0.3, 1), (1.0, 0.6), (1.4, 0)], sn)
            place(send, sc * 0.18, br * bar + 1.875, wrap=True, p=r.uniform(-0.8, 0.8))
    # rising cluster swells (3 phrases of 4 bars)
    clusters = [[mtof(50), mtof(51), mtof(57)],
                [mtof(50), mtof(51), mtof(56), mtof(62)],
                [mtof(50), mtof(51), mtof(56), mtof(57), mtof(62), mtof(63)]]
    for i, cl in enumerate(clusters):
        d = 12.0
        s = strings(cl, d, r, rise=30 + 10 * i)
        e = env_db([(0, -50), (d - 1.5, -3), (d - 0.4, 0), (d - 0.06, 0), (d, -90)], N(d))
        s = s * e * (0.25 + 0.05 * i)
        place(out, s * 0.6, i * 12.0, wrap=True)
        place(send, s * 0.5, i * 12.0, wrap=True)
        place(send, rev_swell(r, 2.5, 98 + 10 * i) * 0.12, (i + 1) * 12.0 - 2.5, wrap=True)
    out += reverb_circ(send, ir_hall(True), 1.0, 0.0) + send * 0.4
    return finish_music(out, P, 7.0)


@snd("mus_combat", 1, gain=0.55, loop=True, folder="music")
def mus_combat(v, r):
    P = 38.4
    L = N(P)
    t = T(L)
    step = 0.15
    bar = 2.4
    out = np.zeros((2, L))
    room = np.zeros((2, L))
    hall = np.zeros((2, L))
    out += pan(0.18 * osc("sine", qf(D1, P), L), 0)
    dr = np.zeros(L)
    for k in range(3):
        dr += osc("saw", qf(55.0 * cents(r.uniform(-8, 8)), P), L, r.random())
    out += pan(0.08 * unit(lp(dr, 220, 2, periodic=True)), 0)
    A = [0, 0, 12, 0, 0, 0, 1, 0, 0, 0, 12, 0, 6, 0, 1, 0]
    roots = [0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 0, 0, 6, 6, 0, 0]
    for b in range(16):
        tb = b * bar
        fill = b in (7, 11, 15)
        intro = b < 4
        ks = [0, 8] + ([10] if b % 2 else []) if intro else ([0, 3, 6, 8, 10, 12, 13, 14, 15] if fill else [0, 3, 8, 10])
        for s in ks:
            place(out, kick(r) * (0.9 if s in (0, 8) else 0.7), tb + s * step, wrap=True)
        for s in [4, 12] + ([14, 15] if fill else []):
            a = anvil(r) * (0.6 if intro else 0.9) * (0.7 if s > 12 else 1)
            place(out, a * 0.55, tb + s * step, wrap=True, p=0.1)
            place(room, a * 0.3, tb + s * step, wrap=True, p=0.1)
        rp = np.random.default_rng(77 + b % 4)
        for s in [2, 7, 11, 15]:
            if rp.random() < 0.55:
                place(out, pipe(r, [233.1, 311.1, 207.7][rp.integers(3)]) * 0.3, tb + s * step, wrap=True, p=rp.uniform(-0.7, 0.7))
        if b >= 2:
            for s in range(16):
                g = 0.22 if s % 4 == 2 else 0.1
                place(out, hat(r, 0.05 if s % 4 == 2 else 0.02) * g * (1.2 if not intro else 0.8), tb + s * step + 0.004, wrap=True,
                      p=0.35 if s % 2 else -0.25)
        # bass ostinato
        root = roots[b]
        for s in range(16):
            if b < 2 and s not in (0, 8):
                continue
            if b == 15 and s >= 8:
                note = [6, 6, 7, 7, 1, 1, 0, 0][s - 8]
            else:
                note = A[s] + root
            if s in (5, 9) and not fill:
                continue
            dur = step * (3.6 if (b < 2) else 0.85)
            place(out, bass(D2 * 2 ** (note / 12), dur, r) * 0.32, tb + s * step, wrap=True)
        if b >= 4 and b % 2 == 0:
            f = D2 * 2 ** (root / 12)
            st = stab([f, f * 1.5, f * 2 ** (13 / 12)], 0.5, r)
            place(out, st * 0.18, tb, wrap=True, p=-0.2)
            place(hall, st * 0.2, tb, wrap=True, p=0.3)
        if b % 4 == 3:
            place(hall, riser(r, bar) * 0.25, tb, wrap=True, p=-0.4 if b % 8 == 3 else 0.4)
        if b % 4 == 0 and b >= 4 or b == 0:
            place(out, crash(r) * 0.18, tb, wrap=True, p=0.2)
            place(hall, crash(r) * 0.1, tb, wrap=True)
    out += reverb_circ(room, ir_metal(True), 1.0, 0.0) * 0.6
    out += reverb_circ(hall, ir_hall(True), 1.0, 0.0) * 0.6 + hall * 0.5
    return finish_music(out, P)


@snd("mus_boss", 1, gain=0.6, loop=True, folder="music")
def mus_boss(v, r):
    P = 48.0
    L = N(P)
    t = T(L)
    step = 0.125
    bar = 2.0
    out = np.zeros((2, L))
    room = np.zeros((2, L))
    hall = np.zeros((2, L))
    out += pan(0.18 * osc("sine", qf(D1, P), L), 0)
    roots = [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 6, 6, 0, 0, 0, 0, 1, 1, 1, 1, 6, 6, 0, 0]
    B8 = [0, 12, 0, 0, 12, 0, 1, 0]
    for b in range(24):
        tb = b * bar
        B = b >= 12
        root = roots[b]
        fill = b in (11, 23)
        ks = [0, 4, 8, 12] + ([6, 14] if B else []) + ([13, 15] if fill else [])
        for s in ks:
            place(out, kick(r, 140, 40, 3.5) * 0.9, tb + s * step, wrap=True)
        ts = ([2, 3, 10, 11, 14, 15] if B else ([10, 11] if b % 2 == 0 else [14]))
        if b in (17, 23):
            ts = ts + list(range(8, 16))
        for s in sorted(set(ts)):
            tm = tom(r, [D2, D2 * 1.335, D2 * 0.75][s % 3]) * (0.55 if B else 0.45)
            place(out, tm, tb + s * step, wrap=True, p=[-0.5, 0.0, 0.5][s % 3])
            place(room, tm * 0.4, tb + s * step, wrap=True)
        for s in [4, 12] + ([7] if B and b % 2 else []):
            a = anvil(r, 420 if s != 7 else 600)
            place(out, a * 0.45, tb + s * step, wrap=True, p=0.15)
            place(room, a * 0.3, tb + s * step, wrap=True)
        for s in range(16 if B else 8):
            ss = s if B else 2 * s
            place(out, hat(r, 0.025) * (0.16 if ss % 4 == 2 else 0.08), tb + ss * step, wrap=True, p=0.3)
        for i, n_ in enumerate(B8):
            place(out, bass(D2 * 2 ** ((n_ + root - 12 * (i % 2 == 0)) / 12), step * 1.7, r, 3.5) * 0.3,
                  tb + i * 2 * step, wrap=True)
        f = D2 * 2 ** (root / 12)
        for s in ([0, 3, 6, 10, 12, 14] if B else [0, 6, 10]):
            st = stab([f, f * 1.5, f * 2, f * 2 ** (13 / 12)], 0.18 if s else 0.35, r)
            place(out, st * (0.16 if B else 0.12), tb + s * step, wrap=True, p=-0.2)
            place(hall, st * 0.1, tb + s * step, wrap=True)
    # sirens
    for b0, p, path in [(4, -0.4, [(0, 74), (3, 80), (5, 75), (8, 74)]), (8, 0.4, [(0, 74), (2.5, 75), (5, 80), (8, 74)]),
                        (12, -0.6, [(0, 74), (2, 80), (4, 81), (8, 74)]), (12, 0.6, [(0, 80), (3, 74), (5, 75), (8, 80)]),
                        (16, -0.3, [(0, 75), (3, 81), (6, 80), (8, 74)]), (20, 0.5, [(0, 74), (2, 80), (5, 86), (8, 80)]),
                        (20, -0.5, [(0, 68), (4, 74), (8, 69)])]:
        sn = N(8.0)
        fp = mtof(env(path, sn, "smooth"))
        sr_ = siren(fp, sn, r) * env([(0, 0), (1.5, 1), (6.5, 0.9), (8, 0)], sn)
        g = 0.07 if b0 < 12 else 0.09
        place(out, sr_ * g, b0 * bar, wrap=True, p=p)
        place(hall, sr_ * g * 1.4, b0 * bar, wrap=True, p=-p)
    # choir clusters
    for b0, notes, vw, g in [(0, [62, 69], "o", 0.10), (4, [62, 69], "o", 0.12), (8, [62, 69, 75], "o", 0.14),
                             (12, [62, 63, 69, 74], "a", 0.17), (16, [62, 63, 69, 74], "a", 0.18),
                             (20, [62, 63, 68, 69, 74], "a", 0.2)]:
        c = choir([mtof(m) for m in notes], 9.0, r, vw)
        place(out, c * g, b0 * bar - 0.5, wrap=True)
        place(hall, c * g, b0 * bar - 0.5, wrap=True)
    for b in (11, 23):
        place(hall, riser(r, bar) * 0.3, b * bar, wrap=True)
        place(out, crash(r) * 0.2, (b + 1) * bar, wrap=True)
    out += reverb_circ(room, ir_metal(True), 1.0, 0.0) * 0.6
    out += reverb_circ(hall, ir_hall(True), 1.0, 0.0) * 0.6 + hall * 0.3
    return finish_music(out, P)


# ---------------------------------------------------------- music box score
TITLE = [(1.0, 69, 1.0), (1.75, 74, .9), (2.5, 77, .95), (3.25, 76, .85), (4.6, 74, .8), (5.4, 69, .6),
         (7.6, 69, .9), (8.35, 74, .85), (9.1, 77, .9), (9.85, 81, 1.0), (10.9, 79, .8), (11.6, 77, .75),
         (12.3, 75, .85), (13.6, 74, .8),
         (16.5, 70, .8), (17.2, 69, .75), (17.9, 68, .85), (18.6, 69, .7), (19.8, 77, .8), (20.5, 76, .75), (21.6, 74, .8),
         (24.2, 69, .9), (24.95, 74, .85), (25.7, 77, .9), (26.45, 76, .8), (27.5, 79, .8), (28.3, 77, .75),
         (29.0, 76, .7), (30.3, 73, .75), (31.5, 74, .9),
         (35.0, 81, .4), (36.4, 75, .35)]
TITLE_LOW = [(1.0, 62, .5), (7.6, 58, .5), (16.5, 55, .5), (24.2, 57, .5), (31.5, 50, .55), (31.55, 57, .4)]
WRONG = {75, 68}


def mbox_score(buf, notes, r, wrap, tscale=1.0, t0=0.0, detune=8.0):
    for tt, m, vel in notes:
        c = r.uniform(-detune, detune) - (14 if m in WRONG else 0)
        nt = mbox_note(mtof(m) * cents(c), r, vel)
        place(buf, nt, t0 + tt * tscale + r.uniform(-0.02, 0.02), wrap=wrap, p=r.uniform(-0.35, 0.35))


@snd("mus_title", 1, gain=0.55, loop=True, folder="music")
def mus_title(v, r):
    P = 40.0
    L = N(P)
    t = T(L)
    mb = np.zeros((2, L))
    mbox_score(mb, TITLE + TITLE_LOW, r, True)
    mb = np.stack([wow(mb[0], P, ph=0.0), wow(mb[1], P, ph=0.15)])
    mb = lp(mb, 9000, 2, periodic=True)
    out = reverb_circ(mb, ir_hall(True), 0.5, 0.8)
    out += drone_bed(P, r, 0.22, 0.6)
    for ch in range(2):
        out[ch] += 0.03 * colored(L, r, -4, lo=40, hi=600)
    return finish_music(out, P)


@snd("mus_ending", 1, gain=0.6, loop=False, folder="music")
def mus_ending(v, r):
    D = 30.5
    n = N(D)
    t = T(n)
    mb = np.zeros((2, n))
    mel = [(0.8, 69, 1), (1.85, 74, .9), (2.9, 77, .95), (3.95, 76, .85), (5.6, 74, .8), (6.9, 69, .6),
           (8.8, 69, .9), (9.85, 74, .85), (10.9, 77, .9), (11.95, 81, 1), (13.3, 79, .8), (14.4, 77, .75),
           (15.5, 76, .75), (17.0, 73, .7), (18.6, 74, .9),
           (18.6, 62, .6), (18.75, 69, .6), (18.9, 74, .7), (19.1, 78, .75), (19.35, 81, .7),
           (22.5, 86, .3), (23.6, 81, .25), (25.4, 78, .2)]
    mbox_score(mb, mel, r, False, detune=5.0)
    mb = np.stack([wow(mb[0], None, ph=0.0), wow(mb[1], None, ph=0.2)])
    pad = np.zeros((2, n))
    for ch in range(2):
        y = np.zeros(n)
        for m, a in [(38, 1), (45, 0.8), (50, 0.6), (57, 0.45), (66, 0.18), (64, 0.1)]:
            for k in range(3):
                y += a * osc("saw", mtof(m) * cents(r.uniform(-6, 6)), n, r.random())
        pad[ch] = unit(lp(y, 900))
    pad *= env_db([(0, -90), (14, -60), (19.5, -2), (21, 0), (29.5, -40), (30.5, -90)], n)
    lowd = np.zeros((2, n))
    for ch in range(2):
        lowd[ch] = unit(lp(sum(osc("saw", f * cents(r.uniform(-6, 6)), n, r.random()) for f in (D2, 110.0)), 300))
    lowd *= env([(0, 0), (3, 0.6), (15, 0.6), (20, 0)], n)
    wind = np.zeros((2, n))
    for ch in range(2):
        w = colored(n, r, -3)
        w = tvf(w, 600 * 2 ** (0.8 * np.sin(TAU * 0.07 * t + ch) + 0.3 * np.sin(TAU * 0.19 * t)), 1.5, "bp")
        wind[ch] = unit(w)
    wind *= env([(0, 0), (3, 1), (25, 0.7), (30.5, 0)], n)
    out = reverb(mb, ir_hall(True), 0.5, 0.8)[:, :n]
    out += 0.25 * pad + 0.12 * lowd + 0.06 * wind
    out *= env_db([(0, 0), (22, 0), (30.0, -50), (30.5, -90)], n)
    return finish_music(out)


@snd("mus_death", 1, gain=0.75, loop=False, folder="music")
def mus_death(v, r):
    D = 6.0
    n = N(D)
    out = np.zeros((2, n))
    hn = N(1.5)
    hit = thump(hn, 60, 30, 0.1, 0.6) + 0.5 * metal_hit(hn, r, 73.4, 0.8, "bell", noise=0.2) + 0.4 * burst(hn, r, 0.3, None, 300)
    hit += 0.3 * bowed(hn, r, [D2, 77.78, 103.83], 200) * ad(hn, 0.001, 0.6)
    w = reverb(hit, ir_hall(True), 1.0, 0.5)[:, :N(2.0)]
    sw = w[:, ::-1] * np.linspace(0, 1, N(2.0)) ** 2
    place(out, fade(sw, 0.005, 0.005) * 0.8, 0.0)
    tn = N(1.2)
    th = thump(tn, 75, 30, 0.04, 0.35) + 0.6 * burst(tn, r, 0.08, None, 250)
    place(out, lp(th, 400), 2.0)
    mb = np.zeros((2, n))
    for tt, m in [(2.45, 69), (2.95, 74), (3.45, 77)]:
        place(mb, mbox_note(mtof(m) * cents(-30), r, 0.9), tt, p=r.uniform(-0.3, 0.3))
    tt_ = T(n)
    rate = np.where(tt_ < 3.0, 1.0, np.clip(1 - (tt_ - 3.0) / 2.3, 0, 1) ** 1.6)
    pos = np.cumsum(rate) - 1
    ts = np.stack([np.interp(pos, np.arange(n), mb[c]) for c in range(2)]) * np.sqrt(rate)
    out += ts * 0.9
    out = reverb(out, ir_hall(True), 0.3, 1.0)[:, :n]
    out *= env([(0, 1), (5.0, 1), (6.0, 0)], n)
    return finish_music(out)
