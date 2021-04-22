@echo off
REM Fetch CXML files from the BoM using FTP client and script
CALL conda.bat activate base
set PYTHONPATH=C:\WorkSpace\lib\python
cd \incoming\que

python C:\workspace\lib\python\ftpscriptrunner.py -c c:\workspace\bin\fetch\tc\fetch_cxml.ini -v
