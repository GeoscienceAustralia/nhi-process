@echo off
title Fetch AXF observations
REM Fetch observations (AXF files) from the BoM using FTP client and script
CALL conda.bat activate base
REM cd \incoming\que
python C:\workspace\lib\python\ftpscriptrunner.py -c C:\workspace\bin\fetch\obs\fetch_obs.ini -v
REM perl c:\workspace\bin\fetch\ftpclient.pl -c c:\workspace\bin\fetch\obs\fetch_obs.ini -v
