@echo off
title Fetch AXF observations
REM Fetch observations (AXF files) from the BoM using FTP client and script
CALL conda.bat activate process
cd \incoming\que
set PYTHONPATH=C:\workspace\lib\python 
python C:\workspace\lib\python\ftpscriptrunner.py -c C:\workspace\bin\fetch\obs\fetch_obs.ini -v
