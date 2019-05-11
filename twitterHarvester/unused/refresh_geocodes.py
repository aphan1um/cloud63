# Credit to: https://gis.stackexchange.com/a/208574
# Credit to: https://stackoverflow.com/a/36400130

import sys
import couchdb
import fiona
from shapely.geometry import shape, mapping, Point, Polygon, MultiPolygon

SHP_FILE_LOC = sys.argv[1]
DB_LOC = sys.argv[2]

# load shape file
shape_f = fiona.open(SHP_FILE_LOC)
# get all LGA polygons
lgas = [region for region in shape_f]

server = couchdb.Server(DB_LOC)
db_geocodes = server['geocodes']

# go through each location in view
location_view = db_geocodes.view("locnames/coords")
view = [v for v in location_view]

for loc in view:
    loc_doc = db_geocodes.get(loc.id)
    print("Processing id: %s" % (loc.id))

    if 'lga' in loc_doc or loc_doc['state'] != 'Victoria':
        continue

    pt = Point(loc.key[1], loc.key[0])
    for region in lgas:
        if pt.within(shape(region['geometry'])):
            loc_doc['lga'] = region['properties']['lga_code']
            db_geocodes.save(loc_doc)

