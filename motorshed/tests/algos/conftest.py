import pytest


@pytest.fixture()
def lebanon_map():
    from motorshed.example_parameters import example_maps
    from motorshed import overpass

    example_name = "lebanon_nh 2km"
    example = example_maps[example_name]

    G, center_node, origin_point = overpass.get_map(
        example["center_address"], distance=example["distance_m"]
    )
    return G, center_node, origin_point
