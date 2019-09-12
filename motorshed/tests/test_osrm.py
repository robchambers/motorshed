import pytest
from motorshed import osrm

@pytest.fixture()
def lebanon_map():
    from motorshed.example_parameters import example_maps, example_maps_list, example_map_names
    from motorshed import overpass
    example_name = 'lebanon_nh 2km'
    example = example_maps[example_name]

    G, center_node, origin_point = overpass.get_map(
        example['center_address'],
        distance=example['distance_m']
    )
    return G, center_node, origin_point

def test_chunks():
    from motorshed.osrm import chunks
    ch = list(chunks(list(range(10)), 4))
    assert len(ch[0]) == 4
    assert len(ch[1]) == 4
    assert len(ch[2]) == 2

def test_get_transit_times(lebanon_map):
    G, center_node, origin_point = lebanon_map
    G2 = G.copy()
    osrm.get_transit_times(G2, center_node)

    for n, node in enumerate(G2.node):
        nnode = G2.node[node]
        assert 'transit_time' in nnode
        assert (nnode['transit_time'] > 0) or (node == center_node)

def test_get_directions(lebanon_map):
    G, center_node, origin_point = lebanon_map
    G2 = G.copy()
    osrm.get_transit_times(G2, center_node)

    I_NODE = 100 # a random test node
    node_id = list(G2.nodes)[I_NODE]
    nnode = G2.nodes[node_id]

    route, transit_time, r = osrm.osrm(G2, nnode, center_node)

    assert transit_time == nnode['transit_time']
    assert len(route) > 2
    assert route[0] == node_id
    assert route[-1] == center_node

