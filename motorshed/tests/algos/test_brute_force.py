import pytest
from contexttimer import Timer

from motorshed.algos import brute_force


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


def test_increment_route(a_route):
    G2, center_node, origin_point, route = a_route
    G3 = G2.copy()

    route = [node for node in route if node in list(G2)]
    brute_force.increment_edges(route, G3)

    t = 0
    for i in range(len(route) - 1):
        n = route[i]
        e = (route[i], route[i + 1], 0)
        n3 = G3.nodes[n]
        e3 = G3.edges[e]
        assert e3["through_traffic"] >= t
        t = e3["through_traffic"]
        assert t > 0


def test_find_all_routes(lebanon_map):
    G, center_node, origin_point = lebanon_map

    with Timer(prefix="Calculate traffic"):
        missing_edges, missing_nodes, n_requests = brute_force.find_all_routes(
            G, center_node, max_requests=500  # 60_000
        )

    assert n_requests > 10
    # Would be nice to do some other checks here, but I'm not
    #  sure what they should be...
