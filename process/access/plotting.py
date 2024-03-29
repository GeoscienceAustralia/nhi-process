import os
from os.path import join as pjoin
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib.pyplot as plt
from cartopy import crs as ccrs
from cartopy.mpl.ticker import LongitudeFormatter, LatitudeFormatter
import cartopy.feature as cfeature
from datetime import datetime

import seaborn as sns

precipcolorseq = ['#FFFFFF', '#ceebfd', '#87CEFA', '#4969E1', '#228B22',
                  '#90EE90', '#FFDD66', '#FFCC00', '#FF9933',
                  '#FF6600', '#FF0000', '#B30000', '#73264d']
precipcmap = sns.blend_palette(
    precipcolorseq, len(precipcolorseq), as_cmap=True)
helicitymap = sns.blend_palette(
    precipcolorseq[::-1], len(precipcolorseq), as_cmap=True)
preciplevels = [0.4, 1.0, 5.0, 10., 15,
                20.0, 30.0, 40.0, 50.0, 60.0, 80.0, 100]
windlevels = np.arange(5, 76, 5)
radarlevels = np.arange(20, 76, 5)
helicitylevels = np.arange(-500, 1, 50)

cbar_kwargs = {"shrink": 0.9, 'ticks': preciplevels, }
states = cfeature.NaturalEarthFeature(
    category='cultural',
    name='admin_1_states_provinces_lines',
    scale='10m',
    facecolor='none')


def precip(da, fh, outputFile, metadata):
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.figure.set_size_inches(15, 12)
    tmpda = da.isel(time=-1) - da.isel(time=0)
    tmpda.attrs = da.attrs
    tmpda.plot.contourf(ax=ax, transform=ccrs.PlateCarree(),
                        levels=preciplevels, extend='both', cmap=precipcmap,
                        cbar_kwargs=cbar_kwargs)
    ax.set_aspect('equal')

    vt = pd.to_datetime(
        da.isel(time=-1).time.values).strftime("%Y-%m-%d %H:%M")
    plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}",
             transform=ax.transAxes, ha='right')
    plt.text(0.0, 1.01, f"ACCESS-C3 +{fh:02d}HRS",
             transform=ax.transAxes, ha='left', fontsize='medium')
    plt.text(1.0, 1.01, f"Valid time: {vt}",
             transform=ax.transAxes, ha='right', fontsize='medium')
    ax.set_title(f"ACCUM PRCP")
    ax.coastlines(resolution='10m')
    ax.add_feature(states, edgecolor='0.15', linestyle='--')

    gl = ax.gridlines(draw_labels=True, linestyle=":")
    gl.top_labels = False
    gl.right_labels = False
    plt.savefig(outputFile, bbox_inches='tight', metadata=metadata)
    plt.close()


def windgust(da, fh, outputFile, metadata):
    """
    Plot surface wind gust speed in knots
    :param da: `xarray.DataArray` containing the gridded wind speed data
    (data is stored in units of m/s)
    :param int fh: Forecast hour (time from initial timestep)
    :param str outputFile: Path to output location to save figure
    :param dict metadata: Additional metadata to store in the figure file
    (this only works for PNG format files with the `agg` backend)
    """
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.figure.set_size_inches(15, 12)
    (da.max(axis=0)*1.94384).plot.contourf(
        ax=ax, transform=ccrs.PlateCarree(),
        levels=windlevels, extend='both',
        cmap=precipcmap,
        cbar_kwargs={
            "shrink": 0.9,
            'ticks': windlevels,
            "label": "wndgust10m [kts]"
        }
    )
    vt = pd.to_datetime(da.time.values[-1]).strftime("%Y-%m-%d %H:%M UTC")
    plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}",
             transform=ax.transAxes, ha='right')
    plt.text(0.0, 1.01, f"ACCESS-C3 +{fh:02d}HRS",
             transform=ax.transAxes, ha='left', fontsize='medium')
    plt.text(1.0, 1.01, f"Valid time:\n{vt}",
             transform=ax.transAxes, ha='right', fontsize='medium')
    ax.set_title(f"Surface wind gusts")
    ax.coastlines(resolution='10m')
    ax.add_feature(states, edgecolor='0.15', linestyle='--')

    gl = ax.gridlines(draw_labels=True, linestyle=":")
    gl.top_labels = False
    gl.right_labels = False
    plt.savefig(outputFile, bbox_inches='tight', metadata=metadata)
    plt.close()


def helicity(da, fh, outputFile, metadata):
    """
    Plot updraft helicity. In southern hemisphere, we use the *minimum* updraft
    helicity, since the relative vorticity is *negative*. There may be
    situations where positive updraft helicity arises (anti-cyclonic rotating
    updrafts), so we may want to update this and use the absolute value of both
    maximum and minimum updraft helicity.

    :param da: `xarray.DataArray`
    """
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.figure.set_size_inches(15, 12)
    (da.min(axis=0).plot.contourf(
        ax=ax, transform=ccrs.PlateCarree(),
        levels=helicitylevels, extend='both',
        cmap=helicitymap,
        cbar_kwargs={
            "shrink": 0.9,
            'ticks': helicitylevels,
            "label": r"Updraft helicity [$m^2/s^2$]"
        }
    ))
    vt = pd.to_datetime(da.time.values[-1]).strftime("%Y-%m-%d %H:%M UTC")
    plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}",
             transform=ax.transAxes, ha='right')
    plt.text(0.0, 1.01, f"ACCESS-C3 +{fh:02d}HRS",
             transform=ax.transAxes, ha='left', fontsize='medium')
    plt.text(1.0, 1.01, f"Valid time:\n{vt}",
             transform=ax.transAxes, ha='right', fontsize='medium')
    ax.set_title("Minimum updraft helicity")
    ax.coastlines(resolution='10m')
    ax.add_feature(states, edgecolor='0.15', linestyle='--')

    gl = ax.gridlines(draw_labels=True, linestyle=":")
    gl.top_labels = False
    gl.right_labels = False
    plt.savefig(outputFile, bbox_inches='tight', metadata=metadata)
    plt.close()


def radar(da, fh, outputFile, metadata):
    """
    Plot radar reflectivity

    :param da: `xarray.DataArray`
    """
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.figure.set_size_inches(15, 12)
    (da.max(axis=0)).plot.contourf(
        ax=ax, transform=ccrs.PlateCarree(),
        levels=radarlevels, extend='both',
        cmap=precipcmap,
        cbar_kwargs={
            "shrink": 0.9,
            'ticks': radarlevels,
            "label": r"Radar reflectivity 1km AGL [dBZ]"
        }
    )
    vt = pd.to_datetime(da.time.values[-1]).strftime("%Y-%m-%d %H:%M UTC")
    plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}",
             transform=ax.transAxes, ha='right')
    plt.text(0.0, 1.01, f"ACCESS-C3 +{fh:02d}HRS", transform=ax.transAxes,
             ha='left', fontsize='medium')
    plt.text(1.0, 1.01, f"Valid time:\n{vt}", transform=ax.transAxes,
             ha='right', fontsize='medium')
    ax.set_title("Radar reflectivity 1km AGL")
    ax.coastlines(resolution='10m')
    ax.add_feature(states, edgecolor='0.15', linestyle='--')

    gl = ax.gridlines(draw_labels=True, linestyle=":")
    gl.top_labels = False
    gl.right_labels = False
    plt.savefig(outputFile, bbox_inches='tight', metadata=metadata)
    plt.close()
