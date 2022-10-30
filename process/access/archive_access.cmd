@echo off
REM Archive raw ACCESS-C3 data
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
python C:\workspace\bin\process\access\archiveAccess.py -c C:\workspace\bin\process\access\archiveAccess.ini -v

