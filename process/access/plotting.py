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

precipcolorseq=['#FFFFFF', '#ceebfd', '#87CEFA', '#4969E1', '#228B22', 
                '#90EE90', '#FFDD66', '#FFCC00', '#FF9933', 
                '#FF6600', '#FF0000', '#B30000', '#73264d']
precipcmap = sns.blend_palette(precipcolorseq, len(precipcolorseq), as_cmap=True)
preciplevels = [0.4, 1.0, 5.0, 10., 15, 20.0, 30.0, 40.0, 50.0, 60.0, 80.0, 100]
windlevels = np.arange(5, 76, 5)

cbar_kwargs = {"shrink":0.9, 'ticks': preciplevels,}
states = cfeature.NaturalEarthFeature(
        category='cultural',
        name='admin_1_states_provinces_lines',
        scale='10m',
        facecolor='none')

def precip(da, fh, outputFile, metadata):
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.figure.set_size_inches(15,12)
    da.isel(time=fh).plot.contourf(ax=ax, transform=ccrs.PlateCarree(), 
                                   levels=preciplevels, extend='both',cmap=precipcmap,
                                   cbar_kwargs=cbar_kwargs)
    ax.set_aspect('equal')

    vt = pd.to_datetime(da.isel(time=fh).time.values).strftime("%Y-%m-%d %H:%M")
    plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}", transform=ax.transAxes, ha='right')
    plt.text(0.0, 1.01, f"ACCESS-C3 +{fh:02d}HRS", transform=ax.transAxes, ha='left', fontsize='medium')
    plt.text(1.0, 1.01, f"Valid time: {vt}", transform=ax.transAxes, ha='right',fontsize='medium')
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
    :param da: `xarray.DataArray`
    """
    ax = plt.axes(projection=ccrs.PlateCarree())
    ax.figure.set_size_inches(15, 12)
    windlevels = np.arange(5, 76, 5)
    (da.max(axis=0)*1.94384).plot.contourf(ax=ax, transform=ccrs.PlateCarree(), 
                                levels=windlevels, extend='both',
                                cmap=precipcmap, 
                                cbar_kwargs={"shrink":0.9,
                                             'ticks': windlevels,
                                             "label":"wndgust10m [kts]"})
    vt = pd.to_datetime(da.time.values[-1]).strftime("%Y-%m-%d %H:%M UTC")
    plt.text(1.0, -0.05, f"Created: {datetime.now():%Y-%m-%d %H:%M %z}", transform=ax.transAxes, ha='right')
    plt.text(0.0, 1.01, f"ACCESS-C3 +{fh:02d}HRS", transform=ax.transAxes, ha='left', fontsize='medium')
    plt.text(1.0, 1.01, f"Valid time:\n{vt}", transform=ax.transAxes, ha='right',fontsize='medium')
    ax.set_title(f"Surface wind gusts")
    ax.coastlines(resolution='10m')
    ax.add_feature(states, edgecolor='0.15', linestyle='--')

    gl = ax.gridlines(draw_labels=True, linestyle=":")
    gl.top_labels = False
    gl.right_labels = False
    plt.savefig(outputFile, bbox_inches='tight', metadata=metadata)
    plt.close()
