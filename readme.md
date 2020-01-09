# Motorshed

See http://www.motorshed.io for a gallery and more info on this project.

Motorshed is an open-source project to explore and visualize traffic patterns using beautiful, stylized maps.

A **Motorshed Map** shows the flow of traffic to (or from) a single point on the map (origin point), 
from (or to) every other point on the map. A motorshed (our term) is named by analogy to a watershed map, 
which shows the flow of water downhill from every point in a watershed to a single outlet point. But 
whereas water follows the elevation gradient, traffic follows the travel-time-to-destination gradient.

Motorshed maps are meant to be interesting, thought-provoking, and aesthetically pleasing. But,
they are also (ostensibly) useful: given a motorshed map with your home as the origin point, you
can trace the lines (biggest to smallest) to find the quickest route from your house to any point
on the map, and vice-versa.

You might also find the maps useful for carpool planning (with the origin as your workplace?).

The basic motorshed map can be extended in a few interesting ways:

* **The bidirectional map**: shows the *from* and *to* maps either side-by-side, or overlaid with
  different colors. The maps differ slightly due to, e.g., one-way-streets and difficult left turns.
* **The Bicycle, Pedestrian, or Public Transit Map**: is like a motorshed, but for alternate
  modes of transportation. It can be fun/intersting to compare motorsheds with bikesheds, sneakersheds,
  or... transitsheds? (Obviously, we could use some help on the naming :) )
* **The Transit-time Map**: You can add transit-time information to the map by, e.g. coloring the lines
  or adding isochrone (equal-travel-time) contours. You can even plot a 3-d map where elevation is given
  by the contours. The use-cases are obvious, but we've found it's hard to get this much info on a 
  motorshed map without destroying the aesthetics. We'd love to see some cool suggestions!

This repo contains the basic code to create Motorshed maps using publicly available GIS services based
on open street map.

An example tri-pane bidirectional map of a street address in San Francisco (10km on a side):

![Bidirectional map](images/example_10k_sf_bidir_tripane.png)

Or, for the New York Stock Exchange (see the notebooks for this example):
![Bidirectional map](images/11%20Wall%20Street%20New%20York%20NY.5000.bi_dir_tri_pane.png)

** IMPORTANT NOTE **: The public services (Overpass and OSRM) that we rely on are free; PLEASE don't 
abuse them. If you're creating anything more than a few maps, please set up your own Overpass and
OSRM servers, and/or switch to a paid API like Mapbox.

## Setup
This section assumes you want to install motorshed into its own Anaconda (Python) environment.

### Install dependencies (OSMNX and other stuff)
First, install Anaconda on your system.

Then,
 
```sh
# Creates conda environment named 'motorshed'
conda env create -f environment.yaml

# activates that environment
conda activate motorshed

```

### Install this package
In order to be able to `import motorshed` from anywhere on your system, you must either
mess with your `PYTHONPATH` or, preferably, just run:
```sh
# make sure you're in the conda env that you will be using in the future
conda activate motorshed

# Then make the package importable by installing it in 'editable' mode:
# In the `motorshed` directory, which contains setup.py:
pip install -e ./
```
To confirm that it worked, try running `import motorshed` in any Python terminal.

### To run the tests
In the `motorshed` directory that contains `motorshed/setup.py`:

```sh
pytest ./
```

## Running Motorshed

We've created a couple of scripts that demonstrate how to make a basic (very small) map.

In the base repo directory, run 

```
python motorshed/scripts/run_basic_map.py
```

which should create a small test map (4km on a side) leading to the Foster City, CA Tesla
dealership. (Note the cool road pattern of the engineered landfill neighborhood.)

![Basic map](images/391%20Foster%20City%20Blvd%20Foster%20City%20CA%2094404.3000.basic_example.png)

Or, to maker a bidirectional map (shows traffic in both directions), run:

```
python motorshed/scripts/run_bidir_map.py
```

The tri-pane version of this map (showing to, from, and combined views) looks like:
![Bidirectional map](images/391%20Foster%20City%20Blvd%20Foster%20City%20CA%2094404.3000.bi_dir_tri_pane.png)


## Notebooks

Just run `jupyter notebook` in, e.g., the `notebooks` directory. This is a great
way to explore the maps, and there are several examples to get you started.

You can browse most of the notebooks on Github to see what they look like.
