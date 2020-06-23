import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output, State

import dash_leaflet as dl
from dash_leaflet import express as dlx

import dash_bootstrap_components as dbc
try:
    import app.utils as utils
except:
    import utils


ANGLE_COLOR_MAP = utils.ANGLE_COLOR_MAP

## Define the legend
MARKS = ["0&deg - 4&deg", "4&deg - 8&deg", "8&deg - 12&deg", "12&deg - 16&deg", "16&deg+", "Crosswalk", "Blocked"]
COLORSCALE = list(ANGLE_COLOR_MAP.values())[0:5] + ['yellow', 'red']
COLORBAR = dlx.categorical_colorbar(
        categories=MARKS, colorscale=COLORSCALE,
        width=520, height=30, position="bottomleft",
        style={'font-size':'12pt', 'background-color':'lightgrey'}
        )


with open('data/brighton/brighton_addresses', 'r') as addr_file:
    ADDRESS_LIST = [html.Option(value=addr) for addr in addr_file]

## start the app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, ])
server = app.server

# TODO: style constants!
## some styles
PADDED_TEXT = {'padding-top':'5px', 'padding-bottom':'5px'}
SLIDER_LABELS = {'font-size':'12pt', 'color':'black'}
INVISIBLE = {'display':'none'}

# TODO: find out if people get mad about this parens style

app.layout = html.Div([
    dbc.Col(
        dcc.Markdown("""
        # WheelWay
        ### Directions for everybody
        """
        )
    ),
    dbc.Col(
        html.Div([
            dcc.Markdown("#### Enter any street address in Brighton -- no need to add the city or state!"),
            dbc.Row([
                html.Datalist(id='addresses',children=ADDRESS_LIST),
                dbc.Col([
                    dbc.Input(id='origin',
                              placeholder="Type your origin here", value='', type='text',
                              debounce=True, bs_size="lg",
                              list = 'addresses')], width=6),
                dbc.Col([
                    html.Div([
                        dbc.Button(children="Find me a route with no obstructions",
                                   color="success", id='obs_button', n_clicks=0)],
                             style=PADDED_TEXT)
                ])
            ]),
            dbc.Row([
                dbc.Col([
                    html.Div([
                        dbc.Input(id='dest', placeholder="Type your destination here",
                                  value='', type='text', debounce=True, bs_size="lg",
                                  list = 'addresses')
                    ], style=PADDED_TEXT)
                ], width=6)
            ]),
        ]), width='auto', align='start'),
    dbc.Col([
        dbc.Row([
            dbc.Col([
                html.Div([
                    dcc.Dropdown(id="routing",
                                 placeholder="Find the route with...",
                                 options=[
                                     {"label": "Lowest slope", "value": 'slope'},
                                     {"label": "Balanced slope and length", "value":'balance'},
                                     {"label": "Shortest length", 'value': 'short'}
                                 ], style={'width': '800px'}),
                         ], style={'padding_top':'5px', 'padding-bottom':'5px', 'font-size':'16pt'})
            ], width=6),
            dbc.Col(
                html.Div([
                    dcc.Slider(id='alpha', min=.4, max=20.4, step=1, value=.4,
                               marks={
                                   .4: {'label': "I don't mind some hills",
                                        'style': SLIDER_LABELS},
                                   20.4: {'label': "I hate hills!", 'style': SLIDER_LABELS}
                        }
                    )
                ], style=INVISIBLE, id='slider-display'), 
                width=4)
        ], justify='start')
    ]),
    dbc.Col([
        dcc.Loading(id='loading-1', children=[html.Div(id='warning', children=[html.P(children="\u00A0", id='warning-p')], style={'height':'24pt'})], type="dot", style={'position':'fixed','left':'10px'}),
        html.Div([dl.Map([dl.TileLayer(),
                          dl.LayerGroup(id='layer'), COLORBAR],
                         style={'width': '1000px', 'height': '500px'},
                         zoomControl=False, id="the_map"
                  )
        ], id='map_div'),
        html.Div(id='blurs', style=INVISIBLE),
        html.Div(id='dd-output-container', style=INVISIBLE),
        html.Div([
            dbc.Row([
                dbc.Col(
                    html.Div(
                        dbc.Nav([dbc.NavLink("github", href="www.github.com/saltzadam/WheelWay"),
                                 dbc.NavLink("slides", href="https://docs.google.com/presentation/d/19f61V7LoHI-ZXnIFEBYhvRCBrFPMcy5li7T9MQJW-nM/edit?usp=sharing")
                        ])
                    ),
                    width=4),
                dbc.Col(html.Div(), width=4)
            ], justify="between")
        ])
    ])
])

def update_working(loading_state):
    print(loading_state)
    try:
        is_loading = loading_state['is_loading']
        if is_loading:
            return 'Working...'
        else:
            return []
    except TypeError:
        return []
## Controls the color of the "Route around obstructions" button
@app.callback(
        [Output('obs_button', 'color'),
         Output('obs_button', 'children')],
        [Input('obs_button', 'n_clicks')])

def update_color(n):
    if n % 2 == 0:
        return 'success', "Click to route around sidewalk problems"
    else:
        return 'warning', "Click to ignore sidewalk problems"


## Signals when all the input fields are full (or at least visited?) and a routing option has been picked
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

## Stores routing value
# TODO: pretty sure this is an artifact of another change and should be removed.
@app.callback(
        Output('dd-output-container', 'children'),
        [Input('routing', 'value')])

def update_dd(routing):
    return routing

## Displays slider only when 'balance' route finding
@app.callback(
        Output('slider-display', 'style'),
        [Input('dd-output-container', 'children')])

def show_slider(routing):
    if routing == 'balance':
        return {}
    else:
        return INVISIBLE

## Fetches the route
@app.callback(
    [Output('warning-p', 'children'),
     Output('layer', 'children'),
     Output('the_map', 'bounds')],
    [Input('blurs', 'children'),
     Input('alpha', 'value'),
     Input('routing', 'value'),
     Input('obs_button', 'n_clicks')],
    [State('origin', 'value'),
     State('dest', 'value')])

def update_figure(nb, alpha, routing, obs_n, ori_str, dest_str):
    obs = (obs_n % 2 == 1)
    if (not ori_str) or (not dest_str) or (routing not in ['slope', 'balance', 'short']):
        return '\u00A0', [], utils.STANDARD_BOUNDS
    else:
        return utils.get_fig(ori_str, dest_str, routing, alpha, obs)

# How important is it
if __name__ == '__main__':
    app.run_server(debug=False,
                   port=8050)
