#!/usr/bin/env python3

# -------------------------------------------------------------------------------
#
# This code generates a taginfo project list file (see more https://wiki.openstreetmap.org/wiki/Taginfo/Projects )
#
### Attribution & Disclaimer:
# This code is based on :
# Paul Norman code : https://github.com/osmlab/osm2pgsql_taginfo
# Sven Geggus code : https://github.com/giggls/openstreetmap-carto-de/blob/master/views_osmde/generate_taginfo.py
# -------------------------------------------------------

import json
import os
import re
import yaml
import argparse
parser = argparse.ArgumentParser()
parser.add_argument("-v", "--verbose", help="Print debug info",action="store_true")
args = parser.parse_args()


# -------------------------  parameters ----------------------------
taginfo = {
    "data_format": 1,
    "project": {
        "name": "OpenStreetMap Carto keys",
        "description": "Default OpenStreetMap.org style using CartoCSS",
        "project_url": "https://github.com/gravitystorm/openstreetmap-carto",
        "contact_name": "openstreetmap-carto maintainers",
        "contact_email": "openstreetmap-carto (at) gravitystorm (dot) co (dot) uk"
    },
    "tags": []
}
cwd = os.getcwd()

osm2pgsql_file        = os.path.join(cwd, '..', 'openstreetmap-carto.style')
cartocss_project_file = os.path.join(cwd, '..', 'project.mml')
search_url            = 'https://github.com/gravitystorm/openstreetmap-carto/search?utf8=%E2%9C%93&q='

# ----------------------------------  Examples --------------------
#  tags @> 'capital=>yes'"]
#  tags ? 'wetland'"
#  tags->'wetland'
#  tags->'leaf_type'
#  tags @> '"generator:source"=>wind'
re_tags_one     = re.compile(r"[^a-zA-Z0-9_]tags[^'^)^\[^\]]*'.+?'")


# ----------------------------------  Examples --------------------
#  tags -> ARRAY['wheelchair',ramp:wheelchair']
#  tags ?& ARRAY['wheelchair',ramp:wheelchair']
#  tags ?| ARRAY['wheelchair',ramp:wheelchair']
re_tags_array = re.compile(  r"[^a-zA-Z0-9_]tags\s*[@\?-][>&\|]\s*[aA][rR][rR][aA][yY]\[.+?\]"  )

allhstoretags={}

def processOSMkeys(_layer, _ds_geometry, _osmtype,_tag):
    key=_tag.split("'")[1].split("=")[0].replace('"','')
    if key:
        if args.verbose:
            print("--:", _ds_geometry,"->", _osmtype, " key:", key)
        if key not in allhstoretags:
            k = [ _osmtype ]
            allhstoretags[key]=k
        elif _osmtype not in allhstoretags[key]:
            allhstoretags[key].append(_osmtype)
    return


#
# Parsing openstreetmap-carto.style file
#
with open( osm2pgsql_file , 'r') as style:
    for line in style:
        if line[0] == '#':
            continue
        keyline = line.split()
        if len(keyline) != 4:
            continue
        if keyline[3] == 'delete' or 'nocolumn' in keyline[3]:
            continue
        key = keyline[1]
        object_types = []
        if 'node' in keyline[0]:
            object_types.append('node')
        if 'way' in keyline[0]:
            object_types.append('way')
            if 'polygon' in keyline[3]:
                object_types.append('area')

        if ('area' in object_types) or ('way' in object_types ):
                object_types.append('relation')

        if key not in ('z_order','way_area'):
            taginfo["tags"].append(
                {
                    "key": key,
                    "object_types": object_types,
                    "description": "Used in the osm2pgsql database backend, see more in the github repo",
                    "doc_url": search_url+key
                })



#
# Parsing "project.mml" file for the HSTORE keys (  tags-> )
#

with open( cartocss_project_file , 'r') as f:
  newf = yaml.load(f.read())
f.closed

for layer in newf["Layer"]:
    if args.verbose:
        print( "########### processing Layer: ", layer["id"]," ###########" )
    _layer      = layer["id"]
    ds_geometry = layer.get("geometry")

    ds_type = layer["Datasource"].get("type")
    if ds_type and ds_type == "postgis":
        ds_table = layer["Datasource"].get("table")
        if ds_table:

            osmtype = ''
            if ds_geometry:
                if (ds_geometry=='point'):
                    osmtype='node'
                elif ds_geometry=='linestring':
                    osmtype='way'
                elif ds_geometry=='polygon':
                    osmtype='area'
            else:
                # If no Geometry type - we try to guess the type.
                if 'planet_osm_point' in ds_table.lower():
                    osmtype='node'
                elif 'planet_osm_polygon'  in ds_table.lower():
                    osmtype='area'
                elif 'planet_osm_line'  in ds_table.lower():
                    osmtype='way'
                elif 'planet_osm_ways'  in ds_table.lower():
                    osmtype='way'
                else:
                    if args.verbose:
                        print( 'table Not found:', ds_table.lower() )

            tags_one = re_tags_one.findall(ds_table)
            if tags_one:
                if args.verbose:
                    print(tags_one)
                for tag in tags_one:
                    processOSMkeys(_layer,ds_geometry,osmtype,tag)

            tags_array = re_tags_array.findall(ds_table)
            if tags_array:
                for tags in tags_array:
                    for tag in tags.split(','):
                        processOSMkeys(_layer,ds_geometry,osmtype,tag)

for k in allhstoretags:
  # add "relation" if  "area" or "way"
  if ('area' in allhstoretags[k]) or ('way' in allhstoretags[k]):
    allhstoretags[k].append("relation")

  taginfo["tags"].append(
  {
    "key": k,
    "object_types": allhstoretags[k],
    "description": "Used as a hstore tags-> in the database backend, see more in the github repo",
    "doc_url": search_url+k
  })



with open('taginfo-openstreetmap-carto.json', 'w') as outfile:
    json.dump(taginfo, outfile, indent=4)

