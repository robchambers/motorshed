import osmnx as ox

from motorshed import util


def get_map(address, place=None, distance=1000):
    """Get the graph (G) and end_node from OSMNX, initializes through_traffic, transit_time, and calculated.
    Uses local cache (via Pickle) when possible."""

    if place is not None:
        distance = 100

    # calculate cache_name for cache using fxn arguments.
    cache_name = "%s.%s%s" % (address, place or "", distance)
    try:
        # Try to load cache
        (G, center_node, origin_point) = util.from_cache_pkl(cache_name)
        center_node = ox.get_nearest_node(G, origin_point)
        return (G, center_node, origin_point)
    except:
        # If cache miss, then load from netowrk.
        print("Cache miss. Loading.")

        G, origin_point = ox.graph_from_address(
            address,
            distance=distance,
            network_type="drive",
            return_coords=True,
            simplify=False,
        )

        if place is not None:
            G = ox.graph_from_place(place, network_type="drive", simplify=False)

        # get center node:
        center_node = ox.get_nearest_node(G, origin_point)

        G = ox.project_graph(G)

        # initialize edge traffic to 1, source node traffic to 1:
        for u, v, k, data in G.edges(data=True, keys=True):
            data["through_traffic"] = 1  # BASELINE

        for node, data in G.nodes(data=True):
            data["calculated"] = False

        # Save to cache for next time.
        util.cache_to_pkl(cache_name, (G, center_node, origin_point))

        return (G, center_node, origin_point)
