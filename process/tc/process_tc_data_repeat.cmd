@echo off
REM Start process_tc_data_repeat.py
title Process TC data

c:

CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
cd \WorkSpace\bin\process\tc
python process_tc_data_repeat.py -c process_tc_data_repeat.ini
