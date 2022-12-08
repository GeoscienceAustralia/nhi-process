@echo off
title Fetch NHIRS for SY domain
CALL C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\proenv.bat

set PYTHONPATH=C:\Workspace\lib\python
cd \Workspace\bin\fetch\nhirs

python fetch_nhirs.py -c fetch_nhirs_sy.ini