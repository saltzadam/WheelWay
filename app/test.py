import geocoder
import psycopg2
import sqlalchemy as sql
import plotly_express as px

Safe = px.colors.qualitative.Safe
angle_color_map = {
        0: Safe[3],
        1: Safe[6],
        2: Safe[2],
        3: Safe[1],
        4: Safe[9],
        None: 'blue'}
angle_data = {(u,v):angle for (u,v,angle) in brighton_G.edges.data('angle_class')}

COLORS = [Safe[3], Safe[6], Safe[2], Safe[1], Safe[9]]

hostname = "wheelway2.cgfv5tiyps6x.us-east-1.rds.amazonaws.com"
username = "postgres"
with open('/home/adam/rdskey') as keyfile:
    rds_key = keyfile.readline().strip()
    
con = psycopg2.connect(database = "wheelway", 
                       user=username, 
                       host=hostname, 
                       password=rds_key, 
                       port=5432
                      )

engine = sql.create_engine('postgresql+psycopg2://{user}:{pwd}@{host}:{port}/wheelway'.format(user=username,
                                                                                     pwd=rds_key,
                                                                                     host=hostname,
                                                                                     port=5432
                                                                                     ))

cur = con.cursor()

def get_nearest_node(lng, lat):
    cur.execute("""
    SELECT id, the_geom <-> ST_SetSRID(ST_MakePoint(%s, %s), 4326) AS dist 
    FROM brighton_edges_noded_vertices_pgr
    ORDER BY dist LIMIT 1;""", (lng, lat))
    # TODO: hacky
    pt_string = cur.fetchall()[0][0][6:-1].split()
    return tuple([float(z) for z in pt_string])


def get_route(ori_str, des_str):
    g1 = geocoder.osm(ori_str + " Brighton, MA")
    g2 = geocoder.osm(des_str + " Brighton, MA")
    p1 = (g1.json['lng'], g1.json['lat'])
    p2 = (g2.json['lng'], g2.json['lat'])
    n1 = ox.get_nearest_node(brighton_G,p1, method='haversine')
    n2 = ox.get_nearest_node(brighton_G,p2, method='haversine')
    route = nx.shortest_path(brighton_G, n1, n2)
    return route


def fixed_route(rows):
    #dedupe and keep order
    rows = list(dict.fromkeys(rows))
    first_row = rows.pop(0)
    relinked = [(first_row[2],first_row[3], first_row[1])]
    for row in rows:
        row = (row[1], row[2], row[3])
        last_row = relinked[-1]
        if row == last_row:
            continue
        elif last_row[2] == row[1]:
            relinked.append(row)
        else:
            relinked.append((row[2], row[1], row[0]))
    return relinked

# why do we need to split this ourselves??
def query_route(ori_int, des_int):
    cur.execute("SELECT node, b.angle_class, ST_AsText(ST_StartPoint(b.geom)), ST_AsText(ST_EndPoint(b.geom)), ST_AsText(b.geom) FROM pgr_dijkstra('SELECT id, source, target, cost FROM brighton_edges', %s, %s, directed:=true) a LEFT JOIN brighton_edges b ON (a.edge = b.id)", (ori_int, des_int))
    raw_route = cur.fetchall()
    return fixed_route(raw_route)


