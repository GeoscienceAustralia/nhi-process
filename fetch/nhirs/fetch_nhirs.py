"""

Run the following command at the command prompt to activate the ArcGIS Pro Python environment:
C:\Windows\System32\cmd.exe /k "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\proenv.bat"

"""

import os
import sys
import arcpy
import logging
import argparse
from os.path import join as pjoin, isfile, dirname, basename

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
        Bool: True if the layer exists in the given workspace, False otherwise
    """
    arcpy.env.workspace = workspace
    if arcpy.Exists(layername):
        LOGGER.debug(f"{layername} already exists")
        return True
    else:
        return False


def main(config):

    fcast_time = currentCycle(delay=3)
    fcast_time_str = fcast_time.strftime(DATETIMEFMT)
    LOGGER.debug(f"Forecast time string: {fcast_time_str}")

    maxfeatures = config.get('Defaults', 'MaxFeatures', fallback=30000)
    sourceWFS = config.get('Defaults', 'Source')
    destGDB = config.get('Defaults', 'Geodatabase')
    featureClass = config.get('Domain', 'FeatureClass')
    destination = f"{destGDB}/{featureClass}"

    LOGGER.info(f"Retrieving data from {sourceWFS}")
    LOGGER.info(f"Data will be stored at {destination}")
    layers = config.items('Layers')

    temppath = "C:/WorkSpace/temp.gdb"
    LOGGER.debug(f"Temporary storage: {temppath}")

    for idx, layername in layers:
        outname = f"{layername}_{fcast_time_str}"
        LOGGER.debug(outname)
        arcpy.env.workspace = temppath
        if alreadyProcessed(destination, outname):
            LOGGER.info(f"{outname} already exists in {destination} - have you already fetched this data?")
            continue

        try:
            arcpy.conversion.WFSToFeatureClass(sourceWFS, layername, temppath, outname, max_features=maxfeatures)
        except:
            msgs = arcpy.GetMessages()
            LOGGER.error(msgs)
        else:
            nfeatures = arcpy.GetCount_management(outname)
            LOGGER.info(f"Retrieved {nfeatures} features from WFS")

        infeatures = f"{temppath}/{outname}"
        arcpy.env.workspace = destination
        rc = 0
        if arcpy.Exists(outname):
            LOGGER.info(f"{outname} already exists in {destination} - have you already fetched this data?")
        else:
            LOGGER.info(f"Moving {infeatures} to {destination}")
            try:
                arcpy.conversion.FeatureClassToFeatureClass(infeatures, destination, outname)
            except:
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
    logFile = config.get('Logging', 'LogFile',
                         fallback=sys.argv[0].replace(".py", ".log"))
    logLevel = config.get('Logging', 'LogLevel', fallback='INFO')
    verbose = config.getboolean('Logging', 'Verbose', fallback=verbose)
    datestamp = config.getboolean('Logging', 'Datestamp', fallback=False)
    logging.basicConfig(level=getattr(logging, logLevel),
                    format='%(asctime)s: %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    filename=logFile,
                    filemode='w')
    LOGGER = logging.getLogger()

    if verbose:
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(getattr(logging, logLevel))
        formatter = logging.Formatter(
            '%(asctime)s: %(levelname)s %(message)s',
            '%H:%M:%S', )
        console.setFormatter(formatter)
        LOGGER.addHandler(console)
    LOGGER.info(f'Started log file {logFile} (detail level {logLevel})')
    LOGGER.info(f'Running {sys.argv[0]} (pid {os.getpid()})')
    main(config)



start()