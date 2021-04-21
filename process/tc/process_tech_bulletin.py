import os
import re
import sys
import time
import logging
import argparse
import glob

from datetime import time, timedelta, datetime as dt
from configparser import ConfigParser, ExtendedInterpolation
from os.path import join as pjoin, realpath, isdir, dirname, splitext

import pandas as pd

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile, pInit
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

    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=False)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    if args.verbose:
        verbose = True

    pInit(configFile)
    main(config, verbose)

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

def cnfRefreshCachedIniFile(configFile):
    global config
    LOGGER.info(f"Reloading {configFile}")
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)
    #return config

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


def parseForecast(line):
    """
    Parse a line that is expected to contain forecast information and strip out
    latitude, longitude, the forecast hour (`tau`) and the central pressure

    """

    line.strip('\n')
    splitter = re.compile(r'\s*:\s+|\s+')
    fields = re.split(splitter, line)
    tau = int(fields[0].strip('+'))
    day, hr = fields[1].split('/')
    try:
        lat = -1*float(fields[2].strip('S'))
    except ValueError:
        LOGGER.debug(f"No forecast data for tau: +{tau:02d}")
        return None
    else:
        lon = float(fields[3].strip('E'))
        prs = float(fields[8])
        return (tau, day, hr, lat, lon, prs)


def processTimes(validTime, issueTime):
    """
    Calculate the actual valid time, if the issue time is recently after 00 UTC
    For example, if the issue time is 00:30 UTC, and the valid time is something like
    22:00 UTC, then we need to set the valid date back one day relative to the issue date.
    
    :param validTime: a :class:`datetime.time` instance that represents the time the data in the bulletin refers to
    :param issueTime: a :class:`datetime.datetime` instance that represents when the bulletin was issued
    
    :returns: a new :class:`datetime.datetime` instance for the valid time of the bulletin
    """
    if issueTime.hour == 0 & validTime.hour >=22:
        validDate = issueTime.date() - timedelta(days=1)
    else: 
        validDate = issueTime.date()
    return dt.combine(validDate, validTime.time())

def processFile(filename, outputDir):
    """
    Parse a text file to extract required data to form a track file
    
    :param str filename: Path to a file to process
    """
    
    idnum_regex = re.compile(r'^(ID\w\d+)')
    issue_ctr_regex = re.compile(r'^Issued by\s(.*)')
    issue_time_regex = re.compile(r'^at\:\s*(\d*)\s*(\w+)\s*(\d{1,2})\/(\d{2})\/(\d{4})')
    name_regex = re.compile(r'^Name\:\s*(.*)$')
    identifier_regex = re.compile(r'^Identifier\:\s*(\S*)')
    valid_time_regex = re.compile(r'^Data At\:\s*(\d*)(?:\s+)(\w{3})')
    lat_regex = re.compile(r'^Latitude\:\s*(\d+\.\d)(\w)')
    lon_regex = re.compile(r'^Longitude\:\s*(\d+\.\d)(\w)')
    loc_regex = re.compile(r'^Location.*\:\s\w*\s(\d{1,})\s(\w+)\s+(?:\(|\[)(\d+)\s(\w+)(?:\)|\])')
    init_dir_regex = re.compile(r'^Movement Towards\:\s*(.*)(?:\(|\[)(\d+)(.+)(?:\)|\])')
    init_speed_regex = re.compile(r'^Speed of movement\:\s+(\d+)\s+(\w*)\s+(?:\(|\[)(\d*)\s(.*)(?:\)|\])')
    init_pcentre_regex = re.compile(r'^Central Pressure\:\s*(\d*)\s*(\w*)')
    init_rmax_regex = re.compile(r'^Radius of Maximum Winds\:\s*(\d+)\s*(\w+)\s+(?:\(|\[)(\d+)\s(\w+)(?:\)|\])')
    missing_rmax_regex = re.compile(r'^Radius of Maximum Winds\:\s*$')
    vmax_mean_regex = re.compile(r'^Maximum 10-Minute.*\:\s+(\d+)\s(\w+)')
    vmax_gust_regex = re.compile(r'^Maximum 3-second.*\:\s+(\d+)\s(\w+)')
    poci_regex = re.compile(r'^Pressure.*outermost.*\:\s+(\d+)\s(\w+)')
    roci_regex = re.compile(r'^Radius.*outermost.*\:\s+(\d+)\s(\w+)')
    fcast_regex = re.compile(r'^\+(\d+)')

    tc_info = {}
    tc_fcast = pd.DataFrame(columns=['tau', 'datetime', 'lat', 'lon', 'pressure', 'rmax', 'poci'])
    
    with open(filename) as fh:
        for line in fh:
            idnum_match = re.match(idnum_regex, line)
            issue_ctr_match = issue_ctr_regex.match(line)
            issue_time_match = issue_time_regex.match(line)
            name_match = name_regex.match(line)
            identifier_match = identifier_regex.match(line)
            valid_time_match = valid_time_regex.match(line)
            lat_match = lat_regex.match(line)
            lon_match = lon_regex.match(line)
            loc_match = loc_regex.match(line)
            init_pcentre_match = init_pcentre_regex.match(line)
            init_rmax_match = init_rmax_regex.match(line)
            fcast_match = fcast_regex.match(line)
            poci_match = poci_regex.match(line)
            
            if idnum_match:
                tc_info['id_num'] = idnum_match.group(1)
                LOGGER.debug(tc_info['id_num'])
            if issue_ctr_match:
                tc_info['issue_ctr'] = issue_ctr_match.group(1)
                LOGGER.debug(tc_info['issue_ctr'])
            if issue_time_match:
                issue_time_str = "{4}-{3}-{2} {0} {1}".format(*issue_time_match.group(1,2,3,4,5))
                tc_info['issue_time'] = dt.strptime(issue_time_str, "%Y-%m-%d %H%M %Z")
                LOGGER.info(f"Issue time: {tc_info['issue_time']: %Y-%m-%d %H:%M}")
            if valid_time_match:
                valid_time_str = "{0} {1}".format(*valid_time_match.group(1,2))
                tc_info['valid_time'] = dt.strptime(valid_time_str, "%H%M %Z")
                tc_info['valid_date'] = processTimes(tc_info['valid_time'], tc_info['issue_time'])
                LOGGER.info("Valid date: {0}".format(dt.strftime(tc_info['valid_date'], "%Y-%m-%d %H:%M %Z")))
            if name_match:
                tc_info['tc_name'] = name_match.group(1)
                LOGGER.debug(f"TC name: {tc_info['tc_name']}")
            if identifier_match:
                tc_info['tc_identifier'] = identifier_match.group(1)
                LOGGER.debug(f"TC identifier: {tc_info['tc_identifier']}")
            if lat_match:
                # Assume we're in the southern hemisphere here:
                initLat = -1*float(lat_match.group(1))
            if lon_match:
                initLon = float(lon_match.group(1))
            if loc_match:
                rmax = loc_match.group(3)
                LOGGER.debug(f"RMAX value: {rmax} from accuracy")
            if init_pcentre_match:
                initPrs = float(init_pcentre_match.group(1))
            if init_rmax_match:
                rmax = init_rmax_match.group(3)
            if poci_match:
                poci = poci_match.group(1)
    
            if fcast_match:
                retval = parseForecast(line)
                if retval:
                    tau, day, hr, lat, lon, prs = retval
                    fcastdt = tc_info['valid_date'] + timedelta(hours=int(tau))
                    tc_fcast = tc_fcast.append({'tau':tau, "datetime":fcastdt,
                                     "lat":lat, "lon":lon, "pressure":prs,
                                     "rmax": None, "poci":None}, ignore_index=True)
    
    initData = [{'tau': 0, 'datetime': tc_info['valid_date'],
                 "lat": initLat, "lon": initLon, "pressure": initPrs,
                 "rmax": rmax, "poci": poci}]
    tc_fcast = pd.concat([pd.DataFrame(initData), tc_fcast], ignore_index=True)
    tc_fcast['rmax'] = rmax
    tc_fcast['poci'] = poci

    filename = f"tctrack.{tc_info['tc_identifier']}.{tc_info['valid_date']:%Y%m%d%H%M}.csv"
    LOGGER.info(f"Saving track data to {filename}")
    tc_fcast.to_csv(pjoin(outputDir, filename), index=False)
    return True

start()