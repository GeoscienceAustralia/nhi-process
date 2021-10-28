@echo off
REM Process ACCESS-VT data
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python

python C:\workspace\bin\process\access\process_windgust.py -c C:\workspace\bin\process\access\process_windgust_vic.ini -v
python C:\workspace\bin\process\access\process_helicity.py -c C:\workspace\bin\process\access\process_helicity_vic.ini -v
python C:\workspace\bin\process\access\process_rainfall.py -c C:\workspace\bin\process\access\process_rainfall_vic.ini -v
