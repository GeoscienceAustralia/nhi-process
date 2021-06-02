:: Process a new TC Technical Bulletin and initiate TCIM simulation
@echo off
title Process TC Tech Bulletin
CALL conda.bat activate
set PYTHONPATH=C:\Workspace\lib\python

cd \WorkSpace\bin\process\tc

echo Processing technical bulletin
python process_tech_bulletin.py -c process_tech_bulletin.ini

echo Processing template configuration file
cd \WorkSpace\bin\process\config
python process_config_template.py -c process_config_templates.ini

REM echo Running TCIM...
REM c:
REM CALL conda.bat activate tcrm
REM cd \WorkSpace\tcrm
REM set PYTHONPATH=C:\WorkSpace\tcrm;C:\WorkSpace\tcrm\Utilities
REM python tcevent.py -c tcim-impact.ini

REM cd \WorkSpace\bin\process\windfield
REM \python27\ArcGIS10.5\python TCWindfieldConversion.py -c TCWindfieldConversion.ini


:: Fetch AXF files for posterity:
REM cd \WorkSpace\bin\fetch\obs
REM echo Fetching observation files
REM cd \incoming\que
REM perl c:\workspace\bin\fetch\ftpclient.pl -c c:\workspace\bin\fetch\obs\fetch_obs.ini -v

REM echo Pushing data to external destination...
REM cd \WorkSpace\bin\push
REM perl push_tcim.pl -c push_tcim.ini

