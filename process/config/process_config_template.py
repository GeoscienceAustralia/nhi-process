import os
import re
import logging
import argparse
import glob

from configparser import ConfigParser, ExtendedInterpolation, NoOptionError
from os.path import join as pjoin, realpath, isdir, dirname

from process import pAlreadyProcessed, pWriteProcessedFile, pArchiveFile, pInit
from files import flStartLog, flGetStat

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

    global config_file

    config_file = args.config_file
    verbose = args.verbose
    config = ConfigParser(allow_no_value=True,
                          interpolation=ExtendedInterpolation())
    config.optionxform = str
    config.read(config_file)

    logfile = config.get('Logging', 'LogFile')
    logdir = dirname(realpath(logfile))

    # if log file directory does not exist, create it
    if not isdir(logdir):
        try:
            os.makedirs(logdir)
        except OSError:
            logfile = pjoin(os.getcwd(), 'fetch.log')

    verbose = config.getboolean('Logging', 'Verbose', fallback=False)
    if args.verbose:
        verbose = True

    pInit(config_file)
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
    Given a file specification and a category, list all files that match the
    spec and add them to the :dict:`g_files` dict. The `category` variable
    corresponds to a section in the configuration file that includes an item
    called 'OriginDir'. The given `spec` is joined to the `category`'s
    'OriginDir' and all matching files are stored in a list in
    :dict:`g_files` under the `category` key.

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
    originDir = config.get('Defaults', 'OriginDir')
    deleteWhenProcessed = config.getboolean('Files', 'DeleteWhenProcessed', fallback=False)
    LOGGER.debug(f"Origin directory: {originDir}")
    LOGGER.debug(f"DeleteWhenProcessed: {deleteWhenProcessed}")

    category = "Input"
    for f in g_files[category]:
        LOGGER.info(f"Processing {f}")
        directory, fname, md5sum, moddate = flGetStat(f)
        if pAlreadyProcessed(directory, fname, "md5sum", md5sum):
            LOGGER.info(f"Already processed {f}")
        else:
            if processFile(config, f):
                LOGGER.debug(f"Successfully processed {f}")
                pWriteProcessedFile(f)
                if deleteWhenProcessed:
                    LOGGER.debug(f"Deleting {f}")
                    os.unlink(f)
                else:
                    LOGGER.debug(f"Archiving {f}")
                    pArchiveFile(f)

def processInfoFile(filename):

    id_regex = re.compile(r'TC\sID\:\s(\w*)')
    vt_regex = re.compile(r'^Valid\s*\w*\:\s*(\d{4})-(\d{2})-(\d{2})\s(\d{2})\:(\d{2})')
    with open(filename, 'r') as fh:
        for line in fh:
            id_match = id_regex.match(line)
            vt_match = vt_regex.match(line)
            if id_match:
                tcid = id_match.group(1)
                LOGGER.debug(f"TC ID: {tcid}")
            if vt_match:
                vt = "{0}{1}{2}{3}{4}".format(*vt_match.group(1, 2, 3, 4, 5))
                LOGGER.debug(f"Valid time: {vt}")
    trackfile = f"tctrack.{tcid}.csv"
    return tcid, trackfile, vt


def processTemplate(config, template, tcid, trackfile, vt):
    """
    Process a templated configuration file

    :param config: `ConfigParser` object with configuration settings
    :param str template: Name of the template to process. This must have a
                         corresponding section in the configuration file
    :param str tcid: TC id number
    :param str trackfile: Full path to the prepared track file
    :param str vt: string representation of the valid time of the forecast.

    :returns: `True` if successful, `False` otherwise.
    """

    cnffile = config.get(template, 'Config')
    cnftemplate = cnffile + '.template'
    LOGGER.info(f"Processing template for {cnffile}")
    replacements = config.get(template, 'Replacements').split(',')

    with open(cnftemplate, 'r') as fh:
        filedata = fh.read()

    filedata = filedata.replace('{TCID}', tcid)
    filedata = filedata.replace('{VALIDTIME}', vt)
    filedata = filedata.replace('{TRACKFILE}', trackfile)
    for replacement in replacements:
        # Set a default replacement - might be common across all templates for
        # example
        try:
            default = config.get('Defaults', replacement)
        except NoOptionError:
            default = ''
        replacestr = config.get(template, replacement, fallback=default)
        LOGGER.debug(f"Replacing all occurrences of {{{replacement}}} with {replacestr}")
        filedata = filedata.replace(f"{{{replacement}}}", replacestr)

    LOGGER.debug(f"Writing output configuration file {cnffile}")
    with open(cnffile, 'w') as fh:
        fh.write(filedata)

    return True

def processFile(config, filename):
    """
    Process a TC info file to update configuration templates

    :param str filename: Path to a TC info file
    :param str outputpath: Output path for configuration files.
    """
    pathname = os.path.dirname(filename)
    tcid, trackfile, vt = processInfoFile(filename)
    trackfile = pjoin(pathname, trackfile)

    templates = config.items('Templates')
    for idx, template in templates:
        retval = processTemplate(config, template, tcid, trackfile, vt)
        if not retval:
            LOGGER.warning(f"Couldn't process {template}")

    return True

start()