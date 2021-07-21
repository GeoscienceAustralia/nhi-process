@echo off
title Fetch Observations - repeat
CALL conda.bat activate process
set PYTHONPATH=C:\workspace\lib\python 
cd \workspace\bin\fetch\obs
python \workspace\bin\fetch\obs\fetch_obs_repeat.py -c \workspace\bin\fetch\obs\fetch_obs_repeat.ini

