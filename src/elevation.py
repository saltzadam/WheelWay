import rasterio
import numpy as np
from scipy import ndimage, array, interpolate

import util
import geometry

import math

# TODO: make pipeline-y
dataset = rasterio.open("data/brighton/elevation.tif")

# get the first "band"
# this is a numpy array
# now dataset.index(lat, lon) gives the array index for that point
band1 = dataset.read(1)

# need to flip lngs because the top of the image has greater lng
lats = np.arange(dataset.bounds.left, dataset.bounds.right, (dataset.bounds.right - dataset.bounds.left)/3601)
lngs = np.arange( dataset.bounds.top, dataset.bounds.bottom, -(dataset.bounds.top - dataset.bounds.bottom)/3601)

# fyi this is bilinear B-spline
interp_elev = interpolate.interp2d(lats, lngs, band1, kind='quintic', bounds_error=True)
# interp_elev = interpolate.interp2d(lats, lngs, band1, kind='linear')

# kx, ky = 5 is quintic interpolation
# s is smoothing factor. general advice is to keep it between s - sqrt(2s) and s + sqrt(2s) so...
# the format here is (x[i], y[i], z[i])
#spline_points = [(y,x,band1[i,j]) for i, x in enumerate(lats) for j, y in enumerate(lngs)]
#print("(lat,lng,height)", spline_points[0])
#xs = [pts[0] for pts in spline_points]
#ys = [pts[1] for pts in spline_points]
#zs = [pts[2] for pts in spline_points]
##spline_elev = interpolate.bisplrep(xs, ys, zs, kx=5, ky=5, s = len(lats))
#spline_elev = interpolate.SmoothBivariateSpline(xs, ys, zs, kx=5, ky=5)
#print("loaded")

# del(xs)
# del(ys) 
# del(zs)
# del(spline_points)




def get_elev(lat, lon):
    return interp_elev(lat,lon)[0]

def get_midpoint(linestring):
    p0, p1 = linestring.coords[:]
    m0 = (p0[0] + p1[0])/2
    m1 = (p0[1] + p1[1])/2
    return (m0, m1)


def get_slope(row):
    rise = row['elevation_1'] - row['elevation_0']
    run = row['length_m']
    return rise/run
# def get_slope(row):
#     print(row)
#     lat, lon = get_midpoint(row['geometry'])
#     f_x = interp_elev(lat, lon, dx = 1, dy = 0)
#     f_y = interp_elev(lat, lon, dx = 0, dy = 1)
#     gradient_norm = math.sqrt(f_x ** 2 + f_y ** 2)
#     return 100*gradient_norm


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
    assert gdf.crs == "EPSG:4326"
    gdf['elevation_0'] =gdf.geometry.map(lambda x : get_elev(x.coords[0][0], x.coords[0][1]))
    gdf['elevation_1'] =gdf.geometry.map(lambda x : get_elev(x.coords[1][0], x.coords[1][1]))
    gdf = gdf.to_crs("EPSG:26919") # TODO: pipeline-ify
    gdf['cut_geometry'] = gdf.geometry.map(lambda x : geometry.recursive_cut(x, 4))
    gdf = util.list_explode(gdf)
    gdf.drop(inplace=True, columns=['cut_geometry'])
    gdf['length_m'] = gdf.length
    gdf = gdf[gdf.length != 0]
    gdf['slope'] = gdf.apply(get_slope, axis=1)
    gdf['angle_deg'] = gdf['slope'].map(lambda x : atan(x) * 360 / (2 * pi))

    # gdf.drop(inplace=True, columns=['elevation_0','elevation_1','slope'])
    gdf.drop(inplace=True, columns=['slope'])

    gdf = gdf.to_crs("EPSG:4326") # TODO: pipeline-ify
    gdf['angleclass'] = gdf['angle_deg'].map(get_angle_class)
    return gdf
