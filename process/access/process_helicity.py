
import sys
import logging
import argparse
from configparser import ConfigParser, ExtendedInterpolation
from itertools import filterfalse
from os.path import join as pjoin, isfile, dirname, basename
from datetime import datetime, timedelta
from files import flStartLog, flProgramVersion

import xarray as xr
import cfgrib

from plotting import helicity


global LOGGER
DATETIMEFMT = "%Y%m%d%H"
DOMAINS = {"VT": "IDY25420",
           "SY": "IDY25421",
           "BN": "IDY25422",
           "PH": "IDY25423",
           "AD": "IDY25424",
           "DN": "IDY25425",
           "NQ": "IDY25426"}

g_files = {}
forecast_periods = {"00-12": (1, 13),
                    "12-24": (13, 25),
                    "24-36": (25, 37),
                    "00-36": (1, 37)}


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
    LOGGER.debug(f"Current time: {now}")
    fcast_time = now
    if now.hour < delay:
        # e.g. now.hour = 01 and delay = 3
        fcast_time = fcast_time - timedelta(cycle/24)
        fcast_hour = (fcast_time.hour // cycle) * cycle
        fcast_time = fcast_time.replace(hour=fcast_hour, minute=0, second=0, microsecond=0)
    else:
        fcast_hour = ((fcast_time.hour - delay) // cycle) * cycle
        fcast_time = fcast_time.replace(hour=fcast_hour, minute=0, second=0, microsecond=0)
    LOGGER.debug(f"Forecast time: {fcast_time}")
    return fcast_time


def checkFileList(filelist):
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

    if args.archive:
        processArchiveFile(config)
    else:
        main(config)


def processArchiveFile(config):
    pass


def main(config):
    """
    Main processing loop for current (near real-time) processing.

    :param config: :class:`ConfigParser` object that holds the configuration
    settings read from the configuration file

    """

    LOGGER.info("Running main loop for updraft helicity processing")
    provmsg = (f"{datetime.now():%Y-%m-%d %H:%M:%S}: {basename(sys.argv[0])}"
               f" -c {basename(configFile)} ({flProgramVersion(dirname(sys.argv[0]))})")
    LOGGER.debug(provmsg)
    provflag = False
    domain = config.get('Forecast', 'Domain')
    delay = config.getint('Forecast', 'Delay', fallback=2)
    group = config.get('Forecast', 'Group', fallback="helicity")
    inputPath = config.get('Files', 'SourceDir')
    outputPath = config.get('Files', 'DestDir', fallback=inputPath)

    fcast_time = currentCycle(delay=delay)
    fcast_time_str = fcast_time.strftime(DATETIMEFMT)
    LOGGER.info(f"Forecast time: {fcast_time_str}")

    for fp, rng in forecast_periods.items():
        timelist = [f"{t:03d}" for t in range(*rng)]
        filelist = [pjoin(inputPath, f"{DOMAINS[domain]}.APS3.{group}.slv.{fcast_time_str}.{t}.surface.grb2") for t in timelist]
        if not checkFileList(filelist):
            LOGGER.warning("Not all files exist")
            continue
        else:
            tds = processFiles(filelist)
            tds.attrs.update({"history":provmsg})
            LOGGER.info(f"Saving {DOMAINS[domain]} data for {fp} forecast period")
            helicity(tds.min_updraft_helicity, rng[1]-1,
                     pjoin(outputPath, f"{DOMAINS[domain]}.APS3.helicity.slv.{fcast_time_str}.{fp}.png"),
                     metadata={"history":provmsg})
            uda = tds.max_updraft_helicity.max(axis=0)
            dda = tds.min_updraft_helicity.min(axis=0)
            outds = xr.Dataset({"max_updraft_helicity": uda,
                                "min_updraft_helicity": dda},
                                attrs=tds.attrs)
            outds.to_netcdf(pjoin(outputPath, f"{DOMAINS[domain]}.APS3.helicity.slv.{fcast_time_str}.{fp}.surface.nc4"))


def processFiles(filelist):
    """
    Process a list of files to convert from the native grib format to netcdf,
    and additionally aggregate to time periods based on the 0-12, 12-24, 24-36
    and 0-36 hour time periods

    :param list filelist: list of filenames in the input folder

    :returns: :class:`xarray.Dataset`

    """

    dslist = []
    for filename in filelist:
        LOGGER.debug(f"Reading data from {filename}")
        ds = cfgrib.open_datasets(filename)

        hmaxds = ds[1]
        hminds = ds[0]
        nds = xr.Dataset()
        nds['max_updraft_helicity'] = hmaxds.unknown
        nds['min_updraft_helicity'] = hminds.unknown
        nds.attrs = hmaxds.attrs

        nds.min_updraft_helicity.attrs['long_name'] = 'min_updraft_helicity'
        nds.min_updraft_helicity.attrs['standard_name'] = 'Minimum updraft helicity'
        nds.min_updraft_helicity.attrs['units'] = 'm2 s-2'

        nds.max_updraft_helicity.attrs['long_name'] = 'max_updraft_helicity'
        nds.max_updraft_helicity.attrs['standard_name'] = 'Maximum updraft helicity'
        nds.max_updraft_helicity.attrs['units'] = 'm2 s-2'
        dslist.append(nds)

    LOGGER.debug("Concatenating datasets")
    outds = xr.concat(dslist, 'time')

    return outds


start()
