import os
import re
import glob
import argparse
import logging
from os.path import join as pjoin
from datetime import datetime, timedelta
from configparser import ConfigParser, ExtendedInterpolation
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import warnings

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile, pInit
from files import flStartLog, flGetStat, flSize

warnings.simplefilter('ignore', RuntimeWarning)
pd.set_option('mode.chained_assignment', None)
sns.set_style('whitegrid')
logging.getLogger('matplotlib').setLevel(logging.WARNING)

LOGGER = logging.getLogger()
PATTERN = re.compile(r".*Data_(\d{6}).*\.txt")
STNFILE = re.compile(r".*StnDet.*\.txt")
TZ = {"QLD":10, "NSW":10, "VIC":10,
      "TAS":10, "SA":9.5, "NT":9.5,
      "WA":8, "ANT":0}

def start():
    """
    Parse command line arguments, initiate processing module (for tracking
    processed files) and start the main loop.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config_file', help="Configuration file")
    parser.add_argument('-v', '--verbose', help="Verbose output",
                        action='store_true')
    args = parser.parse_args()

    configFile = args.config_file
    verbose = args.verbose
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)

    pInit(configFile)
    main(config, verbose)

def main(config, verbose=False):
    """
    Start logger and call the loop to process source files.

    :param config: `ConfigParser` object with configuration loaded
    :param boolean verbose: If `True`, print logging messages to STDOUT

    """

    logfile = config.get('Logging', 'LogFile')
    loglevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=verbose)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    LOGGER = flStartLog(logfile, loglevel, verbose, datestamp)

    ListAllFiles(config)
    processStationFiles(config)
    processFiles(config)

# This is for tracking down memory leaks:
"""
def display_top(snapshot, key_type='lineno', limit=10):
    snapshot = snapshot.filter_traces((
        tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
        tracemalloc.Filter(False, "<unknown>"),
    ))
    top_stats = snapshot.statistics(key_type)

    LOGGER.info("Top %s lines" % limit)
    for index, stat in enumerate(top_stats[:limit], 1):
        breakpoint()
        frame = stat.traceback[0]
        # replace "/path/to/module/file.py" with "module/file.py"
        filename = os.sep.join(frame.filename.split(os.sep)[-2:])
        LOGGER.info("#%s: %s:%s: %.1f KiB"
              % (index, filename, frame.lineno, stat.size / 1024))
        line = linecache.getline(frame.filename, frame.lineno).strip()
        if line:
            LOGGER.info('    %s' % line)

    other = top_stats[limit:]
    if other:
        size = sum(stat.size for stat in other)
        LOGGER.info("%s other: %.1f KiB" % (len(other), size / 1024))
    total = sum(stat.size for stat in top_stats)
    LOGGER.info("Total allocated size: %.1f KiB" % (total / 1024))

def printHeap():
    '''
    Print a report on the memory use of objects
    '''
    thestats = THEHEAP.heapu()
    LOGGER.info(f"Total objects: {thestats.count}")
    LOGGER.info(f"Total size: {thestats.size} bytes")
    LOGGER.info(f"Number of entries: {thestats.numrows}")
    LOGGER.info("Entries:")
    LOGGER.info("Index Count    Size    Cumulative size       Object name")
    for row in thestats.get_rows():
        LOGGER.info("%5d%5d%8d%8d%30s"% (row.index, row.count, row.size, row.cumulsize, row.name))

    LOGGER.info("\nMeasuring Unreachable Objects From This Reference Point Onwards")
    THEHEAP.setref()
    LOGGER.info(THEHEAP.heapu(stat = 0))
    # breakpoint()
"""
def ListAllFiles(config):
    """
    For each item in the 'Categories' section of the configuration file, load
    the specification (glob) for the files, then pass to `expandFileSpecs`

    :param config: `ConfigParser` object
    """
    global g_files
    g_files = {}
    categories = config.items('Categories')
    for idx, category in categories:
        specs = []
        items = config.items(category)
        for k, v in items:
            if v == '':
                specs.append(k)
        expandFileSpecs(config, specs, category)

def expandFileSpec(config, spec, category):
    """
    Given a file specification and a category, list all files that match the
    spec and add them to the :dict:`g_files` dict.
    The `category` variable corresponds to a section in the configuration file
    that includes an item called 'OriginDir'.
    The given `spec` is joined to the `category`'s 'OriginDir' and all matching
    files are stored in a list in :dict:`g_files` under the `category` key.

    :param config: `ConfigParser` object
    :param str spec: A file specification. e.g. '*.*' or 'IDW27*.txt'
    :param str category: A category that has a section in the source configuration file
    """
    if category not in g_files:
        g_files[category] = []

    origindir = config.get(category, 'OriginDir',
                           fallback=config.get('Defaults', 'OriginDir'))
    spec = pjoin(origindir, spec)
    files = glob.glob(spec)
    LOGGER.info(f"{len(files)} {spec} files to be processed")
    for file in files:
        if os.stat(file).st_size > 0:
            if file not in g_files[category]:
                g_files[category].append(file)

def expandFileSpecs(config, specs, category):
    for spec in specs:
        expandFileSpec(config, spec, category)

def processStationFiles(config):
    """
    Process all the station files to populate a global station file DataFrame

    :param config: `ConfigParser` object
    """

    global g_files
    global g_stations
    global LOGGER

    stnlist = []
    category = 'Stations'
    for f in g_files[category]:
        LOGGER.info(f"Processing {f}")
        stnlist.append(getStationList(f))
    g_stations = pd.concat(stnlist)

def processFiles(config):
    """
    Process a list of files in each category
    """
    global g_files
    global LOGGER
    unknownDir = config.get('Defaults', 'UnknownDir')
    defaultOriginDir = config.get('Defaults', 'OriginDir')
    deleteWhenProcessed = config.getboolean('Files', 'DeleteWhenProcessed', fallback=False)
    archiveWhenProcessed = config.getboolean('Files', 'ArchiveWhenProcessed', fallback=True)
    outputDir = config.get('Output', 'Path', fallback=unknownDir)
    LOGGER.debug(f"DeleteWhenProcessed: {deleteWhenProcessed}")
    LOGGER.debug(f"Output directory: {outputDir}")
    if not os.path.exists(unknownDir):
        os.mkdir(unknownDir)

    if not os.path.exists(outputDir):
        os.mkdir(outputDir)
        os.mkdir(pjoin(outputDir, 'dailymax'))
        os.mkdir(pjoin(outputDir, 'dailymean'))
        os.mkdir(pjoin(outputDir, 'plots'))
        os.mkdir(pjoin(outputDir, 'events'))

    category = "Input"
    originDir = config.get(category, 'OriginDir', fallback=defaultOriginDir)
    LOGGER.debug(f"Origin directory: {originDir}")

    for f in g_files[category]:
        LOGGER.info(f"Processing {f}")
        directory, fname, md5sum, moddate = flGetStat(f)
        if pAlreadyProcessed(directory, fname, "md5sum", md5sum):
            LOGGER.info(f"Already processed {f}")
        else:
            if processFile(f, outputDir):
                LOGGER.info(f"Successfully processed {f}")
                pWriteProcessedFile(f)
                if archiveWhenProcessed:
                    pArchiveFile(f)
                elif deleteWhenProcessed:
                    os.unlink(f)

def processFile(filename: str, outputDir: str) -> bool:
    """
    process a file and store output in the given output directory

    :param str filename: path to a station data file
    :param str outputDir: Output path for data & figures to be saved
    """

    global g_stations

    LOGGER.info(f"Loading data from {filename}")
    LOGGER.debug(f"Data will be written to {outputDir}")
    m = PATTERN.match(filename)
    stnNum = int(m.group(1))
    stnState = g_stations.loc[stnNum, 'stnState']
    stnName = g_stations.loc[stnNum, 'stnName']
    LOGGER.info(f"{stnName} - {stnNum} ({stnState})")
    filesize = flSize(filename)
    if filesize == 0:
        LOGGER.warning(f"Zero-sized file: {filename}")
        rc = False
    else:
        basename = f"{stnNum:06d}.pkl" # os.path.basename(filename)
        dfmax, dfmean, eventdf = extractDailyMax(filename, stnState, stnName, stnNum, outputDir)
        if dfmax is None:
            LOGGER.warning(f"No data returned for {filename}")
        else:
            LOGGER.debug(f"Writing data to {pjoin(outputDir, 'dailymax', basename)}")
            dfmax.to_pickle(pjoin(outputDir, 'dailymax', basename))
            dfmean.to_pickle(pjoin(outputDir, 'dailymean', basename)) # Date is the index
            if eventdf is not None:
                LOGGER.debug(f"Writing data to {pjoin(outputDir, 'events', basename)}")
                eventdf.to_pickle(pjoin(outputDir, 'events', basename))
        rc = True
    return rc

def getStationList(stnfile: str) -> pd.DataFrame:
    """
    Extract a list of stations from a station file

    :param str stnfile: Path to a station file

    :returns: :class:`pd.DataFrame`
    """
    LOGGER.debug(f"Retrieving list of stations from {stnfile}")
    colnames = ["id", 'stnNum', 'rainfalldist', 'stnName', 'stnOpen', 'stnClose',
            'stnLat', 'stnLon', 'stnLoc', 'stnState', 'stnElev', 'stnBarmoeterElev',
            'stnWMOIndex', 'stnDataStartYear', 'stnDataEndYear',
            'pctComplete', 'pctY', 'pctN', 'pctW', 'pctS', 'pctI', 'end']
    df = pd.read_csv(stnfile, sep=',', index_col='stnNum', names=colnames,
                     keep_default_na=False,
                     converters={
                         'stnName': str.strip,
                         'stnState': str.strip
                         })
    LOGGER.debug(f"There are {len(df)} stations")
    return df

def wdir_diff(wd1, wd2):
    """
    Calculate change in wind direction. This always returns a positive
    value, which is the minimum change in direction.

    :param wd: array of wind direction values
    :type wd: `np.ndarray`
    :return: Array of changes in wind direction
    :rtype: `np.ndarray`
    """

    diff1 = (wd1 - wd2)% 360
    diff2 = (wd2 - wd1)% 360
    res = np.minimum(diff1, diff2)
    return res

def extractDailyMax(filename, stnState, stnName, stnNum, outputDir, variable='windgust', threshold=90.):
    """
    Extract daily maximum value of `variable` from 1-minute observation records
    contained in `filename`

    :param filename: str, path object or file-like object
    :param stnState: str, station State (for determining local time zone)
    :param str outputDir: Path to output directory for storing plots
    :param str variable: the variable to extract daily maximum values - default "windgust"
    :param float threshold: Threshold value of `variable` for additional data extraction - default 90.0

    :returns: `pandas.DataFrame`s

    """
    """
    # 2021 version:
    names = ['id', 'stnNum',
             'YYYY', 'MM', 'DD', 'HH', 'MI',
             'YYYYl', 'MMl', 'DDl', 'HHl', 'MIl',
             'rainfall', 'rainq', 'rain_duration',
             'temp', 'tempq', 'dewpoint', 'dewpointq', 'rh', 'rhq',
             'windspd', 'windspdq', 'winddir', 'winddirq',
             'windsd', 'windsdq', 'windgust', 'windgustq',
             'mslp', 'mslpq', 'stnp', 'stnpq', 'end']
    dtypes = {'id': str, 'stnNum': int,
              'YYYY': int, "MM": int, "DD": int, "HH": int, "MI": int,
              'YYYYl': int, "MMl": int, "DDl": int, "HHl": int, "MIl": int,
              'rainfall': float, 'rainq': str, 'rain_duration': float,
              'temp': float, 'tempq': str,
              'dewpoint': float, 'dewpointq': str,
              'rh':float, 'rhq':str,
              'windspd':float, 'windspdq':str,
              'winddir': float, 'winddirq': str,
              'windsd':float, 'windsdq':str,
              'windgust': float, 'windgustq': str,
              'mslp':float, 'mslpq':str,
              'stnp': float, 'stnpq': str, 'end': str}
    """
    # 2022 version
    names = ['id', 'stnNum',
             'YYYY', 'MM', 'DD', 'HH', 'MI',
             'YYYYl', 'MMl', 'DDl', 'HHl', 'MIl',
             'rainfall', 'rainq', 'rain_duration',
             'temp', 'tempq',
             'temp1max', 'temp1maxq',
             'temp1min', 'temp1minq',
             'wbtemp', 'wbtempq',
             'dewpoint', 'dewpointq',
             'rh', 'rhq',
             'windspd', 'windspdq',
             'windmin', 'windminq',
             'winddir', 'winddirq',
             'windsd', 'windsdq',
             'windgust', 'windgustq',
             'mslp', 'mslpq', 'stnp', 'stnpq',
             'end']
    dtypes = {'id': str, 'stnNum': int,
              'YYYY': int, "MM": int, "DD": int, "HH": int, "MI": int,
              'YYYYl': int, "MMl": int, "DDl": int, "HHl": int, "MIl": int,
              'rainfall': float, 'rainq': str, 'rain_duration': float,
              'temp': float, 'tempq': str,
              'temp1max': float, 'temp1maxq': str,
              'temp1min': float, 'temp1minq': str,
              'wbtemp': float, 'wbtempq': str,
              'dewpoint': float, 'dewpointq': str,
              'rh':float, 'rhq':str,
              'windspd':float, 'windspdq':str,
              'windmin': float, 'windminq': str,
              'winddir': float, 'winddirq': str,
              'windsd':float, 'windsdq':str,
              'windgust': float, 'windgustq': str,
              'mslp':float, 'mslpq':str,
              'stnp': float, 'stnpq': str, 'end': str}
    LOGGER.debug(f"Reading station data from {filename}")
    try:
        df = pd.read_csv(filename, sep=',', index_col=False, dtype=dtypes,
                        names=names, header=0,
                        parse_dates={'datetime':[7, 8, 9, 10, 11]},
                        na_values=['####'],
                        skipinitialspace=True)
    except Exception as err:
        LOGGER.exception(f"Cannot load data from {filename}: {err}")
        return None, None
    LOGGER.debug("Filtering on quality flags")
    for var in ['temp', 'temp1max', 'temp1min', 'wbtemp',
                'dewpoint', 'rh', 'windspd', 'windmin',
                'winddir', 'windsd', 'windgust', 'mslp', 'stnp']:
        df.loc[~df[f"{var}q"].isin(['Y']), [var]] = np.nan

    # Hacky way to convert from local standard time to UTC:
    df['datetime'] = pd.to_datetime(df.datetime, format="%Y %m %d %H %M")
    LOGGER.debug("Converting from local to UTC time")
    df['datetime'] = df.datetime - timedelta(hours=TZ[stnState])
    df['date'] = df.datetime.dt.date
    df.set_index('datetime', inplace=True)
    LOGGER.debug("Determining daily maximum wind speed record")
    dfmax = df.loc[df.groupby(['date'])[variable].idxmax().dropna()]

    dfdata = pd.DataFrame(columns=['gustratio', 'pretemp', 'posttemp',
                                   'temprise', 'tempdrop', 'dirrate',
                                   'prsdrop', 'prsrise'],
                          index=dfmax.index)
    LOGGER.debug("Calculating other obs around daily max wind gust")

    frames = []

    for idx in df.groupby(['date'])['windgust'].idxmax().dropna():
        startdt = idx - timedelta(hours=1)
        enddt = idx + timedelta(hours=1)
        maxgust = df.loc[idx]['windgust']
        meangust = df.loc[startdt : enddt]['windspd'].mean()
        pretemp = df.loc[startdt : idx]['temp'].mean()
        posttemp = df.loc[idx : enddt]['temp'].mean()
        tempchange = (df.loc[startdt : enddt]
                      .rolling('1800s')['temp']
                      .apply(lambda x: x[-1] - x[0])
                      .agg(['min', 'max']))
        maxtempchange = tempchange['max']
        mintempchange = tempchange['min']
        prschange = (df.loc[startdt : enddt]
                     .rolling('1800s')['stnp']
                     .apply(lambda x: x[-1] - x[0])
                     .agg(['min', 'max']))
        prsdrop = prschange['min']
        prsrise = prschange['max']
        dirchange = (df.loc[startdt : enddt]
                     .rolling('1800s')['winddir']
                     .apply(lambda x: wdir_diff(x[-1], x[0]))
                     .max())
        dfdata.loc[idx] = [maxgust/meangust, pretemp, posttemp, maxtempchange,
                           mintempchange, dirchange, prsdrop, prsrise]

        if maxgust > threshold:
            LOGGER.info(f"Extracting additional data for gust event on {datetime.strftime(idx, '%Y-%m-%d')}")
            deltavals = df.loc[startdt : enddt].index - idx
            gustdf = df.loc[startdt : enddt].set_index(deltavals)
            pct = ((gustdf.isnull() | gustdf.isna()).sum() * 100 / gustdf.index.size)
            qccols = ['windgust', 'temp', 'stnp', 'winddir']
            if np.any(pct[qccols] > 20.0):
                LOGGER.info("Missing values found in gust, temperature, pressure or wind direction data")
                continue

            gustdf['tempanom'] = gustdf['temp'] - gustdf['temp'].mean()
            gustdf['stnpanom'] = gustdf['stnp'] - gustdf['stnp'].mean()
            dirchange = (gustdf.rolling('1800s')['winddir']
                               .apply(lambda x: wdir_diff(x[-1], x[0])))
            gustdf['windchange'] = dirchange

            x = (gustdf.index/60/1_000_000_000)
            newdf = gustdf[['windgust', 'temp', 'tempanom', 'winddir', 'windchange',
                            'stnp', 'stnpanom', 'rainfall']]
            newdf['tdiff'] = x.values.astype(float)
            newdf['date'] = datetime.strftime(idx, "%Y-%m-%d")
            newdf['time'] = df.loc[startdt : enddt].index.values
            #plotEvent(newdf, idx, stnName, stnNum, outputDir, filename)
            frames.append(newdf)

    LOGGER.debug("Joining other observations to daily maximum wind data")
    dfmax = dfmax.join(dfdata)

    LOGGER.debug("Determining daily mean values")
    dfstats = df.groupby(['date']).aggregate({
        variable: ['mean', 'std', 'max'],
        'windspd': ['mean', 'std', 'max'],
        'temp': ['mean', 'min', 'max'],
        'temp1max': ['max'],
        'temp1min': ['min'],
        'wbtemp': ['mean', 'max'],
        'dewpoint': ['mean', 'max']})
    dfstats.columns = dfstats.columns.map('_'.join)
    if len(frames) > 0:
        eventdf = pd.concat(frames)
        return dfmax, dfstats, eventdf
    else:
        return dfmax, dfstats, None

def plotEvent(df: pd.DataFrame, dt: datetime, stnName: str,
              stnNum: int, outputDir: str, filename: str):
    """
    Plot a time history of the event, including the preceding
    and following hour of data


    :param df: `pd.DataFrame` containing the data
    :param dt: `datetime` object of a gust event
    :param str stnName: Station name
    :param int stnNum: Station identifier
    :param str outputDir: Output directory for data and figures
    :param str filename: Name of the file
    """

    LOGGER.debug(f"Plotting data for {filename} on {dt.strftime('%Y-%m-%d')}")
    fig, ax = plt.subplots(1, 1, figsize=(8, 4))
    df.set_index('tdiff', inplace=True)
    x = df.index # /60/1_000_000_000
    lns1 = ax.plot(x, df['windgust'], 'ko-', markerfacecolor='white',
                   label="Gust speed [km/h]")
    ax2 = ax.twinx()
    ax3 = ax.twinx()
    ax4 = ax.twinx()
    ax5 = ax.twinx()
    lns2 = ax2.plot(x, df['windchange'], 'go', markersize=3,
                    markerfacecolor='w', label='Wind direction change')
    lns3 = ax3.plot(x, df['tempanom'], 'r', label=r"Temperature anomaly [$^{o}$C]")
    lns4 = ax4.plot(x, df['stnpanom'], 'purple', label="Pressure anomaly [hPa]")
    lns5 = ax5.bar(x, df['rainfall'], width=0.75, label='Rainfall [mm]', color='b', alpha=0.5)
    ax3.spines['right'].set_position(("axes", 1.1))
    ax4.spines['right'].set_position(("axes", 1.2))
    ax5.spines['right'].set_position(("axes", 1.3))
    ax2.spines[['right']].set_color(lns2[0].get_color())
    ax3.spines[['right']].set_color(lns3[0].get_color())
    ax4.spines[['right']].set_color(lns4[0].get_color())
    ax5.spines[['right']].set_color('b')

    ax2.yaxis.label.set_color(lns2[0].get_color())
    ax3.yaxis.label.set_color(lns3[0].get_color())
    ax4.yaxis.label.set_color(lns4[0].get_color())
    ax5.yaxis.label.set_color('b')

    ymin, ymax = ax.get_ylim()
    ax.set_ylim((0, max(100, ymax)))
    # Fix the range of the wind change plot
    ax2.set_ylim((0, 180))
    # Set the rainfall limits to be 2 or higher
    ymin, ymax = ax5.get_ylim()
    ax5.set_ylim((0, max(2, ymax)))


    ax2.tick_params(axis='y', colors=lns2[0].get_color())
    ax3.tick_params(axis='y', colors=lns3[0].get_color())
    ax4.tick_params(axis='y', colors=lns4[0].get_color())
    ax5.tick_params(axis='y', colors='b')
    ax2.set_ylabel(r"Wind direction change [$^{\circ}$]")
    ax3.set_ylabel(r"Temperature anomaly [$^{\circ}$C]")
    ax4.set_ylabel(r"Pressure anomaly [hPa]")
    ax5.set_ylabel(r"Rainfall [mm]")
    ax2.grid(False)
    ax3.grid(False)
    ax4.grid(False)
    ax5.grid(False)

    ax.set_xlabel("Minutes")
    ax.set_ylabel("Gust wind speed [km/h]")

    ax.set_title(f"{stnName.rstrip()} ({stnNum}) {dt.strftime('%Y-%m-%d %H:%M UTC')}")
    dtstring = dt.strftime("%Y%m%d")
    basename = os.path.basename(filename)
    figname = basename.replace(".txt", f".{dtstring}.png")
    figname = os.path.join(outputDir, 'plots', figname)
    plt.savefig(figname, bbox_inches="tight")
    plt.close(fig)
    return

def dt(*args):
    """
    Convert args to `datetime`
    """
    return datetime(*args)

start()
