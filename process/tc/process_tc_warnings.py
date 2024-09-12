import os
import re
import sys
import time
import logging
import argparse
import glob
import zipfile

from datetime import time, timedelta, datetime as dt
from configparser import ConfigParser, ExtendedInterpolation
from os.path import join as pjoin, realpath, isdir, dirname, splitext

import pandas as pd

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile, pInit, pArchiveTimestamp
from files import flStartLog, flGetStat
from tendo import singleton

g_files = {}
g_output_path = os.getcwd()
LOGGER = logging.getLogger()


def start():
    """
    Handle command line args, start loggers, and call
    processing functions
    """

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

    logFile = config.get('Logging', 'LogFile')
    logdir = dirname(realpath(logFile))

    # if log file directory does not exist, create it
    if not isdir(logdir):
        try:
            os.makedirs(logdir)
        except OSError:
            logFile = pjoin(os.getcwd(), 'fetch.log')

    verbose = config.getboolean('Logging', 'Verbose', fallback=False)

    if args.verbose:
        verbose = True

    pInit(configFile)
    pArchiveTimestamp(config.getboolean('Preferences', 'ArchiveTimestamp'))
    main(config, verbose)


def ListAllFiles(config):
    global g_files
    global LOGGER
    g_files = {}
    categories = config.items('Categories')
    for idx, category in categories:
        specs = []
        items = config.items(category)
        for k, v in items:
            if v == '':
                specs.append(k)
        expandFileSpecs(config, specs, category)


def cnfRefreshCachedIniFile(configFile):
    global config
    LOGGER.info(f"Reloading {configFile}")
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)
    # return config


def expandFileSpec(config, spec, category):
    """
    Given a file specification and a category, list all files that match the
    spec and add them to the :dict:`g_files` dict.
    The `category` variable corresponds to a section in the configuration file
    that includes an item called 'OriginDir'.
    The given `spec` is joined to the `category`'s 'OriginDir' and all
    matching files are stored in a list in :dict:`g_files` under the
    `category` key.

    :param config: `ConfigParser` object
    :param str spec: A file specification. e.g. '*.*' or 'IDW27*.txt'
    :param str category: A category that has a section in the source
                         configuration file
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


def main(config, verbose=False):
    logFile = config.get('Logging', 'LogFile')
    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=verbose)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    LOGGER = flStartLog(logFile, logLevel, verbose, datestamp)

    ListAllFiles(config)
    processFiles(config)


def processFiles(config):

    global g_files
    global LOGGER
    unknownDir = config.get('Defaults', 'UnknownDir')
    originDir = config.get('Defaults', 'OriginDir')
    deleteWhenProcessed = config.getboolean(
        'Files', 'DeleteWhenProcessed', fallback=False
        )
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
        cutOffDelta = config.getint(category, "CutOffDelta", fallback=6)
        cutOffDateTime = dt.utcnow() - timedelta(hours=cutOffDelta)
        LOGGER.debug(f"Cutoff time is: {cutOffDateTime}")
        if dt.strptime(moddate, "%c") < cutOffDateTime:
            LOGGER.info(f"{f} is too old (> {cutOffDelta} hours old). Skipping")
            continue
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


def processTimes(validTime, issueTime):
    """
    Calculate the actual valid time, if the issue time is recently after 00 UTC
    For example, if the issue time is 00:30 UTC, and the valid time is
    something like 22:00 UTC, then we need to set the valid date back one day
    relative to the issue date.

    :param validTime: a :class:`datetime.time` instance that represents the
                      time the data in the bulletin refers to
    :param issueTime: a :class:`datetime.datetime` instance that represents
                      when the bulletin was issued

    :returns: a new :class:`datetime.datetime` instance for the valid time
              of the bulletin
    """
    if issueTime.hour == 0 & validTime.hour >= 22:
        validDate = issueTime.date() - timedelta(days=1)
    else:
        validDate = issueTime.date()
    return dt.combine(validDate, validTime.time())


def processFile(filename, outputDir):
    """
    Process a zip file containing geospatial data related to TC warnings

    :param filename: Name of the zip file to process
    :type filename: str
    :param outputDir: Path to store output data
    :type outputDir: str
    """

    LOGGER.info(f"Processing {filename}")
    zz = zipfile.ZipFile(filename)
    zz.extractall(path=outputDir)
    return True


start()
