""" These can be used in unit tests, demos, etc."""

example_maps = {
    "foster_city_tesla 2km": {
        "center_address": "391 Foster City Blvd, Foster City, CA 94404",
        "distance_m": 2_000,
    },
    "foster_city_tesla place": {
        "center_address": "391 Foster City Blvd, Foster City, CA 94404",
        "place": "Foster City, CA, USA",
    },
    "lebanon_nh 2km": {
        "center_address": "32 Bank St Lebanon, NH 03766",
        "distance_m": 2_000,
    },
    "lebanon_nh place": {
        "center_address": "32 Bank St Lebanon, NH 03766",
        "place": "Lebanon, NH, USA",
    },
}

example_maps_list = list(example_maps.values())

example_map_names = list(example_maps.keys())
