@echo off
REM Archive raw AXF data
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
python C:\workspace\bin\process\obs\archiveObs.py -c C:\workspace\bin\process\obs\archiveObs.ini -v

