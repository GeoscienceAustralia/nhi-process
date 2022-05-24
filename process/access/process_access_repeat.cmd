@echo off
title Process ACCESS-C3 for all domains - repeat
REM Process ACCESS data on repeat
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
python C:\workspace\bin\process\access\process_access_repeat.py -c C:\workspace\bin\process\access\process_access_repeat.ini
