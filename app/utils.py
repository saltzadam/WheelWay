import os

import geocoder
import psycopg2
import sqlalchemy as sql

from  shapely.wkt import loads
import shapely
import dash_leaflet as dl


## Defines colors for lines based on angle classes
# the None key is basically there for debugging
# TODO: remove it and check that nothing breaks
ANGLE_COLOR_MAP = {
        0: "#8dd544ff",
        1: "#35b479ff",
        2: "#218f8dff",
        3: "#33638dff",
        4: "#45337dff",
        None: 'blue'}


# you should fill in your own database here
HOSTNAME = "wheelway4.cgfv5tiyps6x.us-east-1.rds.amazonaws.com"
USERNAME = "postgres"

# Import your password
# This is for the user 'postgres' in your database, not for AWS

try:
    # load key in Heroku
    rds_key = os.environ['RDS_KEY']
except:
    with open('/home/adam/rdskey') as keyfile:
        rds_key = keyfile.readline().strip()

# TODO: error handling!
def get_nearest_node(lng, lat, cur):
    # search the edges, ordered by distance from (lng, lat)
    # LIMIT 1 returns the first, i.e the closest
    cur.execute("""
    SELECT source, geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS dist 
    FROM my_edges
    ORDER BY dist LIMIT 1;""", (lng, lat))
    raw = cur.fetchall()
    ID = raw[0][0] # throw out the distance
    # This is a nice, lightweight debugger
    print(ID)
    return ID

# converts 'POINT (coord, coord)' to (coord, coord)
def pt_to_pair(ptstring):

    print(ptstring)
    pt = loads(ptstring) # From shapely. Takes a WKT string
                         # and returns a shapely.geometry.Point.
    return pt.coords[0]  # We only want (coord, coord)
                         # TODO: clearer as [:]

def process_row(row):
    return ([pt_to_pair(row[0]), pt_to_pair(row[1])], row[2], row[3], row[4])
 

# TODO: parametrize this over slopes for the 'slope' search.
#       the others could be defaults
FOUND_ROUTE_MESSAGE = "Here's your route."

# TODO: rewrite with sqlalchemy, please
# also parametrize
short_sql_query = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angle_deg, b.key, b.obstructed
                       FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost FROM my_edges 
                       ', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.id)""" # (ori_int, des_int)

short_sql_query_obs = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angle_deg, b.key, b.obstructed
                       FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost FROM my_edges WHERE obstructed=0 
                       ', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.id)"""

balance_sql_query = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angle_deg, b.key, b.obstructed
                       FROM pgr_dijkstra('SELECT id, source, target, POWER(cost * (1 + %s * abs(angle_deg)/15), 2) AS cost, (cost * POWER(1 + %s * abs(angle_deg)/15, 2)) AS reverse_cost FROM my_edges', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.id)""" # (ALPHA, ALPHA, ori_int, des_int)

balance_sql_query_obs = """SELECT ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), b.angle_deg, b.key, b.obstructed
                       FROM pgr_dijkstra('SELECT id, source, target, (cost * (1 + %s * abs(angle_deg)/15)) AS cost, (cost * (1 + %s * abs(angle_deg)/15)) AS reverse_cost FROM my_edges WHERE obstructed=0', %s, %s, FALSE) a 
                       LEFT JOIN my_edges b 
                       ON (a.edge = b.id)""" # (ALPHA, ALPHA, ori_int, des_int)

slope_sql_query = """SELECT st_astext(st_startpoint(b.geom)), st_astext(st_endpoint(b.geom)), b.angle_deg, b.key, b.obstructed
                           FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost
                                              FROM my_edges 
                                              WHERE angle_deg < %s AND angle_deg > -(%s)', %s, %s, FALSE) a 
                           LEFT JOIN my_edges b 
                           ON (a.edge = b.id)""" # (i, i, ori_int, des_int))

slope_sql_query_obs = """SELECT st_astext(st_startpoint(b.geom)), st_astext(st_endpoint(b.geom)), b.angle_deg, b.key, b.obstructed
                           FROM pgr_dijkstra('SELECT id, source, target, cost, cost AS reverse_cost
                                              FROM my_edges
                                              WHERE angle_deg < %s AND angle_deg > -(%s) AND obstructed=0', %s, %s, FALSE) a 
                           LEFT JOIN my_edges b 
                           ON (a.edge = b.id)""" # (i, i, ori_int, des_int))

def stream_route(ori_int, des_int, routing, alpha, obs, con):
    # a good lightweight debug
    print(routing)
    # TODO: this should all be dicts or whatever
    # actually should make the queries functions of obs, c'mon

    # set the cursor to make the query
    if routing == 'short' and obs:
        cur = con.cursor('short')
        cur.execute(short_sql_query_obs, (ori_int, des_int))
    elif routing == 'short' and not obs:
        cur = con.cursor('short')
        cur.execute(short_sql_query, (ori_int, des_int))
    elif routing == 'balance' and obs:
        cur = con.cursor('balance')
        cur.execute(balance_sql_query_obs, (alpha, alpha, ori_int, des_int))
    elif routing == 'balance' and not obs:
        cur = con.cursor('balance')
        cur.execute(balance_sql_query, (alpha, alpha, ori_int, des_int))
    elif routing == 'slope' and not obs:
        for i in range(0, 39, 2):
            # originally used named cursors above so that the requests could be returned at streams
            # i.e. to stop memory errors
            # But each named cursor can execute only once. So it was hard to write 
            # a loop like this. TODO: rewrite the iterative part in SQL so that it's
            # still only one request
            # TODO: evaluate if we actually need the named cursors. (Or maybe that's
            #       best practice anyway??)
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
    elif routing == 'slope' and obs:
        for i in range(0, 39, 2):
            cur = con.cursor()
            
            cur.execute(slope_sql_query_obs, (i, i, ori_int, des_int))
            if i >= 38:
                return [], "I'm sorry, we can't find a route without very high slopes."
            if cur.fetchone() is not None:
                cur = con.cursor()
                cur.execute(slope_sql_query_obs, (i, i, ori_int, des_int))
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

    # For whatever reason the query is often returned with edges not properly 'aligned'
    # i.e. you should have (a,b) then (b,c) then (c,d) where each tuple is a line represented
    # by its endpoints. But sometimes we get (b,a) (b,c) (d,c). (Could be 'directed' toggle
    # in the queries)
    # The first row can be 'misaligned' and the only way to tell is by adding the second row as well,
    # then correcting:

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
 
    seen_rows = [first_row, second_row]
    for row in cur:
        # last row is (None, None, None) or somesuch:
        if row[0] is None:
            continue

        # get new row
        row = process_row(row)
        # check out the most recently added row
        last_row = relinked[-1]
        # flip to be aligned
        if last_row[0][-1] == row[0][1]:
            row = flip_dir(row)

        # if the new row and the most recent row are the same color,
        # we want them to end up together in a PolyLine rather than as
        # two separate lines.
        # So check if they are the same color, then add the new coordinate (there's only
        # one!) to the old line.
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
        if obs:
            SUCCESS_STRING = "Here's your route with no sidewalk problems."
        else:
            SUCCESS_STRING = "Here's your route."
        return relinked, SUCCESS_STRING

def get_route(ori_str, des_str,routing, alpha, obs, con):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    cur = con.cursor()
    n1 = get_nearest_node(p1[0], p1[1], cur)
    n2 = get_nearest_node(p2[0], p2[1], cur)
    cur.close()

    route_message = stream_route(n1, n2, routing, alpha, obs, con)
    return route_message

def make_line(row):
    points, angle_deg, key, obstruct = row
    if abs(angle_deg) < 4:
        angleclass=0
    elif abs(angle_deg) < 8:
        angleclass=1
    elif abs(angle_deg) < 12:
        angleclass=2
    elif abs(angle_deg) < 16:
        angleclass=3
    else:
        angleclass=4
    points = [[point[1], point[0]] for point in points]

    # 'key == 1' precisely if the segment is a crosswalk
    # note that crosswalks are never obstructed (for now!)
    if key == 1:
        color = 'yellow'
    elif obstruct == 1:
        color = 'red'
    else:
        color = ANGLE_COLOR_MAP[angleclass]
    return dl.Polyline(positions=points, color=color, weight= 4)

def make_lines(route):
    first_seg = route.pop(0)
    lines = [make_line(first_seg)]
    # now we have to check the accumulator as we go
    for row in route:
        last_line = lines[-1]
        new_line = make_line(row)
        # TODO: is this redundant with the new stream_route??
        #       in other words: with stream_route as it is,
        #       will this condition ever hold?
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

# decent map bounds to show Brighton
STANDARD_BOUNDS = [[42.331, -71.17], [42.36, -71.13405]]

def get_fig(ori_str, des_str, routing, alpha, obs):
    # connect to the database
    con = psycopg2.connect(database = "wheelway", 
                       user=USERNAME, 
                       host=HOSTNAME, 
                       password=rds_key, 
                       port=5432
                      )

    # get the route
    route, message = get_route(ori_str, des_str, routing, alpha, obs, con)

    # point here is to keep the bounds as they are.  "STANDARD_BOUNDS are the 
    # bounds for the empty route."
    if route is None or route == []:
        return message, [], STANDARD_BOUNDS 
    # draw the lines with colors and so on
    lines = make_lines(route)
    con.commit()
    con.close
    # engine.dispose()
    return message, lines, get_bounds(lines)

