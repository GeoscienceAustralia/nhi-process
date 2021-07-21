@echo off
REM Fetch TC GIS format warning data from the BoM using FTP client and script
CALL conda.bat activate process
set PYTHONPATH=C:\workspace\lib\python
cd \incoming\que

python C:\workspace\lib\python\ftpscriptrunner.py -c c:\workspace\bin\fetch\tc\fetch_tc_warning.ini -v

