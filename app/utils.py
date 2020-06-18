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
        4: "#45337dff",
        3: "#33638dff",
        2: "#218f8dff",
        1: "#35b479ff",
        0: "#8dd544ff",
        None: 'blue'}


hostname = "wheelway4.cgfv5tiyps6x.us-east-1.rds.amazonaws.com"
username = "postgres"
#with open('rdskey') as keyfile:
#    rds_key = keyfile.readline().strip()
try:
    rds_key = os.environ['RDS_KEY']
except:
    with open('/home/adam/rdskey') as keyfile:
        rds_key = keyfile.readline().strip()

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

def process_row(row):
    return ([pt_to_pair(row[0]), pt_to_pair(row[1])], row[2], row[3])
  

def fixed_route(rows):
    
    # last row is basically null

    # add rows, flipping the two points if necessary. should be
    # (start point, end point, angle class)
    first_row = process_row(rows.pop(0))
    # fix this tomorrow:!
    second_row = process_row(rows.pop(0))
    if first_row[1] == second_row[0]:
        relinked = [first_row, second_row]
    elif first_row[0] == second_row[0]:
        relinked = [(first_row[1],first_row[0],first_row[2]),second_row]
    elif first_row[1] == second_row[1]:
        relinked = [first_row, (second_row[1], second_row[0], second_row[2])]
    elif first_row[0] == second_row[1]:
        relinked = [(first_row[1],first_row[0],first_row[2]), (second_row[1], second_row[0], second_row[2])]
    for row in rows:
        #last row:
        if row == (None, None, None):
            continue
        row = process_row(row)
        last_row = relinked[-1]
        if row == last_row:
            continue
        elif last_row[1] == row[0]:
            relinked.append(row)
        elif last_row[1] == row[1]:
            relinked.append([row[1], row[0], row[2]])
        else: # probably should throw # row == (None, None, None):
            continue
    return relinked


FOUND_ROUTE_MESSAGE = "Here's your route."

short_sql_query = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angleclass, b.key
                       FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost FROM my_edges WHERE obstructed=0', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.osmid)""" # (ori_int, des_int)
balance_sql_query = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angleclass, b.key
                       FROM pgr_dijkstra('SELECT id, source, target, (cost * (1 + %s * abs(angle_deg)/15)) AS cost, (cost * (1 + %s * abs(angle_deg)/15)) AS reverse_cost FROM my_edges WHERE obstructed=0', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.osmid)""" # (ALPHA, ALPHA, ori_int, des_int)
                       # ALPHA = 2/5
slope_sql_query = """SELECT st_astext(st_startpoint(b.geom)), st_astext(st_endpoint(b.geom)), b.angleclass, b.key
                           FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost
                                              FROM my_edges 
                                              WHERE angle_deg < %s AND angle_deg > -(%s) AND obstructed=0', %s, %s, FALSE) a 
                           LEFT JOIN my_edges b 
                           ON (a.edge = b.osmid)""" # (i, i, ori_int, des_int))

ALPHA = 2/5

def stream_route(ori_int, des_int, routing, con):
    if routing == 'short':
        cur = con.cursor('short')
        cur.execute(short_sql_query, (ori_int, des_int))
    elif routing == 'balance':
        cur = con.cursor('balance')
        cur.execute(balance_sql_query, (ALPHA, ALPHA, ori_int, des_int))
    elif routing == 'slope':
        for i in range(32):
            cur = con.cursor()
            cur.execute(slope_sql_query, (i, i, ori_int, des_int))
            if i == 31:
                return None
            if cur.fetchone() is not None:
                cur = con.cursor('balance')
                cur.execute(slope_sql_query, (i, i, ori_int, des_int))
                max_slope = i
            else:
                continue
    try:
        first_row = process_row(cur.next())
    except StopIteration:
        return [], "I'm sorry, we can't find a route."
    second_row = process_row(cur.next())
    if first_row == second_row:
        second_row = process_row(cur.next())
 
    def flip_dir(row):
        return ([row[0][1], row[0][0]], row[2], row[3])

    if first_row[0][1] == second_row[0][0]:
        relinked = [first_row, second_row]
    elif first_row[0][0] == second_row[0][0]:
        relinked = [flip_dir(first_row),second_row]
    elif first_row[0][1] == second_row[0][1]:
        relinked = [first_row, flip_dir(second_row)]
    elif first_row[0][0] == second_row[0][1]:
        relinked = [flip_dir(first_row), flip_dir(second_row)]
 
    for row in cur:
        #last row:
        if row[0] is (None,None):
            continue
        row = process_row(row)
        last_row = relinked[-1]
        # dedupe
        if row == last_row:
            continue
        # flip to be aligned
        if last_row[0][1] == row[0][1]:
            row = flip_dir(row)
        # concatenate
        if (row[1], row[2]) == (last_row[1], last_row[2]):
            last_row = relinked.pop() # remove last_row
            last_row[0].append(row[0][1]) # add in new coordinates
            relinked.append(last_row) # reattach last_row
        else:
            relinked.append(row)
    if routing == 'slope':
        return relinked, "This route has a maximum slope of " + str(max_slope) + " degrees."
    else:
        return relinked, "Here's your route."



                # def slope_route_message(j):
                #     return "We found you a route with maximum slope " + str(i) + " degrees."
                # return fixed_route(raw_route), slope_route_message(i)
        # return None, "There's no route which avoids hills with slope up to 30 degrees!"
            
 

def get_route(ori_str, des_str,routing,con):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    cur = con.cursor()
    n1 = get_nearest_node(p1[0], p1[1], cur)
    n2 = get_nearest_node(p2[0], p2[1], cur)
    cur.close()
    # this returns a list (lng, lat, class)
    route_message = stream_route(n1, n2, routing, con)
    # returns a list of tuples [(lng, lat)]
    return route_message

def make_line(row):
    source, target, angleclasss, key = row
    if key == 1:
        color = 'red'
    else:
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

    route, message = get_route(ori_str, des_str, routing, con)
    if route is None:
        return message, [], STANDARD_BOUNDS # should be some standard bounds maybe
    lines = make_lines(route)
    con.commit()
    con.close
    # engine.dispose()
    return message, lines, get_bounds(lines)

