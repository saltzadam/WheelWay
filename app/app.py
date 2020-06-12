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

import folium
import osmnx as ox

external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']


with open("brighton_graph.pkl", 'rb') as pklfile:
    brighton_G = pkl.load(pklfile)

# edges = brighton_G.edges(data=True)

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

def _make_folium_polyline(
    edge, edge_color, edge_width, edge_opacity, popup_attribute=None, **kwargs
):
    """
    Turn row GeoDataFrame into a folium PolyLine with attributes.
    Parameters
    ----------
    edge : GeoSeries
        a row from the gdf_edges GeoDataFrame
    edge_color : string
        color of the edge lines
    edge_width : numeric
        width of the edge lines
    edge_opacity : numeric
        opacity of the edge lines
    popup_attribute : string
        edge attribute to display in a pop-up when an edge is clicked, if
        None, no popup
    kwargs : dict
        Extra parameters passed through to folium
    Returns
    -------
    pl : folium.PolyLine
    """
    # check if we were able to import folium successfully
    if not folium:
        raise ImportError("The folium package must be installed to use this optional feature.")

    # locations is a list of points for the polyline
    # folium takes coords in lat,lon but geopandas provides them in lon,lat
    # so we have to flip them around
    locations = list([(lat, lng) for lng, lat in edge["geometry"].coords])

    # if popup_attribute is None, then create no pop-up
    if popup_attribute is None:
        popup = None
    else:
        # folium doesn't interpret html in the html argument (weird), so can't
        # do newlines without an iframe
        popup_text = json.dumps(edge[popup_attribute])
        popup = folium.Popup(html=popup_text)

    # create a folium polyline with attributes
    pl = folium.PolyLine(
        locations=locations,
        popup=popup,
        color=edge_color,
        weight=edge_width,
        opacity=edge_opacity,
        **kwargs,
    )
    return pl



def plot_route_folium_colored(
    G,
    route,
    route_map=None,
    popup_attribute=None,
    tiles="cartodbpositron",
    zoom=1,
    fit_bounds=True,
    color_fn=(lambda x : "#cc0000"),
    route_width=5,
    route_opacity=1,
    **kwargs,
):
    """
    Plot a route on an interactive folium web map.
    Parameters
    ----------
    G : networkx.MultiDiGraph
        input graph
    route : list
        the route as a list of nodes
    route_map : folium.folium.Map
        if not None, plot the route on this preexisting folium map object
    popup_attribute : string
        edge attribute to display in a pop-up when an edge is clicked
    tiles : string
        name of a folium tileset
    zoom : int
        initial zoom level for the map
    fit_bounds : bool
        if True, fit the map to the boundaries of the route's edges
    route_color : string
        color of the route's line
    route_width : numeric
        width of the route's line
    route_opacity : numeric
        opacity of the route lines
    kwargs : dict
        Extra parameters passed through to folium
    Returns
    -------
    route_map : folium.folium.Map
    """
    # check if we were able to import folium successfully
    if not folium:
        raise ImportError("The folium package must be installed to use this optional feature.")

    # create gdf of the route edges
    gdf_edges = ox.utils_graph.graph_to_gdfs(G, nodes=False, fill_edge_geometry=True)
    route_nodes = list(zip(route[:-1], route[1:]))
    index = [
        gdf_edges[(gdf_edges["u"] == u) & (gdf_edges["v"] == v)].index[0] for u, v in route_nodes
    ]
    gdf_route_edges = gdf_edges.loc[index]

    # get route centroid
    x, y = gdf_route_edges.unary_union.centroid.xy
    route_centroid = (y[0], x[0])

    # create the folium web map if one wasn't passed-in
    if route_map is None:
        route_map = folium.Map(location=route_centroid, zoom_start=zoom, tiles=tiles)

    # add each route edge to the map
    for _, row in gdf_route_edges.iterrows():
        pl = _make_folium_polyline(
            edge=row,
            edge_color=color_fn(row),
            edge_width=route_width,
            edge_opacity=route_opacity,
            popup_attribute=popup_attribute,
            **kwargs,
        )
        pl.add_to(route_map)

    # if fit_bounds is True, fit the map to the bounds of the route by passing
    # list of lat-lng points as [southwest, northeast]
    if fit_bounds and isinstance(route_map, folium.Map):
        tb = gdf_route_edges.total_bounds
        bounds = [(tb[1], tb[0]), (tb[3], tb[2])]
        route_map.fit_bounds(bounds)

    return route_map

def get_edge_color(row):
    return str(angle_color_map[row['angle_class']])

def get_fig(ori_str, des_str):
    print('get route')
    route = get_route(ori_str, des_str)
    print('make map')
    the_map = plot_route_folium_colored(brighton_G, route, color_fn = get_edge_color,route_width = 2)
    print('save and load')
    the_map.save('assets/the_map.html')
    # return app.get_asset_url('the_map.html')
    return open('assets/the_map.html', 'r').read()


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
    html.Iframe(id='the map', width='100%', height='400'),
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
    Output('the map', 'srcDoc'),
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
        return ""
    else:
        return get_fig(ori_str, dest_str)    


if __name__ == '__main__':
    app.run_server(debug=True,
            port = 8050)
