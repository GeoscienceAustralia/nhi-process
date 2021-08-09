"""
Read the objective TC reanalysis data from CSV and extract the lifetime maximum
intensity of each separate TC. 

Source:
http://www.bom.gov.au/cyclone/history/database/OTCR_alldata_final_external.csv

NOTES:
The original data downloaded includes a comments field. For some records, there
is a carriage return in the comment, which leads to blank records in the data.
Please check the data and remove these carriage returns (or the blank lines)
prior to running the script.

"""
from os.path import join as pjoin
import numpy as np
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from shapely.geometry import LineString
from shapely.geometry import box as sbox

import seaborn as sns

# From TCRM codebase
from Utilities.loadData import getSpeedBearing


DATEFMT = "%Y-%m-%d %H:%M"

def filter_tracks_domain(df, minlon=90, maxlon=180, minlat=-40, maxlat=0):
    """
    Takes a `DataFrame` and filters on the basis of whether the track interscts
    the given domain, which is specified by the minimum and maximum longitude and 
    latitude.
    
    NOTE: This assumes the tracks and bounding box are in the same geographic 
    coordinate system (i.e. generally a latitude-longitude coordinate system). 
    It will NOT support different projections (e.g. UTM data for the bounds and
    geographic for the tracks).
    
    NOTE: This doesn't work if there is only one point for the track. 
    
    :param df: :class:`pandas.DataFrame` that holds the TCLV data
    :param float minlon: minimum longitude of the bounding box
    :param float minlat: minimum latitude of the bounding box
    :param float maxlon: maximum longitude of the bounding box
    :param float maxlat: maximum latitude of the bounding box
    """
    domain = sbox(minlon, minlat, maxlon, maxlat, ccw=False)
    tracks = df.groupby('num')
    tempfilter = tracks.filter(lambda x: len(x) > 1)
    tempfilter.head()
    filterdf = tempfilter.groupby('num').filter(lambda x: LineString(zip(x['lon'], x['lat'])).intersects(domain))
    return filterdf


inputPath = "X:/georisk/HaRIA_B_Wind/data/raw/from_bom/tc"
outputPath = "X:/georisk/HaRIA_B_Wind/data/derived/tc/lmi"

inputFile = pjoin(inputPath, "Objective Tropical Cyclone Reanalysis - QC.csv")
source = "http://www.bom.gov.au/cyclone/history/database/OTCR_alldata_final_external.csv"

best = pd.read_csv(inputFile,
                   skiprows=[1],
                   usecols=[0, 1, 2, 7, 8, 11, 12, 13, 19, 52],
                   na_values=[' '],
                   parse_dates=['TM'],
                   infer_datetime_format=True)

best.rename(columns={
    'DISTURBANCE_ID':'num',
    'TM':'datetime',
    'LAT': 'lat', 'LON':'lon',
    'adj. ADT Vm (kn)':'vmax',
    'CP(CKZ(Lok R34,LokPOCI, adj. Vm),hPa)': 'pmin',
    'POCI (Lok, hPa)':'poci',
    'CENTRAL_PRES':'pmin_old',
    'MAX_WIND_SPD':'vmax_old'
                     },
            inplace=True)

best = best[best.vmax.notnull()]
obstc = filter_tracks_domain(best, 90, 160, -35, -5)

obstc['deltaT'] = obstc.datetime.diff().dt.total_seconds().div(3600, fill_value=0)
idx = obstc.num.values
varidx = np.ones(len(idx))
varidx[1:][idx[1:] == idx[:-1]] = 0
speed, bearing = getSpeedBearing(varidx, obstc.lon.values, obstc.lat.values, obstc.deltaT.values)
speed[varidx==1] = 0
obstc['speed'] = speed

lmidf = obstc.loc[obstc.groupby(["num"])["vmax"].idxmax()]

lmidf['lmidt'] = pd.to_datetime(obstc.loc[obstc.groupby(["num"])["vmax"].idxmax()]['datetime'])
lmidf['lmidtyear'] = pd.DatetimeIndex(lmidf['lmidt']).year
lmidf['startdt'] = pd.to_datetime(obstc.loc[obstc.index.to_series().groupby(obstc['num']).first().reset_index(name='idx')['idx']]['datetime']).values
lmidf['lmitelapsed'] = (lmidf.lmidt - lmidf.startdt).dt.total_seconds()/3600.
lmidf['initlat'] = obstc.loc[obstc.index.to_series().groupby(obstc['num']).first().reset_index(name='idx')['idx']]['lat'].values
lmidf['initlon'] = obstc.loc[obstc.index.to_series().groupby(obstc['num']).first().reset_index(name='idx')['idx']]['lon'].values
lmidf['lmilat'] = obstc.loc[obstc.groupby(["num"])["vmax"].idxmax()]['lat']
lmidf['lmilon'] = obstc.loc[obstc.groupby(["num"])["vmax"].idxmax()]['lon']

lmidf.to_csv(pjoin(outputPath, "OTCR.lmi.csv"), index=False, date_format=DATEFMT)

# Plot distribution of LMI:
fig, ax = plt.subplots(figsize=(10, 8))
sns.histplot(lmidf.vmax, ax=ax, kde=True)
ax.set_xlabel("Maximum wind speed [kts]")
plt.text(0.0, -0.1, f"Source: {source}",
         transform=ax.transAxes, fontsize='xx-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='xx-small', ha='right')
plt.savefig(pjoin(outputPath, "lmivmax_dist.png"), bbox_inches='tight')

# Plot distribution of latitude of LMI
fig, ax = plt.subplots(figsize=(10, 8))
sns.histplot(lmidf.lmilat, ax=ax, kde=True)
ax.set_xlabel(r"Latitude of LMI [$^{\circ}$S]")
plt.text(0.0, -0.1, f"Source: {source}",
         transform=ax.transAxes, fontsize='xx-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='xx-small', ha='right')
plt.savefig(pjoin(outputPath, "lmilat_dist.png"), bbox_inches='tight')

# Plot scatter plot of latitude of LMI vs year:
fig, ax = plt.subplots(figsize=(10, 6))
sns.regplot(x='lmidtyear', y='lmilat', data=lmidf, ax=ax)
ax.grid(True)
ax.set_xlabel("Season")
ax.set_ylabel(r"Latitude of LMI [$^{\circ}$S]")
plt.text(0.0, -0.1, f"Source: {source}",
         transform=ax.transAxes, fontsize='xx-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='xx-small', ha='right')
plt.savefig(pjoin(outputPath, "lmilat_timeseries.png"), bbox_inches='tight')

# Plot scatter plot of vmax vs year:
fig, ax = plt.subplots(figsize=(10, 6))
sns.regplot(x='lmidtyear', y='vmax', data=lmidf, ax=ax)
ax.grid(True)
ax.set_xlabel("Season")
ax.set_ylabel(r"Maximum wind speed [kts]")
plt.text(0.0, -0.1, f"Source: {source}",
         transform=ax.transAxes, fontsize='xx-small', ha='left',)
plt.text(1.0, -0.1, f"Created: {datetime.now():%Y-%m-%d %H:%M}",
         transform=ax.transAxes, fontsize='xx-small', ha='right')
plt.savefig(pjoin(outputPath, "lmivmax_timeseries.png"), bbox_inches='tight')
