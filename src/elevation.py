import rasterio
import numpy as np
from scipy import ndimage, array, interpolate

import util
import geometry

# TODO: make pipeline-y
dataset = rasterio.open("data/brighton/elevation.tif")

# get the first "band"
# this is a numpy array
# now dataset.index(lat, lon) gives the array index for that point
band1 = dataset.read(1)

# need to flip lngs because the top of the image has greater lng
lats = np.arange(dataset.bounds.left, dataset.bounds.right, (dataset.bounds.right - dataset.bounds.left)/3601)
lngs = np.arange( dataset.bounds.top, dataset.bounds.bottom, -(dataset.bounds.top - dataset.bounds.bottom)/3601)

fn = band1 #array([band1[x,y] for x in range(3601) for y in range(3601)])

new_x = np.arange(dataset.bounds.left, dataset.bounds.right, (dataset.bounds.right - dataset.bounds.left)/360100)
new_y = np.arange(dataset.bounds.bottom, dataset.bounds.top, (dataset.bounds.top - dataset.bounds.bottom)/360100)

# takes lat lng and gives interpolated height
# switched from cubic to linear to give less dramatic results (?)
#interp_elev = interpolate.interp2d(lats, lngs, band1, kind='cubic')
interp_elev = interpolate.interp2d(lats, lngs, band1, kind='linear')


def get_elev(lat, lon):
    return interp_elev(lat,lon)[0]

def get_slope(row):
    rise = row['elevation_1'] - row['elevation_0']
    run = row['length_m']
    return rise/run

def get_angle_class(angle):
    angle = abs(angle)
    if angle < 1:
        return 0
    elif angle < 2:
        return 1
    elif angle < 3:
        return 2
    elif angle < 4:
        return 3
    else:
        return 4

from math import atan, pi
def add_angle(gdf):
    gdf['cut_geometry'] = gdf.geometry.map(lambda x : geometry.recursive_cut(x, 2))
    gdf = util.list_explode(gdf)
    gdf = gdf.to_crs("EPSG:4326")
    gdf['elevation_0'] =gdf.geometry.map(lambda x : get_elev(x.coords[0][0], x.coords[0][1]))
    gdf['elevation_1'] =gdf.geometry.map(lambda x : get_elev(x.coords[1][0], x.coords[1][1]))
    gdf.drop(inplace=True, columns=['cut_geometry'])
    gdf = gdf.to_crs("EPSG:26919") # TODO: pipeline-ify
    gdf['length_m'] = gdf.length
    gdf = gdf[gdf.length != 0]
    gdf['slope'] = gdf.apply(get_slope, axis=1)
    gdf['angle_deg'] = gdf['slope'].map(lambda x : atan(x) * 360 / (2 * pi))

    gdf.drop(inplace=True, columns=['elevation_0','elevation_1','slope'])

    gdf = gdf.to_crs("EPSG:4326") # TODO: pipeline-ify
    gdf['angle_class'] = gdf['angle_deg'].map(get_angle_class)
    return gdf
