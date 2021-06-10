import os
import re
import glob
import zipfile
import argparse
import logging
from os.path import join as pjoin
from datetime import datetime, timedelta
from configparser import ConfigParser, ExtendedInterpolation
import pandas as pd

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile, pInit
from files import flStartLog, flGetStat

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
    processFiles(config)

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

def processFiles(config):
    """
    Process a list of files in each category
    """
    global g_files
    global LOGGER
    unknownDir = config.get('Defaults', 'UnknownDir')
    originDir = config.get('Defaults', 'OriginDir')
    deleteWhenProcessed = config.getboolean('Files', 'DeleteWhenProcessed', fallback=False)
    archiveWhenProcessed = config.getboolean('Files', 'ArchiveWhenProcessed', fallback=True)
    outputDir = config.get('Output', 'Path', fallback=unknownDir)
    LOGGER.debug(f"Origin directory: {originDir}")
    LOGGER.debug(f"DeleteWhenProcessed: {deleteWhenProcessed}")
    LOGGER.debug(f"Output directory: {outputDir}")
    if not os.path.exists(unknownDir):
        os.mkdir(unknownDir)

    category = "Input"
    for f in g_files[category]:
        LOGGER.info(f"Processing {f}")
        directory, fname, md5sum, moddate = flGetStat(f)
        if pAlreadyProcessed(directory, fname, "md5sum", md5sum):
            LOGGER.info(f"Already processed {f}")
        else:
            if processFile(f, outputDir):
                LOGGER.debug(f"Successfully processed {f}")
                pWriteProcessedFile(f)
                if deleteWhenProcessed:
                    os.unlink(f)
                elif archiveWhenProcessed:
                    pArchiveFile(f)

def processFile(filename, outputDir):
    """
    process a file and store output in the given output directory
    """
    LOGGER.info(f"Processing {filename}")
    if zipfile.is_zipfile(filename):
        zz = zipfile.ZipFile(filename)
        filelist = zz.namelist()
        gen = (f for f in filelist if PATTERN.match(f))
        stnfile = [f for f in filelist if STNFILE.match(f)][0]
        stnlist = getStationList(zz.open(stnfile))
        for f in gen:
            LOGGER.info(f"Loading data from {f}")
            m = PATTERN.match(f)
            stnNum = int(m.group(1))
            stnState = stnlist.loc[stnlist.stnNum==stnNum, 'stnState'].values[0]
            LOGGER.debug(f"Station number: {stnNum} ({stnState})")
            with zz.open(f) as fh:
                dfmax = extractDailyMax(fh, stnState)
                LOGGER.info(f"Writing data to {pjoin(outputDir, f)}")
                dfmax.to_csv(pjoin(outputDir, f), index=False)
        rc = True
    else:
        LOGGER.warn(f"{filename} is not a zip file")
        rc = False
    return rc

def getStationList(stnfile):
    LOGGER.debug(f"Retrieving list of stations from {stnfile}")
    colnames = ["id", 'stnNum', 'rainfalldist', 'stnName', 'stnOpen', 'stnClose',
            'stnLat', 'stnLon', 'stnLoc', 'stnState', 'stnElev', 'stnBarmoeterElev',
            'stnWMOIndex', 'stnDataStartYear', 'stnDataEndYear',
            'pctComplete', 'pctY', 'pctN', 'pctW', 'pctS', 'pctI']
    df = pd.read_csv(stnfile, sep=',', index_col=False, names=colnames,
                     keep_default_na=False, converters={'stnState': str.strip})
    return df

def extractDailyMax(filename, stnState, variable='windgust'):
    """
    Extract daily maximum value of `variable` from 1-minute observation records
    contained in `filename`

    :param filename: str, path object or file-like object
    :param str variable: the variable to extract daily maximum values

    :returns: `pandas.DataFrame`

    """
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
    LOGGER.debug(f"Reading station data from {filename}")
    df = pd.read_csv(filename, sep=',', index_col=False, dtype=dtypes,
                     names=names, header=0,
                     parse_dates={'datetime':[7, 8, 9, 10, 11]},
                     date_parser=dt, na_values=['####'],
                     skipinitialspace=True)

    # Hacky way to convert from local standard time to UTC:
    LOGGER.debug("Converting from local to UTC time")
    df['datetime'] = df.datetime - timedelta(hours=TZ[stnState])
    df['date'] = df.datetime.dt.date
    LOGGER.debug("Determining daily maximum wind speed record")
    dfmax = df.loc[df.groupby(['date'])[variable].idxmax().dropna()]
    return dfmax

def dt(*args):
    """
    Convert args to `datetime`
    """
    return datetime(*args)

start()
