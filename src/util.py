import shapely

# want
# MultiLineString -> [LineString]
# to be safe, add
# LineString -> [LineString]
def multis_to_line_list_safe(ls_or_mls):
    if type(ls_or_mls) == shapely.geometry.LineString:
        return [ls_or_mls]
    else:
        return list(ls_or_mls)

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
