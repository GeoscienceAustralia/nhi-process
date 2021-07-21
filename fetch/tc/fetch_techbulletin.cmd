@echo off
REM Fetch TC technical Bulletin from the BoM using FTP client and script
CALL conda.bat activate process
set PYTHONPATH=C:\WorkSpace\lib\python
cd \incoming\que

python C:\workspace\lib\python\ftpscriptrunner.py -c c:\workspace\bin\fetch\tc\fetch_techbulletin.ini -v
