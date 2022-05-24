import os
import sys
import time
import logging
import argparse
import glob
import subprocess
from datetime import datetime, timedelta

from configparser import ConfigParser, ExtendedInterpolation
from os.path import join as pjoin, realpath, isdir, dirname, splitext

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile
from files import flStartLog, flModDate
from tendo import singleton

g_files = {}
LOGGER = logging.getLogger()
def start():
    """
    Handle command line args, start loggers, and call
    processing functions
    """

    p = argparse.ArgumentParser()

    p.add_argument('-c', '--config_file', help="Configuration file")
    p.add_argument('-v', '--verbose',
                   help="Verbose output", 
                   action='store_true')
    args = p.parse_args()

    global configFile

    configFile = args.config_file
    verbose = args.verbose
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)

    logFile = config.get('Logging', 'LogFile')
    logdir = dirname(realpath(logFile))

    # if log file directory does not exist, create it
    if not isdir(logdir):
        try:
            os.makedirs(logdir)
        except OSError:
            logFile = pjoin(os.getcwd(), 'fetch.log')

    verbose = False
    if args.verbose:
        verbose = True

    mainLoop(config, verbose)


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


def processFiles(config):
    """
    This is used to move files from a source directory to a destination directory, 
    as specified for each category in the configuration file. It serves as the 
    basis of `process_que.py`
    
    The function relies on the existence of global variables `g_files` and the `config` object
    """

    global g_files
    global LOGGER
    unknownDir = config.get('Defaults', 'UnknownDir')
    originDir = config.get('Defaults', 'OriginDir')
    LOGGER.debug(f"Origin directory: {originDir}")
    if not os.path.exists(unknownDir):
        os.mkdir(unknownDir)

    categories = config.items('Categories')
    for idx, category in categories:
        LOGGER.info(f"Processing {category} files")
        if category in g_files:
            fileNum = 0
            cutoffNum = config.getint(category, 'NumFiles')
            # Cut off time difference given in hours:
            cutoffDelta = config.getint(category, 'CutoffTime', fallback=-6)
            cutoffDate = datetime.now() + timedelta(cutoffDelta/24)
            LOGGER.debug(f"Cutoff time: {cutoffDate}")
            action = config.get(category, 'Action')
            for f in g_files[category]:
                file_date = flModDate(f, dateformat=None)
                if file_date < cutoffDate:
                    LOGGER.info(f"{f} is too old")
                    continue
                fileNum += 1
            if fileNum >= cutoffNum:
                subprocess.call(action)
            else:
                LOGGER.info(f"There are {fileNum} {category} files. Need {cutoffNum}")


def cnfRefreshCachedIniFile(configFile):
    """
    Update the contents of the configuration by re-reading the configuration file

    :param str configFile: path to the configuration file.

    :returns: Updates the global `config` object
    """
    global config
    LOGGER.info(f"Reloading {configFile}")
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)

def mainLoop(config, verbose=False):

    logFile = config.get('Logging', 'LogFile')
    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=verbose)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    interval = config.getint('Repeat', 'Interval', fallback=0)
    LOGGER = flStartLog(logFile, logLevel, verbose, datestamp)

    while True:
        if interval < 0:
            LOGGER.exception("Interval must be greater than or equal to zero")
            sys.exit()
        LOGGER.debug(f"Interval: {interval} seconds")

        if config.getboolean("Preferences", "RefreshConfigFile", fallback=True):
            cnfRefreshCachedIniFile(configFile)

        ListAllFiles(config)
        processFiles(config)
        if interval > 0:
            LOGGER.info(f"Process complete. Waiting {interval} seconds")
            time.sleep(interval)
        else:
            LOGGER.info("Running once and exiting")
            break


def expandFileSpec(config, spec, category):
    """
    Given a file specification and a category, list all files that match the spec and add them to the :dict:`g_files` dict. 
    The `category` variable corresponds to a section in the configuration file that includes an item called 'OriginDir'. 
    The given `spec` is joined to the `category`'s 'OriginDir' and all matching files are stored in a list in 
    :dict:`g_files` under the `category` key.
    
    :param config: `ConfigParser` object 
    :param str spec: A file specification. e.g. '*.*' or 'IDW27*.txt'
    :param str category: A category that has a section in the source configuration file
    """
    global LOGGER
    if category not in g_files:
        g_files[category] = []

    origindir = config.get(category, 'OriginDir',
                           fallback=config.get('Defaults', 'OriginDir'))
    spec = pjoin(origindir, spec)
    files = glob.glob(spec)
    for file in files:
        if os.stat(file).st_size > 0:
            if file not in g_files[category]:
                g_files[category].append(file)

def expandFileSpecs(config, specs, category):
    for spec in specs:
        expandFileSpec(config, spec, category)

start()