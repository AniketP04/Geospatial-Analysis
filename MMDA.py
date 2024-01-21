# -*- coding: utf-8 -*-

import osmnx as ox
import sqlite3
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

import math
import seaborn as sns
import folium
from folium import Choropleth, Circle, Marker
from folium.plugins import HeatMap, MarkerCluster
import psycopg2
from geopandas.tools import sjoin
from shapely.geometry import Point, LineString, Polygon

import warnings
warnings.filterwarnings("ignore")

df = pd.read_csv('data_mmda_traffic_spatial.csv')

df_map = df.copy()
imap = folium.Map(location=[14.6091, 121.0223], tiles='openstreetmap', zoom_start=12)

mc = MarkerCluster()

for idx, row in df_map.iterrows():
    if not math.isnan(row['Longitude']) and not math.isnan(row['Latitude']):
        mc.add_child(Marker([row['Latitude'], row['Longitude']]))

imap.add_child(mc)
imap

# Insert details here
conn = psycopg2.connect(dbname="postgis",
                 user="xxxx",
                 password="xxxxx",
                 host="xxx",
                 port=0000)

q = '''
SELECT *
FROM ph_point
'''

df_pt = pd.read_sql(q, conn)

q = '''
SELECT *
FROM gadm.ph_brgy
LIMIT 100
'''

df_gadm = pd.read_sql(q, conn)

cols = ['Date', 'Time', 'Country', 'City', 'Location', 'Latitude', 'Longitude',
        'Direction', 'Type', 'Involved']

cols = ['Date', 'Country', 'City', 'Location', 'Latitude', 'Longitude']

df_accident = df[cols]
df_accident = df_accident.loc[df_accident.Latitude != 0]
df_accident['Location'] = df_accident['Location'].fillna('TBD')
x = df_accident.loc[df_accident.City.isna()].loc[df_accident.Location.str.contains('MABINI')].index
df_accident.loc[x] = df_accident.loc[x].fillna('Pasig City')
x = df_accident.loc[df_accident.City.isna()].loc[df_accident.Location.str.contains('MARCOS HIGHWAY')].index
df_accident.loc[x] = df_accident.loc[x].fillna('Pasig City')
x = df_accident.loc[df_accident.City.isna()].loc[df_accident.Location.str.contains('OKADA')].index
df_accident.loc[x] = df_accident.loc[x].fillna('Pasay City')
df_accident.City = df_accident.City.fillna('Manila')
df_accident.replace({'ParaÃ±aque':'Parañaque'}, inplace=True)

gdf = gpd.GeoDataFrame(df_accident, geometry=gpd.points_from_xy(df_accident.Longitude, df_accident.Latitude))

ph_shp = gpd.read_postgis('''
SELECT *
from gadm.ph
''',con=conn,geom_col = 'geom')

mm_pts = gpd.read_postgis('''
SELECT p.*
FROM ph_point as p
JOIN gadm.ph as g ON st_within(p.way, g.geom)
WHERE p.amenity != 'None' AND g.name_1 = 'Metropolitan Manila'
''', con = conn, geom_col = 'way')

mm_shp = ph_shp[ph_shp['name_1']=='Metropolitan Manila']
ax = mm_shp.plot(figsize = (10,10), alpha=0.8, color='black')
gdf.plot(ax=ax,color='firebrick',markersize=2)
ax.set_axis_off()

radius = 0.02

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'police' AND p.name IS NOT NULL AND g.name_1 = 'Metropolitan Manila'
'''

police = gpd.read_postgis(q, con=conn, geom_col='way')

ncr_shp = gpd.read_postgis(
'''
SELECT *
FROM gadm.ph
WHERE name_1 = 'Metropolitan Manila'
'''
,con = conn, geom_col ='geom'
)

ncr = ncr_shp[['name_2', 'geom']]

fig, ax = plt.subplots(figsize=(10, 10))
ncr.plot(ax=ax, alpha=0.8, color='black')
gdf.plot(ax=ax,color='firebrick',markersize=2)
police.plot(ax=ax,color='cornflowerblue',markersize=5)
for i in police.index:
    cx = police.loc[i]['way'].xy[0][0]
    cy = police.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.2, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

police1 = police.copy()
police1['way'] = police1['way'].buffer(radius)
gdf_ncr = gdf.copy()

police2 = police1.copy()
count_list = []
for i in police1.index:
    point = sjoin(gdf_ncr, police1.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police2['accident_count'] = count_list

police.shape

radius = 0.02

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'hospital' AND p.name IS NOT NULL AND g.name_1 = 'Metropolitan Manila'
'''

hospital = gpd.read_postgis(q, con=conn, geom_col='way')

fig, ax = plt.subplots(figsize=(10, 10))
ncr.plot(ax=ax, alpha=0.8, color='black')
gdf.plot(ax=ax,color='firebrick',markersize=2)
hospital.plot(ax=ax,color='yellow',markersize=5)
for i in hospital.index:
    cx = hospital.loc[i]['way'].xy[0][0]
    cy = hospital.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.2, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

hospital1 = hospital.copy()
hospital1['way'] = hospital1['way'].buffer(radius)
gdf_ncr = gdf.copy()

hospital2 = hospital1.copy()
count_list = []
for i in hospital1.index:
    point = sjoin(gdf_ncr, hospital1.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
hospital2['accident_count'] = count_list

"""## Quezon City

### Police
"""

# Check which coverage will cover all accidents
radius = 0.035

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'police' AND p.name IS NOT NULL AND g.name_2 = 'Quezon City'
'''

police_qc = gpd.read_postgis(q, con=conn, geom_col='way')

qc_shp = gpd.read_postgis(
'''
SELECT *
FROM gadm.ph_brgy
WHERE name_2 = 'Quezon City'
'''
,con = conn, geom_col ='geom'
)

qc = qc_shp[['name_2', 'name_3', 'geom']]
qc

pointInPolys2 = sjoin(gdf, qc, how='left')
gdf_qc = pointInPolys2.dropna()

fig, ax = plt.subplots(figsize=(10, 10))
qc.plot(ax=ax, alpha=0.8, color='black')
gdf_qc.plot(ax=ax,color='firebrick',markersize=2, alpha=0.6)
police_qc.plot(ax=ax,color='cornflowerblue',markersize=5)
for i in police_qc.index:
    cx = police_qc.loc[i]['way'].xy[0][0]
    cy = police_qc.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.15, color='cornflowerblue')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

police_qc1 = police_qc.copy()
police_qc1['way'] = police_qc1['way'].buffer(radius)
gdf_qc1 = gdf.loc[gdf.City == 'Quezon City']
police_qc2 = police_qc1.copy()

count_list = []
for i in police_qc2.index:
    point = sjoin(gdf_qc1, police_qc2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police_qc2['accident_count'] = count_list
police_qc2

radius = 0.025

qc_shp = gpd.read_postgis(
'''
SELECT *
FROM gadm.ph_brgy
WHERE name_2 = 'Quezon City'
'''
,con = conn, geom_col ='geom'
)

qc = qc_shp[['name_2', 'name_3', 'geom']]
qc

pointInPolys2 = sjoin(gdf, qc, how='left')
gdf_qc = pointInPolys2.dropna()

police_qc1 = police_qc.copy()
police_qc1['way'] = police_qc1['way'].buffer(radius)
gdf_qc1 = gdf.loc[gdf.City == 'Quezon City']
police_qc2 = police_qc1.copy()

count_list = []
for i in police_qc2.index:
    point = sjoin(gdf_qc1, police_qc2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police_qc2['accident_count'] = count_list

police_qc2 = police_qc1.copy()
gdf_qc2 = gdf_qc1.copy()

for i in police_qc2.index:
    point = sjoin(gdf_qc1, police_qc2.loc[[i]], how='left')
    count = point.dropna()
    mask = gdf_qc2[gdf_qc2.index.isin(count.index)].index
    gdf_qc2 = gdf_qc2.drop(index=mask)

fig, ax = plt.subplots(figsize=(10, 10))
qc.plot(ax=ax, alpha=0.8, color='black')
gdf_qc2.plot(ax=ax, color='firebrick', markersize=2)
ax.set_axis_off()
plt.show()

pointInPolys2 = sjoin(gdf, qc, how='left')
gdf_qc = pointInPolys2.dropna()

police_qc1 = police_qc.copy()
police_qc1['way'] = police_qc1['way'].buffer(radius)
gdf_qc1 = gdf.loc[gdf.City == 'Quezon City']

add_police = gpd.GeoDataFrame(pd.DataFrame({'name_2':['Quezon City'],
                'amenity':['police'],
                'name':['Proposed Police Station 1'],
                  'way': [Point(121.070271, 14.664651).buffer(radius)]}),
                              geometry='way')
# 14.664651, 121.070271

police_qc2 = gpd.GeoDataFrame(pd.concat([police_qc1, add_police],
                                        ignore_index=True), geometry='way')

count_list = []
for i in police_qc2.index:
    point = sjoin(gdf_qc1, police_qc2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police_qc2['accident_count'] = count_list

fig, ax = plt.subplots(figsize=(10, 10))
qc.plot(ax=ax, alpha=0.8, color='black')
gdf_qc1.plot(ax=ax,color='firebrick',markersize=2)
police_qc1.plot(ax=ax,color='cornflowerblue', alpha=0.2)
add_police.plot(ax=ax,color='yellow', alpha=0.2)
ax.set_axis_off()
plt.show()

gdf_qc1

police_qc2

qc

point = sjoin(qc, add_police, how='left')
count = point.dropna()

point1 = sjoin(gdf_qc1, add_police, how='left')
count1 = point1.dropna()

fig, ax = plt.subplots(figsize=(10, 10))
count.plot(ax=ax, alpha=0.8, color='black')
count1.plot(ax=ax,color='firebrick',markersize=2)
add_police.plot(ax=ax,color='yellow', alpha=0.2)
ax.set_axis_off()
plt.show()

import osmnx as ox
import sqlite3
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import networkx as nx

ox.config(log_file=True, log_console=True, use_cache=True)

fig, ax = plt.subplots(figsize=(10, 10))
police_x = ox.graph_from_point([14.661660, 121.070399], dist=2000, network_type='drive', simplify=False)
edge_color = ox.plot.get_edge_colors_by_attr(police_x, attr = 'length')
count1.plot(ax=ax,color='firebrick', markersize=10)
ox.plot_graph(police_x, edge_color=edge_color, node_size=0, ax=ax)
plt.show()

count_list = []
for i in police_qc2.index:
    point = sjoin(gdf_qc1, add_police.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)

"""### Hospital"""

radius = 0.04

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'hospital' AND p.name IS NOT NULL AND g.name_2 = 'Quezon City'
'''

hospital_qc = gpd.read_postgis(q, con=conn, geom_col='way')

pointInPolys2 = sjoin(gdf, qc, how='left')
gdf_qc = pointInPolys2.dropna()

fig, ax = plt.subplots(figsize=(10, 10))
qc.plot(ax=ax, alpha=0.8, color='black')
gdf_qc.plot(ax=ax,color='firebrick',markersize=2)
hospital_qc.plot(ax=ax,color='cornflowerblue',markersize=5)
for i in hospital_qc.index:
    cx = hospital_qc.loc[i]['way'].xy[0][0]
    cy = hospital_qc.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.2, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

pointInPolys2 = sjoin(gdf, qc, how='left')
gdf_qc = pointInPolys2.dropna()

hospital_qc1 = hospital_qc.copy()
hospital_qc1['way'] = hospital_qc1['way'].buffer(radius)
gdf_qc1 = gdf.loc[gdf.City == 'Quezon City']

add_hospital = gpd.GeoDataFrame(pd.DataFrame({'name_2':['Quezon City'],
                'amenity':['hospital'],
                'name':['Proposed Hospital 1'],
                  'way': [Point(121.07935, 14.60144).buffer(radius)]}),
                              geometry='way')

hospital_qc2 = gpd.GeoDataFrame(pd.concat([hospital_qc1, add_hospital],
                                        ignore_index=True), geometry='way')

count_list = []
for i in hospital_qc2.index:
    point = sjoin(gdf_qc1, hospital_qc2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
hospital_qc2['accident_count'] = count_list

fig, ax = plt.subplots(figsize=(10, 10))
qc.plot(ax=ax, alpha=0.8, color='black')
gdf_qc1.plot(ax=ax,color='firebrick',markersize=2)
hospital_qc1.plot(ax=ax,color='cornflowerblue', alpha=0.2)
add_hospital.plot(ax=ax,color='yellow', alpha=0.2)
ax.set_axis_off()
plt.show()

"""## Mandaluyong

### Police
"""

# Check which coverage will cover all accidents
radius = 0.01

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'police' AND p.name IS NOT NULL AND g.name_2 = 'Mandaluyong'
'''

police_manda = gpd.read_postgis(q, con=conn, geom_col='way')

manda_shp = gpd.read_postgis(
'''
SELECT *
FROM gadm.ph_brgy
WHERE name_2 = 'Mandaluyong'
'''
,con = conn, geom_col ='geom'
)

manda = manda_shp[['name_2', 'name_3', 'geom']]

pointInPolys2 = sjoin(gdf, manda, how='left')
gdf_manda = pointInPolys2.dropna()

fig, ax = plt.subplots(figsize=(10, 10))
manda.plot(ax=ax, alpha=0.8, color='black')
gdf_manda.plot(ax=ax,color='firebrick',markersize=2)
police_manda.plot(ax=ax,color='cornflowerblue',markersize=5)
for i in police_manda.index:
    cx = police_manda.loc[i]['way'].xy[0][0]
    cy = police_manda.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.3, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

police_manda1 = police_manda.copy()
police_manda1['way'] = police_manda1['way'].buffer(radius)
gdf_manda1 = gdf.loc[gdf.City == 'Mandaluyong']

count_list = []
for i in police_manda1.index:
    point = sjoin(gdf_manda1, police_manda1.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police_manda1['accident_count'] = count_list
police_manda1

pointInPolys2 = sjoin(gdf, manda, how='left')
gdf_manda = pointInPolys2.dropna()

police_manda1 = police_manda.copy()
police_manda1['way'] = police_manda1['way'].buffer(radius)
gdf_manda1 = gdf.loc[gdf.City == 'Mandaluyong']

add_police = gpd.GeoDataFrame(pd.DataFrame({'name_2':['Mandaluyong'],
                'amenity':['police'],
                'name':['Proposed Police Station 1'],
                  'way': [Point(121.04841, 14.57245).buffer(radius)]}), geometry='way')

police_manda2 = gpd.GeoDataFrame(pd.concat([police_manda1, add_police],
                                           ignore_index=True), geometry='way')

count_list = []
for i in police_manda2.index:
    point = sjoin(gdf_manda1, police_manda2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police_manda2['accident_count'] = count_list

fig, ax = plt.subplots(figsize=(10, 10))
manda.plot(ax=ax, alpha=0.8, color='black')
gdf_manda1.plot(ax=ax,color='firebrick',markersize=2)
police_manda1.plot(ax=ax,color='cornflowerblue', alpha=0.2)
add_police.plot(ax=ax,color='yellow', alpha=0.2)
ax.set_axis_off()
plt.show()

"""### Hospital"""

# Check which coverage will cover all accidents
radius = 0.03

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'hospital' AND p.name IS NOT NULL AND g.name_2 = 'Mandaluyong'
'''

hospital_manda = gpd.read_postgis(q, con=conn, geom_col='way')

pointInPolys2 = sjoin(gdf, manda, how='left')
gdf_manda = pointInPolys2.dropna()

fig, ax = plt.subplots(figsize=(10, 10))
manda.plot(ax=ax, alpha=0.8, color='black')
gdf_manda.plot(ax=ax,color='firebrick',markersize=2)
hospital_manda.plot(ax=ax,color='cornflowerblue',markersize=5)
for i in hospital_manda.index:
    cx = hospital_manda.loc[i]['way'].xy[0][0]
    cy = hospital_manda.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.2, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

pointInPolys2 = sjoin(gdf, manda, how='left')
gdf_manda = pointInPolys2.dropna()

hospital_manda1 = hospital_manda.copy()
hospital_manda1['way'] = hospital_manda1['way'].buffer(radius)
gdf_manda1 = gdf.loc[gdf.City == 'Mandaluyong']

add_hospital = gpd.GeoDataFrame(pd.DataFrame({'name_2':['Mandaluyong'],
                'amenity':['hospital'],
                'name':['Proposed Hospital 1'],
                  'way': [Point(121.05538, 14.59545).buffer(radius)]}),
                              geometry='way')

hospital_manda2 = gpd.GeoDataFrame(pd.concat([hospital_manda1, add_hospital],
                                        ignore_index=True), geometry='way')

count_list = []
for i in hospital_manda2.index:
    point = sjoin(gdf_manda1, hospital_manda2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
hospital_manda2['accident_count'] = count_list

fig, ax = plt.subplots(figsize=(10, 10))
manda.plot(ax=ax, alpha=0.8, color='black')
gdf_manda1.plot(ax=ax,color='firebrick',markersize=2)
add_hospital.plot(ax=ax,color='yellow', alpha=0.2)
hospital_manda1.plot(ax=ax, color='cornflowerblue', alpha=0.2)
ax.set_axis_off()
plt.show()

"""## Makati

### Police
"""

# Check which coverage will cover all accidents
radius = 0.02

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'police' AND p.name IS NOT NULL AND g.name_2 = 'Makati City'
'''

police_makati = gpd.read_postgis(q, con=conn, geom_col='way')

makati_shp = gpd.read_postgis(
'''
SELECT *
FROM gadm.ph_brgy
WHERE name_2 = 'Makati City'
'''
,con = conn, geom_col ='geom'
)

makati = makati_shp[['name_2', 'name_3', 'geom']]

pointInPolys2 = sjoin(gdf, makati, how='left')
gdf_makati = pointInPolys2.dropna()

fig, ax = plt.subplots(figsize=(10, 10))
makati.plot(ax=ax, alpha=0.8, color='black')
gdf_makati.plot(ax=ax,color='firebrick',markersize=2)
police_makati.plot(ax=ax,color='cornflowerblue',markersize=5)
for i in police_makati.index:
    cx = police_makati.loc[i]['way'].xy[0][0]
    cy = police_makati.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.3, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

police_makati1 = police_makati.copy()
police_makati1['way'] = police_makati1['way'].buffer(radius)
gdf_makati1 = gdf.loc[gdf.City == 'Makati City']

count_list = []
for i in police_makati1.index:
    point = sjoin(gdf_makati1, police_makati1.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police_makati1['accident_count'] = count_list
police_makati1

pointInPolys2 = sjoin(gdf, makati, how='left')
gdf_makati = pointInPolys2.dropna()

police_makati1 = police_makati.copy()
police_makati1['way'] = police_makati1['way'].buffer(radius)
gdf_makati1 = gdf.loc[gdf.City == 'Makati City']

add_police = gpd.GeoDataFrame(pd.DataFrame({'name_2':['Makati City', 'Makati City'],
                'amenity':['police', 'police'],
                'name':['Proposed Police Station 1', 'Proposed Police Station 2'],
                  'way': [Point(121.05755, 14.54972).buffer(radius),
                          Point(121.02611, 14.54753).buffer(radius)]}), geometry='way')

police_makati2 = gpd.GeoDataFrame(pd.concat([police_makati1, add_police],
                                           ignore_index=True), geometry='way')

count_list = []
for i in police_makati2.index:
    point = sjoin(gdf_makati1, police_makati2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
police_makati2['accident_count'] = count_list

fig, ax = plt.subplots(figsize=(10, 10))
makati.plot(ax=ax, alpha=0.8, color='black')
gdf_makati1.plot(ax=ax,color='firebrick',markersize=2)
police_makati1.plot(ax=ax,color='cornflowerblue', alpha=0.2)
add_police.plot(ax=ax,color='yellow', alpha=0.2)
ax.set_axis_off()
plt.show()

"""### Hospital"""

# Check which coverage will cover all accidents
radius = 0.042

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'hospital' AND p.name IS NOT NULL AND g.name_2 = 'Makati City'
'''

hospital_makati = gpd.read_postgis(q, con=conn, geom_col='way')

pointInPolys2 = sjoin(gdf, makati, how='left')
gdf_makati = pointInPolys2.dropna()

fig, ax = plt.subplots(figsize=(10, 10))
makati.plot(ax=ax, alpha=0.8, color='black')
gdf_makati.plot(ax=ax,color='firebrick',markersize=2)
hospital_makati.plot(ax=ax,color='cornflowerblue',markersize=5)
for i in hospital_makati.index:
    cx = hospital_makati.loc[i]['way'].xy[0][0]
    cy = hospital_makati.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.2, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

pointInPolys2 = sjoin(gdf, makati, how='left')
gdf_makati = pointInPolys2.dropna()

hospital_makati1 = hospital_makati.copy()
hospital_makati1['way'] = hospital_makati1['way'].buffer(radius)
gdf_makati1 = gdf.loc[gdf.City == 'Makati City']

# Add hospital location
add_hospital = gpd.GeoDataFrame(pd.DataFrame({'name_2':['Makati City'],
                'amenity':['hospital'],
                'name':['Proposed Hospital 1'],
                  'way': [Point(121.05380, 14.53798).buffer(radius)]}),
                              geometry='way')

hospital_makati2 = gpd.GeoDataFrame(pd.concat([hospital_makati1, add_hospital],
                                        ignore_index=True), geometry='way')

count_list = []
for i in hospital_makati2.index:
    point = sjoin(gdf_makati1, hospital_makati2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
hospital_makati2['accident_count'] = count_list

fig, ax = plt.subplots(figsize=(10, 10))
makati.plot(ax=ax, alpha=0.8, color='black')
gdf_makati1.plot(ax=ax,color='firebrick',markersize=2)
add_hospital.plot(ax=ax,color='yellow', alpha=0.2)
hospital_makati1.plot(ax=ax, color='cornflowerblue', alpha=0.2)
ax.set_axis_off()
plt.show()

"""## NCR Hospital"""

radius = 0.03

q = '''
SELECT g.name_2, p.amenity, p.name, p.way
FROM ph_point as p
JOIN gadm.ph_brgy as g ON st_within(p.way, g.geom)
WHERE p.amenity ~* 'hospital' AND p.name IS NOT NULL AND g.name_1 = 'Metropolitan Manila'
'''

hospital = gpd.read_postgis(q, con=conn, geom_col='way')

fig, ax = plt.subplots(figsize=(10, 10))
ncr.plot(ax=ax, alpha=0.8, color='black')
gdf.plot(ax=ax,color='firebrick',markersize=2)
hospital.plot(ax=ax,color='yellow',markersize=5)
for i in hospital.index:
    cx = hospital.loc[i]['way'].xy[0][0]
    cy = hospital.loc[i]['way'].xy[1][0]
    circle = plt.Circle((cx, cy), radius, alpha=0.2, color='gray')
    ax.add_patch(circle)
ax.set_axis_off()

plt.show()

hospital1 = hospital.copy()
hospital1['way'] = hospital1['way'].buffer(radius)
gdf_ncr = gdf.copy()

hospital2 = hospital1.copy()
count_list = []
for i in hospital1.index:
    point = sjoin(gdf_ncr, hospital1.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
hospital2['accident_count'] = count_list

# Choose best coverage
radius = 0.02

hospital1 = hospital.copy()
hospital1['way'] = hospital1['way'].buffer(radius)
gdf_ncr1 = gdf.copy()
hospital2 = hospital1.copy()

count_list = []
for i in hospital2.index:
    point = sjoin(gdf_ncr1, hospital2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
hospital2['accident_count'] = count_list

hospital2 = hospital1.copy()
gdf_ncr2 = gdf_ncr1.copy()

for i in hospital2.index:
    point = sjoin(gdf_ncr1, hospital2.loc[[i]], how='left')
    count = point.dropna()
    mask = gdf_ncr2[gdf_ncr2.index.isin(count.index)].index
    gdf_ncr2 = gdf_ncr2.drop(index=mask)

fig, ax = plt.subplots(figsize=(10, 10))
ncr.plot(ax=ax, alpha=0.8, color='black')
gdf_ncr2.plot(ax=ax, color='firebrick', markersize=2)
ax.set_axis_off()
plt.show()

hospital1 = hospital.copy()
hospital1['way'] = hospital1['way'].buffer(radius)

# Add hospital location
add_hospital = gpd.GeoDataFrame(pd.DataFrame({'name_2':['San Juan'],
                'amenity':['hospital'],
                'name':['Proposed Hospital 1'],
                  'way': [Point(121.047888, 14.601078).buffer(radius)]}),
                              geometry='way')

hospital2 = gpd.GeoDataFrame(pd.concat([hospital1, add_hospital],
                                        ignore_index=True), geometry='way')

count_list = []
for i in hospital2.index:
    point = sjoin(gdf, hospital2.loc[[i]], how='left')
    count = point.dropna().shape[0]
    count_list.append(count)
hospital2['accident_count'] = count_list

fig, ax = plt.subplots(figsize=(10, 10))
ncr.plot(ax=ax, alpha=0.8, color='black')
gdf_ncr.plot(ax=ax,color='firebrick',markersize=2)
add_hospital.plot(ax=ax,color='yellow', alpha=0.2)
hospital1.plot(ax=ax, color='cornflowerblue', alpha=0.1)
ax.set_axis_off()
plt.show()