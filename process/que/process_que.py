"""
process_que.py - move files from incoming folder to processing folder.

This program move files from a temporary incoming location to a processing
folder, to ensure the processing does not try and process partially written
files. The program is designed to be continuously running, checking
periodically for files and moving any new files as per the configuration.

Files are grouped into categories, enabling glob-style definitions to move
to destination folders. Default settings can be used for files that do not
match any of the defined categories.

Requirements:
1) a suitably defined conda environment
2) the pylib library of functions

.. code::

    CALL conda.bat activate process
    set PYTHONPATH=C:\Workspace\lib\python
    cd \WorkSpace\bin\process\que
    python process_que.py -c process_que.ini


"""

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
            logFile = pjoin(os.getcwd(), 'process_que.log')

    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=False)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    if args.verbose:
        verbose = True

    mainLoop(config)


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
    This is used to move files from a source directory to a destination
    directory, as specified for each category in the configuration file.
    It serves as the basis of `process_que.py`

    The function relies on the existence of global variables `g_files`
    and the `config` object

    :param config: A :class:`configparser.ConfigParser` object.
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
            destination = config.get(category, 'DestDir')
        if not os.path.exists(destination):
            os.mkdir(destination)
        for file in g_files[category]:
            fname = os.path.basename(file)
            dest_file = pjoin(destination, fname)
            try:
                LOGGER.debug(f"Moving {file} to {dest_file}")
                os.replace(file, dest_file)
                fileNum += 1

            except OSError:
                LOGGER.warn(f"Cannot move {file} to {dest_file}")
        LOGGER.info(f"Moved {fileNum} {category} files")

def cnfRefreshCachedIniFile(configFile: str):
    """
    Update the configuration file by reading from the file again.

    :param configFile: Path to an updated configuration file
    """
    global config
    LOGGER.info(f"Reloading {configFile}")
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)
    #return config

def mainLoop(config):
    """
    Main processing loop. All required settings are read from the
    :class:`configparser.ConfigParser` object. This initiates a continuous loop
    that sleeps for a defined interval between running actions. 

    :param config: A :class:`configparser.ConfigParser` object
    """
    logFile = config.get('Logging', 'LogFile')
    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=True)
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