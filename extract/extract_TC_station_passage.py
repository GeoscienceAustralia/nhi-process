"""
extract_TC_station_passage.py - find all TCs that pass within a defined distance
of a weather station

"""

import os
import logging
from os.path import join as pjoin
import numpy as np
import pandas as pd
import geopandas as gpd

import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry import box as sbox

from Utilities import track

logger = logging.getLogger()

def filter_tracks_domain(df, minlon=90, maxlon=180, minlat=-40, maxlat=0):
    """
    Takes a `DataFrame` and filters on the basis of whether the track interscts
    the given domain, which is specified by the minimum and maximum longitude
    and latitude.
    
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

    :returns: :class:`pd.DataFrame` of tracks that pass through the given box.
    """
    logger.info("Filtering tracks to the given domain")
    domain = sbox(minlon, minlat, maxlon, maxlat, ccw=False)
    tracks = df.groupby('num')
    tempfilter = tracks.filter(lambda x: len(x) > 1)
    filterdf = tempfilter.groupby('num').filter(
        lambda x: LineString(zip(x['lon'], x['lat'])).intersects(domain))
    return filterdf


def load_obs_tracks(trackfile: str) -> gpd.GeoDataFrame:
    """
    Load track data from IBTrACS file, add geometry and CRS. Basic
    categorisation using minimum central pressure is applied.

    :param str trackfile: Path to IBTrACS data file

    :returns: :class:`geopandas.GeoDataFrame`
    """
    logger.info(f"Loading tracks from {trackfile}")
    usecols = [0, 1, 2, 7, 8, 11, 12, 13]
    colnames = ['NAME', 'DISTURBANCE_ID', 'TM', 'LAT', 'LON',
                'adj. ADT Vm (kn)', 'CP(CKZ(Lok R34,LokPOCI, adj. Vm),hPa)', 
                'POCI (Lok, hPa)']
    dtypes = [str, str, str, float, float, float, float, float]

    df = pd.read_csv(trackfile, usecols=usecols,
                 dtype=dict(zip(colnames, dtypes)), na_values=[' '], nrows=13743)
    colrenames = {'DISTURBANCE_ID': 'num',
                  'TM': 'datetime',
                  'LON': 'lon', 'LAT': 'lat',
                  'adj. ADT Vm (kn)':'vmax',
                  'CP(CKZ(Lok R34,LokPOCI, adj. Vm),hPa)': 'pmin',
                  'POCI (Lok, hPa)': 'poci'}
    df.rename(colrenames, axis=1, inplace=True)

    df['datetime'] = pd.to_datetime(df.datetime, format="%Y-%m-%d %H:%M", errors='coerce')

    obstc = filter_tracks_domain(df)
    trackgdf = []
    for k, t in obstc.groupby('num'):
        segments = []
        for n in range(len(t.num) - 1):
            segment = LineString([[t.lon.iloc[n], t.lat.iloc[n]],
                                  [t.lon.iloc[n+1], t.lat.iloc[n+1]]])
            segments.append(segment)

        gdf = gpd.GeoDataFrame.from_records(t[:-1])
        gdf['geometry'] = segments
        gdf['category'] = pd.cut(gdf['pmin'],
                                 bins=[0, 930, 955, 970, 985, 990, 1020],
                                 labels=[5, 4, 3, 2, 1, 0])
        trackgdf.append(gdf)

    trackgdf = pd.concat(trackgdf)
    trackgdf = trackgdf.set_crs("EPSG:4326") # WGS84 for IBTrACS - double check!
    return trackgdf

def load_stations(stationfile: str, dist: float) -> gpd.GeoDataFrame:
    """
    Load weather station locations from a file, add geometry and a buffer to
    each feature.

    We put the station data into GDA 2020

    :param stationfile: Path to the station file
    :param dist: Buffer distance around each station - needs to be in the same
    units as the station coordinates (i.e. probably degrees)
    """
    logger.info(f"Loading stations from {stationfile}")
    colnames = ["id", 'stnNum', 'rainfalldist', 'stnName', 'stnOpen',
                'stnClose', 'stnLat', 'stnLon', 'stnLoc', 'stnState',
                'stnElev', 'stnBarmoeterElev', 'stnWMOIndex',
                'stnDataStartYear', 'stnDataEndYear', 'pctComplete',
                'pctY', 'pctN', 'pctW', 'pctS', 'pctI']

    df = pd.read_csv(stationfile, sep=',', index_col=False,
                     names=colnames, keep_default_na=False,
                     header=0)
    gdf = gpd.GeoDataFrame(df,
                           geometry=gpd.points_from_xy(
                               df.stnLon, df.stnLat, crs="EPSG:7844").buffer(dist)
                           )
    #gdf['geometry'] = gdf.buffer(dist)
    return gdf


stationFile = r"X:\georisk\HaRIA_B_Wind\data\raw\from_bom\2019\Daily\DC02D_StnDet_999999999632559.txt"
trackFile = r"X:\georisk\HaRIA_B_Wind\data\raw\from_bom\tc\Objective Tropical Cyclone Reanalysis - QC.csv"

tracks = load_obs_tracks(trackFile)
stations = load_stations(stationFile, 3)

selected = gpd.overlay(tracks, stations.to_crs(tracks.crs), how='intersection')
import pdb; pdb.set_trace()
