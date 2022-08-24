"""
extract_TC_station_passage.py - find all TCs that pass within a defined distance
of a weather station

We first calculate the closest point of approach (CPA) between a weather station location and each TC track. For all records where the TC passes within 2 degrees of the station, we store the date/time of the passage and the distance of the CPA.

For each station, we then load the daily maximum wind gust observations, and extract the observations closest to the date/time of CPA, plus the observations from one day prior and one day after. We then take the maximum of those observaations and assign that value to the cyclone event.

We check the observations for the day prior and after to ensure we capture the maximum gust from the cyclone. It is possible that the CPA occurs on one day, but the strongest gust may be on the next day

NOTE: The wind speed observations are in m/s, but appear to be converted from the original recording units of knots, then rounded to 1 decimal place. This causes an element of anomalous clustering around specific values in the data recorded in the files.

"""
import os
import logging
import warnings
import pandas as pd
import geopandas as gpd
from datetime import timedelta

import matplotlib.pyplot as plt
from shapely.geometry import LineString
from shapely.geometry import box as sbox
from vincenty import vincenty

logger = logging.getLogger()

warnings.filterwarnings("ignore", category=FutureWarning)

TZ = {"QLD": 10, "NSW": 10, "VIC": 10,
      "TAS": 10, "SA": 9.5, "NT": 9.5,
      "WA": 8, "ANT": 0}


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


def load_obs_tracks(trackfile: str, format: str) -> gpd.GeoDataFrame:
    """
    Load track data from IBTrACS file, add geometry and CRS. Basic
    categorisation using minimum central pressure is applied.

    :param str trackfile: Path to BoM best track data file
    :param str format: Whether its a raw or QC'd BoM best track file

    :returns: :class:`geopandas.GeoDataFrame`
    """
    logger.info(f"Loading tracks from {trackfile}")

    if format == 'QC':
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
                      'adj. ADT Vm (kn)': 'vmax',
                      'CP(CKZ(Lok R34,LokPOCI, adj. Vm),hPa)': 'pmin',
                      'POCI (Lok, hPa)': 'poci'}
        df.rename(colrenames, axis=1, inplace=True)
    else:
        usecols = [0, 1, 2, 7, 8, 16, 20, 53]
        colnames = ['NAME', 'num', 'datetime',
                    'lat', 'lon', 'pmin', 'poci', 'vmax']
        dtypes = [str, str, str, float, float, float, float, float]
        df = pd.read_csv(trackfile, usecols=usecols, header=0, skiprows=5, names=colnames,
                         dtype=dict(zip(colnames, dtypes)), na_values=[' '],)

    df['datetime'] = pd.to_datetime(
        df.datetime, format="%Y-%m-%d %H:%M", errors='coerce')
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
    # WGS84 for IBTrACS - double check!
    trackgdf = trackgdf.set_crs("EPSG:4326")
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
    gdf.set_index('stnNum', drop=False, inplace=True)
    return gdf


def load_obs_data(stationFile: str, stnState: str) -> pd.DataFrame:
    """
    Load observations for a given station

    :param str stationFile: path to a file containing formatted daily
    observations of the maximum wind gust and the corresponding present
    and past weather conditions
    :param str stnState: abbreviated state name for the station. Required
    to determine UTC offset (obs datetimes are local time, TC datetimes are
    UTC)

    :returns: `pd.DataFrame` containing the observations, with datetime
    converted to UTC. Any records with missing/null maximum daily gust values
    are eliminated.
    """
    logger.info(f"Loading {stationFile}")
    colnames = ["dc", "stnNum", "Year", "Month", "Day",
                "gust", "gust_q", "direction", "direction_q", "time", "time_q",
                "preswx00", "Qpreswx00", "preswx03", "Qpreswx03", "preswx06", "Qpreswx06",
                "preswx09", "Qpreswx09", "preswx12", "Qpreswx12", "preswx15", "Qpreswx15",
                "preswx18", "Qpreswx18", "preswx21", "Qpreswx21", "pastwx00", "Qpastwx00",
                "pastwx03", "Qpastwx03", "pastwx06", "Qpastwx06", "pastwx09", "Qpastwx09",
                "pastwx12", "Qpastwx12", "pastwx15", "Qpastwx15", "pastwx18", "Qpastwx18",
                "pastwx21", "Qpastwx21", "Null"]

    dtypes = [str, str, str, str, str, float, str, float, str, str, str,
              float, str, float, str, float, str, float, str, float, str,
              float, str, float, str, float, str, float, str, float, str,
              float, str, float, str, float, str, float, str, float, str,
              float, str, ]
    df = pd.read_csv(stationFile, names=colnames, sep=",", index_col=False,
                     header=0, parse_dates={'datetime': [2, 3, 4, 9]},
                     na_values=['', '     '], keep_default_na=False)
    # Change local time to UTC time. Have to assume we're not working with
    # DLS times - would be somewhat complex to determine, since some states
    # actually went thru periods of having DLS, but typically don't!
    df['datetime'] = df.datetime - timedelta(hours=TZ[stnState])
    # Drop rows with no gust observation 
    df = df[~df.gust.isna()]
    return df


def calculateCPA(stationFile: str, trackFile: str, trackFormat: str) -> pd.DataFrame:
    """
    Calculate the closest point of approach to each station for each cyclone.

    NOTE: Currently also writes the data to a csv file at a hard-coded location

    :param str stationFile: Full path to the list of available stations
    :param str trackFile: Full path to the best track data
    :param str trackFormat: either "raw" or "QC". Indicates which best track
        data to load

    :returns: `pd.DataFrame` with the datetime of each instance of a cyclone
        passage, along with distance, central pressure and poci of the storm at
        the time of CPA.
    """
    tracks = load_obs_tracks(trackFile, trackFormat)
    stations = load_stations(stationFile, 2)
    stations.set_index('stnNum', drop=False, inplace=True)
    selected = gpd.overlay(tracks, stations.to_crs(
        tracks.crs), how='intersection')
    selected['cpa'] = selected.apply(lambda x: vincenty(
        (x['lat'], x['lon']), (x['stnLat'], x['stnLon'])), axis=1)
    # Closest point of approach (CPA)
    stncpa = selected.loc[selected.groupby(['stnNum', 'num']).cpa.idxmin()]
    stncpa = stncpa.loc[stncpa.cpa < 250.]
    stncpa.drop('geometry', axis=1, inplace=True)
    stncpa.to_csv(
        r"X:\georisk\HaRIA_B_Wind\data\derived\tcobs\stncpa.csv", index=False)
    return stncpa


def extractObs(cpadf: pd.DataFrame, stations: pd.DataFrame) -> pd.DataFrame:
    outdf = pd.DataFrame(columns=['stnNum', 'stnName', 'dtObs', 'gust', 'gustq',
                                  'direction', 'dtTC', 'TCName',
                                  'TCCPA'])
    cpagroup = cpadf.groupby('stnNum')
    for stnNum, group in cpagroup:
        # Load the data - need the state to determine offset from UTC
        stnState = stations.loc[stnNum, 'stnState'].strip()
        stnName = stations.loc[stnNum, 'stnName']
        dataFile = os.path.join(
            stationPath, f"DC02D_Data_{stnNum:06d}_999999999632559.txt")
        obsData = load_obs_data(dataFile, stnState)
        if obsData.empty:
            print(f"No station observation data for {stnNum}")
            continue

        obsData.set_index('datetime', inplace=True, drop=False)
        for idx, tc in group.iterrows():
            # First find the index of the obs data closest to the time of CPA
            try:
                indx = obsData.index.get_loc(
                    tc.datetime, method='nearest', tolerance=pd.Timedelta('1D'))
            except KeyError:
                print(
                    f"No obs within 1 day of {tc.datetime} at {stnNum} for {tc.NAME}")
                continue

            # Redundant?
            if indx == -1:
                breakpoint()
            if indx == 0:
                # No records:
                continue

            # Select the records either side of the selected time - maximum wind
            # gust may have occured on previous or following day compared to the
            # time of CPA (e.g. CPA at 01:00, but highest gust at 23:00 previous
            # day)
            obsgrp = obsData.iloc[indx-1:indx+2]
            # Now take the max value of those records:
            obs = obsgrp.loc[obsgrp['gust'].idxmax()]

            if obs.gust is not None:
                print(stnNum, obs.datetime, obs.gust,
                      obs.direction, tc.datetime, tc.NAME, tc.cpa)
                outdf = outdf.append(
                    pd.DataFrame([[stnNum, stnName, obs.datetime, obs.gust, obs.gust_q, obs.direction, tc.datetime, tc.NAME, tc.cpa]],
                                 columns=['stnNum', 'stnName', 'dtObs', 'gust', 'gustq', 'direction', 'dtTC', 'TCName', 'TCCPA']),
                    ignore_index=True)
    return outdf


stationPath = r"X:\georisk\HaRIA_B_Wind\data\raw\from_bom\2019\Daily"
stationFile = os.path.join(stationPath, "DC02D_StnDet_999999999632559.txt")
trackFile = r"X:\georisk\HaRIA_B_Wind\data\raw\from_bom\tc\IDCKMSTM0S - 20210722.csv"

stncpa = calculateCPA(stationFile, trackFile, 'raw')
stations = load_stations(stationFile, 2)
outdf = extractObs(stncpa, stations)
tdiff = abs(outdf.dtObs - outdf.dtTC)

# Remove any obs where the time difference between CPA and the obs is greater than 36 hours
outdf = outdf[tdiff < pd.Timedelta('36h')]
outdf.to_csv(
    r"X:\georisk\HaRIA_B_Wind\data\derived\tcobs\stncpa_obs.csv", index=False)


for stnNum, obs in outdf.groupby('stnNum'):
    if len(obs) > 10:
        print(stnNum, stations.loc[stnNum, 'stnName'], len(obs))


