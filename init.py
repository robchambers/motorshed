import subprocess, os
cwd = os.getcwd()

extract = 'docker run -t -v %s:/data osrm/osrm-backend osrm-extract -p /opt/car.lua /data/oregon-latest.osm.pbf' % cwd
partition = 'docker run -t -v %s:/data osrm/osrm-backend osrm-partition /data/oregon-latest.osrm' % cwd
customize = 'docker run -t -v %s:/data osrm/osrm-backend osrm-customize /data/oregon-latest.osrm' % cwd
routed = 'docker run -t -i -p 5000:5000 -v %s:/data osrm/osrm-backend osrm-routed --algorithm mld /data/oregon-latest.osrm' % cwd

subprocess.check_call(extract.split(' '))
subprocess.check_call(partition.split(' '))
subprocess.check_call(customize.split(' '))
router = subprocess.Popen(routed.split(' '))

# router.terminate()