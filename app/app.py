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


#marks = ["0-1", "1-2", "2-3", "3-4", "4+"]
marks = ["Low slope", "", "", "", "High slope"]
colorscale = list(angle_color_map.values())[0:5]
colorbar = dlx.categorical_colorbar(categories=marks, colorscale=colorscale, width=300, height=30, position="bottomleft")

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

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
    ### Directions for everybody
    """),
    dbc.Col(html.Div([
        dcc.Markdown("Enter any street address in Brighton -- no need to add the city or state!"),
        # dcc.Markdown("Origin:"),
        dbc.Input(id='origin', placeholder="Type your origin here", value='', type='text', debounce=True, bs_size="lg"),
        # dcc.Markdown("Destination:"),
        dbc.Input(id='dest', placeholder="Type your destination here", value='', type='text', debounce=True, bs_size="lg"),
        html.Hr(),
    ]), width=6),
    html.Div([
        dbc.Nav([
                dbc.NavLink("Minimize slope", id='slope_button', n_clicks=0, href="#"),
                dbc.NavLink("Balance slope and length", id='balance_button', n_clicks=0, href="#"),
                dbc.NavLink("Shortest route", id='short_button', n_clicks=0, href="#")
                ],
            pills=True)
        ]),
    html.Div(id='warning'),
    html.Div(id='a_string', children=""),
    html.Div([dl.Map([dl.TileLayer(), dl.LayerGroup(id='layer'), colorbar], style={'width': '1000px', 'height': '500px'}, id="the_map")]),
    html.Div(id='blurs', style={'display': 'none'}),
    html.Div(id='dd-output-container', style={'display': 'none'}),
    html.Div([
            dbc.Row([
                dbc.Col(html.Div(),width=4),
                dbc.Col(html.Div(
                    dbc.Nav([dbc.NavLink("github", href="www.github.com/saltzadam/WheelWay"),
                        dbc.NavLink("slides", href="#")
                        ])
                    ),width=4)
             ], justify="between")
        ])
    ])

@app.callback(
        Output('blurs', 'children'),
        [Input('origin', 'n_blur'),
         Input('dest', 'n_blur'),
         Input('slope_button', 'n_clicks'),
         Input('balance_button', 'n_clicks'),
         Input('short_button', 'n_clicks')])
def update_blurs(blur_o, blur_d, b1, b2, b3):
    if (not blur_o) or (not blur_d):
        return 0
    else:
        return int(blur_o) + int(blur_d) + b1 + b2 + b3

@app.callback(
        Output('dd-output-container', 'children'),
        [Input('slope_button', 'n_clicks'),
         Input('balance_button', 'n_clicks'),
         Input('short_button', 'n_clicks')],
        )
def update_dd(b1, b2, b3):
    ctx = dash.callback_context
    state = ctx.triggered[0]['prop_id']
    if state == "slope_button.n_clicks":
        return 'slope'
    elif state == "balance_button.n_clicks":
        return 'balance'
    elif state == "short_button.n_clicks":
        return 'short'
    else:
        return 'slope'
   
@app.callback(
    [ Output('warning', 'children'),
      Output('layer', 'children'),
      Output('the_map','bounds')],
    [Input('blurs', 'children')],# Input('dest', 'value')],
    [State('origin', 'value'),
     State('dest', 'value'),
     State('dd-output-container', 'children')
    ]
    )
def update_figure(nb, ori_str, dest_str, routing):
    if (not ori_str) or (not dest_str):
        return [], 'Enter your origin and destination!', utils.STANDARD_BOUNDS 
    else:
        return utils.get_fig(ori_str, dest_str, routing)

@app.callback([Output('slope_button', 'active'),
               Output('balance_button', 'active'),
               Output('short_button', 'active')],
               [Input('dd-output-container', 'children')]
               )
def update_active(routing):
    if routing == 'slope':
        return [True, False, False]
    elif routing == 'balance':
        return [False, True, False]
    elif routing == 'short':
        return [False, False, True]
    else: 
        return [True, False, False]



if __name__ == '__main__':
    app.run_server(debug=True,
            port = 8050)
