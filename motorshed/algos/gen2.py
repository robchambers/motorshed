""" "Gen2" algorithms, which try to minimize routing calls by
inferring routes using the transit times from the much faster
Table API."""

import concurrent.futures

import numpy as np
import osmnx as ox
import pandas as pd
from contexttimer import Timer

from motorshed import osrm


def create_initial_dataframes(G, towards_origin=True):
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
    # v2                   int64    if the routing says (u,v,w), but (v,w) doesn't exist, then just propagate traffic from (u,v) to (v2,w)
    # dtype: object
    """
    with Timer(prefix="Create initial dataframes"):

        # Graph -> geodataframes
        Gn, Ge = ox.graph_to_gdfs(G, node_geometry=False, fill_edge_geometry=False)
        Gn, Ge = Gn.copy(), Ge.copy()  # make sure original graph is unchanged.

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
        # Reverse if needed
        if not towards_origin:
            Ge[["u", "v"]] = Ge[["v", "u"]]
            Ge["reversed"] = True
        else:
            Ge["reversed"] = False

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


def initial_routing(Ge, Gn):
    """Use the transit times from the table API (must already have been run) to do an easy,
    initial routing that can safe us from querying the slower routing API. Basically,
    we know that if a segment (u,v) can only continue on to a single follow-on segment (v,w)
    that gets us closer to the target (that is, all other options take us farther away according
    to the transit times), then we know that the next step is 'w', unambiguously.
    """

    with Timer(prefix="Initial routing using heuristics"):
        # Grab edge's start & end time from nodes.
        Ge["start_time"] = Gn.loc[Ge.u].transit_time.values
        Ge["end_time"] = Gn.loc[Ge.v].transit_time.values
        # dt is how much transit times changes when this edge is traversed.
        #   If negative, then we made progress.
        Ge["dt"] = Ge["end_time"] - Ge["start_time"]

        # Create multiindex
        ### Q: should we sort 'length'? or keep all copies?  << done >>
        ###   Might this cause problems later w/ missing segments?
        Ge = Ge.sort_values("length", ascending=False).groupby(["u", "v"]).first()

        # Ignore streets that we know will have traffic b/c they: footways; and service roads.
        #  (unless we are later routed through them by the OSRM API)
        Ge["ignore"] = False
        Ge.ignore = (
            Ge.ignore
            # | (Ge.dt > 0)  # take us further away;
            | Ge.highway.str.contains("footway")  # shouldn't route here
            | Ge.highway.str.contains("service")  # shouldn't route here
            | Ge.highway.str.contains("path")  # shouldn't route here
            | Ge.highway.str.contains("driveway")  # shouldn't route here
        )

        # Calculate how efficiently each possible route gets us towards our goal.
        Ge["speed_mps"] = (
            Ge.maxspeed.str.replace(" mph", "").astype(float).fillna(25) * 1609 / 3600
        )
        Ge["est_transit_time_s"] = Ge["length"] / Ge["speed_mps"]
        Ge["efficiency"] = Ge["dt"] / Ge["est_transit_time_s"]

        # Gives us back an unambiguous dummy index (integers, 0..len(Ge)) but keeps u,v as cols
        # that we can query more flexibly than if they are in the index
        Ge = Ge.reset_index()

        # Calculate the 'best' next step for each route, based on efficiency, but
        #  only allowing choices that get us closer (to avoid cycles)
        best_edges = (
            Ge.query("dt<0")
            .sort_values("efficiency", ascending=True)
            .groupby("u")
            .v.first()
        )

        # Now we have a u->v (n1->n2) mapping¬, like:
        # u
        # 25240726       250117169
        # 25240774       250142020
        #                  ...
        # 5089035979     194721949
        # Name: v, Length: 245, dtype: int64

        # We create a new column, 'w', which contains the 'next step' of (u,v) if
        #  we know it... and is 0 otherwise.
        Ge["w"] = Ge.v.map(best_edges).fillna(0).astype(np.long)

        # Special value -1 for 'w' means it's the final traffic sink.
        Ge.loc[Ge.end_time == 0, "w"] = -1

        # We make a copy of 'v' that is used to keep track of how to 'skip' to
        #  a later segment if the following segment (v,w) doesn't exist (anwer:
        #  just route traffic to (v2,w) and accept there there will be a 'gap'
        #  on screen.
        Ge["v2"] = Ge["v"].astype("int")

        # Re-index Ge as (u,v) for fast access.
        Ge = Ge.set_index(["u", "v"])

        return Ge, Gn


def followup_heuristic_routing(Ge, Gn):
    """ Route edges that aren't clear by recursively searching for alternative
    routes that eventually get us closer. I think this is needed because the
    table API can give bogus results. But, if this doesn't work, we'll just
    use the OSRM Routing API directly in the next step."""
    with Timer(prefix="Follow-up routing using heuristics"):
        print(
            f"Need to fix {len(Ge.query('w==0 and ignore==False'))} ambiguous edges (Currently: {len(Ge.query('ignore==True'))} ignored, {len(Ge.query('w!=0 and ignore==False'))} resolved, {len(Ge)} total)"
        )

        def get_options(s, depth):
            """ Recursive enumeration of all routes we can take away from
            this spot. We'll then pick the best one. This is SLOW and should
             be improved or skipped."""
            u, v = s.name
            if depth <= 0:
                return [[s]]
            options = []
            #     if s.w:
            try:
                # next_options = Ge.query('u==@v and v==@s.w') if s.w else Ge.query('u==@v')
                # here, should we ignore footpaths, etc?
                if s.w:
                    next_options = Ge.loc[([v], [s.w]), :]
                else:
                    next_options = Ge.loc[[v], :]
            except KeyError:
                return [[s]]
            #     else:
            #         next_options = Ge.loc[(v, slice(None))]#.query('u==@v')
            for (up, vp), sp in next_options.iterrows():
                options += [[s] + spp for spp in get_options(sp, depth - 1)]
            return options

        def option_length(option):
            return sum([o.length for o in option])

        # Loop through every un-calculated edge.
        df_to_fix = Ge.query("w==0 and ignore==False").sort_values(
            "end_time", ascending=False
        )
        for i, ((u, v), s) in enumerate(df_to_fix.iterrows()):
            if Ge.loc[(u, v), "w"] != 0:
                continue  # might have been filled in by previous loops; skip! :)

            if i % 100 == 0:
                print(f"{i}/{len(df_to_fix)}")

            # Search out farther and farther hoping that we find
            #  a route that gets us closer than we are now.
            for n in range(1, 4, 1):
                options = get_options(s, n)
                if not len(options):
                    break

                df = pd.DataFrame.from_dict(
                    {
                        i: {"dt": o[-1].end_time - s.end_time, "l": option_length(o)}
                        for i, o in enumerate(options)
                    },
                    orient="index",
                )

                df = df.query("dt<0")
                df.loc[:, "efficiency"] = df.dt / df.l
                df = df.sort_values("efficiency")
                if not len(df):
                    continue

                # cool - we found a path that gets us closer. Let's route
                #  accordingly.
                option = options[
                    df.index[0]
                ]  # grab the best otion as decided by sorting df
                for i, step in enumerate(option[:-1]):
                    assert (step.w == 0) or (step.w == option[i + 1].name[1])
                    Ge.loc[step.name, "w"] = option[i + 1].name[1]
                #             print('Found new sub-path w/ depth %d: \n%s' % (n, str(df.iloc[0])))
                break
            else:
                print(RuntimeWarning("Couldn" "t find workable option by n==%d" % n))
                ### Should we do an OSRM route lookup here?
                ## Might be efficient, especially if we started with the
                ## furthest-away ambiguous edge...

    return Ge, Gn


def followup_osrm_routing_parallel(
    G, Ge, Gn, center_node, min_iter=5, max_iter=100, towards_origin=True
):
    """ Use OSRM routing API calls to fix any remaining unsolved edges.
    This version uses parallelized/simultaneous OSRM calls to speed things up."""

    # How many routings to do before re-scanning for candidate nodes, which
    #  may have been resolved in the meantime
    BATCH_SIZE = 25
    # How many calls to do in parallel.
    N_WORKERS = 5

    # Spin up a thread pool for parallelization of the OSRM calls.
    with concurrent.futures.ThreadPoolExecutor(max_workers=N_WORKERS) as executor:

        with Timer(prefix="Fix missing bits with OSRM"):
            for i in range(max_iter):
                df_unsolved = Ge.query("w==0 and ignore==False")
                print("There are %d unsolved edges." % len(df_unsolved))

                # We get as many unresolved nodes as we can.
                df_to_solve = df_unsolved.sample(min(BATCH_SIZE, len(df_unsolved)))

                # And if we need others, we choose them randomly.
                n_extra_needed = BATCH_SIZE - len(df_to_solve)
                if n_extra_needed:
                    df_to_solve = df_to_solve.append(
                        Ge.query("w > 0 and ignore==False").sample(n_extra_needed)
                    )

                # OK - these are the nodes we need to route to/from
                node_ids = df_to_solve.index.get_level_values("v").unique()
                nodes = set(Ge.index.get_level_values(1)).union(
                    Ge.index.get_level_values(0)
                )

                # Submit the OSRM requests.
                if towards_origin:
                    future_to_node = {
                        executor.submit(
                            osrm.osrm, G, G.nodes[node_id], center_node
                        ): node_id
                        for node_id in node_ids
                    }
                else:
                    future_to_node = {
                        executor.submit(
                            osrm.osrm, G, center_node, G.nodes[node_id]
                        ): node_id
                        for node_id in node_ids
                    }

                # Now grab all of the results and put them into an array.
                routings = []
                for future in concurrent.futures.as_completed(future_to_node):
                    v = future_to_node[future]
                    try:
                        route, transit_time, r = future.result()
                    except Exception as exc:
                        print(exc)
                        continue

                    for uu, vv in df_to_solve.loc[pd.IndexSlice[:, [v]], :].index:
                        rroute = list(filter(lambda e: e in nodes, route))
                        if not towards_origin:
                            rroute = rroute[::-1]
                        if rroute[0] != vv:
                            rroute = [vv] + rroute
                        rroute = [uu] + rroute

                        # Add to 'routings' as (u,v,w) triplets.
                        routings += [rroute[i : i + 3] for i in range(len(rroute) - 2)]

                # A dataframe of all the triplets from all of the OSRM requests we just did
                dfroutings = pd.DataFrame(routings, columns=["u", "v", "w"])

                # de-dup, taking most common 'w' if there are multiples. (especially on high-traffic routes,
                #  we probably will have a lot of duplicates from our parallel requests)
                dfroutings2 = dfroutings.groupby(["u", "v"]).agg(
                    lambda x: pd.Series.mode(x)[0]
                )

                # Now, get rid of any (u,v) pairs that aren't in the edges array Ge.
                common_index = dfroutings2.index.intersection(Ge.index)
                missing_index = dfroutings2.index.difference(Ge.index)
                # for (u, v) in missing_index:
                #
                #     uu, vv = u, v
                #
                #     for i in range(500):
                #         ww = dfroutings2.loc[(uu, vv)].item()
                #
                #         if (vv, ww) in Ge.index:
                #             Ge.loc[(u, v), "v2"] = int(vv)
                #             Ge.loc[(u, v), "w"] = int(ww)
                #             print(f"!{i}")
                #             break
                #         else:
                #             uu, vv = vv, ww
                #     else:
                #         # raise Exception()
                #         print(f'Oh crap! {i}')
                n_new_solved = len(common_index.intersection(df_unsolved.index))
                print(f"Solved {n_new_solved} new edges.")
                Ge.loc[common_index, "w"] = dfroutings2.loc[common_index, "w"]

                # If we've solved them all, and have done our min_iter iterations,then break.
                if (len(df_unsolved) == 0) and (i >= min_iter):
                    break

    return Ge


def propagate_edges(Ge):
    """Propagate traffic from each edge towards the center node, using the routings that we just
     figured out. """

    # Reset index to a dummy integer index for faster/easier access
    Gge = Ge.copy().reset_index()

    # Make a mapping from ('u','v') to this new dummy index to speed up some stuff below.
    edge_mapping = Gge[["u", "v"]].copy()
    edge_mapping["edge_idx"] = edge_mapping.index
    edge_mapping = edge_mapping.set_index(["u", "v"])

    Gge["through_traffic"] = 0  # how much traffic has gone through each edge.
    Gge["current_traffic"] = 0  # Amount of traffic on that edge
    valid_edges = Gge.query("w != 0")

    # Each non-ignored edge gets 1 car, plus another 1 car per every 50 m of length.
    Gge.loc[valid_edges.index, "current_traffic"] = valid_edges.length / 50  # +1

    # No traffic originates on freeways
    Gge.loc[Gge.highway.str.startswith("motorway") == True, "current_traffic"] = 0

    # Residential streets spawn more traffic
    Gge.loc[
        Gge.highway.isin(["residential", "tertiary", "secondary"]) == True,
        "current_traffic",
    ] *= 5

    old_status = ""
    with Timer(prefix="Propagate Edges"):
        while True:
            edges_to_propagate = (
                Gge.query("(current_traffic > 0)")  # .reset_index()  # & (w != 0)")
                .loc[:, ["u", "v", "v2", "w", "current_traffic"]]
                .copy()
            )

            if not len(edges_to_propagate):
                break

            try:
                # Print status, and check to make sur eit changed, otherwise
                # we are in a loop
                assert (edges_to_propagate.w != 0).all()
                status = "Edges to propagate: %d. Traffic: %d. Cars on road: %d." % (
                    len(edges_to_propagate),
                    edges_to_propagate.current_traffic.mean(),
                    edges_to_propagate.current_traffic.sum(),
                )
                print(status)
                if status == old_status:
                    print("Looping without traffic updates. STOP!")
                    # raise Exception()
                    break
                old_status = status
            except Exception as e:
                raise
                pass

            # Tally up current traffic as through traffic
            Gge.loc[
                edges_to_propagate.index, "through_traffic"
            ] += edges_to_propagate.current_traffic

            # Zero current traffic on main copy
            Gge.current_traffic = 0

            # Propagate current traffic to next step using the routing we figured out earlier.
            traffic = (
                edges_to_propagate.query("w>0")
                .groupby(["v2", "w"])
                .current_traffic.sum()
            )

            # Drop any edges that don't exist
            common_index = traffic.index.intersection(edge_mapping.index)
            traffic = traffic.loc[common_index]
            dummyindexed_traffic = pd.Series(
                traffic.values,
                index=edge_mapping.loc[traffic.index, "edge_idx"].values.astype(int),
            )

            # Now propagate into the main copy to be ready for the next iteration.
            Gge.loc[
                dummyindexed_traffic.index, "current_traffic"
            ] = dummyindexed_traffic

    return Gge
