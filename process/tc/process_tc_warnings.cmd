:: Process new TC warning data
@echo off
title Process TC warning data
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python

cd \WorkSpace\bin\process\tc

echo Processing TC warning data
python process_tc_warnings.py -c process_tc_warnings.ini
