from motorshed import overpass
from motorshed.example_parameters import (
    example_maps,
    example_maps_list,
    example_map_names,
)


def test_import_examples():
    assert len(example_maps_list)
    assert len(example_maps)
    assert len(example_map_names)
    for name in example_map_names:
        assert "center_address" in example_maps[name]
        assert "distance_m" in example_maps[name] or "place" in example_maps[name]


def test_get_map_with_address():
    example_name = "foster_city_tesla 2km"
    example = example_maps[example_name]

    G, center_node, origin_point = overpass.get_map(
        example["center_address"], distance=example["distance_m"]
    )


def test_get_map_with_place():
    example_name = "foster_city_tesla place"
    example = example_maps[example_name]

    G, center_node, origin_point = overpass.get_map(
        example["center_address"], place=example["place"]
    )
