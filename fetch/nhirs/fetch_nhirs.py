"""
Fetch data from the NHIRS WFS and store in an archive file geodatabase.

The destination geodatabase and feature class are defined in a configuration
file, along with the layers to retrieve.

Run the following command at the command prompt to activate the ArcGIS Pro
Python environment:

set CONDA_NEW_ENV=arcgispro-py3
CALL "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\activate.bat" "%CONDA_NEW_ENV%"


"""

import os
import sys
import arcpy
import logging
import argparse
import datetime
from dtutils import currentCycle
from configparser import ConfigParser, ExtendedInterpolation

global LOGGER

DATETIMEFMT = "%Y%m%d%H"


def alreadyProcessed(workspace, layername):
    """
    Check if a layer already exists in a workspace.

    Args:
        workspace (str): Workspace
        layername (str): feature class layer name

    Returns:
        Bool: True if the layer exists in the given workspace,
        False otherwise
    """
    arcpy.env.workspace = workspace
    if arcpy.Exists(layername):
        LOGGER.debug(f"{layername} already exists")
        return True
    else:
        return False


def main(config):
    """
    Main processing loop to retrieve NHIRS data from WFS

    :param config: :class:`ConfigParser` object containing
    configuration options

    """

    maxfeatures = config.get("Defaults", "MaxFeatures", fallback=40000)
    sourceWFS = config.get("Defaults", "Source")
    destGDB = config.get("Defaults", "Geodatabase")
    featureClass = config.get("Domain", "FeatureClass")
    delay = config.getint("Domain", "Delay", fallback=3)
    destination = f"{destGDB}/{featureClass}"
    fcast_time = currentCycle(delay=delay)
    fcast_time_str = fcast_time.strftime(DATETIMEFMT)

    LOGGER.debug(f"Forecast time string: {fcast_time_str}")
    LOGGER.info(f"Retrieving data from {sourceWFS}")
    LOGGER.info(f"Data will be stored at {destination}")
    layers = config.items("Layers")

    temppath = "C:/WorkSpace/temp.gdb"
    LOGGER.debug(f"Temporary storage: {temppath}")

    for idx, layername in layers:
        outname = f"{layername}_{fcast_time_str}"
        LOGGER.debug(outname)
        arcpy.env.workspace = temppath
        if alreadyProcessed(destination, outname):
            LOGGER.info((f"{outname} already exists in {destination}"
                         " - have you already fetched this data?"))

            continue
        LOGGER.info(f"Retrieving layer {idx} of {len(layers)} layers")
        try:
            arcpy.conversion.WFSToFeatureClass(
                sourceWFS,
                layername,
                temppath,
                outname,
                max_features=maxfeatures
            )
        except Exception:
            msgs = arcpy.GetMessages()
            LOGGER.error(msgs)
        else:
            # nfeatures = arcpy.GetCount_management(outname)
            LOGGER.info(f"Retrieved {outname} features from WFS")

        infeatures = f"{temppath}/{outname}"
        arcpy.env.workspace = destination
        rc = 0
        if arcpy.Exists(outname):
            LOGGER.info((f"{outname} already exists in {destination}"
                         " - have you already fetched this data?"))
        else:
            LOGGER.info(f"Moving {infeatures} to {destination}")
            try:
                arcpy.conversion.FeatureClassToFeatureClass(
                    infeatures, destination, outname
                )
            except Exception:
                msgs = arcpy.GetMessages()
                LOGGER.error(msgs)
                rc = 0
            else:
                LOGGER.info(f"Moved {infeatures} to destination")
                rc = 1
        if rc == 1:
            LOGGER.debug("Removing temporary features")
            arcpy.env.workspace = temppath
            arcpy.DeleteFeatures_management(f"{temppath}/{outname}")


def start():
    """
    Start the process (logging, config, etc.) and call the main process
    """
    p = argparse.ArgumentParser()

    p.add_argument(
        "-c", "--config_file",
        help="Configuration file"
        )
    p.add_argument(
        "-v", "--verbose",
        help="Verbose output",
        action="store_true"
        )
    args = p.parse_args()

    global configFile
    global LOGGER

    configFile = args.config_file
    verbose = False
    if args.verbose:
        verbose = True

    config = ConfigParser(
        allow_no_value=True,
        interpolation=ExtendedInterpolation()
        )
    config.optionxform = str
    config.read(configFile)
    logFile = config.get(
        "Logging", "LogFile", fallback=sys.argv[0].replace(".py", ".log")
    )
    logLevel = config.get("Logging", "LogLevel", fallback="INFO")
    verbose = config.getboolean("Logging", "Verbose", fallback=verbose)
    datestamp = config.getboolean("Logging", "DateStamp", fallback=False)
    if datestamp:
        base, ext = os.path.splitext(logFile)
        curdate = datetime.datetime.now()
        curdatestr = curdate.strftime("%Y%m%d%H%M")
        # The lstrip on the extension is required as splitext leaves it on.
        logFile = "%s.%s.%s" % (base, curdatestr, ext.lstrip("."))

    logging.basicConfig(
        level=getattr(logging, logLevel),
        format="%(asctime)s: %(levelname)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=logFile,
        filemode="w",
    )
    LOGGER = logging.getLogger()

    if verbose:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(getattr(logging, logLevel))
        formatter = logging.Formatter(
            "%(asctime)s: %(levelname)s %(message)s",
            "%H:%M:%S",
        )
        console.setFormatter(formatter)
        LOGGER.addHandler(console)
    LOGGER.info(f"Running {sys.argv[0]} (pid {os.getpid()})")
    LOGGER.info(f"Started log file {logFile} (detail level {logLevel})")
    main(config)

    LOGGER.info("Completed")


start()
