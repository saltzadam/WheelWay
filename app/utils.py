import geocoder
import psycopg2
import sqlalchemy as sql

from  shapely.wkt import loads
import dash_leaflet as dl
import plotly_express as px

import os

# controls angle scaling for balanced paths
ALPHA = 2/5

angle_color_map = {
        0: "#45337dff",
        1: "#33638dff",
        2: "#218f8dff",
        3: "#35b479ff",
        4: "#8dd544ff",
        None: 'blue'}

hostname = "wheelway2.cgfv5tiyps6x.us-east-1.rds.amazonaws.com"
username = "postgres"
#with open('rdskey') as keyfile:
#    rds_key = keyfile.readline().strip()
rds_key = os.environ['RDS_KEY']
 

def get_nearest_node(lng, lat, cur):
    cur.execute("""
    SELECT source, geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS dist 
    FROM my_edges
    ORDER BY dist LIMIT 1;""", (lng, lat))
    raw = cur.fetchall()
    ID = raw[0][0]
    print(ID)
    return ID

# converts 'POINT (coord, coord)' to (coord, coord)
def pt_to_pair(ptstring):
    pt = loads(ptstring) # from shapely
    return pt.coords[0]



def fixed_route(rows):
    def process_row(row):
        return (pt_to_pair(row[0]), pt_to_pair(row[1]), row[2])
    #dedupe and keep order
    rows = list(dict.fromkeys(rows))
    
    # last row is basically null
    rows = rows[:-1]

    # add rows, flipping the two points if necessary. should be
    # (start point, end point, angle class)
    first_row = rows.pop(0)
    relinked = [process_row(first_row)]
    for row in rows:
        row = process_row(row)
        last_row = relinked[-1]
        if row == last_row:
            continue
        elif last_row[1] == row[0]:
            relinked.append(row)
        elif last_row[1] == row[1]:
            relinked.append([row[1], row[0], row[2]])
        else:# row == (None, None, None):
            continue
    return relinked


FOUND_ROUTE_MESSAGE = "Here's your route."

def query_route(ori_int, des_int, routing, cur):
    print(routing)
    if routing == 'short':
        cur.execute("""SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angleclass 
                       FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost FROM my_edges', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.osmid)""", (ori_int, des_int))
        raw_route = cur.fetchall()
        return fixed_route(raw_route), FOUND_ROUTE_MESSAGE
    elif routing == 'ADA':
        cur.execute("""SELECT st_astext(st_startpoint(b.geom)), st_astext(st_endpoint(b.geom)), b.angleclass
                       FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost 
                                          FROM my_edges 
                                          WHERE angle_deg < 5 AND angle_deg > -5', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.osmid)""", (ori_int, des_int))
        raw_route = cur.fetchall()
        if raw_route == []:
            return None,  "We're sorry, there's no ADA-compliant route available."
        return fixed_route(raw_route), FOUND_ROUTE_MESSAGE
    elif routing == 'balance':
        # scaling factor for angle
        ALPHA = 2/5
        cur.execute("""SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angleclass
                       FROM pgr_dijkstra('SELECT id, source, target, (cost * (1 + %s * abs(angle_deg)/15)) AS cost, (cost * (1 + %s * abs(angle_deg)/15)) AS reverse_cost FROM my_edges', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.osmid)""", (ALPHA, ALPHA, ori_int, des_int))
        raw_route = cur.fetchall()
        return fixed_route(raw_route), FOUND_ROUTE_MESSAGE
    elif routing == 'slope':
        for i in range(31):
            cur.execute("""SELECT st_astext(st_startpoint(b.geom)), st_astext(st_endpoint(b.geom)), b.angleclass
                           FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost
                                              FROM my_edges 
                                              WHERE angle_deg < %s AND angle_deg > -(%s)', %s, %s, FALSE) a 
                           LEFT JOIN my_edges b 
                           ON (a.edge = b.osmid)""", (i, i, ori_int, des_int))
            raw_route = cur.fetchall()
            if raw_route == []:
                continue
            else:
                def slope_route_message(j):
                    return "We found you a route with maximum slope " + str(i) + " degrees."
                return fixed_route(raw_route), slope_route_message(i)
        return None, "There's no route which avoids hills with slope up to 30 degrees!"
            
 

def get_route(ori_str, des_str,routing,con):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    cur = con.cursor()
    n1 = get_nearest_node(p1[0], p1[1], cur)
    n2 = get_nearest_node(p2[0], p2[1], cur)
    # this returns a list (lng, lat, class)
    route_message = query_route(n1, n2, routing, cur)
    cur.close()
    # returns a list of tuples [(lng, lat)]
    return route_message

def make_line(row):
    source, target, angleclasss = row
    color = angle_color_map[angleclasss]
    return dl.Polyline(positions=[[source[1], source[0]], [target[1], target[0]]], color=color, weight= 4)

def make_lines(route):
    first_seg = route.pop(0)
    lines = [make_line(first_seg)]
    # now we have to check the accumulator as we go
    for row in route:
        last_line = lines[-1]
        new_line = make_line(row)
        if (last_line.color == new_line.color):
            last_line.positions.append(new_line.positions[1])
            lines.pop()
            lines.append(last_line)
        else:
            lines.append(new_line)
        
    print('drew',len(lines),'lines')
    return lines

def get_bounds(lines):
    points = [line.positions for line in lines]
    xs = [p[0] for pairs in points for p in pairs]
    ys = [p[1] for pairs in points for p in pairs]
    botleft = [min(xs), min(ys)]
    topright = [max(xs), max(ys)]
    return [botleft, topright]

STANDARD_BOUNDS = [[42.331, -71.17], [42.36, -71.13405]]

def get_fig(ori_str, des_str, routing):
    con = psycopg2.connect(database = "wheelway", 
                       user=username, 
                       host=hostname, 
                       password=rds_key, 
                       port=5432
                      )

    # engine = sql.create_engine('postgresql+psycopg2://{user}:{pwd}@{host}:{port}/wheelway'.format(user=username,
    #                                                                                  pwd=rds_key,
    #                                                                                  host=hostname,
    #                                                                                  port=5432
    #                                                                                  ))
    route, message = get_route(ori_str, des_str, routing, con)
    if route is None:
        return message, [], STANDARD_BOUNDS # should be some standard bounds maybe
    lines = make_lines(route)
    con.commit()
    con.close
    # engine.dispose()
    return message, lines, get_bounds(lines)

