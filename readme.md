# Install dependencies (OSMNX and other stuff)

`
conda config --add channels conda-forge 
conda create -c conda-forge --override-channels --name geo osmnx tqdm
source activate geo
`

## You will also want to run docker, either by init.py, or...
`
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/oregon-latest.osrm
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/oregon-latest.osrm
docker run -t -i -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/oregon-latest.osrm
`

### example:

`
import motorshed
address = '2960 Charnelton Street, Eugene, Oregon'
G, center_node = motorshed.get_map(address, distance=5000)
`

### or, you can run by place:
`
place = 'Eugene, Oregon, USA'
G, center_node = motorshed.get_map(address, place=place)
`


### then analyze and draw the map:
`
missing_edges, missing_nodes = motorshed.find_all_routes(G, center_node)
motorshed.draw_map(G, center_node, color_by='through_traffic')
`