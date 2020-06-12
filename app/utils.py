import geocoder
import pickle as pkl
import networkx as nx
import osmnx as ox

import dash_leaflet as dl
import plotly_express as px

import math 
with open("brighton_graph.pkl", 'rb') as pklfile:
    brighton_G = pkl.load(pklfile)

# controls angle scaling for balanced paths
ALPHA = 2/5

edge_getter = brighton_G.edges

Safe = px.colors.qualitative.Safe
angle_color_map = {
        0: Safe[3],
        1: Safe[6],
        2: Safe[2],
        3: Safe[1],
        4: Safe[9],
        None: 'blue'}

angle_dash_map = {
        0: None,
        1: "4 1",
        2: "3 1",
        3: "2 1",
        4: "1 1",
        None: None}


def get_route(ori_str, des_str,routing):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    n1 = ox.get_nearest_node(brighton_G,p1, method='haversine')
    n2 = ox.get_nearest_node(brighton_G,p2, method='haversine')
    if routing=='short':
        try:
            route = nx.shortest_path(brighton_G, n1, n2, weight='length_m')
        except nx.NetworkXNoPath:
            route = None
    elif routing=='ADA':
        def ada_fn(u,v,data):
            if abs(data[0]['angle_deg']) >= 5:
                return None
            else:
                return data[0]['length_m']
        try:
            route = nx.single_source_dijkstra(brighton_G, n1, n2, weight=ada_fn)[1]
        except nx.NetworkXNoPath:
            route = None
    elif routing=='balance':
       def slope_fn(u,v,data):
            return data[0]['length_m'] * (1 + ALPHA * abs(data[0]['angle_deg']))/15
       try:
            route = nx.single_source_dijkstra(brighton_G, n1, n2, weight=slope_fn)[1]
       except nx.NetworkXNoPath:
            route = None
    elif routing=='slope':
        for i in range(1,15):
            try:
                route = nx.shortest_path(brighton_G, n1, n2, weight=(lambda u,v,data : None if abs(data[0]['angle_m']) > i else data[0]['length_m']))
            except:
                continue
        route = None
    return route, " "


def make_line(u,v):
    geom = edge_getter[u,v,0]['geometry']
    p0 = geom.coords[0]
    p1 = geom.coords[-1]
    angle_class = edge_getter[u,v,0]['angle_class']
    color = angle_color_map[angle_class]
    return dl.Polyline(positions=[[p0[1], p0[0]], [p1[1], p1[0]]], color=color, weight= 2 + angle_class)

def get_edge_color(row):
    return str(angle_color_map[row['angle_class']])

# # determines if they're within VAR degrees of each other
# def aligned(line0, line1):
#     VAR = 5
#     if line0.color != line1.color:
#         return False
#     (p0, p1) = line0.getLatLngs
#     (p2, p3) = line1.getLatLngs
#     vec0 = (p1[0] - p0[0], p1[1] - p0[1])
#     vec1 = (p3[0] - p2[0], p3[1] - p2[1])
#     dot = vec0[0] * vec1[0] + vec0[1] * vec1[1]
#     mag0 = math.hypot(vec0)
#     mag1 = math.hypot(vec1)
#     costheta = dot/(mag0 * mag1)
#     return math.degrees(math.acos(costheta)) < VAR

def make_lines(route):
    route_pairs = list(zip(route[:-1], route[1:]))
    # just insert the first element
    first_seg = route_pairs.pop(0)
    lines = [make_line(first_seg[0], first_seg[1])]
    # now we have to check the accumulator as we go
    for pair in route_pairs:
        last_line = lines[-1]
        new_line = make_line(pair[0],pair[1])
        if (last_line.color == new_line.color):
            last_line.positions.append(new_line.positions[1])
            lines.pop()
            lines.append(last_line)
        else:
            lines.append(new_line)
        
    print('drew',len(lines),'lines')
    return lines, "Here's your route."

def get_bounds(lines):
    points = [line.positions for line in lines]
    xs = [p[0] for pairs in points for p in pairs]
    ys = [p[1] for pairs in points for p in pairs]
    botleft = [min(xs), min(ys)]
    topright = [max(xs), max(ys)]
    return [botleft, topright]

STANDARD_BOUNDS = [[42.331, -71.17], [42.36, -71.13405]]

def get_fig(ori_str, des_str, routing):
    route, message = get_route(ori_str, des_str, routing)
    if route is None:
        if routing=='ADA':
            return "We're sorry, there's no ADA-compliant route available.", [], STANDARD_BOUNDS
        elif routing=='slope':
            return "There's no route which avoids hills with an angle of at least 15 degrees.", [], STANDARD_BOUNDS
        else:
            return "We're sorry, somehow you picked two disconnected points.", [], STANDARD_BOUNDS
    else:
        lines, message = make_lines(route)
        return message, lines, get_bounds(lines)

