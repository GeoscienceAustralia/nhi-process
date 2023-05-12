@echo off
title Fetch NHIRS for NQ domain

REM Make sure you have set the PYTHONPATH variable to point to
REM the location of the nhi-pylib scripts
REM The call to activate the arcgispro-enabled environment is stored here:
REM C:\Windows\System32\cmd.exe /k  "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\proenv.bat"

set CONDA_NEW_ENV=arcgispro-py3
CALL "C:\Program Files\ArcGIS\Pro\bin\Python\Scripts\activate.bat" "%CONDA_NEW_ENV%"

python %CD%\fetch_nhirs.py -c %CD%\fetch_nhirs_nq.ini