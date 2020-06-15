import shapely
import networkx as nx
import osmnx as ox
import geopandas as gpd

# want
# MultiLineString -> [LineString]
# to be safe, add
# LineString -> [LineString]
def multis_to_line_list_safe(ls_or_mls):
    if type(ls_or_mls) == shapely.geometry.LineString:
        return [ls_or_mls]
    else:
        return list(ls_or_mls)

def ls_to_mls(linestring):
    linelist = linestring.coords
    pairlist = list(zip(linelist, linelist[1:]))
    return shapely.geometry.MultiLineString(pairlist)
    
CRS_GLOBAL = "EPSG:4326"
# A GeoDataFrame is "global" if it's in EPSG:4326, i.e. lat/long
# Otherwise it's "local"
# never want to have a GeoDataFrame with no crs!
def is_global(gdf):
    if gdf.crs is None:
        raise ValueError("This GeoDataFrame has no crs.")
    else:
        return gdf.crs == CRS_GLOBAL

def is_local(gdf):
    if gdf.crs is None:
        raise ValueError("This GeoDataFrame has no crs.")
    return gdf.crs != CRS_GLOBAL

from shapely.geometry import Point
def edge_gdf_to_graph(gdf):
    edge_points = gpd.GeoDataFrame(list(map(Point, (list(set(
                [point for ls in list(gdf.geometry.map(lambda x : list(x.coords)).values) for point in ls]
            ))))))
    edge_points.geometry = edge_points[0]
    return ox.utils_graph.graph_from_gdfs(edge_points, gdf)

from copy import deepcopy

def list_explode(gdf):
    rows = []
    old_rows = []
    for i, row in gdf.iterrows():
        mline = row['cut_geometry']
        new_rows = [deepcopy(row) for i in range(len(row['cut_geometry']))]
        for n, inline in enumerate(mline):
            new_rows[n]['geometry'] = inline
            old_rows.append(i)
        rows.extend(new_rows)
    new_gdf = gpd.GeoDataFrame(rows).reset_index(drop=True)
    new_gdf.crs = "EPSG:26919"
    return new_gdf
