"""
Convert storm data to geospatial data and plot rates of occurrence, proportion
of storm types, etc. on maps

"""
from os.path import join as pjoin
from datetime import datetime
import pandas as pd
from stndata import ONEMINUTESTNNAMES
import geopandas as gpd

from cartopy import crs as ccrs
import matplotlib.pyplot as plt
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import cartopy.feature as cfeature

BASEDIR = r"X:\georisk\HaRIA_B_Wind\data\derived\obs\1-minute\events"
OUTPUTPATH = pjoin(BASEDIR, "results")
df = pd.read_pickle(pjoin(OUTPUTPATH, "stormclass.pkl"))
allstnfile = r"X:\georisk\HaRIA_B_Wind\data\raw\from_bom\2022\1-minute\HD01D_StationDetails.txt"
allstndf = pd.read_csv(allstnfile, sep=',', index_col='stnNum',
                       names=ONEMINUTESTNNAMES,
                       keep_default_na=False,
                       converters={
                            'stnName': str.strip,
                            'stnState': str.strip
                        })

states = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='10m',
        facecolor='none')

stormclasses = ["Synoptic storm", "Synoptic front",
                "Storm-burst", "Thunderstorm",
                "Front up", "Front down",
                "Spike", "Unclassified"]

groupdf = (df.reset_index(drop=True)
           .groupby(['stnNum', 'stormType'])
           .size()
           .reset_index(name='count'))

pivotdf = groupdf.pivot_table(index='stnNum', columns='stormType',
                              values='count', fill_value=0)

fulldf = pivotdf.join(allstndf, on='stnNum', how='left')
fulldf['Convective'] = fulldf[['Thunderstorm', 'Front up', 'Front down']].sum(axis=1)
fulldf['Non-convective'] = fulldf[['Synoptic storm', 'Synoptic front', 'Storm-burst']].sum(axis=1)
fulldf['stormCount'] = fulldf[stormclasses].sum(axis=1)

pd.options.mode.copy_on_write = True

propdf = fulldf
propdf[stormclasses] = fulldf[stormclasses].div(fulldf['stormCount'], axis=0)
propdf['Convective'] = fulldf['Convective'].div(fulldf['stormCount'], axis=0)
propdf['Non-convective'] = fulldf['Non-convective'].div(fulldf['stormCount'],
                                                        axis=0)

gdf = gpd.GeoDataFrame(fulldf,
                       geometry=gpd.points_from_xy(fulldf.stnLon,
                                                   fulldf.stnLat),
                       crs='epsg:7844')

propgdf = gpd.GeoDataFrame(propdf,
                           geometry=gpd.points_from_xy(
                               propdf.stnLon, propdf.stnLat
                               ),
                           crs='epsg:7844')
gax = plt.axes(projection=ccrs.PlateCarree())
gax.figure.set_size_inches(15, 12)
propgdf.plot(column='Convective', legend=True, scheme='quantiles',
             k=7, ax=gax)

gax.coastlines(resolution='10m')
gax.add_feature(states, edgecolor='0.15', linestyle='--')
gax.set_extent([110, 160, -45, -10])
gl = gax.gridlines(draw_labels=True, linestyle=":")
gl.top_labels = False
gl.right_labels = False
gax.set_title("Convective storms")
plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}",
         transform=gax.transAxes, ha='right')
plt.savefig(pjoin(OUTPUTPATH, "convective_map.png"), bbox_inches='tight')
plt.close()

gax = plt.axes(projection=ccrs.PlateCarree())
gax.figure.set_size_inches(15, 12)
propgdf.plot(column='Non-convective', legend=True, scheme='quantiles',
             k=7, ax=gax)

gax.coastlines(resolution='10m')
gax.add_feature(states, edgecolor='0.15', linestyle='--')
gax.set_extent([110, 160, -45, -10])
gl = gax.gridlines(draw_labels=True, linestyle=":")
gl.top_labels = False
gl.right_labels = False
gax.set_title("Non-convective storms")
plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}",
         transform=gax.transAxes, ha='right')
plt.savefig(pjoin(OUTPUTPATH, "nonconvective_map.png"), bbox_inches='tight')
plt.close()
