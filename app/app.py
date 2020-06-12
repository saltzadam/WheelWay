import json
import pickle as pkl

import osmnx as ox
import networkx as nx


import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import plotly_express as px

import dash_leaflet as dl

import folium
import osmnx as ox

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


with open("brighton_graph.pkl", 'rb') as pklfile:
    brighton_G = pkl.load(pklfile)


Safe = px.colors.qualitative.Safe
angle_color_map = {
        0: Safe[3],
        1: Safe[6],
        2: Safe[2],
        3: Safe[1],
        4: Safe[9],
        None: 'blue'}
# angle_data = {(u,v):angle for (u,v,angle) in brighton_G.edges.data('angle_class')}
# angle_edge_map = {}
# for edge in angle_data:
#     if angle_data[edge] in angle_edge_map:
#         angle_edge_map[angle_data[edge]].append(edge)
#     else:
#         angle_edge_map[angle_data[edge]] = [edge]

# for num in range(5):
#     if num not in angle_edge_map:
#         angle_edge_map[num] = []

# COLORS = [Safe[3], Safe[6], Safe[2], Safe[1], Safe[9]]

edge_getter = brighton_G.edges

import geocoder
def get_route(ori_str, des_str):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    n1 = ox.get_nearest_node(brighton_G,p1, method='haversine')
    n2 = ox.get_nearest_node(brighton_G,p2, method='haversine')
    route = nx.shortest_path(brighton_G, n1, n2, weight='length_m')
    return route


def make_line(u,v):
    print(edge_getter[u,v,0]['geometry'])
    geom = edge_getter[u,v,0]['geometry']
    p0 = geom.coords[0]
    p1 = geom.coords[-1]
    color = angle_color_map[edge_getter[u,v,0]['angle_class']]
    print(p0, p1, color)
    return dl.Polyline(positions=[[p0[1], p0[0]], [p1[1], p1[0]]], color=color)

def get_edge_color(row):
    return str(angle_color_map[row['angle_class']])

def get_fig(ori_str, des_str):
    print('get route')
    route = get_route(ori_str, des_str)
    route_nodes = list(zip(route[:-1], route[1:]))
    lines = [make_line(u,v) for (u,v) in route_nodes]
    print('drew',len(lines),'lines')
    return lines


app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

server = app.server
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

app.layout = html.Div([
    dcc.Markdown("""
    # WheelWay
    ### Directions for people with mobility impairments
    """),
    dcc.Markdown("Origin:"),
    dcc.Input(id='origin', value='', type='text', debounce=True),
    dcc.Markdown("Destination:"),
    dcc.Input(id='dest', value='', type='text', debounce=True),
    html.Div(id='a_string', children=""),
    # dcc.Graph(id='the_graph')
    # html.Div(id='the_graph', children="")
    # dcc.Graph(id='the map', ),
    # html.Iframe(id='the map', width='100%', height='400'),
    html.Div([dl.Map([dl.TileLayer(), dl.LayerGroup(id='layer')], style={'width': '1000px', 'height': '500px'}, center=[42.3493223,-71.1562415], zoom=15, id="the_map")]),
    html.Div(id='blurs', style={'display': 'none'})
])
@app.callback(
    Output('a_string', 'children'),
    [Input('origin', 'value'),
     Input('dest', 'value')]
    )
def update_string(ori_str, dest_str):
    if (not ori_str) or (not dest_str):
        return("You haven't entered an origin and destination yet.")
    else:
        return("You're trying to go from " + ori_str + " to " + dest_str + ".")

@app.callback(
        Output('blurs', 'children'),
        [Input('origin', 'n_blur'),
         Input('dest', 'n_blur')])
def update_blurs(blur_o, blur_d):
    if (not blur_o) or (not blur_d):
        return 0
    else:
        return int(blur_o) + int(blur_d)

@app.callback(
    Output('layer', 'children'),
    [Input('blurs', 'children')],# Input('dest', 'value')],
    [State('origin', 'value'),
     State('dest', 'value')]
    )
# def update_figure(ori_str, dest_str):
#     if (not ori_str) or (not dest_str):
#             return("You haven't entered an origin and destination yet.")
#     else:
#             return("You're trying to go from " + ori_str + " to " + dest_str + ". The route uses nodes: " + str(get_fig(ori_str, dest_str)))
def update_figure(nb, ori_str, dest_str):
    if (not ori_str) or (not dest_str):
        return []
    else:
        return get_fig(ori_str, dest_str)


if __name__ == '__main__':
    app.run_server(debug=True,
            port = 8050)
