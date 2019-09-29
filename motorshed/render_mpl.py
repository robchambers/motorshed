import imageio
import matplotlib.cm as cm
import numpy as np
from bokeh.palettes import Magma256
from contexttimer import Timer
from matplotlib import pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.collections import LineCollection


def render_layer(
    Gn, Ge, center_node, bgcolor="black", canvas_inches=8, dpi=150, max_edge_width=None
):
    """ Fast matplotlib-based function to render the graph defined by Gn and Ge,
      with concentric circles at the center_node. Return
      as an image: np.ndarray `rgb_arr`.
    """

    # guess approximate geographic size to help w/ guessing a good line width.
    approx_width_m = (Gn.x.max() - Gn.x.min() + Gn.y.max() - Gn.y.min()) / 2

    # If needed, take into account graph size and complexity, and figure size, to guess
    #  a good edge width. This is based on past "good" value, and seems to work pretty
    #  well.
    if max_edge_width is None:
        max_edge_width = (
            3
            * (10000 / approx_width_m) ** 0.25
            * (50000 / len(Ge)) ** 0.15
            * (30000 / len(Gn)) ** 0.1
            * (canvas_inches / 8) ** 0.33
        )

        print(f"Guessing a good max width: {max_edge_width} pixels")

    # Temporary dataframe for prepping graph.
    gdf = Ge.query("through_traffic!=0").reset_index().copy()

    # Limit how small edges can get.
    min_intensity_ratio = 1.1 / 255
    min_edge_width = max_edge_width * 0.05

    # we make 'edge intensity' a logarithmic fxn of the through
    #  traffic, with a '+2' that prevents verrry small through
    #  traffics from re-scaling the graph.
    gdf["edge_intensity"] = np.log2(gdf.through_traffic + 2.0)
    # Edge widths scale as edge intensity, between our min and max
    #  allowable edge widthsl.
    gdf["edge_widths"] = (gdf.edge_intensity / gdf.edge_intensity.max()) * (
        max_edge_width - min_edge_width
    ) + min_edge_width

    # Make edge intensity between 0->255 (uint8) for easier plotting.
    gdf.edge_intensity = (gdf.edge_intensity / gdf.edge_intensity.max()) * (
        1 - min_intensity_ratio
    ) + min_intensity_ratio
    gdf.edge_intensity = (gdf.edge_intensity * 255).astype(np.uint8)

    # Sort edges so that when plotted, the brightest/thickest ones are on top.
    gdf.sort_values("edge_widths", ascending=True, inplace=True)

    # Vectorized operations to calculate inputs to the plotting function
    xy1 = Gn.loc[gdf.u, ["x", "y"]].values
    xy2 = Gn.loc[gdf.v, ["x", "y"]].values
    line_coords = list(
        zip(xy1, xy2)
    )  # wish this was a numpy op; that might be possible
    line_colors = cm.magma(
        gdf.edge_intensity
    )  # map edge intensities using chosen color map

    # Create a matplotlib canvas
    fig, ax = plt.subplots(
        figsize=(canvas_inches, canvas_inches), facecolor=bgcolor, dpi=dpi
    )
    ax.set_facecolor(bgcolor)

    # add the lines to the axis as a linecollection (a pretty fast MPL actor)
    lc = LineCollection(
        line_coords, colors=line_colors, linewidths=gdf.edge_widths, capstyle="round"
    )
    ax.add_collection(lc)

    # Try to set axes. Would be better to use an actual bounding box
    ax.set_xlim(Gn.x.min(), Gn.x.max())
    ax.set_ylim(Gn.y.min(), Gn.y.max())
    ax.set_aspect("equal")

    # Get rid of stuff we dont need like axes, tickets, margins, etc
    xaxis = ax.get_xaxis()
    yaxis = ax.get_yaxis()
    xaxis.get_major_formatter().set_useOffset(False)
    yaxis.get_major_formatter().set_useOffset(False)
    ax.axis("off")
    ax.margins(0)
    ax.tick_params(which="both", direction="in")
    xaxis.set_visible(False)
    yaxis.set_visible(False)

    #####
    # Draw the 'center node'. This is ugly and could be refactored/shortened. Or,
    #  it would be nice to have other options, e.g., a graphic icon
    R = 100  # 100 meters approx
    cmap = Magma256

    ax.add_artist(
        plt.Circle(
            (Gn.loc[center_node].x, Gn.loc[center_node].y),
            zorder=2,
            radius=R,
            color=cmap[150],
            alpha=0.1,
        )
    )
    ax.add_artist(
        plt.Circle(
            (Gn.loc[center_node].x, Gn.loc[center_node].y),
            zorder=2,
            radius=R * 0.75,
            color=cmap[190],
            alpha=0.2,
        )
    )
    ax.add_artist(
        plt.Circle(
            (Gn.loc[center_node].x, Gn.loc[center_node].y),
            zorder=2,
            radius=R * 0.65,
            color=cmap[210],
            alpha=0.3,
        )
    )
    ax.add_artist(
        plt.Circle(
            (Gn.loc[center_node].x, Gn.loc[center_node].y),
            zorder=2,
            radius=R * 0.55,
            color=cmap[220],
            alpha=0.4,
        )
    )
    ax.add_artist(
        plt.Circle(
            (Gn.loc[center_node].x, Gn.loc[center_node].y),
            zorder=2,
            radius=R * 0.45,
            color=cmap[235],
            alpha=0.55,
        )
    )
    ax.add_artist(
        plt.Circle(
            (Gn.loc[center_node].x, Gn.loc[center_node].y),
            zorder=2,
            radius=R * 0.35,
            color=cmap[255],
            alpha=1.0,
        )
    )

    # Tight layout to use more of the Field of View
    fig.tight_layout()

    # Create an aggregator and render
    canvas = FigureCanvasAgg(fig)
    canvas.draw()

    # Extract as an RGBA numpy array
    s, (width, height) = canvas.print_to_buffer()
    rgba_arr = np.frombuffer(s, np.uint8).reshape((height, width, 4))
    print(rgba_arr.shape)
    plt.close(fig)

    # Return the array (image)
    return rgba_arr


def save_layer(fn, rgba_arr):
    """ Save the RGBA array as a PNG. Return the filename."""
    with Timer(prefix="PNG"):
        fn_png = fn + ".png"
        print(fn_png)
        imageio.imwrite(fn_png, rgba_arr)

    return fn_png
