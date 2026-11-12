"""World / environment one-shots."""
import numpy as np
from dsp import *
from registry import snd
from sfx_player import tail_fade


def small_hits(n, r, t0, t1, density, fmin, fmax, tau=0.015, decay=None, amp=1.0):
    y = np.zeros(n)
    dens = density if not decay else (lambda x: density * np.exp(-x / decay))
    for tt in poisson_times(r, t1 - t0, dens):
        hn = N(tau * 8)
        h = unit(modal(hn, r, np.exp(r.uniform(np.log(fmin), np.log(fmax))), rand_ratios(r, 5), tau))
        a = r.uniform(0.2, 1.0) * amp * (np.exp(-tt / decay) if decay else 1)
        place(y, h * a, t0 + tt)
    return y


@snd("door_open", 1, gain=0.6)
def door_open(v, r):
    n = N(2.7)
    t = T(n)
    fm = env([(0, 30), (0.35, 92), (2.05, 100), (2.2, 100), (2.6, 45)], n)
    me = env([(0, 0), (0.12, 1), (2.1, 1), (2.45, 0)], n)
    motor = lp(osc("saw", fm, n), 1200) + 0.25 * osc("sine", fm * 7.0, n) + 0.08 * osc("sine", fm * 11.3, n)
    motor = unit(peq(motor, 600, 5, 2)) * me
    ge = env([(0, 0), (0.25, 1), (2.0, 0.9), (2.15, 0)], n)
    grind = unit(bp(r.standard_normal(n), 200, 1500)) * (0.5 + 0.5 * np.abs(smooth_rand(n, r, 25)) * 3) ** 2
    grind = unit(grind) * ge
    cr = creak(n, r, 40 + 25 * smooth_rand(n, r, 2), [310, 740, 1210, 2300], 8) * ge
    chain = small_hits(n, r, 0.15, 2.1, 24, 900, 3200, 0.015)
    cl = N(0.6)
    clunk = metal_hit(cl, r, 90, 0.35, "plate", noise=0.4) + 1.5 * thump(cl, 85, 40, 0.02, 0.12) + 0.5 * burst(cl, r, 0.02, None, 1200)
    y = 0.4 * motor + 0.35 * grind + 0.25 * cr + 0.25 * chain
    place(y, unit(clunk) * 1.2, 2.18)
    y = reverb(y, ir_metal(), 0.25)
    return tail_fade(y, 2.6, 0.12)


@snd("door_locked", 1, gain=0.55)
def door_locked(v, r):
    n = N(0.5)
    y = np.zeros(n)
    for tt in (0.0, 0.24):
        bn = N(0.18)
        b = osc("square", 110, bn) + 0.7 * osc("saw", 55, bn) + 0.6 * osc("square", 116.5, bn)
        b = sat(b * 0.7, 4)
        b = bp(b, 120, 3000)
        b *= env([(0, 0), (0.004, 1), (0.16, 0.9), (0.18, 0)], bn)
        place(y, b, tt)
    return tail_fade(y, 0.5, 0.03)


@snd("switch_lever", 1, gain=0.6)
def switch_lever(v, r):
    n = N(0.7)
    y = np.zeros(n)
    clack = unit(modal(N(0.1), r, 1400, rand_ratios(r, 8), 0.02)) + click(N(0.1), r)
    place(y, clack * 0.5, 0.0)
    cn = N(0.5)
    clunk = 1.4 * thump(cn, 150, 60, 0.015, 0.08) + 0.6 * metal_hit(cn, r, 160, 0.18, "plate") * ad(cn, 0.001, 0.15)
    clunk += 0.5 * burst(cn, r, 0.015, None, 2000)
    place(y, clunk, 0.16)
    place(y, small_hits(N(0.3), r, 0, 0.2, 30, 1500, 4000, 0.01, decay=0.06) * 0.2, 0.2)
    y = reverb(y, ir_metal(), 0.22)
    return tail_fade(y, 0.6, 0.08)


@snd("power_up", 1, gain=0.65)
def power_up(v, r):
    n = N(3.6)
    t = T(n)
    fg = 8 + 65.4 * (1 - np.exp(-t / 1.0))
    hum = np.zeros(n)
    for k in range(1, 9):
        hum += osc("sine", fg * k, n, r.random()) / k
    hum = unit(lp(hum, 1500)) * env([(0, 0), (0.3, 0.3), (2.5, 1), (3.5, 0.9)], n)
    whine = osc("sine", fg * 12, n) * env([(0, 0), (1, 0.05), (3, 0.12)], n)
    y = 0.5 * hum + 0.3 * whine
    for tt in [0.3, 0.9, 1.4, 1.75, 2.2, 2.26]:
        cn = N(0.12)
        c = unit(modal(cn, r, r.uniform(1500, 2500), rand_ratios(r, 6), 0.01)) + 0.8 * thump(cn, 300, 120, 0.004, 0.012)
        place(y, c * 0.35, tt)
    # fluorescent ballast flicker
    gate = np.zeros(n)
    tt = 1.8
    while tt < 2.8:
        on = r.uniform(0.02, 0.09)
        gate[N(tt):N(tt + on)] = 1
        tt += on + r.uniform(0.02, 0.15)
    gate[N(2.85):] = 1
    gate = lp(gate, 300)
    bz = hp(osc("saw", 146.83, n) + 0.5 * osc("square", 146.83 * 2, n), 800)
    bz = unit(lp(bz, 6000)) * gate * 0.12
    y += bz
    y = reverb(y, ir_metal(), 0.15)
    return tail_fade(y, 3.5, 0.3)


@snd("steam_burst", 2, gain=0.5)
def steam_burst(v, r):
    n = N(1.25)
    x = colored(n, r, 0, lo=900)
    x = peq(x, [3500, 5000][v], 6, 0.7) * (1 + 0.25 * smooth_rand(n, r, 40))
    x = lp(x, 11000)
    e = env_db([(0, -60), (0.015, 0), (0.25, -1.5), (0.6, -6), (1.15, -40), (1.2, -90)], n)
    wh = burst(n, r, 0.05, None, 300)
    y = unit(x) * e + 0.5 * wh
    y = reverb(y, ir_metal(), 0.1)
    return tail_fade(y, 1.2, 0.08)


@snd("spark_zap", 3, gain=0.45)
def spark_zap(v, r):
    n = N(0.26)
    gate = np.zeros(n)
    tt = 0.0
    while tt < 0.17:
        d = r.uniform(0.015, 0.05)
        gate[N(tt):N(tt + d)] = r.uniform(0.5, 1)
        tt += d + r.uniform(0.005, 0.04)
    gate = lp(gate, 400)
    cr = unit(crackle(n, r, 4000, 1500, 9000))
    arc = sat(osc("square", 120 * (1 + 0.1 * v), n) + 0.5 * r.standard_normal(n), 4)
    arc = unit(hp(arc, 300))
    nz = unit(hp(r.standard_normal(n), 2500))
    y = (0.6 * cr + 0.3 * arc + 0.3 * nz) * gate * ad(n, 0.001, 0.12)
    return tail_fade(y, 0.25, 0.03)


@snd("metal_clank", 4, gain=0.5)
def metal_clank(v, r):
    if v == 0:  # pipe knock
        n = N(0.9)
        y = np.zeros(N(1.2))
        for tt, a in [(0, 1), (0.33, 0.8), (0.52, 0.45)]:
            place(y, metal_hit(n, r, 210, 0.5, "pipe", noise=0.2) * a, tt)
        dur = 2.4
    elif v == 1:  # chain drop
        y = small_hits(N(1.0), r, 0, 0.7, 70, 600, 2500, 0.03, decay=0.25)
        place(y, 0.6 * thump(N(0.3), 120, 60, 0.02, 0.05), 0.55)
        dur = 2.2
    elif v == 2:  # sheet-metal groan
        n = N(1.6)
        rate = env([(0, 20), (0.6, 60), (1.5, 14)], n)
        y = creak(n, r, rate, [140, 290, 520, 860], 10) * env([(0, 0), (0.2, 1), (1.3, 0.7), (1.6, 0)], n)
        y += 0.6 * bowed(n, r, [118, 167, 241, 333, 467], 60) * env([(0, 0), (0.4, 1), (1.6, 0)], n)
        dur = 3.0
    else:  # something heavy dragged
        n = N(1.8)
        e = env([(0, 0), (0.2, 1), (1.4, 0.9), (1.7, 0)], n)
        g = unit(bp(r.standard_normal(n), 100, 900)) * (np.abs(smooth_rand(n, r, 18)) * 3) ** 1.5
        y = unit(g) * e + 0.5 * creak(n, r, 80 + 30 * smooth_rand(n, r, 3), [200, 450, 900], 8) * e
        place(y, 1.2 * thump(N(0.4), 90, 40, 0.02, 0.1), 1.65)
        dur = 3.0
    y = lp(y, 4500)
    y = reverb(norm(y), ir_hall(False), 1.0, 0.3)
    return tail_fade(y, dur, 0.5)


@snd("drip", 3, gain=0.35)
def drip(v, r):
    n = N(0.15)
    y = bubble(n, r, [1100, 1350, 900][v] * r.uniform(0.95, 1.05), 0.05, 2.0, 0.015)
    y += 0.25 * unit(modal(n, r, r.uniform(2200, 3200), [1, 2.4, 3.9], 0.03))
    y = reverb(y, ir_room(), 0.35)
    return tail_fade(y, 0.3, 0.1)


@snd("stinger_scare", 2, gain=0.95)
def stinger_scare(v, r):
    n = N(1.9)
    t = T(n)
    notes = [[38, 39, 44, 50, 51, 56, 63], [38, 44, 45, 50, 51, 57, 62, 63]][v]
    st = np.zeros(n)
    for m in notes:
        st += supersaw(mtof(m), n, r, 3, 14)
    st = tvf(st, 300 + 5500 * np.exp(-t / 0.05) + 1200 * np.exp(-t / 0.4), 0.9, "lp")
    st = sat(unit(st) * ad(n, 0.003, 0.5) * 1.5, 2.5)
    hit = thump(n, 110, 40, 0.03, 0.3) + 0.5 * burst(n, r, 0.06, None, 3000)
    fd = 22 + 70 * np.exp(-t / 0.35)
    sub = np.sin(TAU * phase(fd, n)) * ad(n, 0.01, 0.6)
    sc = bowed(n, r, np.array([2350, 3120, 4480, 5230]) * r.uniform(0.95, 1.05), 80)
    sc += 0.7 * creak(n, r, env([(0, 200), (1.5, 80)], n), [1800, 2900, 4200], 15)
    sc += 0.4 * screech(n, r, env([(0, 1200), (1.5, 1500)], n), ring_amt=0.6)
    sc = unit(sc) * env([(0, 0), (0.05, 0.3), (0.25, 1), (1.5, 0)], n)
    y = 0.9 * st + 0.9 * hit + 0.8 * sub + 0.35 * sc
    y = lp(y, 11000)
    y = reverb(y, ir_hall(False), 0.4)
    return tail_fade(y, 1.8, 0.35)


@snd("stinger_discover", 1, gain=0.85)
def stinger_discover(v, r):
    n = N(2.3)
    t = T(n)
    rise = 1 + 0.06 * (t / 2.3) ** 2
    y = np.zeros(n)
    for f, a in [(587.33, 1), (622.25, 0.8), (880, 0.6), (1174.66, 0.5), (1661.2, 0.35), (2489, 0.15)]:
        for dc in (-4, 4):
            y += a * np.sin(TAU * phase(f * cents(dc + r.uniform(-1, 1)) * rise, n) + r.random() * TAU)
    y += 0.4 * bowed(n, r, [1244.5, 1760, 2349], 400) * np.sqrt(np.abs(y).max())
    y *= env_db([(0, -55), (2.2, 0), (2.3, 0)], n)
    y = fade(unit(y), 0.003, 0.012)
    y = np.concatenate([y, np.zeros(N(0.3))])
    y = reverb(y, ir_hall(False), 0.25)
    return tail_fade(y, 2.5, 0.2)


@snd("gore_splat", 4, gain=0.6)
def gore_splat(v, r):
    n = N(0.42)
    th = thump(n, [120, 100, 140, 90][v], 50, 0.015, 0.05)
    bu = burst(n, r, 0.04, 200, 1500)
    wc = wet_clicks(n, r, lambda x: 450 * np.exp(-x / 0.06), 200, 2000)
    wc = unit(wc) if np.any(wc) else wc
    sp = burst(n, r, 0.07, 1000, 5000)
    y = 0.8 * th + 0.8 * bu + 0.5 * wc + 0.25 * sp
    for _ in range(r.integers(3, 6)):
        place(y, 0.35 * bubble(N(0.1), r, r.uniform(150, 400), r.uniform(0.03, 0.08), 1.2), r.uniform(0.02, 0.25))
    y = sat(y, 1.5)
    y = reverb(y, ir_room(), 0.12)
    return tail_fade(y, 0.4, 0.06)
