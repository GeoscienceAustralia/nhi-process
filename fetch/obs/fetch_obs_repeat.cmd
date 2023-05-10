@echo off
title Fetch Observations - repeat
CALL conda.bat activate process


python %CD%\fetch_obs_repeat.py -c %CD%\fetch_obs_repeat.ini

