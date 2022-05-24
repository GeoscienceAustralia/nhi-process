@echo off
REM Fetch ACCESS-C3 from the BoM using FTP client and script
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
cd \incoming\que
python C:\workspace\lib\python\sftpscriptrunner.py -c C:\workspace\bin\fetch\access\fetch_access_nq.ini -v
