import json
import pickle as pkl

import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx

import plotly_express as px

with open("brighton_graph.pkl", 'rb') as pklfile:
    brighton_G = pkl.load(pklfile)

node_pd = pd.DataFrame(ox.graph_to_gdfs(brighton_G, edges=False, nodes=True).drop(columns=[0,'osmid']))
edges = brighton_G.edges(data=True)

Safe = px.colors.qualitative.Safe
angle_color_map = {
        0: Safe[3],
        1: Safe[6],
        2: Safe[2],
        3: Safe[1],
        4: Safe[9],
        None: 'blue'}
angle_data = {(u,v):angle for (u,v,angle) in brighton_G.edges.data('angle_class')}

COLORS = [Safe[3], Safe[6], Safe[2], Safe[1], Safe[9]]
# print(brighton_G.edges.data('angle_class'))
import geocoder
def get_route(ori_str, des_str):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    n1 = ox.get_nearest_node(brighton_G,p1, method='haversine')
    n2 = ox.get_nearest_node(brighton_G,p2, method='haversine')
    route = nx.shortest_path(brighton_G, n1, n2)
    return route

route = get_route("34 Claymoss Road", "371 Washington St")
route_pairs = zip(route[:-1],route[1:])

# print({k: angle_data[k] for k in route_pairs})

# for edge in route_pairs:
#     print(edge)
#     print(int(angle_data[edge]) == 1)
color_edge_map = {}
for edge in route_pairs:
    print(edge)
    print(angle_data[edge])
    if angle_data[edge] in color_edge_map:
        color_edge_map[angle_data[edge]].append(edge)
    else:
        color_edge_map[angle_data[edge]] = [edge]

# color_edge_map = {num: 
#         [edge for edge in route_pairs if int(angle_data[edge]) == num] 
#             for num in range(5)}
# # # print(angle_data)
# print(angle_data.items())

print(color_edge_map)

