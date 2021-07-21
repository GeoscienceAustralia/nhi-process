@echo off
REM Process ACCESS-PH data 
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
python C:\workspace\bin\process\access\process_windgust.py -c C:\workspace\bin\process\access\process_windgust_per.ini -v
python C:\workspace\bin\process\access\process_helicity.py -c C:\workspace\bin\process\access\process_helicity_per.ini -v
