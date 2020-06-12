import geopandas as gpd
import pandas as pd
import pandas_explode 
pandas_explode.patch() # adds a `df.explode` method to all DataFrames 
# above should be removed for Python 3.8 but as long as we're using 
# dash we're on 3.7

import sidewalkify

import geometry
import util

LOCAL_CRS="EPSG:26919"
OFFSET=1

# start with a shapefile
# we start with:
streets = gpd.read_file("brighton_streets.shp")

assert util.is_global(streets )

def add_sidewalks(gdf):
    gdf['sw_left'] = OFFSET
    gdf['sw_right'] = OFFSET
    return gdf

# explodes rows with MultiLineStrings into multiple rows with LineStrings 
def explode_geometry(gdf):
    original_crs = gdf.crs
    df_temp = pd.DataFrame(gdf)
    df_temp['geometry'] = df_temp['geometry'].map(util.multis_to_lines)
    df_temp = df_temp.explode('geometry')
    gdf = gpd.GeoDataFrame(df_temp, geometry='geometry')
    gdf.crs = original_crs
    return gdf

streets.to_crs(LOCAL_CRS)

streets = sidewalkify.draw.draw_sidewalks(sidewalkify.graph.graph_workflow(streets))
streets['heading'] = streets.geometry.map(geometry.linestring_heading)

#segment the streets

