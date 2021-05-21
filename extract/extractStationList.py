import os
import re
import zipfile
from os.path import join as pjoin, basename, dirname
import geopandas as gpd
import pandas as pd

import matplotlib.pyplot as plt
import cartopy.crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import cartopy.feature as cfeature

dataPath = "X:/georisk/HaRIA_B_Wind/data/raw/from_bom/1-minute"
tempPath = "C:/WorkSpace/temp"
ziplist = os.listdir(dataPath)
pattern = re.compile(".*StnDet.*\.txt")

stnfiles = []
for z in ziplist:
    filename = pjoin(dataPath, z)
    if zipfile.is_zipfile(filename):
        zz = zipfile.ZipFile(filename)
        filelist = zz.namelist()
        for f in filelist:
            if pattern.match(f):
                stnfiles.append(zz.extract(f, path=tempPath))


dflist = []
colnames = ["id", 'stnNum', 'rainfalldist', 'stnName', 'stnOpen', 'stnClose',
            'stnLat', 'stnLon', 'stnLoc', 'stnState', 'stnElev', 'stnBarmoeterElev',
            'stnWMOIndex', 'stnDataStartYear', 'stnDataEndYear',
            'pctComplete', 'pctY', 'pctN', 'pctW', 'pctS', 'pctI']
for f in stnfiles:
    print(f"Loading data from {f}")
    df = pd.read_csv(f, sep=',', index_col=False, names=colnames, keep_default_na=False)
    dflist.append(df)

fulldf = pd.concat(dflist, ignore_index=True)

gdf = gpd.GeoDataFrame(fulldf, geometry=gpd.points_from_xy(fulldf.stnLon, fulldf.stnLat, crs="EPSG:7844"))
gdf.to_file(pjoin(tempPath, "stationlist.shp"))
gdf.to_file(pjoin(tempPath, "stationlist.json"), driver='GeoJSON')

states = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='10m',
        facecolor='none')

ax = plt.axes(projection=ccrs.PlateCarree())
ax.figure.set_size_inches(15,10)
gdf.plot(ax=ax, marker='o', color='red', markersize=15, alpha=0.75, edgecolor='white', zorder=1)
ax.coastlines(resolution='10m')
ax.add_feature(states, edgecolor='0.15', linestyle='--')
gl = ax.gridlines(draw_labels=True, linestyle=":")
gl.top_labels = False
gl.right_labels = False
ax.set_extent([105, 160, -45, -5])
ax.set_aspect('equal')
plt.savefig(pjoin(tempPath, "aws_stations.png"), bbox_inches='tight')
