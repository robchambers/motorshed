#!/bin/bash

cd maps/oregon
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-partition /data/oregon-latest.osrm
docker run -t -v $(pwd):/data osrm/osrm-backend osrm-customize /data/oregon-latest.osrm
docker run -t -i -p 5000:5000 -v $(pwd):/data osrm/osrm-backend osrm-routed --algorithm mld /data/oregon-latest.osrm
