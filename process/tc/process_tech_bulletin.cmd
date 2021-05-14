:: Process a new TC Technical Bulletin and initiate TCIM simulation
@echo off
title Process TC Tech Bulletin
CALL conda.bat activate
set PYTHONPATH=C:\Workspace\lib\python

cd \WorkSpace\bin\process\tc

echo Processing technical bulletin...
python process_tech_bulletin.py -c process_tech_bulletin.ini

REM echo Processing template configuration file
REM cd \WorkSpace\bin\process\config
REM perl process_config_templates.pl -c process_config_templates.ini

REM echo Running TCIM...
REM c:
REM This will require modifying the path
REM cd \WorkSpace\tcrm-impact
REM \python27.old\python -Wignore tcrm-impact.py -c tcim-impact.ini

REM cd \WorkSpace\bin\process\windfield
REM \python27\ArcGIS10.5\python TCWindfieldConversion.py -c TCWindfieldConversion.ini

::\python27.old\ArcGIS10.2\python TCImpactEstimation.py -c TCImpactEstimation.ini

::cd \WorkSpace\bin\process\tc
::\python -Wignore process_convert_track.py -c process_convert_track.ini


:: Fetch AXF files for posterity:
REM cd \WorkSpace\bin\fetch\obs
REM echo Fetching observation files
REM cd \incoming\que
REM perl c:\workspace\bin\fetch\ftpclient.pl -c c:\workspace\bin\fetch\obs\fetch_obs.ini -v

REM echo Pushing data to external destination...
REM cd \WorkSpace\bin\push
REM perl push_tcim.pl -c push_tcim.ini

