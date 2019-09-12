from motorshed import util


def test_cache_pkl():
    to_pickle = "Hi I'm a Pickle."
    name = "test_pkl_str"
    util.cache_to_pkl(name, to_pickle)
    from_pickle = util.from_cache_pkl(name)
    assert to_pickle == from_pickle
