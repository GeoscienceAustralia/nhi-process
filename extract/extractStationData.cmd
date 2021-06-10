@echo off
title Extract daily maxima from 1-minute observations
CALL conda.bat activate base
set PYTHONPATH=C:\Workspace\lib\python

cd \WorkSpace\bin\extract
python extractStationData.py -c extract_daily_1minmax.ini