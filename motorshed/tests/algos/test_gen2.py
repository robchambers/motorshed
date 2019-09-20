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


def test_gen2_routing(lebanon_map):
    G, center_node, origin_point = lebanon_map

    osrm.get_transit_times(G, center_node)

    Gn, Ge = gen2.create_initial_dataframes(G)

    assert Gn.shape[1] == 10
    assert Ge.shape[1] == 16
    assert len(Gn)
    assert len(Ge)

    assert (Gn.calculated == False).all()
    (Ge.through_traffic == 0).all()

    Ge2, Gn2 = gen2.initial_routing(Ge.copy(), Gn.copy())

    Ge3, Gn3 = gen2.followup_heuristic_routing(Ge2.copy(), Gn2.copy())

    Ge4 = gen2.followup_osrm_routing(G, Ge3, Gn3, center_node)

    assert not len(Ge4.query("w==0 and ignore==False"))

    Gge = gen2.propagate_edges(Ge4)

    assert (Gge[Gge.ignore == False].through_traffic >= 0).all()
    assert (Gge.tmp == 0).all()

