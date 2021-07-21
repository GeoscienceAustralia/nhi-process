@echo off
REM Process ACCESS-AD data 
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
python C:\workspace\bin\process\access\process_windgust.py -c C:\workspace\bin\process\access\process_windgust_adl.ini -v
