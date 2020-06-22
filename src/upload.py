import sys

if sys.version_info[1] < 8:
    print("This script uses features in Pandas 0.24. It therefore requires Python 3.8. Sorry.")

import sqlalchemy as sql
from sqlalchemy_utils import database_exists
import psycopg2
from geoalchemy2 import WKTElement, Geometry
import geopandas as gpd


hostname = "wheelway4.cgfv5tiyps6x.us-east-1.rds.amazonaws.com"
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

# gdf_edges = gpd.read_file("test/final.shp")
gdf_edges = gpd.read_file("test/obstructed.shp")

# make the geometry column compatible with PostGIS
gdf_edges['geom'] = gdf_edges['geometry'].apply(lambda x: WKTElement(x.wkt, srid=4326))
gdf_edges.drop(columns=['geometry'], inplace=True)

# make some column names more standard for pgrouting functions
gdf_edges.rename(columns = {'u':'source',
                 'v':'target',
                 'length_m':'cost'}, inplace=True)

from sqlalchemy import Integer, Float, BigInteger
gdf_edges['id'] = gdf_edges['osmid']
with engine.connect() as connection:
    gdf_edges.to_sql('my_edges', connection, if_exists='replace', index=False, method='multi', chunksize=5000,
                     dtype={'geom': Geometry('LINESTRING', srid=4326),
                                    'angle_class': Integer,
                                    'balanced_l': Float,
                                    'key': Integer,
                                    'cost': Float,
                                    'id': Integer,
                                    'obstructed': Integer,
                                    'osmid': Integer,
                                    'source': Integer,
                                    'target': Integer},
                    )


