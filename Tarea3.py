#!/usr/bin/env python
# coding: utf-8

# In[93]:


#!/usr/bin/env python
# coding: utf-8
# Autor: Ashuin Sharma (A35029)
# Tarea 3.

import os
import requests
import zipfile
import csv
import fiona
import fiona.crs
from shapely.geometry import Point, mapping, shape
from owslib.wfs import WebFeatureService
from geojson import dump
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
get_ipython().run_line_magic('matplotlib', 'inline')
import folium
import plotly.express as px


# In[1]:


print("Descargando capas de cantones y vias..")
# Cargamos la capa de Cantones 1:5mil del SNIT
wfs = WebFeatureService(url='https://geos.snitcr.go.cr/be/IGN_5/wfs', version='1.1.0')
list(wfs.contents)

# Solicitud de capa WFS de Limite Cantonal mediante GET, para retornarse como JSON
# Parámetros de la solicitud
params = dict(service='WFS',
              version='1.1.0', 
              request='GetFeature', 
              typeName='IGN_5:limitecantonal_5k',
              srsName='urn:ogc:def:crs:EPSG::5367',
              outputFormat='json')

# Solicitud
response = requests.get("https://geos.snitcr.go.cr/be/IGN_5/wfs", params=params)

# Descarga de la respuesta en un archivo GeoJSON en cantones.geojson
with open('cantones.geojson', 'w') as file:
   dump(response.json(), file)

# Cargamos la capa de Red Vial 1:200mil del SNIT
wfs = WebFeatureService(url='https://geos.snitcr.go.cr/be/IGN_200/wfs', version='1.1.0')
list(wfs.contents)

# Solicitud de capa WFS de Limite Cantonal mediante GET, para retornarse como JSON
# Parámetros de la solicitud
params = dict(service='WFS',
              version='1.1.0', 
              request='GetFeature', 
              typeName='IGN_200:redvial_200k',
              srsName='urn:ogc:def:crs:EPSG::5367',
              outputFormat='json')

# Solicitud
response = requests.get("https://geos.snitcr.go.cr/be/IGN_200/wfs", params=params)

# Descarga de la respuesta en un archivo GeoJSON en redvial.geojson
with open('redvial.geojson', 'w') as file:
   dump(response.json(), file)

print("Creando archivo GPKG...")
# Creacion del Archivo GeoPackage
# Agregamos capa Cantones al GPKG
with fiona.open('cantones.geojson') as source:
    with fiona.open('densidad-vial.gpkg', 'w', 'GPKG', source.schema, source.crs, layer='cantones') as sink:
        for record in source:
            sink.write(record)

# Agregamos capa Red Vial al GPKG
with fiona.open('redvial.geojson') as source:
    with fiona.open('densidad-vial.gpkg', 'w', 'GPKG', source.schema, source.crs, layer='redvial') as sink:
        for record in source:
            sink.write(record)

# Conteo de longitud de red vial sobre geometria del Canton
# Esquema de la capa con el area del canton, longitud de red vial y densidad
schema = {'geometry':'Unknown',
          'properties':{
                        'rowid':'int',
                        'cod_canton':'int',
                        'canton':'str',
                        'calc_area':'float',
                        'calc_longitud':'float',
                        'calc_densidad_vial':'float',
                        'calc_longitud_autopistas':'float',
                        'calc_longitud_carr_pav_2_vias':'float',
                        'calc_longitud_carr_pav_1_vias':'float',
                        'calc_longitud_carr_nopav_2_vias':'float',
                        'calc_longitud_caminos_tierra':'float',
                       }}

# Recorremos los cantones
print("Calculando areas, longitudes e interescciones...")
with fiona.collection('densidad-vial.gpkg', 'r', layer='cantones') as cant:
    i = 1 # contador de Cantones, para imprimir el progreso del procedimiento
    # Creamos geojson de capa generada con atributos calculados
    with fiona.open('redvial-cantones.geojson','w','GeoJSON', schema, cant.crs) as sink:
        # Por cada Canton calculamos area, interseccion con vias, y la densidad
        for record_cant in cant:
            calc_area =  shape(record_cant['geometry']).area / 1000000
            cod_canton = record_cant['properties']['cod_canton']
            canton = record_cant['properties']['canton']
            calc_longitud = 0.0 # acumulador de longitud vial en el canton
            # Calculos adicionales de longitud
            calc_longitud_autopistas = 0.0 # acumulador de longitud autopistas
            calc_longitud_carr_pav_2_vias = 0.0 # acumulador longitud carreteras con pavimento a 2 o mas vias
            calc_longitud_carr_pav_1_vias = 0.0 # acumulador longitud carretaras con pavimento a 1 via
            calc_longitud_carr_nopav_2_vias = 0.0 # acumulador longitud carreteras sin pavimento a 2 vias
            calc_longitud_caminos_tierra = 0.0 # acumulador de longitud caminos de tierra
            # Calculamos la interseccion y la densidad para el canton
            with fiona.collection('densidad-vial.gpkg', 'r', layer='redvial') as redvial:    
                for registro_red in redvial:
                    intersection = shape(record_cant['geometry']).intersection(shape(registro_red['geometry']))
                    calc_longitud += intersection.length
                    categoria = registro_red['properties']['categoria']
                    match categoria:
                        case "AUTOPISTA":
                            calc_longitud_autopistas += intersection.length
                        case "CARRETERA PAVIMENTO DOS VIAS O MAS":
                            calc_longitud_carr_pav_2_vias += intersection.length
                        case "CARRETERA PAVIMENTO UNA VIA":
                            calc_longitud_carr_pav_1_vias += intersection.length
                        case "CARRETERA SIN PAVIMENTO DOS VIAS":
                            calc_longitud_carr_nopav_2_vias += intersection.length
                        case "CAMINO DE TIERRA":
                            calc_longitud_caminos_tierra += intersection.length
                        case _:
                            continue
                            
            calc_longitud = calc_longitud / 1000
            densidad = calc_longitud / calc_area
            print(i, cod_canton, canton, calc_area, calc_longitud, densidad)
            # Escribimos el archivo geojson
            sink.write({
                'properties': {
                    'rowid':i,
                    'cod_canton':cod_canton,
                    'canton':canton,
                    'calc_area':calc_area,
                    'calc_longitud':calc_longitud,
                    'calc_densidad_vial':densidad,
                    'calc_longitud_autopistas':calc_longitud_autopistas / 1000,
                    'calc_longitud_carr_pav_2_vias':calc_longitud_carr_pav_2_vias / 1000,
                    'calc_longitud_carr_pav_1_vias':calc_longitud_carr_pav_1_vias / 1000,
                    'calc_longitud_carr_nopav_2_vias':calc_longitud_carr_nopav_2_vias / 1000,
                    'calc_longitud_caminos_tierra':calc_longitud_caminos_tierra / 1000
                },
                'geometry':record_cant['geometry']
            }) 
            i += 1

# Ultimo paso. Se agrega el archivo GeoJSON de redvial-cantones al GPKG
print("Salvando archivo GPKG...")
with fiona.open('redvial-cantones.geojson') as source:
    with fiona.open('densidad-vial.gpkg', 'w', 'GPKG', source.schema, source.crs, layer='redvial-cantones') as sink:
        for record in source:
            sink.write(record)
#Fin.


# # 1. Tabla de cantones

# In[86]:


# Tarea 3. Item 1. 
# Tabla de Cantones

# Acumulador de la suma de la longitud de todas las vias del pais.
total_longitud = 0

print("Item 1. Tabla de Cantones.")
i = 0
list = []
# Leemos la capa que creamos en la celda anterior, que contiene todos los valores
# calculados y cada fila se convertira en una Serie que se agregara en una List
# que a su vez se utilizará para crear el DataFrame.
with fiona.collection('densidad-vial.gpkg', 'r', layer='redvial-cantones') as cant:
    for record_cant in cant:
        cod_canton = record_cant['properties']['cod_canton']
        canton = record_cant['properties']['canton']
        calc_longitud = record_cant['properties']['calc_longitud']
        total_longitud += calc_longitud
        densidad = record_cant['properties']['calc_densidad_vial']
        # Calculos adicionales de longitud
        calc_longitud_autopistas = record_cant['properties']['calc_longitud_autopistas']
        calc_longitud_carr_pav_2_vias = record_cant['properties']['calc_longitud_carr_pav_2_vias']
        calc_longitud_carr_pav_1_vias = record_cant['properties']['calc_longitud_carr_pav_1_vias']
        calc_longitud_carr_nopav_2_vias = record_cant['properties']['calc_longitud_carr_nopav_2_vias']
        calc_longitud_caminos_tierra = record_cant['properties']['calc_longitud_caminos_tierra']
        s1 = pd.Series([cod_canton, canton, calc_longitud, densidad, calc_longitud_autopistas, calc_longitud_carr_pav_2_vias,
                           calc_longitud_carr_pav_1_vias, calc_longitud_carr_nopav_2_vias, calc_longitud_caminos_tierra],
                      index = ["cod_canton","Canton", "Longitud Total", "Densidad Total", "Autopistas", "Pav 2 vias",  "Pav 1 via", "Sin Pav 2 vias", "Caminos Tierra"])
        list.append(s1)
tabla_cant = pd.DataFrame(list)
tabla_cant


# # 2. Top 15 Cantones

# In[42]:


# Instanciamos el gráfico de plotly y definios X como Cantón , Y como Longitud.
# Y los colores los definirán las 5 categorias de vía.

# Dataframe filtrado con los top 15 cantones como mayor red vial, para usar en graficación
tabla_cant_grafico = tabla_cant.sort_values("Longitud Total", ascending=[False]).head(15)

fig = px.bar(tabla_cant_grafico, 
             x='Canton', 
             y=["Autopistas", "Pav 2 vias",  "Pav 1 via", "Sin Pav 2 vias", "Caminos Tierra"], 
             title="Top 15 cantones con mayor longitud total de red vial (tipo de vía).",
             labels={
                "value": "Longitud vial (Km)", "variable": "Tipos de vía", "Canton" : "Cantón"
            })

fig.show()


# # 3. Gráfico de Pastel. Distribución Total de Red Vial por Cantones.

# In[63]:


# Dataframe filtrado con los top 15 cantones como mayor red vial, para usar en graficación
tabla_cant_filtro = tabla_cant.sort_values("Longitud Total", ascending=[False]).head(15)

# Obtengo el valor del ultimo canton
nth_row = 14
tabla_cant_filtro = tabla_cant_filtro.iloc[nth_row]
ultimo = tabla_cant_filtro["Longitud Total"]

# Ahora traigo todos pero ordenados y modifico la variable canton de los menores al 15vo.
tabla_cant_pie = tabla_cant.sort_values("Longitud Total", ascending=[False])
tabla_cant_pie.loc[tabla_cant_pie['Longitud Total'] < ultimo, 'Canton'] = 'Otros'

# Creacion del Pie Chart
fig = px.pie(tabla_cant_pie, values='Longitud Total', names='Canton', title='Gráfico de Pastel. Distribución Total de Red Vial por Cantones.')
fig.show()


# ## 4. Mapa de coropletas Densidad Vial de Costa Rica.

# In[109]:


# Carga de registros de Cantones en un dataframe de pandas
cantones = gpd.read_file("cantones.geojson")
cantones

# Carga de registros de RedVial en un dataframe de pandas
redvial = gpd.read_file("redvial.geojson")
redvial

# Creación del mapa base
m = folium.Map(location=[9.8, -84], 
               tiles='CartoDB positron',
               control_scale=True,
               zoom_start=8)

folium.Choropleth(
    name="Densidad Vial",
    geo_data=cantones,
    data=tabla_cant,
    columns=['cod_canton', 'Densidad Total'],
    bins=7,
    key_on='feature.properties.cod_canton',
    fill_color='Reds', 
    fill_opacity=0.8, 
    line_opacity=1,
    legend_name='Densidad vial por cantón',
    width=800, height=700,
    smooth_factor=0).add_to(m)

# Añadir capa de Red Vial
folium.GeoJson(data=redvial, name='Red vial').add_to(m)

# Control de capas
folium.LayerControl().add_to(m)

# Despliegue del mapa
m


# In[ ]:




