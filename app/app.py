import json
import pickle as pkl

import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objects as go

import pandas as pd
import geopandas as gpd
import osmnx as ox
import networkx as nx

import plotly_express as px

from shapely.geometry import Point

server=app.server

EPSG_26919 = "EPSG:26919"
external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

# brighton_sidewalks = gpd.read_file("../insight_project_dc/brighton/brighton_sidewalks/brighton_sidewalks.shp")

# EPSG_26919 = brighton_sidewalks.crs

# from shapely.geometry import Point
# brighton_sw_points = gpd.GeoDataFrame([Point(point) for ls in list(brighton_sidewalks.geometry.map(lambda x : list(x.coords)).values) for point in ls ])
# brighton_G = ox.utils_graph.graph_from_gdfs(brighton_sw_points, brighton_sidewalks)

with open("brighton_graph.pkl", 'rb') as pklfile:
    brighton_G = pkl.load(pklfile)

node_pd = pd.DataFrame(ox.graph_to_gdfs(brighton_G, edges=False, nodes=True).drop(columns=[0,'osmid']))

import geocoder
def get_route(ori_str, des_str):
    g1 = geocoder.osm(ori_str)
    g2 = geocoder.osm(des_str)
    p1 = ox.projection.project_geometry(Point(g1.json['lng'], g1.json['lat']), to_crs=EPSG_26919)[0].coords[0]
    p2 = ox.projection.project_geometry(Point(g2.json['lng'], g2.json['lat']), to_crs=EPSG_26919)[0].coords[0]
    n1 = ox.get_nearest_node(brighton_G,p1, method='haversine')
    n2 = ox.get_nearest_node(brighton_G,p2, method='haversine')
    route = nx.shortest_path(brighton_G.to_undirected(), n1, n2)
    return route

def get_fig(ori_str, des_str):
    route = get_route(ori_str, des_str)
    pts = list(map(lambda x : list(node_pd[node_pd['id'] == x].geometry)[0], route))
    pts = list(map(lambda x : x.coords[0], pts))
    pts_df = pd.DataFrame(pts).rename({0:'lat',1:'lng'},axis=1)
    return px.line_mapbox(pts_df, lat='lat', lon='lng', center={'lat':42.3, 'lon':-71.1}, mapbox_style="open-street-map")

app = dash.Dash(__name__, external_stylesheets=external_stylesheets)

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
    dcc.Graph(id='the map', )
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
        return("You're trying to go from " + ori_str + " to " + dest_str + ". The route uses nodes: " + str(get_route(ori_str, dest_str)))

@app.callback(
    Output('the map', 'figure'),
    [Input('origin', 'value'),
     Input('dest', 'value')]
    )
# def update_figure(ori_str, dest_str):
#     if (not ori_str) or (not dest_str):
#             return("You haven't entered an origin and destination yet.")
#     else:
#             return("You're trying to go from " + ori_str + " to " + dest_str + ". The route uses nodes: " + str(get_fig(ori_str, dest_str)))
def update_figure(ori_str, dest_str):
    if (not ori_str) or (not dest_str):
        return get_fig("34 Claymoss Road", "34 Claymoss Road")
    else:
        return get_fig(ori_str, dest_str)    

if __name__ == '__main__':
    app.run_server(debug=True)
