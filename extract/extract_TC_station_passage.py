"""
extract_TC_station_passage.py - find all TCs that pass within a defined distance
of a weather station

"""

import os
from os.path import join as pjoin
import numpy as np
import pandas as pd
import geopandas as gpd

from pyproj import Geod

import matplotlib.pyplot as plt

from Utilities import track
from shapely.geometry import LineString, Point, Polygon, sbox

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

    obstc = pd.read_csv(trackfile,
                        skiprows=[1],
                        usecols=[0, 6, 8, 9, 11, 113],
                        na_values=[' '],
                        parse_dates=[1])
    obstc.rename(columns={'SID':'num', 'LAT': 'lat', 'LON':'lon',
                          'WMO_PRES':'pmin', 'BOM_POCI':'poci'},
                inplace=True)
    obstc = filter_tracks_domain(obstc)
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
    trackgdf = trackgdf.to_crs("EPSG:4326") # WGS84 for IBTrACS - double check!
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
    colnames = ["id", 'stnNum', 'rainfalldist', 'stnName', 'stnOpen',
                'stnClose', 'stnLat', 'stnLon', 'stnLoc', 'stnState',
                'stnElev', 'stnBarmoeterElev', 'stnWMOIndex',
                'stnDataStartYear', 'stnDataEndYear', 'pctComplete',
                'pctY', 'pctN', 'pctW', 'pctS', 'pctI']

    df = pd.read_csv(stationfile, sep=',', index_col=False,
                     names=colnames, keep_default_na=False)
    gdf = gpd.GeoDataFrame(df,
                           geometry=gpd.points_from_xy(
                               df.stnLon, df.stnLat, crs="EPSG:7844")
                           )
    gdf = gdf.buffer(dist)
    return gdf

