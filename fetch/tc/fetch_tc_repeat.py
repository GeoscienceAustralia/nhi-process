import os
import sys
import time
import logging
import argparse
import glob
from configparser import ConfigParser, ExtendedInterpolation
from os.path import join as pjoin, realpath, isdir, dirname, splitext

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile
from files import flStartLog
from tendo import singleton

g_files = {}


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
    if args.verbose:
        verbose = True
    else:
        verbose = False

    mainLoop(config, verbose)


def cnfRefreshCachedIniFile(configFile):
    global config
    LOGGER.info(f"Reloading {configFile}")
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)


def mainLoop(config, verbose=False):
    global LOGGER
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

        processFiles(config)
        if interval > 0:
            LOGGER.info(f"Process complete. Waiting {interval} seconds")
            time.sleep(interval)
        else:
            break


def processFiles(config):
    global g_files
    global LOGGER
    unknownDir = config.get('Defaults', 'UnknownDir')
    defaultOriginDir = config.get('Defaults', 'OriginDir')
    LOGGER.debug(f"Origin directory: {defaultOriginDir}")
    if not os.path.exists(unknownDir):
        os.mkdir(unknownDir)

    for idx, category in config.items("Categories"):
        LOGGER.info(f"Processing {category}")
        action = config.get(category, "Action")

        os.system(action)


start()
