import geocoder
import psycopg2
import sqlalchemy as sql

from  shapely.wkt import loads
import shapely
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
    return ([pt_to_pair(row[0]), pt_to_pair(row[1])], row[2], row[3], row[4])
 

FOUND_ROUTE_MESSAGE = "Here's your route."

short_sql_query = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angleclass, b.key, b.obstructed
                       FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost FROM my_edges 
                       ', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.id)""" # (ori_int, des_int)
                       #WHERE obstructed=0
balance_sql_query = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angleclass, b.key, b.obstructed
                       FROM pgr_dijkstra('SELECT id, source, target, (cost * (1 + %s * abs(angle_deg)/15)) AS cost, (cost * (1 + %s * abs(angle_deg)/15)) AS reverse_cost FROM my_edges', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.id)""" # (ALPHA, ALPHA, ori_int, des_int)
                       # ALPHA = 2/5
slope_sql_query = """SELECT st_astext(st_startpoint(b.geom)), st_astext(st_endpoint(b.geom)), b.angleclass, b.key, b.obstructed
                           FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost
                                              FROM my_edges 
                                              WHERE angle_deg < %s AND angle_deg > -(%s)', %s, %s, FALSE) a 
                           LEFT JOIN my_edges b 
                           ON (a.edge = b.id)""" # (i, i, ori_int, des_int))

ALPHA = 2/5

def stream_route(ori_int, des_int, routing, alpha, con):
    print(routing)
    if routing == 'short':
        cur = con.cursor('short')
        cur.execute(short_sql_query, (ori_int, des_int))
    elif routing == 'balance':
        cur = con.cursor('balance')
        cur.execute(balance_sql_query, (alpha, alpha, ori_int, des_int))
    elif routing == 'slope':
        for i in range(0, 39, 2):
            cur = con.cursor()
            cur.execute(slope_sql_query, (i, i, ori_int, des_int))
            if i >= 38:
                return [], "I'm sorry, we can't find a route without very high slopes."
            if cur.fetchone() is not None:
                cur = con.cursor()
                cur.execute(slope_sql_query, (i, i, ori_int, des_int))
                max_slope = i
                break
            else:
                continue
    try:
        first_row = process_row(cur.fetchone())
    except StopIteration:
        return [], "I'm sorry, we can't find a route."
    second_row = process_row(cur.fetchone())
    if first_row == second_row:
        second_row = process_row(cur.fetchone())
 
    def flip_dir(row):
        return ([row[0][1], row[0][0]], row[1], row[2], row[3])

    if first_row[0][1] == second_row[0][0]:
        relinked = [first_row, second_row]
    elif first_row[0][0] == second_row[0][0]:
        relinked = [flip_dir(first_row),second_row]
    elif first_row[0][1] == second_row[0][1]:
        relinked = [first_row, flip_dir(second_row)]
    elif first_row[0][0] == second_row[0][1]:
        relinked = [flip_dir(first_row), flip_dir(second_row)]
    else:
        print(first_row)
        print(second_row)
 
    counter = 0
    seen_rows = [first_row, second_row]
    for row in cur:
        # print(counter)
        #last row:
        if row[0] is None:
            continue

        #dedupe
        # if row in seen_rows:
        #     continue
        # else:
        #     seen_rows.append(row)

        row = process_row(row)
        last_row = relinked[-1]
        # flip to be aligned
        if last_row[0][-1] == row[0][1]:
            row = flip_dir(row)
        # counter = counter+1
        # concatenate
        if (row[1], row[2], row[3]) == (last_row[1], last_row[2], last_row[3]):
            last_row = relinked.pop() # remove last_row
            last_row[0].append(row[0][1]) # add in new coordinates
            relinked.append(last_row) # reattach last_row
        else:
            relinked.append(row)
    if routing == 'slope':
        cur.close()
        return relinked, "This route has a maximum slope of " + str(max_slope) + " degrees."
    else:
        cur.close()
        return relinked, "Here's your route."

def get_route(ori_str, des_str,routing, alpha, con):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    cur = con.cursor()
    n1 = get_nearest_node(p1[0], p1[1], cur)
    n2 = get_nearest_node(p2[0], p2[1], cur)
    cur.close()
    # this returns a list (lng, lat, class)
    route_message = stream_route(n1, n2, routing, alpha, con)
    # returns a list of tuples [(lng, lat)]
    return route_message

def make_line(row):
    # print(row)
    points, angleclasss, key, obstruct = row
    points = [[point[1], point[0]] for point in points]
    # print(points)
    if key == 1:
        color = 'yellow'
    elif obstruct == 1:
        color = 'red'
    else:
        color = angle_color_map[angleclasss]
    return dl.Polyline(positions=points, color=color, weight= 4)

def make_lines(route):
    first_seg = route.pop(0)
    lines = [make_line(first_seg)]
    # now we have to check the accumulator as we go
    for row in route:
        last_line = lines[-1]
        new_line = make_line(row)
        if (last_line.color == new_line.color):
            last_line = lines.pop()
            last_line.positions.extend(new_line.positions[0:])
            lines.append(last_line)
        else:
            lines.append(new_line)
    for i, line in enumerate(lines):
        # print(lines)
        if line.color == 'red' or line.color == 'yellow':
            if i != 0:
                last_line = lines[i-1]
                # TODO: combine
                if len(last_line.positions) == 2:
                    pre = last_line.positions
                else:
                    pre = last_line.positions[-2:]
                lines[i-1] = last_line
                line.positions = pre + line.positions
           
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

def get_fig(ori_str, des_str, routing, alpha):
    con = psycopg2.connect(database = "wheelway", 
                       user=username, 
                       host=hostname, 
                       password=rds_key, 
                       port=5432
                      )

    route, message = get_route(ori_str, des_str, routing, alpha, con)
    if route is None or route == []:
        return message, [], STANDARD_BOUNDS # should be some standard bounds maybe
    lines = make_lines(route)
    con.commit()
    con.close
    # engine.dispose()
    return message, lines, get_bounds(lines)

