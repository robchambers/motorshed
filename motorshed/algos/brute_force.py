from tqdm import tqdm
from motorshed import osrm
from tqdm import tqdm

from motorshed import osrm


def increment_edges(route, G, missing_edges=None):
    """For a given route, increment through-traffic for every edge on the route"""
    if missing_edges is None:
        missing_edges = set([])

    if len(route) > 0:
        accum_traffic = 1
        for i0, i1 in zip(route[:-1], route[1:]):
            if not G.nodes[i0]["calculated"]:
                accum_traffic += 1
            try:
                G.edges[i0, i1, 0]["through_traffic"] += accum_traffic  # new way
            except KeyError:
                missing_edges.update([(i0, i1)])
                # continue

        G.nodes[i0]["calculated"] = True

        # increment_edges(route[1:], G, missing_edges)


def find_all_routes(G, center_node, max_requests=None):
    """Run through the nodes in the graph, calculate routes, and recursively increment edges"""

    missing_edges = set([])
    missing_nodes = set([])

    n_requests = 0

    # duration_threshold = pd.Series([G.nodes[n]['transit_time'] for n in G.nodes]).max() * .5
    # print('SHOWING TRAVEL FROM ADDRESSES WITHIN %.1f MINUTES.' % (duration_threshold/60.0))
    for origin_node in tqdm(G.nodes()):
        if not G.nodes[origin_node][
            "calculated"
        ]:  # and G.nodes[start_node]['transit_time'] < duration_threshold:
            n_requests += 1
            # print('calculating (%d / %s).' % (n_requests, max_requests))
            try:
                route, transit_time, r = osrm.osrm(
                    G, origin_node, center_node, missing_nodes, mode="driving"
                )
                route = [node for node in route if node in list(G)]
                increment_edges(route, G, missing_edges)
                if max_requests and (n_requests >= max_requests):
                    print("Max requests reached.")
                    break
            except Exception as e:
                print(e)
        # else:
        # print('skipping.')
    else:
        print("Analyzed all nodes without reaching max requests.")

    return missing_edges, missing_nodes, n_requests
