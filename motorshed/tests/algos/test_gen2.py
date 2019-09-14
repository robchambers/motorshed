import pytest

from motorshed import osrm
from motorshed.algos import gen2


@pytest.fixture()
def a_route(lebanon_map):
    G, center_node, origin_point = lebanon_map
    G2 = G.copy()

    from motorshed import osrm

    I_NODE = 100  # a random test node
    node_id = list(G2.nodes)[I_NODE]
    nnode = G2.nodes[node_id]
    route, transit_time, r = osrm.osrm(G2, nnode, center_node)

    return G2, center_node, origin_point, route


def test_create_initial_DFs(lebanon_map):
    G, center_node, origin_point = lebanon_map

    osrm.get_transit_times(G, center_node)

    Gn, Ge = gen2.create_initial_dataframes(G)

    assert Gn.shape[1] == 10
    assert Ge.shape[1] == 16
    assert len(Gn)
    assert len(Ge)

    assert (Gn.calculated == False).all()
    (Ge.through_traffic == 0).all()
