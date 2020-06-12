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
import math

import app.utils as utils

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']



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
    html.Div(id='container', children = [dcc.Input(id='dest', value='', type='text', debounce=True),
        dcc.Dropdown(id='routing',
            options = [
                {'label': 'Find me an ADA accessible route.', 'value': 'ADA'},
                {'label': 'Find me a route without very steep slopes', 'value': 'slope'},
                {'label': "Find me a route which isn't too long or steep", 'value': 'balance'},
                {'label': 'Just show me the shortest route', 'value': 'short'}],
            value='ADA',
            style={'width': '400px'})],
    html.Div(id='warning'),
    html.Div(id='a_string', children=""),
    html.Div([dl.Map([dl.TileLayer(), dl.LayerGroup(id='layer')], style={'width': '1000px', 'height': '500px'}, id="the_map")]),
    html.Div(id='blurs', style={'display': 'none'}),
    html.Div(id='dd-output-container', style={'display': 'none'})])

@app.callback(
        Output('blurs', 'children'),
        [Input('origin', 'n_blur'),
         Input('dest', 'n_blur'),
         Input('routing', 'value')])
def update_blurs(blur_o, blur_d,routing):
    if (not blur_o) or (not blur_d):
        return 0
    else:
        if routing=='ADA':
            num = 0
        elif routing=='slope':
            num = 1
        elif routing=='balance':
            num = 2
        else:
            num = 3

        return int(blur_o) + int(blur_d) + num

@app.callback(
        Output('dd-output-container', 'children'),
        [Input('routing', 'value')])
def update_dd(value):
    return value

@app.callback(
    [ Output('warning', 'children'),
      Output('layer', 'children'),
      Output('the_map','bounds')],
    [Input('blurs', 'children')],# Input('dest', 'value')],
    [State('origin', 'value'),
     State('dest', 'value'),
     State('routing', 'value')]
    )
def update_figure(nb, ori_str, dest_str, routing):
    if (not ori_str) or (not dest_str):
        return [], 'Enter your origin and destination!', utils.STANDARD_BOUNDS 
    else:
        return utils.get_fig(ori_str, dest_str, routing)

if __name__ == '__main__':
    app.run_server(debug=True,
            port = 8050)
