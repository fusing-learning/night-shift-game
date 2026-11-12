"""Monster vocalisations and foley. Organic, wet, wrong."""
import numpy as np
from dsp import *
from registry import snd
from sfx_player import tail_fade
from sfx_world import small_hits


def splat(n, r, size=1.0, density=400):
    th = thump(n, 130 / size, 50 / size, 0.015, 0.05 * size)
    bu = burst(n, r, 0.035 * size, 200, 1500)
    wc = wet_clicks(n, r, lambda x: density * np.exp(-x / (0.06 * size)), 200, 2200)
    wc = unit(wc) if np.any(wc) else wc
    y = 0.8 * th + 0.8 * bu + 0.5 * wc + 0.2 * burst(n, r, 0.06 * size, 1000, 5000)
    for _ in range(int(3 * size) + 2):
        place(y, 0.3 * bubble(N(0.1), r, r.uniform(150, 450) / size, r.uniform(0.03, 0.08), 1.2), r.uniform(0.01, 0.2 * size))
    return y


def hiss(n, r, lo=1200, center=4500):
    return unit(peq(colored(n, r, 0, lo=lo, hi=11000), center, 5, 0.8) * (1 + 0.25 * smooth_rand(n, r, 40)))


def ringmod(y, f, amt):
    return (1 - amt) * y + amt * y * np.sin(TAU * f * T(len(y)))


# ----------------------------------------------------------------- crawler
@snd("crawler_chitter", 3, gain=0.55)
def crawler_chitter(v, r):
    d = [0.45, 0.6, 0.7][v]
    n = N(d)
    y = np.zeros(n)
    tt = r.uniform(0.0, 0.03)
    while tt < d - 0.08:
        k = r.integers(3, 9)
        rate = r.uniform(28, 48)
        for i in range(k):
            cn = N(0.03)
            c = unit(modal(cn, r, r.uniform(2000, 4500), rand_ratios(r, 4), 0.004)) + 0.6 * click(cn, r, 2000, 9000)
            place(y, c * r.uniform(0.3, 1.0), tt + i / rate + r.uniform(-0.003, 0.003))
        tt += k / rate + r.uniform(0.03, 0.09)
    # mandible rattle
    rat = resbank(pulses(r.uniform(60, 90), n, r, 0.3, 0.5), [2500, 3700, 5100], 6)
    rat = unit(rat) * env([(0, 0), (0.05, 1), (d - 0.05, 0.6), (d, 0)], n) * 0.25
    y = unit(y) + rat
    # squeaks
    for _ in range(r.integers(1, 3)):
        sn = N(r.uniform(0.06, 0.12))
        fa, fb = r.uniform(1700, 2200), r.uniform(2300, 3000)
        sq = voice(sn, r, env([(0, fa), (sn / SR, fb)], sn), "i", 1.6, 0.05, 0.2, 0.0, 0.3, 3000)
        sq = ringmod(sq, r.uniform(150, 400), 0.4) * env([(0, 0), (0.01, 1), (sn / SR, 0)], sn)
        place(y, sq * 0.5, r.uniform(0.02, d - 0.15))
    y = lp(y, 10000)
    y = reverb(y, ir_room(), 0.15)
    return tail_fade(y, d, 0.06)


@snd("crawler_attack", 2, gain=0.7)
def crawler_attack(v, r):
    n = N(0.42)
    f0 = env([(0, 900), (0.05, 2200 - 200 * v), (0.25, 1900), (0.4, 1100)], n)
    s = screech(n, r, f0, rough=0.05, ring=1.37, ring_amt=0.5, bright=3500)
    h = whisper(n, r, "i", 1.5) * 0.5 + hiss(n, r, 2500, 6000) * 0.5
    e = env([(0, 0), (0.004, 1), (0.12, 0.85), (0.4, 0)], n)
    y = (0.6 * s + 0.5 * unit(h)) * e
    y = sat(y * 1.3, 1.8)
    y = lp(y, 10000)
    y = reverb(y, ir_room(), 0.15)
    return tail_fade(y, 0.4, 0.05)


@snd("crawler_death", 2, gain=0.65)
def crawler_death(v, r):
    n = N(0.55)
    y = np.zeros(n)
    sn = N(0.24)
    f0 = env([(0, 2200 + 200 * v), (0.24, 850)], sn) * (1 + 0.03 * np.sin(TAU * 14 * T(sn)))
    sq = voice(sn, r, f0, [(0, "i"), (0.24, "e")], 1.7, 0.06, 0.2, 0.2, 0.3, 3000)
    sq = sq * env([(0, 0), (0.005, 1), (0.21, 0.9), (0.24, 0)], sn)
    place(y, sq * 0.8, 0.0)
    place(y, splat(N(0.3), r, 0.7) * 0.7, 0.19)
    for k in range(3):
        cn = N(0.03)
        place(y, unit(modal(cn, r, r.uniform(2500, 4000), rand_ratios(r, 4), 0.004)) * 0.2, 0.3 + 0.05 * k + r.uniform(0, 0.02))
    y = reverb(y, ir_room(), 0.12)
    return tail_fade(y, 0.5, 0.05)


@snd("crawler_skitter", 3, gain=0.4)
def crawler_skitter(v, r):
    n = N(0.32)
    y = np.zeros(n)
    k = r.integers(8, 15)
    times = np.sort(r.uniform(0.0, 0.27, k))
    for tt in times:
        cn = N(0.05)
        c = unit(modal(cn, r, r.uniform(2500, 5000), rand_ratios(r, 5), 0.006)) + 0.5 * click(cn, r, 3000, 10000)
        c += 0.3 * unit(modal(cn, r, 400, RATIOS["plate"][:6], 0.04))
        place(y, c * r.uniform(0.3, 1.0), tt)
    y = lp(y, 9000)
    y = reverb(y, ir_metal(), 0.08)
    return tail_fade(y, 0.3, 0.04)


# ------------------------------------------------------------------- brute
def growl(n, r, f0, vowels, fscale=0.62, jitter=0.12, sub=0.5, breath=0.6, tilt=900, drive=2.5):
    vc = voice(n, r, f0, vowels, fscale, jitter, 0.35, sub, breath, tilt)
    sb = osc("sine", f0, n) * 0.5
    rb = unit(colored(n, r, -6, lo=30, hi=160)) * 0.3
    return sat(unit(vc + sb + rb) * 0.6, drive)


@snd("brute_growl", 2, gain=0.8)
def brute_growl(v, r):
    n = N(1.25)
    f0 = env([(0, 38), (0.3, 48 + 4 * v), (0.9, 44), (1.2, 34)], n) * (1 + 0.06 * smooth_rand(n, r, 6))
    y = growl(n, r, f0, [(0, "o"), (0.5, "a" if v == 0 else "uh"), (1.1, "u")])
    y *= env([(0, 0), (0.15, 1), (0.9, 0.85), (1.2, 0)], n)
    y = reverb(y, ir_room(), 0.18)
    return tail_fade(y, 1.2, 0.08)


@snd("brute_step", 2, gain=0.7)
def brute_step(v, r):
    n = N(0.45)
    th = 1.2 * thump(n, 75 - 8 * v, 32, 0.03, 0.12) + 0.5 * burst(n, r, 0.04, None, 400)
    pl = unit(modal(n, r, 95, RATIOS["plate"], 0.18)) * 0.3
    rt = small_hits(n, r, 0.02, 0.3, 40, 900, 2500, 0.015, decay=0.1) * 0.3
    y = sat(th + pl + rt, 1.5)
    y = reverb(y, ir_metal(), 0.15)
    return tail_fade(y, 0.4, 0.06)


@snd("brute_charge", 1, gain=0.85)
def brute_charge(v, r):
    n = N(1.45)
    f0 = env([(0, 45), (1.0, 105), (1.4, 95)], n) * (1 + 0.04 * smooth_rand(n, r, 8))
    vc = voice(n, r, f0, [(0, "u"), (0.4, "o"), (0.9, "a")], 0.7, 0.08, 0.3, 0.3, 0.5, 1200)
    roar = unit(bp(colored(n, r, -3), 200, 2000)) * env([(0, 0.2), (1.2, 1)], n)
    dr = env([(0, 1.0), (1.2, 4.0)], n)
    y = np.tanh((vc + 0.4 * roar + 0.4 * osc("sine", f0, n)) * 0.5 * dr)
    y *= env([(0, 0), (0.1, 0.4), (1.15, 1), (1.4, 0)], n)
    y = reverb(y, ir_room(), 0.18)
    return tail_fade(y, 1.4, 0.06)


@snd("brute_slam", 1, gain=0.9)
def brute_slam(v, r):
    n = N(1.0)
    mt = metal_hit(n, r, 70, 0.35, "rand", k=22, bright=0.4, noise=0.3)
    sb = 1.5 * thump(n, 60, 24, 0.06, 0.3)
    cr = burst(n, r, 0.012, 1000, 9000)
    y = 0.8 * mt + sb + 0.5 * cr
    hn = N(0.6)
    hs = hiss(hn, r, 1500, 5000) * env([(0, 0), (0.03, 1), (0.55, 0)], hn)
    place(y, hs * 0.35, 0.12)
    y = sat(y * 0.8, 2)
    y = reverb(y, ir_metal(), 0.3)
    return tail_fade(y, 0.9, 0.12)


@snd("brute_death", 1, gain=0.85)
def brute_death(v, r):
    n = N(2.3)
    y = np.zeros(n)
    gn = N(1.45)
    f0 = env([(0, 75), (0.4, 62), (1.3, 28)], gn) * (1 + 0.05 * smooth_rand(gn, r, 6))
    g = growl(gn, r, f0, [(0, "a"), (0.7, "o"), (1.3, "u")], 0.62, 0.15, 0.6, 0.7) * env([(0, 0), (0.1, 1), (1.1, 0.6), (1.45, 0)], gn)
    place(y, g, 0)
    fn = N(0.8)
    fall = 1.4 * thump(fn, 70, 28, 0.04, 0.2) + 0.5 * metal_hit(fn, r, 85, 0.3, "plate") * ad(fn, 0.001, 0.25)
    fall += small_hits(fn, r, 0.02, 0.4, 40, 700, 2500, 0.02, decay=0.15) * 0.4 + 0.5 * burst(fn, r, 0.05, None, 500)
    place(y, sat(fall, 1.5), 1.35)
    place(y, sat(fall, 1.5) * 0.35, 1.58)
    hn = N(0.8)
    place(y, hiss(hn, r, 1200, 4000) * env([(0, 0), (0.05, 1), (0.8, 0)], hn) * 0.25, 1.45)
    y = reverb(y, ir_room(), 0.18)
    return tail_fade(y, 2.2, 0.15)


# ----------------------------------------------------------------- spitter
def bubbles(n, r, density, fmin=180, fmax=700):
    y = np.zeros(n)
    for tt in poisson_times(r, n / SR, density):
        d = r.uniform(0.02, 0.06)
        place(y, bubble(N(d * 2), r, r.uniform(fmin, fmax), d, r.uniform(0.8, 2.0)) * r.uniform(0.3, 1), tt)
    return y


@snd("spitter_gurgle", 2, gain=0.6)
def spitter_gurgle(v, r):
    n = N(0.95)
    f0 = (85 + 10 * v) * (1 + 0.15 * smooth_rand(n, r, 10))
    vc = voice(n, r, f0, [(0, "o"), (0.4, "u"), (0.8, "o")], 0.85, 0.2, 0.5, 0.3, 0.4, 400)
    vc = vc * (0.5 + 0.5 * np.abs(smooth_rand(n, r, 12)) * 3)
    bb = bubbles(n, r, 35)
    y = 0.6 * unit(vc) + 0.6 * unit(bb)
    y = lp(y, 4000) * env([(0, 0), (0.08, 1), (0.75, 0.8), (0.9, 0)], n)
    y = reverb(y, ir_room(), 0.15)
    return tail_fade(y, 0.9, 0.06)


@snd("spitter_spit", 1, gain=0.65)
def spitter_spit(v, r):
    n = N(0.5)
    y = np.zeros(n)
    hn = N(0.17)
    hk = whisper(hn, r, [(0, "i"), (0.15, "a")], 1.2) * (0.6 + 0.4 * np.sin(TAU * 50 * T(hn))) * env([(0, 0), (0.03, 1), (0.17, 0)], hn)
    place(y, hk * 0.6, 0)
    place(y, splat(N(0.25), r, 0.6) * 0.7, 0.14)
    wn = N(0.32)
    wh = whoosh(wn, r, env([(0, 2500), (0.32, 600)], wn), 1.0) * env([(0, 0), (0.03, 1), (0.32, 0)], wn)
    place(y, wh * 0.4, 0.15)
    y = reverb(y, ir_room(), 0.12)
    return tail_fade(y, 0.45, 0.05)


def sizzle(n, r, tau=0.25):
    s = unit(hp(r.standard_normal(n), 3000)) * 0.4 + unit(crackle(n, r, 700, 2500, 9000))
    return unit(s) * ad(n, 0.01, tau)


@snd("bile_splat", 2, gain=0.6)
def bile_splat(v, r):
    n = N(0.52)
    y = splat(n, r, 0.8 + 0.2 * v) * 0.8
    y += 0.35 * sizzle(n, r, 0.25) + 0.2 * bubbles(n, r, 25, 600, 1500)
    y = reverb(y, ir_room(), 0.1)
    return tail_fade(y, 0.5, 0.08)


@snd("spitter_death", 1, gain=0.7)
def spitter_death(v, r):
    n = N(1.25)
    t = T(n)
    y = np.zeros(n)
    place(y, splat(N(0.4), r, 1.3, 700) * 1.0, 0)
    dn = N(1.05)
    td = T(dn)
    fc = env([(0, 2000), (1.0, 500)], dn)
    fl = 0.5 + 0.5 * np.sin(TAU * phase(45 * np.exp(-td / 0.6) + 10, dn))
    df = tvf(colored(dn, r, -1), fc, 1.5, "bp") * fl * env([(0, 0), (0.04, 1), (0.8, 0.5), (1.05, 0)], dn)
    place(y, unit(df) * 0.45, 0.05)
    place(y, bubbles(N(1.0), r, 20) * 0.4, 0.1)
    y = reverb(y, ir_room(), 0.15)
    return tail_fade(y, 1.2, 0.1)


# ----------------------------------------------------------------- stalker
@snd("stalker_whisper", 3, gain=0.55)
def stalker_whisper(v, r):
    n = N(1.6)
    y = np.zeros(n)
    for voice_i, (fs, amp, off) in enumerate([(0.95, 1.0, 0.0), (1.15, 0.55, 0.07)]):
        seq, tt = [], 0.05 + off
        sylenv = np.zeros(n)
        names = list(VOWELS)
        while tt < 1.4:
            d = r.uniform(0.11, 0.22)
            seq.append((tt, names[r.integers(len(names))]))
            sylenv += bump(T(n), tt + d / 2, d / 1.6) * r.uniform(0.4, 1.0)
            if r.random() < 0.35:
                fr = unit(bp(r.standard_normal(n), *(3000, 7000) if r.random() < 0.5 else (1800, 4000)))
                y += amp * 0.35 * fr * bump(T(n), tt + d + 0.03, 0.04)
            tt += d + r.uniform(0.0, 0.06)
        w = whisper(n, r, seq if len(seq) > 1 else "a", fs) * np.clip(sylenv, 0, 1)
        y += amp * w
    y *= env([(0, 0), (0.08, 1), (1.3, 0.8), (1.5, 0)], n)
    y = hp(y, 180, 2)
    y = reverb(y, ir_big(), 0.3)
    return tail_fade(y, 1.5, 0.15)


@snd("stalker_creak", 2, gain=0.6)
def stalker_creak(v, r):
    n = N(0.62)
    rate = env([(0, 15), (0.25, 60 + 20 * v), (0.5, 25)], n)
    fr = np.array([1700, 2650, 3900, 5200]) * r.uniform(0.9, 1.1)
    y = norm(creak(n, r, rate, fr, 20, 0.5, slip=0.015))
    for _ in range(r.integers(2, 4)):
        place(y, click(N(0.02), r, 3000, 9000) * 0.25, r.uniform(0.05, 0.5))
    y = sat(norm(y) * 4.0, 1.0) * env([(0, 0), (0.03, 1), (0.5, 0.7), (0.6, 0)], n)
    y = reverb(y, ir_room(), 0.08)
    return tail_fade(y, 0.6, 0.05)


@snd("stalker_shriek", 1, gain=0.9)
def stalker_shriek(v, r):
    n = N(0.95)
    t = T(n)
    f0 = env([(0, 1300), (0.06, 1650), (0.6, 1550), (0.9, 1200)], n) * (1 + 0.02 * np.sin(TAU * 9 * t))
    s = screech(n, r, f0, rough=0.04, ring=1.618, ring_amt=0.6, bright=3200)
    ov = np.sin(TAU * phase(f0 * 2.37, n)) * np.sin(TAU * phase(f0 * 0.51, n)) + 0.6 * np.sin(TAU * phase(f0 * 3.11, n))
    br = hiss(n, r, 2000, 5000)
    y = 0.7 * s + 0.3 * ov + 0.25 * br
    y *= env([(0, 0), (0.005, 1), (0.6, 0.8), (0.9, 0)], n)
    y = lp(sat(y, 1.5), 9000)
    y = reverb(y, ir_big(), 0.3)
    return tail_fade(y, 0.9, 0.1)


@snd("stalker_death", 1, gain=0.75)
def stalker_death(v, r):
    n = N(1.3)
    y = np.zeros(n)
    place(y, burst(N(0.05), r, 0.004, 2000, 9000) * 2.0, 0)
    for tt in poisson_times(r, 0.6, lambda x: 200 * np.exp(-x / 0.12)):
        hn = N(0.2)
        h = unit(modal(hn, r, r.uniform(2500, 7000), rand_ratios(r, 6, 0.3, 1.2), r.uniform(0.02, 0.06)))
        place(y, h * r.uniform(0.2, 1.0) * np.exp(-tt / 0.2), tt)
    en = N(0.95)
    ex = whisper(en, r, [(0, "a"), (0.6, "uh"), (0.9, "u")], 0.9) * env([(0, 0), (0.05, 1), (0.95, 0)], en)
    fry = voice(en, r, 60, "uh", 1.0, 0.25, 0.4, 0.4, 0.5, 500) * env([(0, 0), (0.5, 0), (0.7, 1), (0.95, 0)], en)
    place(y, ex * 0.5 + fry * 0.25, 0.25)
    y = reverb(y, ir_room(), 0.2)
    return tail_fade(y, 1.2, 0.1)


# -------------------------------------------------------------------- boss
def furnace_roar(n, r):
    roar = unit(colored(n, r, -2, lo=60, hi=1500)) * (1 + 0.3 * smooth_rand(n, r, 5))
    rum = unit(colored(n, r, -6, lo=25, hi=120))
    cr = unit(crackle(n, r, 300, 1000, 6000))
    return roar + 0.7 * rum + 0.25 * cr


@snd("boss_roar", 2, gain=1.0)
def boss_roar(v, r):
    d = [2.7, 3.0][v]
    n = N(d)
    sm = 1 + 0.05 * smooth_rand(n, r, 6)
    f0s = env([(0, 26), (0.4, 32), (d, 24)], n) * sm
    sub = lp(growl(n, r, f0s, "o", 0.5, 0.15, 0.6, 0.8, 600, 2.0), 400) + 0.6 * osc("sine", f0s, n)
    f0 = env([(0, 70), (0.4, 105 - 10 * v), (d - 0.6, 90), (d, 60)], n) * sm
    mid = voice(n, r, f0, [(0, "o"), (0.5, "a"), (d - 0.5, "a"), (d, "o")], 0.7, 0.08, 0.3, 0.3, 0.5, 1500)
    mid = sat(mid * 0.8, 3)
    mt = bowed(n, r, np.array([870, 1230, 1790, 2510, 3340]) * r.uniform(0.95, 1.05), 120)
    mt += 0.5 * screech(n, r, env([(0, 700), (0.5, 1100), (d, 800)], n), ring=1.33, ring_amt=0.7)
    fr = furnace_roar(n, r)
    y = 0.9 * unit(sub) + 0.9 * unit(mid) + 0.3 * unit(mt) * env([(0, 0), (0.4, 1), (d, 0.3)], n) + 0.35 * unit(fr)
    y *= env([(0, 0), (0.25, 1), (d - 0.8, 0.85), (d, 0)], n)
    y = sat(y * 0.6, 1.5)
    y = lp(y, 9000)
    y = reverb(y, ir_big(), 0.3)
    return tail_fade(y, d, 0.2)


def big_impact(n, r, f0=60, f1=18, debris=1.0):
    y = 1.6 * thump(n, f0, f1, 0.08, 0.45)
    y += 0.7 * metal_hit(n, r, 55, 0.5, "rand", k=24, bright=0.4, noise=0.4)
    y += 0.7 * burst(n, r, 0.08, None, 1500) + 0.4 * burst(n, r, 0.015, 1500, 9000)
    if debris:
        y += debris * 0.5 * small_hits(n, r, 0.1, 1.1, 18, 300, 2500, 0.03, decay=0.4)
    return sat(y * 0.7, 2)


@snd("boss_slam", 1, gain=0.95)
def boss_slam(v, r):
    n = N(1.4)
    y = big_impact(n, r)
    y = reverb(y, ir_big(), 0.3)
    return tail_fade(y, 1.3, 0.2)


@snd("boss_spit", 1, gain=0.8)
def boss_spit(v, r):
    n = N(0.75)
    y = np.zeros(n)
    bn = N(0.45)
    bel = voice(bn, r, 55 * (1 + 0.1 * smooth_rand(bn, r, 8)), [(0, "o"), (0.3, "a")], 0.6, 0.2, 0.4, 0.4, 0.8, 700)
    place(y, sat(bel, 2.5) * env([(0, 0), (0.03, 1), (0.45, 0)], bn) * 0.7, 0)
    fn = N(0.6)
    fire = tvf(colored(fn, r, -1, hi=3000), env([(0, 400), (0.15, 1500), (0.6, 700)], fn), 1.0, "bp")
    fire = unit(fire) + 0.5 * unit(crackle(fn, r, 500, 1500, 7000))
    place(y, fire * env([(0, 0), (0.05, 1), (0.6, 0)], fn) * 0.5, 0.08)
    place(y, splat(N(0.3), r, 1.0) * 0.6, 0.05)
    y = reverb(y, ir_big(), 0.2)
    return tail_fade(y, 0.7, 0.08)


@snd("boss_spawn", 1, gain=0.75)
def boss_spawn(v, r):
    n = N(0.95)
    y = np.zeros(n)
    tn = N(0.32)
    tear = unit(crackle(tn, r, lambda x: 100 + 6000 * x, 500, 4000)) * env([(0, 0.2), (0.3, 1), (0.32, 0)], tn)
    tear += 0.5 * creak(tn, r, env([(0, 80), (0.3, 300)], tn), [400, 800, 1500], 8) * env([(0, 0), (0.3, 1), (0.32, 0)], tn)
    place(y, tear * 0.5, 0)
    place(y, splat(N(0.6), r, 1.6, 800) * 1.0, 0.3)
    place(y, bubbles(N(0.5), r, 20, 120, 400) * 0.4, 0.4)
    y = reverb(y, ir_room(), 0.18)
    return tail_fade(y, 0.9, 0.08)


@snd("boss_hurt", 2, gain=0.85)
def boss_hurt(v, r):
    n = N(0.85)
    f0 = env([(0, 90), (0.08, 170 + 20 * v), (0.45, 140), (0.8, 70)], n)
    vc = voice(n, r, f0, [(0, "a"), (0.5, "o")], 0.7, 0.06, 0.3, 0.2, 0.4, 1800)
    vc = sat(vc * 0.8, 2.5)
    vc = 0.6 * vc + 0.4 * vc * (0.5 * np.sin(TAU * 311 * T(n)) + 0.5 * np.sin(TAU * 467 * T(n)))
    mt = bowed(n, r, [1180, 1650, 2330], 150) + 0.5 * screech(n, r, env([(0, 1100), (0.8, 1400)], n), ring_amt=0.6)
    y = unit(vc) + 0.25 * unit(mt)
    y *= env([(0, 0), (0.02, 1), (0.5, 0.7), (0.82, 0)], n)
    y = reverb(lp(y, 9000), ir_big(), 0.25)
    return tail_fade(y, 0.8, 0.1)


@snd("boss_phase", 1, gain=0.95)
def boss_phase(v, r):
    n = N(3.6)
    t = T(n)
    tn = N(2.5)
    te = env([(0, 0), (0.3, 0.5), (2.2, 1), (2.5, 0)], tn)
    tear = creak(tn, r, env([(0, 20), (2.3, 150)], tn), [220, 510, 980, 1720, 2600], 10) * te
    tear += 0.6 * bowed(tn, r, [97, 143, 211, 289, 377], 50) * te
    tear += 0.4 * unit(crackle(tn, r, lambda x: 100 + 800 * x, 800, 6000)) * te
    tear += 0.6 * small_hits(tn, r, 0.2, 2.4, 4, 300, 1500, 0.08)
    y = np.zeros(n)
    place(y, unit(tear), 0)
    sn = N(1.9)
    fs = 80 * (380 / 80) ** (np.clip(T(sn) / 1.8, 0, 1) ** 1.5)
    scr = voice(sn, r, fs, [(0, "o"), (0.9, "a"), (1.8, "i")], 0.75, 0.06, 0.3, 0.2, 0.4, 2000)
    scr = sat(unit(scr) * 0.8, 2.5) + 0.4 * screech(sn, r, fs * 4, ring_amt=0.6)
    place(y, unit(scr) * env([(0, 0), (1.6, 1), (1.9, 0)], sn) * 0.9, 0.8)
    pn = N(1.0)
    pr = hiss(pn, r, 800, 3500) * env_db([(0, -60), (0.02, 0), (0.9, -40), (1.0, -90)], pn)
    pr += 1.2 * thump(pn, 80, 30, 0.04, 0.3)
    place(y, pr * 0.9, 2.6)
    y = reverb(sat(y, 1.3), ir_big(), 0.3)
    return tail_fade(y, 3.5, 0.3)


@snd("boss_death", 1, gain=1.0)
def boss_death(v, r):
    n = N(6.2)
    y = np.zeros(n)
    rn = N(3.6)
    f0 = env([(0, 110), (0.6, 95), (3.4, 24)], rn) * (1 + 0.05 * smooth_rand(rn, r, 6))
    roar = growl(rn, r, f0, [(0, "a"), (1.5, "o"), (3.4, "u")], 0.6, 0.12, 0.5, 0.6, 1200, 2.5)
    roar += 0.3 * unit(furnace_roar(rn, r)) * env([(0, 1), (3.6, 0)], rn)
    place(y, roar * env([(0, 0), (0.3, 1), (2.5, 0.7), (3.6, 0)], rn), 0)
    mn = N(3.3)
    tm = T(mn)
    fm = 120 * np.exp(-tm / 1.2) + 12
    gate = lp((smooth_rand(mn, r, 12) > -0.05).astype(float), 150)
    motor = unit(lp(osc("saw", fm, mn), 1500) + 0.3 * osc("sine", fm * 7, mn)) * gate
    motor += 0.4 * unit(crackle(mn, r, lambda x: 300 * (x > 0.5) * np.exp(-(x - 0.5) / 1.5), 1500, 8000))
    place(y, motor * env([(0, 0), (0.2, 1), (3.3, 0)], mn) * 0.3, 0.8)
    place(y, big_impact(N(1.8), r, 55, 16, 1.2) * 0.9, 3.4)
    place(y, big_impact(N(1.5), r, 70, 20, 0.6) * 0.6, 3.95)
    sn = N(1.8)
    place(y, hiss(sn, r, 900, 3500) * env([(0, 0), (0.08, 1), (1.8, 0)], sn) * 0.35, 4.0)
    y = reverb(y, ir_big(), 0.3)
    return tail_fade(y, 6.0, 0.6)
