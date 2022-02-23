import os
import re
import gc
from os.path import join as pjoin

import pandas as pd
import xarray as xr
import numpy as np
import geopandas as gpd
from datetime import datetime
import matplotlib as mpl
mpl.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import statsmodels.api as sm

from matplotlib.projections import PolarAxes
import mpl_toolkits.axisartist.floating_axes as FA
import mpl_toolkits.axisartist.grid_finder as GF

class TaylorDiagram(object):
    """
    Taylor diagram.
    Plot model standard deviation and correlation to reference (data)
    sample in a single-quadrant polar plot, with r=stddev and
    theta=arccos(correlation).
    """

    def __init__(self, refstd,
                 fig=None, rect=111, label='_', srange=(0, 1.5), extend=False):
        """
        Set up Taylor diagram axes, i.e. single quadrant polar
        plot, using `mpl_toolkits.axisartist.floating_axes`.
        Parameters:
        * refstd: reference standard deviation to be compared to
        * fig: input Figure or None
        * rect: subplot definition
        * label: reference label
        * srange: stddev axis extension, in units of *refstd*
        * extend: extend diagram to negative correlations
        """

        from matplotlib.projections import PolarAxes
        import mpl_toolkits.axisartist.floating_axes as FA
        import mpl_toolkits.axisartist.grid_finder as GF

        self.refstd = refstd            # Reference standard deviation

        tr = PolarAxes.PolarTransform()

        # Correlation labels
        rlocs = np.array([0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1])
        if extend:
            # Diagram extended to negative correlations
            self.tmax = np.pi
            rlocs = np.concatenate((-rlocs[:0:-1], rlocs))
        else:
            # Diagram limited to positive correlations
            self.tmax = np.pi/2
        tlocs = np.arccos(rlocs)        # Conversion to polar angles
        gl1 = GF.FixedLocator(tlocs)    # Positions
        tf1 = GF.DictFormatter(dict(zip(tlocs, map(str, rlocs))))

        # Standard deviation axis extent (in units of reference stddev)
        self.smin = srange[0] * self.refstd
        self.smax = srange[1] * self.refstd

        ghelper = FA.GridHelperCurveLinear(
            tr,
            extremes=(0, self.tmax, self.smin, self.smax),
            grid_locator1=gl1, tick_formatter1=tf1)

        if fig is None:
            fig = plt.figure()

        ax = FA.FloatingSubplot(fig, rect, grid_helper=ghelper)
        fig.add_subplot(ax)

        # Adjust axes
        ax.axis["top"].set_axis_direction("bottom")   # "Angle axis"
        ax.axis["top"].toggle(ticklabels=True, label=True)
        ax.axis["top"].major_ticklabels.set_axis_direction("top")
        ax.axis["top"].label.set_axis_direction("top")
        ax.axis["top"].label.set_text("Correlation")

        ax.axis["left"].set_axis_direction("bottom")  # "X axis"
        ax.axis["left"].label.set_text("Standard deviation")

        ax.axis["right"].set_axis_direction("top")    # "Y-axis"
        ax.axis["right"].toggle(ticklabels=True)
        ax.axis["right"].major_ticklabels.set_axis_direction(
            "bottom" if extend else "left")

        if smin:
            ax.axis["bottom"].toggle(ticklabels=False, label=False)
        else:
            ax.axis["bottom"].set_visible(False)          # Unused

        self._ax = ax                   # Graphical axes
        self.ax = ax.get_aux_axes(tr)   # Polar coordinates

        # Add reference point and stddev contour
        l, = self.ax.plot([0], self.refstd, 'k*',
                          ls='', ms=10, label=label)
        t = np.linspace(0, self.tmax)
        r = np.zeros_like(t) + self.refstd
        self.ax.plot(t, r, 'k--', label='_')

        # Collect sample points for latter use (e.g. legend)
        self.samplePoints = [l]

    def add_sample(self, stddev, corrcoef, *args, **kwargs):
        """
        Add sample (*stddev*, *corrcoeff*) to the Taylor
        diagram. *args* and *kwargs* are directly propagated to the
        `Figure.plot` command.
        """

        l, = self.ax.plot(np.arccos(corrcoef), stddev,
                          *args, **kwargs)  # (theta, radius)
        self.samplePoints.append(l)

        return l

    def add_grid(self, *args, **kwargs):
        """Add a grid."""

        self._ax.grid(*args, **kwargs)

    def add_contours(self, levels=5, **kwargs):
        """
        Add constant centered RMS difference contours, defined by *levels*.
        """

        rs, ts = np.meshgrid(np.linspace(self.smin, self.smax),
                             np.linspace(0, self.tmax))
        # Compute centered RMS difference
        rms = np.sqrt(self.refstd**2 + rs**2 - 2*self.refstd*rs*np.cos(ts))

        contours = self.ax.contour(ts, rs, rms, levels, **kwargs)

        return contours


locator = mdates.AutoDateLocator(minticks=3, maxticks=9)
formatter = mdates.ConciseDateFormatter(locator)
obspath = "X:/georisk/HaRIA_B_Wind/data/derived/obs/1-minute/wind"
reanpath = "X:/georisk/HaRIA_B_Wind/data/derived/reanalysis/era5/timeseries/10fg/station"
stationfile = "X:/georisk/HaRIA_B_Wind/data/derived/reanalysis/era5/timeseries/stationlist.shp"
outputPath = "X:/georisk/HaRIA_B_Wind/data/derived/obs/1-minute/wind/regression/10fg"

stations = gpd.read_file(stationfile)
stations['rsq'] = 0
stations['m'] = 0
stations['b'] = 0
stations['mciu'] = 0
stations['mcil'] = 0
stations['bciu'] = 0
stations['bcil'] = 0
stations['nobs'] = 0
stations['obssd'] = 0
stations['rasd'] = 0

varname = "fg10"

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
    reandf = reands[varname].to_dataframe().reset_index()

    jointdf = obsdf.merge(reandf.rename(columns={'time':'date'}))

    jointdf[varname] = jointdf[varname] * 3.6

    fig, ax = plt.subplots(figsize=(12, 4))
    plt.plot(reandf.time, reandf[varname]*3.6, alpha=0.5, label="Reanalysis")
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
    ax = sns.lmplot(data=jointdf, x='windgust', y=varname, scatter_kws={'alpha':0.25})
    x_fit = sm.add_constant(jointdf.windgust)
    fit = sm.OLS(jointdf[varname], x_fit).fit()
    ci = fit.conf_int()
    #plt.plot(np.arange(0, 160), np.arange(0, 160), ls='--', color='k')
    #ax.set_axis_labels('Observed wind gusts [km/h]', 'Reanalysis wind gusts [km/h]')
    #ax.ax.set_title(f"{stationName} ({station})")
    #ax.ax.text(0.1, 0.9, rf"$R^2 = ${np.round(fit.rsquared, 4)}", transform=ax.ax.transAxes)
    #ax.ax.text(0.1, 0.85, f"n = {len(obsdf)}", transform=ax.ax.transAxes)
    #plt.savefig(pjoin(outputPath, f"regplot.{station:06d}.png"), bbox_inches='tight')
    stations.loc[stations.stnNum==station, 'rsq'] = fit.rsquared
    stations.loc[stations.stnNum==station, 'nobs'] = len(obsdf)
    stations.loc[stations.stnNum==station, 'm'] = fit.params.windgust
    stations.loc[stations.stnNum==station, 'b'] = fit.params.const
    stations.loc[stations.stnNum==station, 'obssd'] = obsdf.windgust.std()
    stations.loc[stations.stnNum==station, 'rasd'] = jointdf.i10fg.std()

    # Add upper/lower confidence interval on the fitted regression line:
    stations.loc[stations.stnNum==station, 'bcil'] = ci[0].const
    stations.loc[stations.stnNum==station, 'bciu'] = ci[1].const
    stations.loc[stations.stnNum==station, 'mcil'] = ci[0].windgust
    stations.loc[stations.stnNum==station, 'mciu'] = ci[1].windgust

    plt.close('all')
    gc.collect()

breakpoint()
stations.to_file(pjoin(outputPath, 'stationlist.shp'))
pd.DataFrame(stations.drop(columns='geometry')).to_csv(pjoin(outputPath, 'stationlist.csv'))

fields = ['m', 'b', 'rsq', 'nobs', 'stnLat', 'stnLon', 'stnElev']

# Only plot data for valid stations (nobs > 1825 [5 years])
# Plot a pairwise plot of a subset of fields to see if there's any relationship
# between (e.g.) latitude and correlation of the reanalysis & observed wind gust
# data. May lead to additional exploration.
subdf = stations[stations.nobs > (365 * 5)][fields]
g = sns.pairplot(subdf, plot_kws=dict(marker="+", linewidth=1), corner=True)
g.map_lower(sns.kdeplot, levels=5, color=".2")
plt.savefig(pjoin(outputPath, 'station_pairplot.png'), bbox_inches='tight')

breakpoint()
fig, ax = plt.subplots(1, 1)
extend = True
label='Reference'
tr = PolarAxes.PolarTransform()
rlocs = np.array([0, 0.2, 0.4, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1])
tmax = np.pi
rlocs = np.concatenate((-rlocs[:0:-1], rlocs))
tlocs = np.arccos(rlocs)
gl1 = GF.FixedLocator(tlocs)
tf1 = GF.DictFormatter(dict(zip(tlocs, map(str, rlocs))))

refstd = stations.obssd.mean()
srange = (0., 2.)
smin = srange[0] * refstd
smax = srange[1] * refstd

ghelper = FA.GridHelperCurveLinear(tr,
            extremes=(0, tmax, smin, smax),
            grid_locator1=gl1, tick_formatter=tf1)

fig = plt.figure()
ax = FA.FloatingSubplot(fig, 111, grid_helper=ghelper)
fig.add_subplot(ax)
# Adjust axes
ax.axis["top"].set_axis_direction("bottom")   # "Angle axis"
ax.axis["top"].toggle(ticklabels=True, label=True)
ax.axis["top"].major_ticklabels.set_axis_direction("top")
ax.axis["top"].label.set_axis_direction("top")
ax.axis["top"].label.set_text("Correlation")

ax.axis["left"].set_axis_direction("bottom")  # "X axis"
ax.axis["left"].label.set_text("Standard deviation")

ax.axis["right"].set_axis_direction("top")    # "Y-axis"
ax.axis["right"].toggle(ticklabels=True)
ax.axis["right"].major_ticklabels.set_axis_direction(
    "bottom" if extend else "left")
ax.axis["bottom"].toggle(ticklabels=False, label=False)

pax = ax.get_aux_axes(tr)
l, = pax.plot([0], refstd, 'k*',
              ls='', ms=10, label=label)
t = np.linspace(0, tmax)
r = np.zeros_like(t) + refstd
pax.plot(t, r, 'k--', label='_')
samplePoints = [l]

# Add samples
l, = pax.plot(np.arccos(stations['rsq']), stations['rasd'])  # (theta, radius)
samplePoints.append(l)


ax.grid()
rs, ts = np.meshgrid(np.linspace(smin, smax), np.linspace(0, tmax))
rms = np.sqrt(refstd**2 + rs**2 - 2*refstd*rs*np.cos(ts))
contours = pax.contour(ts, rs, rms, levels=5)
plt.clabel(contours, inline=1, fontsize=10, fmt='%.2f')


"""
dia = TaylorDiagram(refstd=stations['obssd'], fig=fig, srange = (0., 20))

for stddev, corrcoef in stations[['rasd', 'rsq']]:
    dia.add_sample(stddev, corrcoef, ms=10, ls='', mfc='r', mec=None, alpha=0.5)

dia.add_grid()
cm = dia.add_contours(colors='0.5')
plt.clabel(cm, inline=1, fontsize=10, fmt='%.2f')
"""