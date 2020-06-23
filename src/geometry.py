## Various geometric functions
# includes most of the work for crosswalks
# TODO: move more stuff here

import math
def linestring_start(linestring):
    (l1,l2) = list(linestring.coords)[0]
    return (l1,l2)

def linestring_end(linestring):
    (l1,l2) = list(linestring.coords)[1]
    return (l1,l2)

def linestring_heading(linestring):
    # 0 is true north, 90 is east
    # so heading = 90 - usual_angle (in standard form)
    (l1,l2) = linestring_start(linestring)
    (m1,m2) = linestring_end(linestring)
    angle_deg = math.atan2(m2-l2, m1-l1) * 360 / (2 * math.pi)
    heading_deg = int((90 - angle_deg) % 360)
    return(heading_deg)

# Thank you Sean Gilles https://gist.github.com/sgillies/465156#file_cut.py
from shapely.geometry import LineString, Point

def cut(line, distance):
    # Cuts a line in two at a distance from its starting point
    if distance <= 0.0 or distance >= line.length:
        return [LineString(line)]
    coords = list(line.coords)
    for i, p in enumerate(coords):
        pd = line.project(Point(p))
        if pd == distance:
            return [
                LineString(coords[:i+1]),
                LineString(coords[i:])]
        if pd > distance:
            cp = line.interpolate(distance)
            return [
                LineString(coords[:i] + [(cp.x, cp.y)]),
                LineString([(cp.x, cp.y)] + coords[i:])]
        

# here's me
def recursive_cut(line, distance):
    if [line] == cut(line, distance):
        return [line]
    else:
        segment, rest = cut(line, distance)
        return [segment] + recursive_cut(rest, distance)

from shapely.ops import snap

def snap_endpoints(linestring, geom, tol):
    linelist = linestring.coords
    assert len(linelist) == 2
    p0 = snap(Point(linelist[0]), geom, tol)
    p1 = snap(Point(linelist[-1]), geom, tol)  
    #return LineString([Point(p0)] + list(map(Point, linelist[1:-1])) + [Point(pn)])
    return LineString([Point(p0), Point(p1)])

   

def round_pt(pt):
    a, b = pt
    a = round(a)
    b = round(b)
    return Point(a,b)

def round_edge(edge):
    a, b = tuple(edge.coords)
    a = round_pt(a)
    b = round_pt(b)
    return LineString([a,b])

import osmnx as ox
from osmnx.distance import great_circle_vec, euclidean_dist_vec

import networkx as nx
# adapted from osmnx.distance
def is_reachable(graph, id1, id2):
    try:
        nx.shortest_path(graph, id1, id2)
        return True
    except nx.NetworkXNoPath:
        return False
import pandas as pd
def get_nearest_crosswalk_nodes(G, point, method="haversine", return_dist=False):
    if len(G) < 1:
        raise ValueError("G must contain at least one node")

    # dump graph node coordinates into a pandas dataframe indexed by node id
    # with x and y columns
    coords = ((n, d["x"], d["y"], d["id"]) for n, d in G.nodes(data=True))
    df = pd.DataFrame(coords, columns=["node", "x", "y", "id"]).set_index("node")

    # add columns to df for the (constant) coordinates of reference point
    df["ref_y"] = point[0]
    df["ref_x"] = point[1]

    # calculate the distance between each node and the reference point
    if method == "haversine":
        # calculate distances using haversine for spherical lat-lng geometries
        df['dists'] = great_circle_vec(lat1=df["ref_y"], lng1=df["ref_x"], lat2=df["y"], lng2=df["x"])

    elif method == "euclidean":
        # calculate distances using euclid's formula for projected geometries
        df['dists'] = euclidean_dist_vec(y1=df["ref_y"], x1=df["ref_x"], y2=df["y"], x2=df["x"])

    else:
        raise ValueError('method argument must be either "haversine" or "euclidean"')
    
    some_best = df.nsmallest(n=17,columns=['dists']).iloc[1:]

    vertices = []
    for _, row in some_best.iterrows():
        if len(vertices) > 4 or great_circle_vec(lat1=row.x, lng1=row.ref_y, lat2=row.ref_x, lng2=row.ref_y) > 10:
            continue
        reachables = [nx.has_path(G, int(row.id), int(vx.id)) for vx in vertices ]
        if any(reachables):
            continue
        vertices.append(row)

    # if caller requested return_dist, return distance between the point and the
    # nearest node as well
    return vertices   

from shapely.geometry import LineString
from math import sqrt
def get_nearest_cw_node_pairs(G, pt):
    pts = get_nearest_crosswalk_nodes(G,pt)
    all_cws = [(u,v) for u in pts for v in pts if u['id'] != v['id']]
    good_cws = sorted(all_cws, key = lambda pair : great_circle_vec(lat1=pair[0].x, lng1=pair[0].y, 
                                                             lat2=pair[1].x, lng2=pair[1].y))
    
    K = len(all_cws)/2
    num_to_return = 2 * int((1 + sqrt(1 + 8*K))/2)
    return good_cws[0:num_to_return]
    
def make_edge(pair):
    u_node = pair[0]
    u = int(u_node.id)
    v_node = pair[1]
    v = int(v_node.id)
    data_dict = {
        'street_id': 0,
        'geometry': LineString([[u_node.y, u_node.x], [v_node.y, v_node.x]]),
        'length_m': great_circle_vec(lat1=u_node.x, lng1=u_node.y, lat2=v_node.x, lng2=v_node.y),
        'angle_deg': 0,
        'osmid': (int(u_node.id) + 1) * (int(v_node.id) + 1),
        'angleclass': 0,
        'key': 1
    }
    return (u,v,data_dict)    


import geopandas as gpd
def get_sidewalks(sidewalk_graph, intersections):
    undirected_G = sidewalk_graph.to_undirected()
    cw_edges = [make_edge(pair) for row in intersections.iterrows() 
            for pair in get_nearest_cw_node_pairs(undirected_G, (row[1].x, row[1].y))]
    return gpd.GeoDataFrame(cw_edges, geometry='geometry')

def add_crosswalks(sidewalk_graph, intersections):
    cw_edges = [make_edge(pair) for row in intersections.iterrows() 
            for pair in get_nearest_cw_node_pairs(sidewalk_graph,(row[1].x, row[1].y))]
    # this is in-place so no need to return
    sidewalk_graph.add_edges_from(cw_edges)
    # unlike jupyter, no need to 
