import osmnx as ox
import requests
import time
from tqdm import tqdm
import numpy as np
import matplotlib.cm as cm
import requests_cache
from contexttimer import Timer
import pickle
import pandas as pd


# Cache HTTP requests (other than map requests, which I think are too complicated
#  to do this with). This is a SQLITE cache that never expires.
requests_cache.install_cache()


def chunks(l, n):
    """Yield successive n-sized chunks from l."""

    for i in range(0, len(l), n):
        yield l[i:i + n]


def get_transit_times(G, origin_point):
    """Calculate transit_time for every node in the graph"""

    end = '%s,%s' % (origin_point[1], origin_point[0])
    starts = ['%s,%s' % (data['lon'], data['lat']) for n, data in G.node(data=True)]
    times = []

    # the table service seems limited in number
    for chunk in chunks(starts, 300):
        chunk = ';'.join(chunk)
        query = 'http://router.project-osrm.org/table/v1/driving/%s;%s?sources=0' % (end, chunk)
        r = requests.get(query)
        times = times + r.json()['durations'][0][1:]

    for n, node in enumerate(G.node):
        G.node[node]['transit_time'] = times[n]


def osrm(G, origin_node, center_node, missing_nodes, mode='driving', localhost=False):
    """Query the local or remote OSRM for route and transit time"""

    start = '%f,%f' % (G.node[origin_node]['lon'], G.node[origin_node]['lat'])
    end = '%f,%f' % (G.node[center_node]['lon'], G.node[center_node]['lat'])

    if localhost:
        query = 'http://localhost:5000/route/v1/%s/%s;%s?steps=true&annotations=true' % (mode, start, end)
    else:
        query = 'http://router.project-osrm.org/route/v1/%s/%s;%s?steps=true&annotations=true' % (mode, start, end)
    r = requests.get(query)

    try:
        route = r.json()['routes'][0]['legs'][0]['annotation']['nodes']
        transit_time = r.json()['routes'][0]['duration']

    except KeyError:
        print('No route found for %i' % origin_node)
        missing_nodes.update(origin_node)
        route, transit_time = [], np.NaN

    return route, transit_time, r


def get_map(address, place=None, distance=1000):
    """Get the graph (G) and center_node from OSMNX, initializes through_traffic, transit_time, and calculated.
    Uses local cache (via Pickle) when possible."""

    if place is not None: distance = 100

    # calculate fn for cache using fxn arguments.
    fn = "%s.%s%s.cache.pkl" % (address, place or '', distance)
    try:
        # Try to load cache
        with open(fn, 'rb') as f:
            (G, center_node, origin_point) = pickle.load(f)
            return (G, center_node, origin_point)
    except:
        # If cache miss, then load from netowrk.
        print('Cache miss. Loading.')

        G, origin_point = ox.graph_from_address(address, distance=distance,
                                                network_type='all', return_coords=True)

        if place is not None:
            G = ox.graph_from_place(place, network_type='drive')

        # get center node:
        center_node = ox.get_nearest_node(G, origin_point)

        G = ox.project_graph(G)

        # initialize edge traffic to 1, source node traffic to 1:
        for u, v, k, data in G.edges(data=True, keys=True):
            data['through_traffic'] = 1

        for node, data in G.nodes(data=True):
            data['calculated'] = False

        # Save to cache for next time.
        with open(fn, 'wb') as f:
            pickle.dump((G, center_node, origin_point), f)

        return G, center_node, origin_point


def increment_edges(route, G, missing_edges):
    """For a given route, increment through-traffic for every edge on the route"""

    if len(route) > 0:
        accum_traffic = 1
        for i0, i1 in zip(route[:-1], route[1:]):
            if not G.node[i0]['calculated']:
                accum_traffic += 1
            try:
                G.edges[i0, i1, 0]['through_traffic'] += accum_traffic # new way
            except KeyError:
                missing_edges.update((i0, i1))
                # continue

            G.node[i0]['calculated'] = True
        # increment_edges(route[1:], G, missing_edges)


def find_all_routes(G, center_node):
    """Run through the nodes in the graph, calculate routes, and recursively increment edges"""

    missing_edges = set([])
    missing_nodes = set([])

    for origin_node in tqdm(G.nodes()):
        if not G.node[origin_node]['calculated']:
            route, transit_time, r = osrm(G, origin_node, center_node, missing_nodes, mode='driving')
            route = [node for node in route if node in list(G)]

            increment_edges(route, G, missing_edges)

    return missing_edges, missing_nodes


def draw_map(G, center_node, color_by='through_traffic', cmap_name='magma', save=True):
    """Draw the map, coloring by through_traffic or by transit_time"""

    edge_intensity = np.log2(np.array([data['through_traffic'] for u, v, data in G.edges(data=True)]))
    edge_widths = (edge_intensity / edge_intensity.max()) * 3  # + 1

    if color_by == 'through_traffic':
        edge_intensity = (edge_intensity / edge_intensity.max()) * .95 + .05
        edge_intensity = (edge_intensity * 255).astype(np.uint8)

    elif color_by == 'transit_time':
        edge_intensity = np.array([G.node[u]['transit_time'] + G.node[v]['transit_time'] for u, v in G.edges()])
        edge_intensity = (edge_intensity / edge_intensity.max()) * .95 + .05
        edge_intensity = (255 - edge_intensity * 255).astype(np.uint8)

    cmap = cm.get_cmap(name=cmap_name)
    edge_colors = cmap(edge_intensity)

    fig, ax = ox.plot_graph(G, edge_color=edge_colors, edge_linewidth=edge_widths, equal_aspect=True,
                            node_size=0, save=True, fig_height=14, fig_width=16, use_geom=True,
                            close=False, show=False, bgcolor='k')

    ax.scatter([G.node[center_node]['x']], [G.node[center_node]['y']],
               color='red', s=150, zorder=10, alpha=.25)
    ax.scatter([G.node[center_node]['x']], [G.node[center_node]['y']],
               color='pink', s=100, zorder=10, alpha=.3)
    ax.scatter([G.node[center_node]['x']], [G.node[center_node]['y']],
               color='yellow', s=50, zorder=10, alpha=.6)
    ax.scatter([G.node[center_node]['x']], [G.node[center_node]['y']],
               color='white', s=30, zorder=10, alpha=.75)

    if save: fig.savefig('map.png', facecolor=fig.get_facecolor(), dpi=600)
    # fig.show()

from bokeh.plotting import figure
from bokeh.models import HoverTool, ColumnDataSource

from bokeh.palettes import Magma256

def make_bokeh_map(G, center_node, color_by='through_traffic', plot_width=500, plot_height=500, output_backend='canvas'):
    """Creates a Bokeh map that can either be displayed live (e.g., in a notebook or webpage) or saved to disk.

    If saving as svg, set output_backend to 'svg'."""

    edge_intensity = np.log2(np.array([data['through_traffic'] for u, v, data in G.edges(data=True)]))
    edge_widths = (edge_intensity / edge_intensity.max() ) * 2 + .5

    if color_by == 'through_traffic':
        edge_intensity = (edge_intensity / edge_intensity.max() ) * .95 + .05
        edge_intensity = (edge_intensity*255).astype(np.uint8)
    elif color_by == 'transit_time':
        edge_intensity = np.array([G.node[u]['transit_time'] + G.node[v]['transit_time'] for u,v in G.edges()])
        edge_intensity = (edge_intensity / edge_intensity.max() ) * .95 + .05
        edge_intensity = (255 - edge_intensity*255).astype(np.uint8)

    lines = []
    for (u, v, data), width, intensity in zip(G.edges(keys=False, data=True), edge_widths, edge_intensity):
        edge_intensity = intensity
        color = Magma256[edge_intensity]
        if 'geometry' in data:
            xs, ys = data['geometry'].xy
        else:
            # if it doesn't have a geometry attribute, the edge is a straight
            # line from node to node
            xs = (G.nodes[u]['x'], G.nodes[v]['x'])
            ys = (G.nodes[u]['y'], G.nodes[v]['y'])

        line = {'xs': tuple(xs), 'ys': tuple(ys), 'color': color, 'width': width, 'u':u, 'v':v,
                'data': str(data)}
        lines.append(line)


    df = pd.DataFrame(lines)
    df = df.sort_values('width')
    source = ColumnDataSource(df)
    p = figure(plot_width=plot_width, plot_height=plot_height, match_aspect=True, output_backend=output_backend)
    p.outline_line_color = None
    p.xaxis.visible = False
    p.yaxis.visible = False
    p.xgrid.visible = False
    p.ygrid.visible = False
    p.background_fill_color = "black" #None
    p.border_fill_color = None
    p.multi_line('xs', 'ys', source=source, color='color', line_width='width',
                line_join='round', line_cap='round')
    hover = HoverTool(tooltips=[#('xs', '@xs'),
                                #('ys', '@ys'),
                                ('color', '@color'),
                                ('width', '@width'),
                                ('u', '@u'),
                                ('v', '@v'),
                                ('data', '@data'),

                               ])
    p.add_tools(hover)

    return p

if __name__ == '__main__':

    address = '601 Minnesota St San Francisco, CA 94107'
    distance = 500

    with Timer(prefix='Get map'):
        G, center_node, origin_point = get_map(address, distance=distance)

    with Timer(prefix='Get transit times'):
        get_transit_times(G, origin_point)

    with Timer(prefix='Calculate traffic via'):
        missing_edges, missing_nodes = find_all_routes(G, center_node)

    # Make a map and save it as .SVG
    from bokeh.io import export_svgs

    fn = ("%s.%s" % (address, distance)).replace(',', '')
    print(fn)

    p = make_bokeh_map(G, center_node, output_backend='svg')

    with Timer(prefix='SVG'):
        export_svgs(p,
                    filename=fn + '.svg')

    from bokeh.io import export_png
    with Timer(prefix='PNG'):
        export_png(p, filename=fn+'.png')