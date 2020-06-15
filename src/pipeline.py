import geopandas as gpd
import pandas as pd
import pandas_explode 
pandas_explode.patch() # adds a `df.explode` method to all DataFrames 
# above should be removed for Python 3.8 but as long as we're using 
# dash we're on 3.7

import shapely

import sidewalkify

import networkx as nx
import osmnx as ox

import geometry
import util
import elevation

LOCAL_CRS="EPSG:26919"
GLOBAL_CRS="EPSG:4326"
OFFSET=3

# start with a shapefile
# we start with:
print("load streets")
streets = gpd.read_file("data/brighton/brighton_streets.shp")

assert util.is_global(streets )

def add_sidewalks(gdf):
    gdf['sw_left'] = OFFSET
    gdf['sw_right'] = OFFSET
    return gdf

# explodes rows with MultiLineStrings into multiple rows with LineStrings 
def explode_geometry(gdf):
    original_crs = gdf.crs
    df_temp = pd.DataFrame(gdf)
    df_temp['geometry'] = df_temp['geometry'].map(util.multis_to_line_list_safe)
    df_temp = df_temp.explode('geometry')
    gdf = gpd.GeoDataFrame(df_temp, geometry='geometry')
    gdf.crs = original_crs
    return gdf

streets = streets.to_crs(LOCAL_CRS)

streets = explode_geometry(streets)
import os.path
# make sidewalks!
if not os.path.isfile("test/elevated.shp"):
    print("draw sidewalks")
    sidewalks = sidewalkify.draw.draw_sidewalks(sidewalkify.graph.graph_workflow(streets))

    assert util.is_local(sidewalks)

    sidewalks['geometry'] = sidewalks.geometry.map(util.ls_to_mls)
    sidewalks = sidewalks.explode().reset_index(drop=True)

    assert len(sidewalks[sidewalks.geometry.map(lambda x : len(x.coords) != 2)]) == 0

    print("snap sidewalks")
    all_sidewalks = shapely.ops.unary_union(pd.Series(sidewalks.geometry))
    sidewalks.geometry = sidewalks.geometry.apply(lambda x: geometry.snap_endpoints(x, all_sidewalks, .75))


    sidewalks = sidewalks.to_crs(GLOBAL_CRS)


    ## add elevation
    print("add elevation")
    sidewalks = elevation.add_angle(sidewalks)

    sidewalks.to_file("test/elevated.shp")
else:
    print("loading elevated.shp")
    sidewalks = gpd.read_file("test/elevated.shp")

print("round sidewalks")
assert sidewalks.crs == GLOBAL_CRS

sidewalks = sidewalks.to_crs(LOCAL_CRS)
sidewalks.geometry = sidewalks.geometry.map(geometry.round_edge)
print("build graph")
# put together points, index them, etc.
from shapely.geometry import Point
sw_points = gpd.GeoDataFrame(list(map(Point, (list(set([point for ls in list(sidewalks.geometry.map(lambda x : list(x.coords)).values) for point in ls]))))))
sw_points.geometry = sw_points[0]
sw_points.crs = LOCAL_CRS

len_sw = len(list(sw_points.geometry.map(lambda x : x.coords)))
sw_coord_dict = dict(list(set(zip(list(sw_points.geometry.map(lambda x : tuple(x.coords)[0])), range(len_sw)))))
sw_coords = sw_coord_dict.keys()

from shapely.coords import CoordinateSequence
sidewalks['u'] = sidewalks.geometry.map(lambda x : sw_coord_dict[x.coords[0]])
sidewalks['v'] = sidewalks.geometry.map(lambda x : sw_coord_dict[x.coords[-1]])
sidewalks['key'] = 0

sw_points['id'] = sw_points.geometry.map(lambda x : sw_coord_dict[x.coords[0]])
sw_points['osmid'] = sw_points.id
sidewalks['osmid'] = sidewalks.index.map(lambda x : 10000 * x)

assert sidewalks.crs == LOCAL_CRS
assert sw_points.crs == LOCAL_CRS
sidewalks = sidewalks.to_crs(GLOBAL_CRS)
sw_points = sw_points.to_crs(GLOBAL_CRS)

sw_points['x'] = sw_points.geometry.map(lambda x : x.coords[0][1])
sw_points['y'] = sw_points.geometry.map(lambda x : x.coords[0][0])



sidewalks_G = ox.graph_from_gdfs(sw_points, sidewalks)
print(len(sidewalks_G.edges))
## time to build crosswalks
print("build crosswalks")
# TODO: this is not pipeline-y!
intersections = gpd.read_file("data/brighton/brighton_points_clean.shp")

# TODO: double-check this algorithm carefully
geometry.add_crosswalks(sidewalks_G, intersections)
print(len(sidewalks_G.edges))

sidewalks = ox.graph_to_gdfs(sidewalks_G, nodes=False, edges=True)

assert sidewalks.crs == GLOBAL_CRS

sidewalks.to_file("test/final.shp")

