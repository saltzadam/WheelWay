import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import dash_leaflet as dl
from dash_leaflet import express as dlx

import dash_bootstrap_components as dbc
#import app.utils as utils
try:
    import app.utils as utils
except:
    import utils

#import plotly_express as px

angle_color_map = {
        0: "#8dd544ff",
        1: "#35b479ff",
        2: "#218f8dff",
        3: "#33638dff",
        4: "#45337dff",
        None: 'blue'}


marks = ["0&deg-4&deg", "4&deg-8&deg", "8&deg-12&deg", "12&deg-16&deg", "16&deg+"]
# marks = ["Low slope", "", "", "", "High slope"]
colorscale = list(angle_color_map.values())[0:5]
colorbar = dlx.categorical_colorbar(categories=marks, colorscale=colorscale, width=300, height=30, position="bottomleft", style={'font-size':'14pt', 'background-color':'lightgrey'})

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

server = app.server
styles = {
    'pre': {
        'border': 'thin lightgrey solid',
        'overflowX': 'scroll'
    }
}

app.layout = html.Div([
    dbc.Col(
        dcc.Markdown("""
        # WheelWay
        ### Directions for everybody
        """)),
    dbc.Col(html.Div([
        dcc.Markdown("Enter any street address in Brighton -- no need to add the city or state!"),
        dbc.Row([dbc.Col([dbc.Input(id='origin', placeholder="Type your origin here", value='', type='text', debounce=True, bs_size="lg")], width=6)
            ]),
        dbc.Row([
            dbc.Col([html.Div([dbc.Input(id='dest', placeholder="Type your destination here", value='', type='text', debounce=True, bs_size="lg")], style={'padding-top':'5px', 'padding-bottom':'5px'})]), 
            dbc.Col([html.Div([dbc.Button(children = "Find me a route with no obstructions", color="success", id='obs_button', n_clicks=0)], style={'padding-top':'5px'})])
            ]),
    ]), width='auto', align='start'),
    dbc.Col([dbc.Row([
    dbc.Col([html.Div([
        dcc.Dropdown(id="routing", 
                     placeholder="Find the route with...", 
                     options = [
                         {"label": "Lowest slope", "value": 'slope'},
                         {"label": "Balanced slope and length", "value":'balance'},
                         {"label": "Shortest length", 'value': 'short'}
                         ], style={'width': '800px'}),
                     ], style={'padding_top':'5px', 'padding-bottom':'5px', 'font-size':'16pt'})]),# width='4'),
    dbc.Col(html.Div([
        dcc.Slider(id='alpha', min = .4, max = 20.4, step = 1, value=.4,
            marks={.4: {'label': "I don't mind some hills", 'style': {'font-size':'12pt', 'color':'blue'}}, 20.4: {'label': "I hate hills!", 'style': {'font-size':'12pt', 'color':'red'}}})
        ], style={'display':'none'}, id='slider-display'), width=4)
    ])]),
    dbc.Col([
    html.Div(id='warning'),
    html.Div(id='a_string', children=""),
    html.Div([dl.Map([dl.TileLayer(), dl.LayerGroup(id='layer'), colorbar], style={'width': '1000px', 'height': '500px'}, zoomControl=False, id="the_map")]),
    html.Div(id='blurs', style={'display': 'none'}),
    html.Div(id='dd-output-container', style={'display': 'none'}),
    html.Div([
            dbc.Row([
                dbc.Col(html.Div(
                    dbc.Nav([dbc.NavLink("github", href="www.github.com/saltzadam/WheelWay"),
                        dbc.NavLink("slides", href="#")
                        ])
                    ),width=4),
                dbc.Col(html.Div(),width=4)
             ], justify="between")
        ])
    ])])

@app.callback(
        [Output('obs_button', 'color'),
         Output('obs_button',  'children')],
        [Input('obs_button', 'n_clicks')])
def update_color(n):
    if n % 2 == 0:
        return 'success', "Click to route around sidewalk problems"
    else:
        return 'warning', "Click to ignore sidewalk problems" 

@app.callback(
        Output('blurs', 'children'),
        [Input('origin', 'n_blur'),
         Input('dest', 'n_blur'),
         Input('routing', 'value')])
def update_blurs(blur_o, blur_d, routing):
    if routing == 'slope':
        c = 0
    elif routing == 'balance':
        c = 1
    else:
        c = 2 
    if (not blur_o) or (not blur_d):
        return 0
    else:
        return int(blur_o) + int(blur_d) + c

@app.callback(
        Output('dd-output-container', 'children'),
        [Input('routing','value')],
        )
def update_dd(routing):
    return(routing)

@app.callback(
        Output('slider-display', 'style'),
        [Input('dd-output-container', 'children')]
        )
def show_slider(routing):
    if routing == 'balance':
        return {}
    else:
        return {'display':'none'}

@app.callback(
    [ Output('warning', 'children'),
      Output('layer', 'children'),
      Output('the_map','bounds')],
    [Input('blurs', 'children'),
     Input('alpha', 'value'), # Input('dest', 'value'),
     Input('routing', 'value'),
     Input('obs_button', 'n_clicks')],
    [State('origin', 'value'),
     State('dest', 'value')
     # State('dd-output-container', 'children')
    ]
    )
def update_figure(nb, alpha, routing, obs_n, ori_str, dest_str):
    obs = (obs_n % 2 == 1)
    if (not ori_str) or (not dest_str) or (routing not in ['slope','balance','short']):
        return [], 'Enter your origin and destination!', utils.STANDARD_BOUNDS 
    else:
        return utils.get_fig(ori_str, dest_str, routing, alpha, obs)



if __name__ == '__main__':
    app.run_server(debug=True,
            port = 8050)
