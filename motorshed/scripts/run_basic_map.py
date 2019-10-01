from motorshed import osrm
from motorshed import overpass
from motorshed.algos import gen2

# address = '601 Minnesota St San Francisco, CA 94107'
# distance = 3_000

address = "32 Bank St Lebanon, NH 03766"
distance = 2_000

G, center_node, origin_point = overpass.get_map(address, distance=distance)

osrm.get_transit_times(G, center_node)

Gn, Ge = gen2.create_initial_dataframes(G)

# assert Gn.shape[1] == 10
# assert Ge.shape[1] == 16
assert len(Gn)
assert len(Ge)

assert (Gn.calculated == False).all()
(Ge.through_traffic == 0).all()

Ge2, Gn2 = gen2.initial_routing(Ge.copy(), Gn.copy())

Ge3, Gn3 = gen2.followup_heuristic_routing(Ge2.copy(), Gn2.copy())

Ge4 = gen2.followup_osrm_routing_parallel(G, Ge3, Gn3, center_node)

assert not len(Ge4.query("w==0 and ignore==False"))

Gge = gen2.propagate_edges(Ge4)

assert (Gge[Gge.ignore == False].through_traffic >= 0).all()
assert (Gge["current_traffic"] == 0).all()

from motorshed import render_mpl

rgba_arr = render_mpl.render_layer(Gn3, Gge, center_node)

fn = ("%s.%s.basic_example" % (address, distance)).replace(",", "")
print(fn)

fn2 = render_mpl.save_layer(fn, rgba_arr)
