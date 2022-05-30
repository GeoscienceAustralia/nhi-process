import sys
import argparse
from configparser import ConfigParser, ExtendedInterpolation
from itertools import filterfalse
from os.path import join as pjoin, isfile, dirname, basename, splitext, realpath
from datetime import datetime, timedelta
from plotting import precip

from files import flStartLog, flProgramVersion, flGetStat
from process import pWriteProcessedFile, pArchiveFile, pAlreadyProcessed, pInit
from dtutils import currentCycle

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
           "DN":"IDY25425",
           "NQ":"IDY25426"}

g_files = {}
forecast_periods = {"00-12": (0, 13),
                    "12-24": (14, 25),
                    "24-36": (26, 37)}

def checkFileList(filelist: list) -> bool:
    """
    Check that all required files exist

    :param list filelist: List of files required to proceed with processing

    :returns: `True` if all files exist, `False` otherwise.
    """

    if all([isfile(f) for f in filelist]):
        LOGGER.debug("All required files exist")
        return True
    else:
        for f in list(filterfalse(isfile, filelist)):
            LOGGER.warning(f"Missing: {f}")
        return False
    
def checkProcessed(filelist: list) -> bool:
    rclist = []
    for file in filelist:
        directory, fname, md5sum, moddate = flGetStat(file)
        if pAlreadyProcessed(directory, fname, "md5sum", md5sum):
            LOGGER.debug(f"Already processed {file}")
            rclist.append(True)
    if any(rclist):
        return True
    else:
        return False

def start():
    """
    Start the process (logging, config, etc.) and call the main process
    """
    p = argparse.ArgumentParser()

    p.add_argument('-c', '--config_file', help="Configuration file")
    p.add_argument('-a', '--archive', help="Archive file processing", action='store_true')
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
    verbose = config.getboolean('Logging', 'Verbose', fallback=verbose)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    LOGGER = flStartLog(logFile, logLevel, verbose, datestamp)
    pInit(configFile)

    if args.archive:
        processArchiveFile(config)
    else:
        main(config)


def main(config):
    """
    Main processing loop for current (near real-time) processing.

    :param config: :class:`ConfigParser` object that holds the configuration
    settings read from the configuration file

    """

    LOGGER.info("Running main loop for rainfall processing")
    provmsg = (f"{datetime.now():%Y-%m-%d %H:%M:%S}: {basename(sys.argv[0])}"
               f" -c {basename(configFile)} ({flProgramVersion(dirname(sys.argv[0]))})")
    LOGGER.debug(provmsg)
    provflag = False
    domain = config.get('Forecast', 'Domain')
    delay = config.getint('Forecast', 'Delay', fallback=2)
    group = config.get('Forecast', 'Group', fallback="group2")
    inputPath = config.get('Files', 'SourceDir')
    outputPath = config.get('Files', 'DestDir', fallback=inputPath)
    deleteWhenProcessed = config.getboolean('Files', 'DeleteWhenProcessed', fallback=False)

    fcast_time = currentCycle(delay=delay)
    fcast_time_str = fcast_time.strftime(DATETIMEFMT)
    LOGGER.info(f"Forecast time: {fcast_time_str}")

    for fp, rng in forecast_periods.items():
        timelist = [f"{t:03d}" for t in range(*rng)]
        filelist = [pjoin(inputPath, f"{DOMAINS[domain]}.APS3.{group}.slv.{fcast_time_str}.{t}.surface.nc4") for t in timelist]
        if not checkFileList(filelist):
            LOGGER.warning("Not all files exist")
            continue
        if checkProcessed(filelist):
            LOGGER.info("Already processed files")
            continue

        tds = xr.open_mfdataset(filelist, combine='by_coords')
        tda = tds.accum_prcp
        tda.attrs['accum_type'] = 'accumulative'
        if 'history' in tds.attrs:
            tds.attrs['history'] = tds.attrs['history'] + provmsg
        else:
            tds.attrs.update({"history":provmsg})
        ds = xr.Dataset({"accum_prcp": tda}, attrs=tds.attrs)
        LOGGER.info(f"Saving {DOMAINS[domain]} data for {fp} forecast period")
        ds.to_netcdf(pjoin(outputPath, f"{DOMAINS[domain]}.APS3.precip.slv.{fcast_time_str}.{fp}.surface.nc4"))
        precip(tda, rng[1]-1, 
               pjoin(outputPath, f"{DOMAINS[domain]}.APS3.precip.slv.{fcast_time_str}.{fp}.png"),
               metadata={"history":provmsg})
        tds.close()
        for file in filelist:
            pWriteProcessedFile(file)
            pArchiveFile(file)

    LOGGER.info("Completed processing")


def processArchiveFile(config):
    """
    Process an archive ACCESS-C file. Requires a modified configuration file,
    and the data file to be prepared using the historical archive of ACCESS-C
    data available on the NCI (project wr45).

    Source: https://dx.doi.org/10.25914/608a993391647

    The following command will merge the required analysis and forecast time
    periods for use in this function:

    `cdo mergetime
        /g/data/wr45/ops_aps3/access-<domain>/1/<YYYYMMDD>/<HHMM>/an/sfc/wndgust10m.nc
        /g/data/wr45/ops_aps3/access-<domain>/1/<YYYYMMDD>/<HHMM>/fc/sfc/wndgust10m.nc
        <DOMAINS[domain]>.APS3.group2.wndgust10m.<YYMMDDHH>.surface.nc4`

    Here <domain> would be one of 'vt', 'sy', 'ad', 'bn', 'dn' or 'ph' and
    <DOMAINS[domain]> would be the value of the dict defined above in this file.
    """
    LOGGER.info(f"Processing an archive ACCESS file")
    provmsg = (f"{datetime.now():%Y-%m-%d %H:%M:%S}: {basename(sys.argv[0])}"
               f" -c {basename(configFile)} ({flProgramVersion(dirname(sys.argv[0]))})")
               

    LOGGER.debug(provmsg)
    provflag = False
    domain = config.get('Forecast', 'Domain')
    group = config.get('Forecast', 'Group', fallback="group2")
    fcast_time = config.get('Forecast', 'Time') # Must be YYYYMMDDHH

    inputPath = config.get('Files', 'SourceDir')
    outputPath = config.get('Files', 'DestDir', fallback=inputPath)
    filename = pjoin(inputPath, f"{DOMAINS[domain]}.APS3.{group}.precip.{fcast_time}.surface.nc4")
    sourcemsg = ("APS3 ACCESS Numerical Weather Prediction (NWP) Models "
                 "- Operational Reference Data Collection "
                 "https://dx.doi.org/10.25914/608a993391647")

    try:
        tds = xr.open_dataset(filename)
    except FileNotFoundError:
        LOGGER.exception(f"Cannot open {filename}")
        raise
    if 'history' in tds.attrs:
        tds.attrs['history'] = tds.attrs['history'] + provmsg
    else:
        tds.attrs.update({"history":provmsg})
    if 'source' in tds.attrs:
        tds.attrs['source'] = tds.attrs['source'] + sourcemsg
    else:
        tds.attrs.update({'source':sourcemsg})

    for fp, rng in forecast_periods.items():
        tda = tds.isel(time=slice(*rng)).wndgust10m
        tda.attrs['accum_type'] = 'time: maximum'
        lon = tds.lon
        lat = tds.lat
        newda = xr.DataArray(tda.max(axis=0), coords=[lat, lon],
                             dims=['lat', 'lon'], attrs=tda.attrs)
        ds = xr.Dataset({"wndgust10m": newda}, attrs=tds.attrs)
        LOGGER.info(f"Saving {DOMAINS[domain]} data for {fp} forecast period")
        ds.to_netcdf(pjoin(outputPath, f"{DOMAINS[domain]}.APS3.precip.slv.{fcast_time}.{fp}.surface.nc4"))
        precip(tda, rng[1]-1,
                 pjoin(outputPath, f"{DOMAINS[domain]}.APS3.precip.slv.{fcast_time}.{fp}.png"),
                 metadata={"history":provmsg})

start()