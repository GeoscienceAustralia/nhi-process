import os
import sys
import glob
import logging
import argparse
from configparser import ConfigParser, ExtendedInterpolation
from itertools import filterfalse
from os.path import join as pjoin, isfile, dirname, basename, splitext, realpath
from datetime import datetime, timedelta
from plotting import windgust

from files import flStartLog, flProgramVersion
from process import pAlreadyProcessed, pWriteProcessedFile

import xarray as xr
import pandas as pd
import numpy as np

global LOGGER
DATETIMEFMT = "%Y%m%d%H"
DOMAINS = {"VT":"IDY25420",
           "SY":"IDY25421",
           "BN":"IDY25422",
           "PH":"IDY25423",
           "AD":"IDY25424",
           "DN":"IDY25425"}

g_files = {}
forecast_periods = {"00-12": (0, 13),
                    "12-24": (14, 25),
                    "24-36": (26, 37),
                    "00-36": (0, 37)}

def currentCycle(now=datetime.utcnow(), cycle=6, delay=3):
    """
    Calculate the forecast start time based on the current datetime, 
    how often the forecast updates (the cycle) and the delay between
    the forecast time and when it becomes available

    :param now: `datetime` representation of the "current" time. Default is
    the current UTC datetime
    :param int cycle: The cycle of forecasts, in hours
    :param int delay: Delay between the initial time of the forecast and when
    the forecast is published (in hours)

    :returns: `datetime` instance of the most recent forecast
    """
    fcast_time = now
    if now.hour < delay:
        # e.g. now.hour = 01 and delay = 3
        fcast_time = fcast_time - timedelta(cycle/24)
        fcast_hour = (fcast_time.hour // cycle) * cycle
        fcast_time = fcast_time.replace(hour=fcast_hour, minute=0, second=0, microsecond=0)
    else: 
        fcast_hour = ((fcast_time.hour - delay) // cycle) * cycle
        fcast_time = fcast_time.replace(hour=fcast_hour, minute=0, second=0, microsecond=0)
    return fcast_time

def checkFileList(filelist):
    if all([isfile(f) for f in filelist]):
        LOGGER.debug("all files exist")
        return True
    else:
        for f in list(filterfalse(isfile, filelist)):
            LOGGER.warning(f"Missing: {f}")
        return False

def start():
    """
    Start the process (logging, config, etc.) and call the main process
    """
    p = argparse.ArgumentParser()

    p.add_argument('-c', '--config_file', help="Configuration file")
    p.add_argument('-v', '--verbose',
                   help="Verbose output", 
                   action='store_true')
    args = p.parse_args()

    global configFile
    global LOGGER

    configFile = args.config_file
    verbose = False
    if args.verbose:
        verbose = True

    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(configFile)
    logFile = config.get('Logging', 'LogFile')
    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.get('Logging', 'Verbose', fallback=verbose)
    datestamp = config.get('Logging', 'Datestamp', fallback=False)
    LOGGER = flStartLog(logFile, logLevel, verbose, datestamp)

    main(config)


def main(config):
    LOGGER.info("Running main loop for wind gust processing")
    provmsg = (f"{datetime.now():%Y-%m-%d %H:%M:%S}: {basename(sys.argv[0])}"
               f" -c {basename(configFile)} ({flProgramVersion(dirname(sys.argv[0]))})")
    LOGGER.debug(provmsg)
    provflag = False
    domain = config.get('Forecast', 'Domain')
    delay = config.getint('Forecast', 'Delay', fallback=2)
    group = config.get('Forecast', 'Group', fallback="group2")
    inputPath = config.get('Files', 'SourceDir')
    outputPath = config.get('Files', 'DestDir', fallback=inputPath)

    fcast_time = currentCycle(delay=delay)
    fcast_time_str = fcast_time.strftime(DATETIMEFMT)
    LOGGER.info(f"Forecast time: {fcast_time_str}")

    for fp, rng in forecast_periods.items():
        timelist = [f"{t:03d}" for t in range(*rng)]
        filelist = [pjoin(inputPath, f"{DOMAINS[domain]}.APS3.{group}.slv.{fcast_time_str}.{t}.surface.nc4") for t in timelist]
        if not checkFileList(filelist):
            LOGGER.warning("Not all files exist")
            continue
        tds = xr.open_mfdataset(filelist, combine='by_coords')
        tda = tds.wndgust10m
        tda.attrs['accum_type'] = 'time: maximum'
        lon = tds.lon
        lat = tds.lat
        newda = xr.DataArray(tda.max(axis=0), coords=[lat, lon],
                            dims=['lat', 'lon'], attrs=tda.attrs)
        # Add provenance message to the netcdf file

        if 'history' in tds.attrs:
            tds.attrs['history'] = tds.attrs['history'] + provmsg
        else:
            tds.attrs.update({"history":provmsg})
        ds = xr.Dataset({"wndgust10m": newda}, attrs=tds.attrs)
        LOGGER.info(f"Saving {DOMAINS[domain]} data for {fp} forecast period")
        ds.to_netcdf(pjoin(outputPath, f"{DOMAINS[domain]}.APS3.wndgust10m.slv.{fcast_time_str}.{fp}.surface.nc4"))
        windgust(tda, rng[1]-1, 
                 pjoin(outputPath, f"{DOMAINS[domain]}.APS3.wndgust10m.slv.{fcast_time_str}.{fp}.png"),
                 metadata={"history":provmsg})


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


start()