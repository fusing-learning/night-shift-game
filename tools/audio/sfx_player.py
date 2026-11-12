"""Player, weapon and UI sound effects."""
import numpy as np
from dsp import *
from registry import snd


def buzz(f, n, r, bright=2500.0, periodic=False):
    """Energy-blade style harmonic buzz around f (array ok)."""
    f = np.asarray(f, float)
    f2 = fix_cycles(f * 1.003, n) if periodic else f * 1.003
    y = 0.55 * osc("saw", f, n) + 0.3 * osc("square", f2, n, pw=0.35) + 0.5 * osc("sine", f, n)
    y = lp(y, bright, 2, periodic)
    y = peq(y, 900, 4, 2, periodic)
    return unit(y)


def tail_fade(y, dur, fl):
    n = N(dur)
    y = y[..., :n].copy()
    if y.shape[-1] < n:
        pad = np.zeros(y.shape[:-1] + (n - y.shape[-1],))
        y = np.concatenate([y, pad], axis=-1)
    m = N(fl)
    y[..., n - m:] *= np.cos(0.5 * np.pi * np.arange(m) / m) ** 2
    return y


# ------------------------------------------------------------- laser gun
@snd("laser_shot", 4, gain=0.75)
def laser_shot(v, r):
    d = [0.28, 0.3, 0.32, 0.29][v]
    n = N(d)
    t = T(n)
    f0 = [2500, 2350, 2700, 2600][v] * r.uniform(0.97, 1.03)
    f1 = [300, 280, 330, 310][v]
    k = [20, 17, 23, 19][v]
    f = f1 + (f0 - f1) * np.exp(-t * k)
    idx = 2.6 * np.exp(-t * 14) + 0.5
    mod = np.sin(TAU * phase(f * [1.5, 1.41, 1.62, 1.5][v], n)) * idx
    car = np.sin(TAU * phase(f, n) + mod)
    sq = osc("square", f * 0.5, n, pw=0.3)
    body = (0.75 * car + 0.25 * sq) * ad(n, 0.0015, [0.07, 0.08, 0.065, 0.075][v])
    body = tvf(body, 1800 + 7000 * np.exp(-t * 16), 0.8, "lp")
    trans = click(n, r, 2500, 10000, 0.0025)
    sub = thump(n, 170, 48, 0.02, 0.06)
    tail = burst(n, r, 0.05, 800, 5000)
    y = 0.85 * unit(body) * 0.5 + 0.25 * trans + 0.55 * sub + 0.06 * tail
    return sat(norm(y) * 1.4, 1.5)


@snd("laser_hit_flesh", 3, gain=0.6)
def laser_hit_flesh(v, r):
    n = N(0.34)
    t = T(n)
    siz = unit(hp(r.standard_normal(n), 3000)) * ad(n, 0.002, 0.09)
    cr = unit(crackle(n, r, lambda x: 900 * np.exp(-x / 0.12), 2500, 9000)) * 0.6
    smack = burst(n, r, 0.03, 250, 1600, a=0.0015)
    th = thump(n, 150 - 15 * v, 65, 0.02, 0.05)
    sq = wet_clicks(n, r, lambda x: 150 * np.exp(-x / 0.08), 300, 1800)
    sq = unit(sq) * ad(n, 0.003, 0.08) if np.any(sq) else sq
    y = 0.35 * siz + 0.35 * cr + 0.8 * smack + 0.7 * th + 0.5 * sq
    for _ in range(3):
        b = bubble(N(0.06), r, r.uniform(250, 600), 0.04)
        place(y, b * 0.3, r.uniform(0.02, 0.15))
    y = reverb(y, ir_room(), 0.12)
    return tail_fade(sat(norm(y) * 1.3, 1.3), 0.32, 0.05)


@snd("laser_hit_metal", 3, gain=0.55)
def laser_hit_metal(v, r):
    n = N(0.42)
    t = T(n)
    fz = 1500 + 3500 * np.exp(-t * 40)
    zap = np.sin(TAU * phase(fz, n) + 2 * np.sin(TAU * phase(fz * 1.7, n))) * ad(n, 0.001, 0.03)
    ping = unit(modal(n, r, r.uniform(1800, 2600), [1, 2.76, 5.40, 8.93], 0.12, tilt=0.4))
    tr = click(n, r, 3000, 11000, 0.002)
    fr = (3300 - 300 * v) - 1500 * np.clip((t - 0.02) / 0.18, 0, 1) ** 0.7
    ric = np.sin(TAU * phase(fr * (1 + 0.01 * np.sin(TAU * 30 * t)), n)) * ad(n, 0.006, 0.07)
    ric = np.concatenate([np.zeros(N(0.02)), ric[:-N(0.02)]])
    y = 0.6 * zap + 0.5 * ping + 0.4 * tr + 0.25 * ric
    y = reverb(y, ir_metal(), 0.15)
    return tail_fade(norm(y), 0.4, 0.06)


@snd("laser_overheat", 1, gain=0.6)
def laser_overheat(v, r):
    n = N(0.95)
    t = T(n)
    hs = colored(n, r, 0, lo=1500, hi=9000)
    hs = peq(hs, 4500, 6, 0.8) * (1 + 0.3 * smooth_rand(n, r, 30))
    hs = unit(hs) * env([(0, 0), (0.03, 1), (0.3, 0.75), (0.88, 0)], n)
    fw = 2200 * np.exp(-t * 2.6) + 180
    fw = fw * (1 + 0.006 * np.sin(TAU * 7 * t))
    wh = 0.6 * osc("saw", fw, n) + 0.6 * osc("sine", fw, n)
    wh = lp(wh, 4000) * ad(n, 0.01, 0.32)
    cl = click(n, r, 1500, 7000, 0.003)
    place(cl, click(n, r, 1500, 7000, 0.003)[:N(0.05)] * 0.7, 0.05)
    th = thump(n, 220, 90, 0.01, 0.03)
    y = 0.45 * hs + 0.4 * unit(wh) * 0.6 + 0.4 * cl + 0.4 * th
    return tail_fade(y, 0.9, 0.08)


@snd("laser_empty", 1, gain=0.5)
def laser_empty(v, r):
    n = N(0.13)
    c1 = unit(modal(n, r, 3000, rand_ratios(r, 6), 0.008)) + click(n, r, 2000, 9000)
    c2 = unit(modal(n, r, 3700, rand_ratios(r, 6), 0.006)) * 0.5
    y = c1.copy()
    place(y, c2, 0.012)
    bz = lp(osc("square", 110, n), 2000) * ad(n, 0.003, 0.025)
    place(y, bz * 0.35, 0.02)
    return tail_fade(y, 0.12, 0.02)


@snd("laser_ready", 1, gain=0.45)
def laser_ready(v, r):
    n = N(0.42)
    t = T(n)
    fc = np.where(t < 0.22, 600 * (2200 / 600) ** (t / 0.22), 2200)
    ch = np.sin(TAU * phase(fc, n) + 0.8 * np.sin(TAU * phase(fc * 2, n)))
    ch *= env([(0, 0), (0.01, 0.5), (0.2, 0.8), (0.25, 0)], n)
    bp_ = np.zeros(n)
    bt = N(0.1)
    beep = (np.sin(TAU * 1760 * T(bt)) + 0.2 * np.sin(TAU * 3520 * T(bt))) * ad(bt, 0.003, 0.035)
    place(bp_, beep, 0.25)
    fz = unit(hp(r.standard_normal(n), 4000)) * env([(0, 0), (0.05, 0.2), (0.22, 0.25), (0.3, 0)], n)
    y = 0.6 * ch + 0.6 * bp_ + 0.15 * fz
    return tail_fade(y, 0.4, 0.06)


# ------------------------------------------------------------ energy blade
@snd("blade_ignite", 1, gain=0.6)
def blade_ignite(v, r):
    n = N(0.52)
    t = T(n)
    f = 90 * (0.42 + 0.58 * (1 - np.exp(-t / 0.07)))
    hum = buzz(f, n, r, 600)
    hum = tvf(hum, 300 + 3000 * (1 - np.exp(-t / 0.1)), 1.2, "lp")
    hum = unit(hum) * env([(0, 0), (0.025, 1), (0.25, 0.8), (0.5, 0)], n)
    cr = unit(crackle(n, r, lambda x: 1200 * np.exp(-x / 0.07), 1500, 8000)) * 0.6
    snap = burst(n, r, 0.012, 2000, 9000)
    y = 0.8 * hum + 0.4 * cr + 0.45 * snap
    return tail_fade(sat(y, 1.5), 0.5, 0.06)


@snd("blade_hum", 1, gain=0.3, loop=True, folder="sfx")
def blade_hum(v, r):
    P = 2.0
    L = N(P)
    t = T(L)
    f = 90 * (1 + 0.004 * np.sin(TAU * 5.5 * t))
    a = buzz(fix_cycles(f, L), L, r, 2600, True)
    b = buzz(np.full(L, 90.5), L, r, 1800, True)
    sub = osc("sine", 45, L)
    y = a + 0.5 * b + 0.3 * sub
    y = lp(y, 3000, 2, periodic=True)
    y *= 1 + 0.08 * np.sin(TAU * 7 * t) + 0.04 * np.sin(TAU * 13 * t)
    y += 0.04 * colored(L, r, 0, lo=4000, hi=9000)
    return y


@snd("blade_swing", 3, gain=0.55)
def blade_swing(v, r):
    n = N(0.36)
    t = T(n)
    c = [0.14, 0.12, 0.17][v]
    w = [0.06, 0.05, 0.07][v]
    g = np.exp(-((t - c) / w) ** 2)
    f = 95 * (1.25 + 0.35 * np.tanh((c - t) / 0.045)) * r.uniform(0.95, 1.05)
    hum = buzz(f, n, r, 3000)
    hum = tvf(hum, 700 + 5000 * g, 0.9, "lp") * g
    air = whoosh(n, r, 600 + 2600 * g, 1.0, -1) * g
    y = 0.9 * unit(hum) * 0.7 + 0.45 * air
    return tail_fade(y, 0.35, 0.05)


@snd("blade_hit", 3, gain=0.7)
def blade_hit(v, r):
    n = N(0.37)
    t = T(n)
    sear = unit(peq(hp(r.standard_normal(n), 2500), 5000, 6, 1)) * ad(n, 0.001, 0.08)
    cr = unit(crackle(n, r, lambda x: 2000 * np.exp(-x / 0.1), 1500, 8000))
    cut = burst(n, r, 0.03, 300, 2000, a=0.001)
    wc = wet_clicks(n, r, lambda x: 250 * np.exp(-x / 0.07), 300, 2200)
    wc = unit(wc) if np.any(wc) else wc
    hb = buzz(140 + 60 * np.exp(-t / 0.05) + 20 * v, n, r, 3000) * ad(n, 0.002, 0.06)
    th = thump(n, 130, 60, 0.015, 0.04)
    y = 0.45 * sear + 0.4 * cr * ad(n, 0.001, 0.15) + 0.6 * cut + 0.4 * wc * ad(n, 0.004, 0.08) + 0.5 * hb + 0.5 * th
    y = reverb(y, ir_room(), 0.1)
    return tail_fade(sat(norm(y) * 1.2, 1.4), 0.35, 0.05)


# --------------------------------------------------------------- movement
def _step(r, grate=False, v=0):
    n = N(0.2)
    heel = thump(n, r.uniform(105, 140), 70, 0.01, 0.018)
    f0 = r.uniform(400, 600) if grate else r.uniform(220, 320)
    plate = unit(modal(n, r, f0, RATIOS["plate"][:10], 0.09 if grate else 0.05, tilt=0.6))
    scuff = burst(n, r, 0.012, 300, 4000)
    y = 0.7 * heel + (0.4 if grate else 0.3) * plate + 0.35 * scuff
    toe = 0.45 * click(n, r, 1000, 5000, 0.004) + 0.2 * unit(modal(n, r, f0 * 1.3, RATIOS["plate"][:8], 0.03))
    place(y, toe * r.uniform(0.4, 0.6), r.uniform(0.03, 0.05))
    if grate:
        for k in range(r.integers(4, 8)):
            tt = r.uniform(0.01, 0.12)
            h = unit(modal(N(0.06), r, r.uniform(1500, 4000), rand_ratios(r, 4), 0.02)) * r.uniform(0.05, 0.2) * np.exp(-tt / 0.05)
            place(y, h, tt)
    y = lp(y, 7000)
    y = reverb(y, ir_metal(), 0.06)
    return tail_fade(y, 0.18 if grate else 0.15, 0.04)


@snd("footstep_metal", 6, gain=0.3)
def footstep_metal(v, r):
    return _step(r, False, v)


@snd("footstep_grate", 4, gain=0.32)
def footstep_grate(v, r):
    return _step(r, True, v)


@snd("dodge", 1, gain=0.45)
def dodge(v, r):
    n = N(0.32)
    g = env([(0, 0), (0.08, 1), (0.3, 0)], n)
    fc = env([(0, 500), (0.1, 1400), (0.3, 600)], n)
    air = whoosh(n, r, fc, 0.8, -2) * g
    rustle = unit(bp(r.standard_normal(n), 1000, 5000)) * np.abs(smooth_rand(n, r, 40)) * 3 * g
    y = 0.8 * air + 0.25 * rustle
    return tail_fade(y, 0.3, 0.04)


def _grunt(n, r, f0a, f0b, vow=("uh", "u")):
    f0 = env([(0, f0a), (n / SR, f0b)], n)
    vc = voice(n, r, f0, [(0, vow[0]), (n / SR, vow[1])], 1.0, 0.03, 0.15, 0.1, 0.6, 700)
    return vc


def helmet(y):
    y = lp(y, 2600)
    y = comb(y, 0.0011, 0.35)
    return peq(y, 900, 4, 1.5)


@snd("player_hurt", 3, gain=0.65)
def player_hurt(v, r):
    n = N(0.38)
    im = thump(n, 130, 55, 0.02, 0.06) + 0.4 * burst(n, r, 0.02, None, 900)
    gn = N(0.24)
    g = _grunt(gn, r, [150, 165, 140][v], [112, 120, 100][v], [("uh", "u"), ("a", "uh"), ("uh", "o")][v])
    g = helmet(g) * env([(0, 0), (0.015, 1), (0.12, 0.7), (0.24, 0)], gn)
    y = 0.7 * im
    place(y, unit(g) * 0.45, 0.02)
    return tail_fade(y, 0.35, 0.05)


@snd("player_death", 1, gain=0.8)
def player_death(v, r):
    n = N(1.75)
    y = np.zeros(n)
    m = N(0.8)
    imp = 1.2 * thump(m, 75, 32, 0.03, 0.25) + 0.5 * burst(m, r, 0.08, None, 600)
    imp += 0.35 * metal_hit(m, r, 180, 0.25, "plate", noise=0.2) * ad(m, 0.001, 0.2)
    place(y, imp, 0.0)
    place(y, 0.4 * (thump(m, 90, 45, 0.02, 0.08) + 0.4 * metal_hit(m, r, 260, 0.12, "plate")), 0.22)
    bn = N(0.85)
    br = whisper(bn, r, [(0, "a"), (0.5, "uh"), (0.8, "u")]) * env([(0, 0), (0.06, 1), (0.6, 0.35), (0.85, 0)], bn)
    place(y, helmet(br) * 0.35, 0.3)
    en = N(1.1)
    te = T(en)
    rate = np.clip(1 - te / 1.0, 0.18, 1) ** 1.2
    fb = 1320 * rate
    beep = osc("square", fb, en, pw=0.4)
    gate = (np.sin(TAU * phase(11 * rate, en)) > -0.2).astype(float)
    gate = lp(gate, 200)
    el = lp(beep, 3500) * gate * env([(0, 0), (0.02, 1), (0.8, 0.5), (1.05, 0)], en)
    hm = lp(osc("saw", 73.4 * rate + 10, en), 900) * env([(0, 0), (0.05, 1), (1.05, 0)], en)
    place(y, 0.18 * el + 0.15 * hm, 0.5)
    y = reverb(y, ir_room(), 0.12)
    return tail_fade(y, 1.6, 0.15)


@snd("flashlight_click", 1, gain=0.35)
def flashlight_click(v, r):
    n = N(0.08)
    c1 = unit(modal(n, r, 2600, rand_ratios(r, 6), 0.006)) + 0.6 * click(n, r)
    c2 = unit(modal(n, r, 3400, rand_ratios(r, 6), 0.004)) * 0.5
    y = c1 + 0.3 * thump(n, 500, 300, 0.005, 0.006)
    place(y, c2, 0.022)
    return tail_fade(y, 0.08, 0.015)


# ---------------------------------------------------------------- pickups
@snd("pickup_energy", 1, gain=0.55)
def pickup_energy(v, r):
    n = N(0.52)
    y = np.zeros(n)
    for i, m in enumerate([74, 77, 81, 86, 89]):
        f = mtof(m + 12)
        bn = N(0.3 if i == 4 else 0.12)
        tb = T(bn)
        b = np.sin(TAU * f * tb + 0.9 * np.sin(TAU * 2 * f * tb)) + 0.25 * osc("square", f, bn)
        b = lp(b, 8000) * ad(bn, 0.002, 0.12 if i == 4 else 0.05)
        place(y, b * (0.7 + 0.08 * i), 0.05 * i)
    fz = unit(hp(r.standard_normal(n), 4000)) * env([(0, 0), (0.05, 1), (0.3, 0.6), (0.5, 0)], n)
    cr = unit(crackle(n, r, 600, 3000, 9000)) * env([(0, 0), (0.05, 1), (0.4, 0)], n)
    y = 0.6 * y + 0.08 * fz + 0.15 * cr
    return tail_fade(y, 0.5, 0.08)


@snd("pickup_health", 1, gain=0.55)
def pickup_health(v, r):
    n = N(0.62)
    y = np.zeros(n)
    for f, tt in [(mtof(81), 0.0), (mtof(86), 0.13)]:
        bn = N(0.48)
        tb = T(bn)
        b = (np.sin(TAU * f * tb) + 0.25 * np.sin(TAU * 2 * f * tb) + 0.06 * np.sin(TAU * 3.01 * f * tb))
        place(y, b * ad(bn, 0.006, 0.18) * 0.5, tt)
    hs = unit(bp(r.standard_normal(n), 3000, 9000)) * ad(n, 0.004, 0.05, hold=0.06)
    y += 0.18 * hs + 0.2 * click(n, r, 1500, 6000)
    y += 0.08 * np.sin(TAU * 293.66 * T(n)) * ad(n, 0.02, 0.2)
    return tail_fade(y, 0.6, 0.1)


@snd("pickup_key", 1, gain=0.55)
def pickup_key(v, r):
    n = N(0.5)
    y = unit(modal(n, r, 1800, rand_ratios(r, 7), 0.012)) * 0.6 + 0.6 * click(n, r, 1500, 9000)
    place(y, unit(modal(N(0.05), r, 2400, rand_ratios(r, 5), 0.006)) * 0.3, 0.015)
    for f, tt, d in [(mtof(88), 0.08, 0.07), (mtof(93), 0.16, 0.14)]:
        bn = N(d + 0.05)
        b = lp(osc("square", f, bn, pw=0.4), 4500) * env([(0, 0), (0.003, 1), (d, 0.7), (d + 0.04, 0)], bn)
        place(y, b * 0.3, tt)
    return tail_fade(y, 0.5, 0.06)


@snd("checkpoint", 1, gain=0.6)
def checkpoint(v, r):
    n = N(1.6)
    b = unit(modal(n, r, 293.66, RATIOS["bell"], 1.1, decay_pow=0.6, tilt=0.5, jit=0.002)) * ad(n, 0.008, 2.0)
    b2 = unit(modal(n, r, 440.0, RATIOS["bell"], 0.8, decay_pow=0.6, tilt=0.7, jit=0.002)) * 0.35
    y = b.copy()
    place(y, b2 * ad(n, 0.01, 1.0), 0.12)
    y = lp(y, 6000)
    y = reverb(y, ir_hall(False), 0.45)
    return tail_fade(y, 1.2, 0.3)


@snd("ui_start", 1, gain=0.8)
def ui_start(v, r):
    n = N(1.6)
    y = np.zeros(n)
    cn = N(1.2)
    cym = unit(hp(r.standard_normal(cn), 3000)) + 0.5 * unit(modal(cn, r, 3200, rand_ratios(r, 20, 0.05, 0.3), 0.5))
    cym = lp(cym, 11000) * ad(cn, 0.001, 0.35)
    cym = reverb(cym, ir_big(), 0.4)[:N(1.4)]
    sw = cym[::-1][-N(0.55):]
    sw = sw * np.linspace(0, 1, len(sw)) ** 0.5
    place(y, unit(sw) * 0.35, 0.0)
    bn = N(1.05)
    boom = thump(bn, 95, 30, 0.08, 0.4) + 0.4 * burst(bn, r, 0.18, None, 220)
    boom += 0.25 * metal_hit(bn, r, 70, 0.6, "bell", noise=0) * ad(bn, 0.004, 0.5)
    boom = reverb(boom, ir_hall(False), 0.3)
    place(y, sat(norm(boom) * 1.5, 1.4), 0.55)
    return tail_fade(y, 1.5, 0.25)
