import os
import re
import glob
import zipfile
import argparse
import logging
from os.path import join as pjoin, basename, dirname, realpath, isdir, splitext
from datetime import datetime
from configparser import ConfigParser, ExtendedInterpolation
import pandas as pd

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile, pInit
from files import flStartLog, flGetStat

LOGGER = logging.getLogger()

PATTERN = re.compile(r".*Data.*\.txt")

def start():
    p = argparse.ArgumentParser()
    p.add_argument('-c', '--config_file', help="Configuration file")
    p.add_argument('-v', '--verbose', help="Verbose output", 
                   action='store_true')
    args = p.parse_args()

    global configFile

    configFile = args.config_file
    verbose = args.verbose
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)

    pInit(configFile)
    main(config, verbose)

def main(config, verbose=False):
    logFile = config.get('Logging', 'LogFile')
    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=verbose)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    LOGGER = flStartLog(logFile, logLevel, verbose, datestamp)

    ListAllFiles(config)
    processFiles(config)

def ListAllFiles(config):
    global g_files
    global LOGGER
    g_files = {}
    categories = config.items('Categories')
    for idx, category in categories:
        specs = []
        items = config.items(category)
        for k,v in items:
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
                else:
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
        for f in gen:
            LOGGER.info(f"Loading data from {f}")
            with zz.open(f) as fh:
                dfmax = extractDailyMax(fh)
                LOGGER.info(f"Writing data to {pjoin(outputDir, f)}")
                dfmax.to_csv(pjoin(outputDir, f), index=False)
        rc = True
    else:
        LOGGER.warn(f"{filename} is not a zip file")
        rc = False
    return rc


def extractDailyMax(filename, variable='windgust'):
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
             'mslp', 'mslpq', 'stnp', 'stnpq','end']
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

    df = pd.read_csv(filename, sep=',', index_col=False, dtype=dtypes,
                     names=names, header=0,
                     parse_dates={'datetime':[2,3,4,5,6]},
                     date_parser=dt, na_values=['####'],
                     skipinitialspace=True)
    df['date'] = df.datetime.dt.date
    dfmax = df.loc[df.groupby(['date'])[variable].idxmax().dropna()]
    return dfmax

def dt(*args):
    """
    Convert args to `datetime`
    """
    return datetime(*args)

start()
