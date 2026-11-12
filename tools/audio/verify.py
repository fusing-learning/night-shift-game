#!/usr/bin/env python3
"""Verify every file in public/audio/manifest.json.

Decodes each FLAC with ffmpeg -> WAV -> numpy and reports duration, peak/RMS dBFS,
DC offset, spectral centroid. Flags: wrong format, clipping, silence, DC, start/end
clicks on one-shots, and loop-seam discontinuities (sample jump across the wrap +
50 ms spectral difference across the wrap vs the file's typical frame-to-frame
difference). Renders log-frequency spectrogram PNGs (pure numpy + zlib, no
matplotlib needed) into tools/audio/spectrograms/.

Exit code 0 when everything passes.
"""
import io
import json
import os
import struct
import subprocess
import sys
import tempfile
import zlib

import numpy as np
from scipy import signal
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
AUDIO = os.path.join(ROOT, "public", "audio")
SPEC_DIR = os.path.join(HERE, "spectrograms")
FFMPEG = "/opt/homebrew/bin/ffmpeg"
SR = 44100

MONO_LOOPS = {"amb_furnace", "amb_alarm", "amb_boss_breath", "heartbeat", "blade_hum"}
STEREO = {"amb_factory", "mus_drone", "mus_tension", "mus_combat", "mus_boss", "mus_title", "mus_ending", "mus_death"}
SPECTRO = {"amb_factory", "mus_drone", "mus_tension", "mus_combat", "mus_boss", "mus_title", "mus_ending", "mus_death",
           "amb_furnace", "amb_alarm", "amb_boss_breath", "heartbeat", "blade_hum",
           "laser_shot", "laser_hit_metal", "laser_overheat", "blade_swing", "footstep_metal", "door_open", "power_up",
           "stinger_scare", "stinger_discover", "crawler_chitter", "brute_growl", "brute_slam", "stalker_shriek",
           "stalker_whisper", "boss_roar", "boss_death", "boss_phase", "ui_start", "checkpoint", "player_hurt",
           "metal_clank", "spitter_gurgle"}


def decode(path):
    with tempfile.TemporaryDirectory() as td:
        wp = os.path.join(td, "x.wav")
        subprocess.run([FFMPEG, "-loglevel", "error", "-i", path, "-acodec", "pcm_s16le", wp], check=True)
        sr, x = wavfile.read(wp)
    probe = subprocess.run([FFMPEG, "-hide_banner", "-i", path], capture_output=True, text=True).stderr
    return sr, x, probe


def dbfs(v):
    return 20 * np.log10(max(v, 1e-12))


def frames_logspec(m, size=2205):
    k = len(m) // size
    fr = m[:k * size].reshape(k, size) * np.hanning(size)
    return np.log10(np.abs(np.fft.rfft(fr, axis=1)) + 1e-6), k


def seam_metrics(x):
    """x: (n, ch) float. Returns (jump_ratio, spec_ratio, click_z).
    jump_ratio: |x[0]-x[-1]| / 99.9th pct of |diff| inside the file (<1 = no jump).
    spec_ratio: log-spectral distance between last and first 50 ms frame divided by
                the 98th pct of consecutive 50 ms frame distances inside the file
                (<~1.25 = seam is no more abrupt than ordinary musical changes).
    click_z:    HF energy of a frame straddling the wrap, z-scored vs frames inside."""
    m = x.mean(axis=1)
    d = np.abs(np.diff(x, axis=0))
    jump = np.abs(x[0] - x[-1])
    p99 = np.percentile(d, 99.9, axis=0) + 1e-9
    jump_ratio = float(np.max(jump / p99))
    size = 2205
    S, k = frames_logspec(m, size)
    dif = np.mean(np.abs(np.diff(S, axis=0)), axis=1)
    typ = np.percentile(dif, 98)
    a = m[-size:] * np.hanning(size)
    b = m[:size] * np.hanning(size)
    sa = np.log10(np.abs(np.fft.rfft(a)) + 1e-6)
    sb = np.log10(np.abs(np.fft.rfft(b)) + 1e-6)
    seam = np.mean(np.abs(sa - sb))
    # also a frame straddling the seam vs typical straddling-frame diffs (detects clicks)
    st = np.concatenate([m[-size // 2:], m[:size // 2]]) * np.hanning(size)
    ss = np.log10(np.abs(np.fft.rfft(st)) + 1e-6)
    hf = slice(len(ss) * 2 // 3, None)  # high-frequency band where a click would show
    mid = len(m) // 2
    ref = []
    for off in np.linspace(size, len(m) - 2 * size, 40).astype(int):
        w = m[off:off + size] * np.hanning(size)
        ref.append(np.mean(np.log10(np.abs(np.fft.rfft(w)) + 1e-6)[hf]))
    click_z = (np.mean(ss[hf]) - np.mean(ref)) / (np.std(ref) + 1e-6)
    return jump_ratio, float(seam / typ), float(click_z)


# ---------------------------------------------------------------- PNG
def write_png(path, rgb):
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


CMAP = np.array([[0, 0, 4], [40, 11, 84], [101, 21, 110], [159, 42, 99], [212, 72, 66], [245, 125, 21],
                 [250, 193, 39], [252, 255, 164]], float)


def colormap(v):
    v = np.clip(v, 0, 1) * (len(CMAP) - 1)
    i = np.minimum(v.astype(int), len(CMAP) - 2)
    f = (v - i)[..., None]
    return (CMAP[i] * (1 - f) + CMAP[i + 1] * f).astype(np.uint8)


def spectrogram_png(x, path, title_dur):
    m = x.mean(axis=1)
    n = len(m)
    dur = n / SR
    nper = 2048 if dur > 3 else 512
    hop = max(nper // 8, int(n / 1400))
    f, t, Z = signal.stft(m, SR, nperseg=nper, noverlap=max(0, nper - hop), boundary=None)
    S = 20 * np.log10(np.abs(Z) + 1e-9)
    S -= S.max()
    H = 300
    fl = np.geomspace(20, 18000, H)[::-1]
    rows = np.array([np.interp(fl, f, S[:, j]) for j in range(S.shape[1])]).T
    W = min(1400, rows.shape[1])
    cols = np.linspace(0, rows.shape[1] - 1, W).astype(int)
    img = colormap((rows[:, cols] + 90) / 90)
    for gf in (100, 1000, 10000):
        y = int(np.argmin(np.abs(fl - gf)))
        img[y, ::4] = [80, 200, 80]
    # waveform strip
    WH = 80
    strip = np.zeros((WH, W, 3), np.uint8) + 20
    seg = np.array_split(np.abs(m), W)
    pk = np.array([s.max() if len(s) else 0 for s in seg])
    rm = np.array([np.sqrt(np.mean(s ** 2)) if len(s) else 0 for s in seg])
    for j in range(W):
        hpk = int(pk[j] * (WH // 2 - 1))
        hr = int(rm[j] * (WH // 2 - 1))
        strip[WH // 2 - hpk:WH // 2 + hpk + 1, j] = [90, 140, 220]
        strip[WH // 2 - hr:WH // 2 + hr + 1, j] = [200, 230, 255]
    # 1-second ticks on the strip
    for s in range(int(dur) + 1):
        j = int(s / dur * (W - 1))
        strip[:6, j] = [255, 80, 80]
    write_png(path, np.concatenate([strip, img], axis=0))


def main():
    with open(os.path.join(AUDIO, "manifest.json")) as fh:
        man = json.load(fh)["sounds"]
    os.makedirs(SPEC_DIR, exist_ok=True)
    problems = []
    total_bytes = 0
    nfiles = 0
    print(f"{'file':38s} {'dur':>6s} {'ch':>2s} {'peak':>6s} {'rms':>6s} {'dc':>8s} {'cent':>6s}  notes")
    for key, e in man.items():
        if not (0 < e["gain"] <= 1):
            problems.append(f"{key}: gain out of range")
        for rel in e["files"]:
            p = os.path.join(AUDIO, rel)
            if not os.path.exists(p):
                problems.append(f"{rel}: missing")
                continue
            total_bytes += os.path.getsize(p)
            nfiles += 1
            sr, xi, probe = decode(p)
            notes = []
            if sr != SR:
                notes.append(f"SR={sr}")
            if xi.dtype != np.int16 or "flac" not in probe or "s16" not in probe:
                notes.append("FORMAT")
            x = xi.astype(float) / 32768.0
            if x.ndim == 1:
                x = x[:, None]
            ch = x.shape[1]
            want = 2 if key in STEREO else 1
            if ch != want:
                notes.append(f"CHANNELS={ch}")
            dur = len(x) / SR
            peak = np.max(np.abs(x))
            r = np.sqrt(np.mean(x ** 2))
            dc = float(np.max(np.abs(x.mean(axis=0))))
            m = x.mean(axis=1)
            sp = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
            fq = np.fft.rfftfreq(len(m), 1 / SR)
            cent = float((sp * fq).sum() / (sp.sum() + 1e-20))
            if np.sum(np.abs(xi) >= 32767) > 0:
                notes.append("CLIP")
            if dbfs(peak) > -0.5 or dbfs(peak) < -1.6:
                notes.append(f"PEAK({dbfs(peak):.1f})")
            if dbfs(r) < -50:
                notes.append("SILENT")
            if dc > 0.002:
                notes.append(f"DC({dc:.4f})")
            if e["loop"]:
                jr, sr_, cz = seam_metrics(x)
                tag = f"seam jump={jr:.2f} spec={sr_:.2f} clickz={cz:+.1f}"
                if jr > 1.0 or sr_ > 1.25 or cz > 3.0:
                    notes.append("SEAM! " + tag)
                else:
                    notes.append(tag)
            else:
                s0, s1 = np.max(np.abs(x[0])), np.max(np.abs(x[-1]))
                if s0 > 0.001 or s1 > 0.001:
                    notes.append(f"EDGE-CLICK(start={s0:.4f},end={s1:.4f})")
                # fade-in sanity: first 1 ms must be quiet relative to peak
                if np.max(np.abs(x[:N1])) > 0.5 * peak:
                    notes.append("HARD-ATTACK")
            bad = [n_ for n_ in notes if n_.isupper() or n_.startswith(("SEAM!", "PEAK", "DC", "EDGE", "CHANNELS", "SR="))]
            for b in bad:
                problems.append(f"{rel}: {b}")
            print(f"{rel:38s} {dur:6.2f} {ch:2d} {dbfs(peak):6.1f} {dbfs(r):6.1f} {dc:8.5f} {cent:6.0f}  {' '.join(notes)}")
            if key in SPECTRO and rel == e["files"][0]:
                spectrogram_png(x, os.path.join(SPEC_DIR, os.path.basename(rel).replace(".flac", ".png")), dur)
    print()
    print(f"{len(man)} keys, {nfiles} files, total {total_bytes / 1e6:.1f} MB")
    if problems:
        print(f"FAIL: {len(problems)} problem(s)")
        for p in problems:
            print("  -", p)
        return 1
    print("PASS: all checks clean")
    return 0


N1 = int(0.001 * SR)

if __name__ == "__main__":
    sys.exit(main())
