@echo off
REM Process ACCESS-SY data 
CALL conda.bat activate base
set PYTHONPATH=C:\Workspace\lib\python
python C:\workspace\bin\process\access\process_windgust.py -c C:\workspace\bin\process\access\process_windgust_syd.ini -v
