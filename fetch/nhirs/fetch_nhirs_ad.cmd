@echo off
title Fetch NHIRS for AD domain
REM C:\Windows\System32\cmd.exe /k  "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\proenv.bat"

set CONDA_NEW_ENV=arcgispro-py3
CALL "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\activate.bat" "%CONDA_NEW_ENV%"


set PYTHONPATH=C:\Workspace\lib\python
cd \Workspace\bin\fetch\nhirs

python fetch_nhirs.py -c fetch_nhirs_ad.ini