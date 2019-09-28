import bz2
import os.path
import pickle

cache_dir = os.path.join(os.path.dirname(__file__), "cache")


def cache_to_pkl(name, obj):
    fn = os.path.join(cache_dir, f"{name}.cache.pkl.bz2")
    with bz2.BZ2File(fn, "wb") as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)


def from_cache_pkl(name):
    fn = os.path.join(cache_dir, f"{name}.cache.pkl.bz2")
    with bz2.BZ2File(fn, "rb") as f:
        obj = pickle.load(f)
    return obj
