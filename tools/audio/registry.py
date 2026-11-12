"""Sound registry: generator modules register functions here with @snd."""
import zlib
import numpy as np

REG = {}


def snd(name, variants=1, gain=0.7, loop=False, folder="sfx"):
    """fn(v, r) -> np.ndarray (mono (n,) or stereo (2, n)), un-normalised."""
    def deco(fn):
        REG[name] = dict(fn=fn, variants=variants, gain=gain, loop=loop, folder=folder)
        return fn
    return deco


def rng_for(name, v):
    return np.random.default_rng(zlib.crc32(f"{name}#{v}".encode()))


def files_for(name):
    e = REG[name]
    if e["variants"] == 1:
        return [f"{e['folder']}/{name}.flac"]
    return [f"{e['folder']}/{name}_{i + 1}.flac" for i in range(e["variants"])]
