@echo off
title Fetch TC data - repeat
CALL conda.bat activate process
set PYTHONPATH=C:\WorkSpace\lib\python
cd c:\workspace\bin\fetch\tc
python c:\workspace\bin\fetch\tc\fetch_tc_repeat.py -c c:\workspace\bin\fetch\tc\fetch_tc_repeat.ini -v

