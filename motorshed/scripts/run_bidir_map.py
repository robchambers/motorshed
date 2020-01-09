from contexttimer import Timer

import motorshed
from motorshed import render_mpl

from motorshed.example_parameters import example_maps

example_map = example_maps["foster_city_tesla 2km"]
address = example_map["center_address"]
distance = example_map["distance_m"]


with Timer(prefix="AWAY from origin"):
    towards_origin = False

    with Timer(prefix="Get map"):
        G, center_node, origin_point = motorshed.overpass.get_map(
            address, distance=distance
        )

    with Timer(prefix="Get transit times"):
        motorshed.osrm.get_transit_times(G, center_node, towards_origin=towards_origin)

    Gn, Ge = motorshed.algos.gen2.create_initial_dataframes(
        G, towards_origin=towards_origin
    )
    assert (Gn.calculated == False).all()
    (Ge.through_traffic == 0).all()

    Ge, Gn = motorshed.algos.gen2.initial_routing(Ge, Gn)

    Ge, Gn = motorshed.algos.gen2.followup_heuristic_routing(Ge, Gn)

    Ge = motorshed.algos.gen2.followup_osrm_routing_parallel(
        G, Ge, Gn, center_node, towards_origin=towards_origin
    )

    Gge = motorshed.algos.gen2.propagate_edges(Ge)

    # if not towards_origin:
    #     Gge[['u', 'v']] = Gge[['v', 'u']]

    Gge_reverse = Gge.copy()

with Timer(prefix="TOWARDS origin"):
    towards_origin = True

    with Timer(prefix="Get map"):
        G, center_node, origin_point = motorshed.overpass.get_map(
            address, distance=distance
        )

    with Timer(prefix="Get transit times"):
        motorshed.osrm.get_transit_times(G, center_node, towards_origin=towards_origin)

    Gn, Ge = motorshed.algos.gen2.create_initial_dataframes(
        G, towards_origin=towards_origin
    )
    assert (Gn.calculated == False).all()
    (Ge.through_traffic == 0).all()

    Ge, Gn = motorshed.algos.gen2.initial_routing(Ge, Gn)

    Ge, Gn = motorshed.algos.gen2.followup_heuristic_routing(Ge, Gn)

    Ge = motorshed.algos.gen2.followup_osrm_routing_parallel(
        G, Ge, Gn, center_node, towards_origin=towards_origin
    )

    Gge = motorshed.algos.gen2.propagate_edges(Ge)

    if not towards_origin:
        Gge[["u", "v"]] = Gge[["v", "u"]]

    Gge_forward = Gge.copy()

fn = ("%s.%s" % (address, distance)).replace(",", "")
print(fn)

rgba_arr_f = motorshed.render_mpl.render_layer(
    Gn, Gge_forward, center_node, cmap=motorshed.render_mpl.cm_red
)

motorshed.render_mpl.showarray(rgba_arr_f)

rgba_arr_r = motorshed.render_mpl.render_layer(
    Gn, Gge_reverse, center_node, cmap=motorshed.render_mpl.cm_blue
)

motorshed.render_mpl.showarray(rgba_arr_r)

rgba_arr = motorshed.render_mpl.combine_layers_max([rgba_arr_f, rgba_arr_r])
motorshed.render_mpl.showarray(rgba_arr)

fn = ("%s.%s.bi_dir" % (address, distance)).replace(",", "")

fn2 = motorshed.render_mpl.save_layer(fn, rgba_arr)
print(fn2)

rgba_arr_all = motorshed.render_mpl.concat_layers_horiz(
    [rgba_arr_r, rgba_arr, rgba_arr_f]
)

fn = ("%s.%s.bi_dir_tri_pane" % (address, distance)).replace(",", "")

fn2 = render_mpl.save_layer(fn, rgba_arr_all)
print(fn2)

motorshed.render_mpl.showarray(rgba_arr_all[::3, ::3, :])
