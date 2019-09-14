""" "Gen2" algorithms, which try to minimize routing calls by
inferring routes using the transit times from the much faster
Table API."""

import numpy as np
import osmnx as ox
from contexttimer import Timer


#
# def do_v2_routing(G, center_node, origin_point):
#     """ G must already have the transit times calculated. """


def create_initial_dataframes(G):
    """
    Convert graph G into two geodataframes Gn and Ge (nodes and edges)
    that are easier to do calculations on. Add a few useful columns, and
    make sure that data types are correct.

    ###
    # Gn columns:  (NODES)
    # y               float64    spherical mercator coords?
    # x               float64    spherical mercator coords?
    # osmid             int64    node ID
    # highway          object
    # ref              object
    # lon             float64    longitude
    # lat             float64    latitude
    # calculated         bool    whether it's calculated
    # transit_time    float64    time to get to center node
    # w                 int64

    ##
    # Ge columns:   (EDGES)
    # u                    int64    start node
    # v                    int64    end node
    # key                  int64
    # osmid               object
    # name                object    name (e.g., 'Gerrish Court')
    # highway             object    type of road (e.g., highway? residential?)
    # oneway                bool    is one way?
    # length             float64    length, meters
    # through_traffic      int64    count of cars through this edge
    # geometry            object    complex geometry object
    # lanes               object
    # ref                 object
    # maxspeed            object
    # bridge              object    is a bridge?
    # w                    int64    where traffic is routed to -- Next edge is (v, w)
    # v2                   int64
    # dtype: object
    """
    with Timer(prefix="Create initial dataframes"):

        # Graph -> geodataframes
        Gn, Ge = ox.graph_to_gdfs(G, node_geometry=False, fill_edge_geometry=False)

        ## Fix up Gn  ( NODES dataframe )
        Gn["w"] = 0
        Gn["calculated"] = False
        # Coerce types of geodataframe to what we want
        for f, t in (
            ("transit_time", float),
            ("calculated", bool),
            ("lat", float),
            ("lon", float),
            ("osmid", int),
            ("x", float),
            ("y", float),
            ("highway", str),
        ):
            Gn[f] = Gn[f].astype(t)

        ## Fix up Ge ( EDGES dataframe )
        Ge["w"] = 0  # Next edge is (v, w)
        Ge["v2"] = 0
        Ge["through_traffic"] = 0
        # Coerce types of geodataframe to what we want
        for f, t in (
            ("through_traffic", int),
            ("u", np.long),
            ("v", np.long),
            ("v2", np.long),
        ):
            Ge[f] = Ge[f].astype(t)
        Ge.highway = Ge.highway.map(str)

    return Gn, Ge
