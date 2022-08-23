@echo off
title Fetch ACCESS-C data - repeat
CALL conda.bat activate process
set PYTHONPATH=C:\WorkSpace\lib\python
cd c:\workspace\bin\fetch\access
python c:\workspace\bin\fetch\access\fetch_access_repeat.py -c c:\workspace\bin\fetch\access\fetch_access_repeat.ini -v

