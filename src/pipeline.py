import pickle as pkl
import os.path

import geopandas as gpd
import pandas as pd
import pandas_explode
pandas_explode.patch() # adds a `df.explode` method to all DataFrames
# above should be removed for Python 3.8 but as long as we're using
# dash we're on 3.7

import shapely
from shapely.geometry import Point, LineString

import sidewalkify
import networkx as nx
import osmnx as ox

import geometry
import util
import elevation

LOCAL_CRS = "EPSG:26919"
GLOBAL_CRS = "EPSG:4326"
OFFSET = 6

# start with a shapefile
# we start with:
print("load streets")
streets = gpd.read_file("data/brighton/brighton_streets.shp")

assert util.is_global(streets)

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
# make sidewalks!
if not os.path.isfile("test/snapped.shp"):
    print("draw sidewalks")
    sidewalks = sidewalkify.draw.draw_sidewalks(sidewalkify.graph.graph_workflow(streets), crs=LOCAL_CRS)

    sidewalks['geometry'] = sidewalks.geometry.map(util.ls_to_mls)
    sidewalks = sidewalks.explode().reset_index(drop=True)

    assert len(sidewalks[sidewalks.geometry.map(lambda x: len(x.coords) != 2)]) == 0

    # sidewalks.geometry = sidewalks.geometry.map(geometry.round_edge)

    print("snap sidewalks")
    # all_sidewalks = shapely.ops.unary_union(pd.Series(sidewalks.geometry))
    # sidewalks.geometry = sidewalks.geometry.apply(lambda x: geometry.snap_endpoints(x, all_sidewalks, 1))
    def concat(lst_of_lsts):
        return [l for lst in lst_of_lsts for l in lst]

    all_points = list(map(shapely.geometry.Point,
                          concat(list((sidewalks['geometry'].map(lambda x: x.coords[:]).values)))))
    all_points = shapely.ops.unary_union(all_points)



    def snap_nearby_point(row_geo, geom):
        print(row_geo)
        line = row_geo
        p0, p1 = line.coords[:]
        p0 = shapely.geometry.Point(p0)
        p1 = shapely.geometry.Point(p1)
        p01 = shapely.ops.unary_union([p0, p1])
        geom = geom.difference(p01)
        p0_new = shapely.ops.snap(p0, geom, 1.5)
        p1_new = shapely.ops.snap(p1, geom, 1.5)
        geom = shapely.ops.unary_union([geom, p0_new, p1_new])
        new_line = shapely.geometry.LineString([p0_new, p1_new])
        return new_line

    sidewalks.geometry = sidewalks.geometry.map(lambda x: snap_nearby_point(x, all_points))

    sidewalks.crs = LOCAL_CRS

    # maybe run this a second time if it's still no bueno

    sidewalks.to_file("test/snapped.shp")
else:
    print("loading snapped.shp")
    sidewalks = gpd.read_file("test/snapped.shp")


sidewalks = sidewalks.to_crs(GLOBAL_CRS)


## add elevation
print("add elevation")
sidewalks = elevation.add_angle(sidewalks)

sidewalks.to_file("test/elevated.shp")

assert sidewalks.crs == GLOBAL_CRS

sidewalks = sidewalks.to_crs(LOCAL_CRS)
# sidewalks.geometry = sidewalks.geometry.map(geometry.round_edge)
print("build graph")

# put together points, index them, etc.
# TODO: good recc from pylint to change this to a set comprehension
# TODO: surely this can be improved anyway
sw_points = gpd.GeoDataFrame(list(
    map(Point,
        (list(set([point for ls in list(sidewalks.geometry.map(lambda x: list(x.coords)).values) for point in ls])))
        )
    ))
sw_points.geometry = sw_points[0]
sw_points.crs = LOCAL_CRS

len_sw = len(list(sw_points.geometry.map(lambda x: x.coords)))
sw_coord_dict = dict(list(set(zip(list(sw_points.geometry.map(lambda x: tuple(x.coords)[0])), range(len_sw)))))

sidewalks['u'] = sidewalks.geometry.map(lambda x: sw_coord_dict[x.coords[0]])
sidewalks['v'] = sidewalks.geometry.map(lambda x: sw_coord_dict[x.coords[-1]])
sidewalks['key'] = 0

sw_points['id'] = sw_points.geometry.map(lambda x: sw_coord_dict[x.coords[0]])
sw_points['osmid'] = sw_points.id
sidewalks['osmid'] = sidewalks.index.map(lambda x: 100000 * x)

with open('test/sw_points_dict.pkl', 'wb') as pklfile:
    pkl.dump(sw_points, pklfile)

assert sidewalks.crs == LOCAL_CRS
assert sw_points.crs == LOCAL_CRS
sidewalks = sidewalks.to_crs(GLOBAL_CRS)
sw_points = sw_points.to_crs(GLOBAL_CRS)

sw_points['x'] = sw_points.geometry.map(lambda x: x.coords[0][1])
sw_points['y'] = sw_points.geometry.map(lambda x: x.coords[0][0])



sidewalks_G = ox.graph_from_gdfs(sw_points, sidewalks)

def angle_reverse(G):
    rev_edges = nx.reverse(G).edges(data=True)
    def reverse_line(linestring):
        p0, p1 = linestring.coords[:]
        return LineString([Point(p1), Point(p0)])

    def rev_angle(dic):
        dic['angle_deg'] = -dic['angle_deg']
        dic['geometry'] = reverse_line(dic['geometry'])
        return dic
    return [(u, v, rev_angle(dat)) for (u, v, dat) in rev_edges]

sidewalks_G.add_edges_from(angle_reverse(sidewalks_G))

print(len(sidewalks_G.edges))
## time to build crosswalks
print("build crosswalks")
# TODO: this is not pipeline-y!
intersections = gpd.read_file("data/brighton/brighton_points_clean.shp")

geometry.add_crosswalks(sidewalks_G, intersections)
print(len(sidewalks_G.edges))

with open("test/brighton_G.pkl", 'wb') as pklfile:
    pkl.dump(sidewalks_G, pklfile)


sidewalks = ox.graph_to_gdfs(sidewalks_G, nodes=False, edges=True)



assert sidewalks.crs == GLOBAL_CRS

sidewalks.to_file("test/final.shp")

