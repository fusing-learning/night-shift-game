#!/usr/bin/env python3
"""Regenerate every game sound + public/audio/manifest.json.

Usage:  python3 tools/audio/build_all.py            # everything
        python3 tools/audio/build_all.py name ...   # only these keys (manifest still fully rewritten)
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import numpy as np  # noqa: E402
import dsp  # noqa: E402
from registry import REG, rng_for, files_for  # noqa: E402
import sfx_player, sfx_world, sfx_monsters, music  # noqa: E402,F401

ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(ROOT, "public", "audio")

# Order matters only for manifest readability.
ORDER = [
    "amb_factory", "mus_drone", "mus_tension", "mus_combat", "mus_boss", "mus_title", "mus_ending", "mus_death",
    "amb_furnace", "amb_alarm", "amb_boss_breath", "heartbeat", "blade_hum",
    "laser_shot", "laser_hit_flesh", "laser_hit_metal", "laser_overheat", "laser_empty", "laser_ready",
    "blade_ignite", "blade_swing", "blade_hit", "footstep_metal", "footstep_grate", "dodge", "player_hurt",
    "player_death", "flashlight_click", "pickup_energy", "pickup_health", "pickup_key", "checkpoint", "ui_start",
    "door_open", "door_locked", "switch_lever", "power_up", "steam_burst", "spark_zap", "metal_clank", "drip",
    "stinger_scare", "stinger_discover", "gore_splat",
    "crawler_chitter", "crawler_attack", "crawler_death", "crawler_skitter",
    "brute_growl", "brute_step", "brute_charge", "brute_slam", "brute_death",
    "spitter_gurgle", "spitter_spit", "bile_splat", "spitter_death",
    "stalker_whisper", "stalker_creak", "stalker_shriek", "stalker_death",
    "boss_roar", "boss_slam", "boss_spit", "boss_spawn", "boss_hurt", "boss_phase", "boss_death",
]


def render(job):
    name, v = job
    t0 = time.time()
    e = REG[name]
    x = e["fn"](v, rng_for(name, v))
    x = np.asarray(x, float)
    if not np.all(np.isfinite(x)):
        raise RuntimeError(f"{name}[{v}] produced non-finite samples")
    if e["loop"]:
        x = dsp.finish_loop(x)
    else:
        x = dsp.finish_oneshot(x)
    path = os.path.join(OUT, files_for(name)[v])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    dsp.write_flac(path, x)
    return name, v, x.shape[-1] / dsp.SR, time.time() - t0


def main():
    missing = [k for k in ORDER if k not in REG]
    extra = [k for k in REG if k not in ORDER]
    assert not missing and not extra, (missing, extra)
    sel = sys.argv[1:] or ORDER
    jobs = [(k, v) for k in sel for v in range(REG[k]["variants"])]
    # longest first for better load balancing
    jobs.sort(key=lambda j: (not REG[j[0]]["folder"] == "music", j[0]))
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=os.cpu_count()) as ex:
        for name, v, dur, el in ex.map(render, jobs):
            print(f"  {name:20s} v{v + 1}  {dur:6.2f}s  ({el:5.1f}s)", flush=True)
    manifest = {"sounds": {}}
    for k in ORDER:
        e = REG[k]
        manifest["sounds"][k] = {"files": files_for(k), "gain": e["gain"], "loop": e["loop"]}
    with open(os.path.join(OUT, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"built {len(jobs)} files in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
