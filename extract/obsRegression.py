import os
import re
from os.path import join as pjoin

import pandas as pd
import xarray as xr
import numpy as np
import geopandas as gpd
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import statsmodels.api as sm


locator = mdates.AutoDateLocator(minticks=3, maxticks=9)
formatter = mdates.ConciseDateFormatter(locator)
obspath = "C:/WorkSpace/data/observations/wind"
obspath = "X:/georisk/HaRIA_B_Wind/data/derived/obs/1-minute/wind"
reanpath = "C:/WorkSpace/reanalysis/data/timeseries"
stationfile = "C:/WorkSpace/reanalysis/data/stationlist.shp"
outputPath = "X:/georisk/HaRIA_B_Wind/data/derived/obs/1-minute/wind/regression"

stations = gpd.read_file(stationfile)
stations['rsq'] = 0
stations['m'] = 0
stations['b'] = 0
stations['mciu'] = 0
stations['mcil'] = 0
stations['bciu'] = 0
stations['bcil'] = 0
stations['nobs'] = 0


obsfilelist = os.listdir(obspath)
reanfilelist = os.listdir(reanpath)
for idx, stn in stations.iterrows():
    station = stn.stnNum
    stationName = stn.stnName
    print(f"Processing {station} ({stationName})")
    r = re.compile(rf".*{station:06d}.*")
    s = re.compile(rf".*{station}.*")
    obsfile = list(filter(r.match, obsfilelist))[0]
    reanfile = list(filter(s.match, reanfilelist))[0]

    obsdatafile = pjoin(obspath, obsfile)
    reandatafile = pjoin(reanpath, reanfile)
    obsdf = pd.read_csv(obsdatafile)
    obsdf['date'] = pd.to_datetime(obsdf['date'])
    obsdf = obsdf[(obsdf['windgustq'] == 'Y') &
                  (obsdf['windgust'] > 0.0)]
    if len(obsdf) < (365 * 5): # minimum 5 years observations (excluding any gaps)
        stations.loc[stations.stnNum==station, 'nobs'] = len(obsdf)
        print("Insufficient observations")
        continue
    reands = xr.open_dataset(reandatafile)
    reandf = reands.i10fg.to_dataframe().reset_index()

    jointdf = obsdf.merge(reandf.rename(columns={'time':'date'}))

    jointdf['i10fg'] = jointdf['i10fg'] * 3.6

    fig, ax = plt.subplots(figsize=(12, 4))
    plt.plot(reandf.time, reandf.i10fg*3.6, alpha=0.5, label="Reanalysis")
    plt.plot(pd.to_datetime(obsdf.date), obsdf.windgust, alpha=0.5, label="Observations")
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    ax.grid(True)
    ax.legend(loc='upper left')
    ax.set_xlim(datetime(2000, 1, 1), datetime(2021, 4, 30))
    ax.set_title(f"Observed and reanalysis daily maximum wind gust - station {station}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Gust wind speed [km/h]")
    plt.savefig(pjoin(outputPath, f"ts.{station:06d}.png"), bbox_inches='tight')
    plt.close(fig)
    ax = sns.lmplot(data=jointdf, x='windgust', y='i10fg', scatter_kws={'alpha':0.25})
    x_fit = sm.add_constant(jointdf.windgust)
    fit = sm.OLS(jointdf.i10fg, x_fit).fit()
    ci = fit.conf_int()
    plt.plot(np.arange(0, 160), np.arange(0, 160), ls='--', color='k')
    ax.set_axis_labels('Observed wind gusts [km/h]', 'Reanalysis wind gusts [km/h]')
    ax.ax.set_title(f"{stationName} ({station})")
    ax.ax.text(0.1, 0.9, rf"$R^2 = ${np.round(fit.rsquared, 4)}", transform=ax.ax.transAxes)
    ax.ax.text(0.1, 0.85, f"n = {len(obsdf)}", transform=ax.ax.transAxes)
    plt.savefig(pjoin(outputPath, f"regplot.{station:06d}.png"), bbox_inches='tight')
    stations.loc[stations.stnNum==station, 'rsq'] = fit.rsquared
    stations.loc[stations.stnNum==station, 'nobs'] = len(obsdf)
    stations.loc[stations.stnNum==station, 'm'] = fit.params.windgust
    stations.loc[stations.stnNum==station, 'b'] = fit.params.const

    # Add upper/lower confidence interval on the fitted regression line:
    stations.loc[stations.stnNum==station, 'bcil'] = ci[0].const
    stations.loc[stations.stnNum==station, 'bciu'] = ci[1].const
    stations.loc[stations.stnNum==station, 'mcil'] = ci[0].windgust
    stations.loc[stations.stnNum==station, 'mciu'] = ci[1].windgust

    plt.close()

stations.to_file(pjoin(outputPath, 'stationlist.shp'))

fields = ['m', 'b', 'rsq', 'nobs', 'stnLat', 'stnLon', 'stnElev']

# Only plot data for valid stations (nobs > 1825 [5 years])
# Plot a pairwise plot of a subset of fields to see if there's any relationship
# between (e.g.) latitude and correlation of the reanalysis & observed wind gust
# data. May lead to additional exploration.
subdf = stations[stations.nobs > (365 * 5)][fields]
g = sns.pairplot(subdf, plot_kws=dict(marker="+", linewidth=1), corner=True)
g.map_lower(sns.kdeplot, levels=5, color=".2")
plt.savefig(pjoin(outputPath, 'station_pairplot.png'), bbox_inches='tight')
