"""
archiveObs.py - archive axf and axf shape files to NAS directory

This program moves files from the incoming directory to a more permanent
folder (preferably on network storage). Essentially a house-keeping role that
ensures the incoming directory does not get too big.

Requirements:
1) a suitably defined conda environment
2) the pylib library of functions

.. code::

    CALL conda.bat activate process
    set PYTHONPATH=C:\Workspace\lib\python
    cd \WorkSpace\bin\process\obs
    python archiveObs.py -c archiveObs.ini

"""

import os
import logging
import argparse
import glob
import shutil
import re
from configparser import ConfigParser, ExtendedInterpolation
from os.path import join as pjoin, realpath, isdir, dirname

from files import flStartLog

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
    LOGGER = flStartLog(logFile, logLevel, verbose, datestamp)

    ListAllFiles(config)
    processFiles(config)

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
    LOGGER.debug(f"Expanding file spec {spec} for {category} files")

    files = sorted(glob.glob(spec))
    LOGGER.debug(f"{len(files)} files in {spec}")
    for file in files:
        if os.stat(file).st_size > 0:
            if file not in g_files[category]:
                g_files[category].append(file)

def expandFileSpecs(config, specs, category):
    for spec in specs:
        expandFileSpec(config, spec, category)


def ListAllFiles(config):
    """
    Populate a hash table of categories and files within each category

    :param config: :class:`ConfigParser` class containing required
        configuration details

    :returns: None - it populates the global `g_files` dict.
    """
    global g_files
    global LOGGER
    g_files = {}
    categories = config.items('Categories')
    for idx, category in categories:
        LOGGER.debug(f"Listing files for {category}")
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
            originDir = config.get(category, 'OriginDir')
            destination_base = config.get(category, 'DestDir',
                                          fallback=config.get('Defaults', 'DestDir'))
            LOGGER.info(f"Moving {category} files from {originDir}")
        if not os.path.exists(destination_base):
            os.mkdir(destination_base)
        current_month = ''
        current_year = ''
        for file in g_files[category]:
            fname = os.path.basename(file)
            year, month = getDate(fname)
            if year != current_year:
                # Build the year directory
                if not os.path.exists(pjoin(destination_base, year)):
                    os.mkdir(pjoin(destination_base, year))

            if month != current_month:
                # Build the month directory
                if not os.path.exists(pjoin(destination_base, year, month)):
                    os.mkdir(pjoin(destination_base, year, month))

            current_year = year
            current_month = month
            dest_file = pjoin(destination_base, year, month, fname)
            try:
                LOGGER.debug(f"Moving {file} to {dest_file}")
                shutil.move(file, dest_file)
                fileNum += 1

            except OSError:
                LOGGER.warning(f"Cannot move {file} to {dest_file}")
        LOGGER.info(f"Moved {fileNum} {category} files")

def getDate(filename):
    """
    Get the year & month of a file to help build the destination folder.

    Args:
        filename (str): _description_
    """
    regex = '(\w{8})\.(\w{4})\.(\w*)\.(\w*)\.(\d{4})(\d{2})(\d{2})(\d{2})\.*'
    m = re.match(regex, filename)
    year = m.group(5)
    month = m.group(6)
    return year, month

start()