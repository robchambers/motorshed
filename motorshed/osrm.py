import os

import numpy as np
import requests
import requests_cache
from contexttimer import Timer

from motorshed.util import cache_dir

# Cache HTTP requests (other than map requests, which I think are too complicated
#  to do this with). This is a SQLITE cache..
cache_fn = os.path.join(cache_dir, "requests_cache")

requests_cache.install_cache(
    cache_fn, backend="sqlite", expire_after=60 * 60 * 24 * 7  # expires after 1 week
)


def chunks(l, n):
    """Yield successive n-sized chunks from l."""

    for i in range(0, len(l), n):
        yield l[i : i + n]


def get_transit_times(G, origin_point):
    """Calculate transit_time for every node in the graph, and add to
    G (in-place) as a 'transit_time' property on each node.
    """
    if type(origin_point) is int:
        origin_point = G.nodes[origin_point]
        origin_point = [origin_point["lat"], origin_point["lon"]]

    end = "%s,%s" % (origin_point[1], origin_point[0])
    starts = ["%s,%s" % (data["lon"], data["lat"]) for n, data in G.node(data=True)]
    times = []

    # the table service seems limited in number
    for chunk in chunks(starts, 300):
        chunk = ";".join(chunk)

        query = (
            "http://router.project-osrm.org/table/v1/driving/%s;%s?destinations=0"
            % (end, chunk)
        )
        # query = (
        #     "http://maps.motorshed.io/osrm/table/v1/driving/%s;%s?destinations=0"
        #     % (end, chunk)
        # )

        # print(query)

        with Timer(prefix="osrm table api"):
            r = requests.get(query)

        times = times + list(np.array(r.json()["durations"])[1:, 0])

    for n, node in enumerate(G.node):
        G.node[node]["transit_time"] = times[n]


def osrm(
    G, start_node, end_node, missing_nodes=None, mode="driving", private_host=True
):
    """Query the local or remote OSRM for route and transit time.
     FROM start_node TO end_node
    If any nodes are not
    found, it updates `missing_nodes` with those nodes.
    Returns the route, transit time, and request response."""

    if missing_nodes is None:
        missing_nodes = set([])

    if not hasattr(end_node, "keys"):
        end_node = G.node[end_node]
    if not hasattr(start_node, "keys"):
        start_node = G.node[start_node]

    start = "%f,%f" % (start_node["lon"], start_node["lat"])
    end = "%f,%f" % (end_node["lon"], end_node["lat"])

    # if private_host:
    # query = (
    #     "http://maps.motorshed.io/osrm/route/v1/%s/%s;%s?steps=true&annotations=true"
    #     % (mode, start, end)
    # )
    # else:
    query = (
        "http://router.project-osrm.org/route/v1/%s/%s;%s?steps=true&annotations=true"
        % (mode, start, end)
    )
    r = requests.get(query)

    try:
        route = r.json()["routes"][0]["legs"][0]["annotation"]["nodes"]
        transit_time = r.json()["routes"][0]["duration"]

    except KeyError:
        print("No route found for %i" % start_node)
        missing_nodes.update(start_node)
        route, transit_time = [], np.NaN

    return route, transit_time, r

def osrm_parallel(G2, node_pairs):
    N_WORKERS = 4

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=N_WORKERS) as executor:
        future_to_node = {
            executor.submit(osrm, G2, n1, n2): (n1, n2)
            for (n1, n2) in node_pairs}

    results = []
    for future in concurrent.futures.as_completed(future_to_node):
        nnode = future_to_node[future]
        try:
            route, transit_time, r  = future.result()
        except Exception as exc:
            print(exc)
            continue
        results.append((route, transit_time))

    return results