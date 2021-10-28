@echo off
REM Process ACCESS-DN data
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python

python C:\workspace\bin\process\access\process_windgust.py -c C:\workspace\bin\process\access\process_windgust_dar.ini -v
python C:\workspace\bin\process\access\process_helicity.py -c C:\workspace\bin\process\access\process_helicity_dar.ini -v
python C:\workspace\bin\process\access\process_rainfall.py -c C:\workspace\bin\process\access\process_rainfall_dar.ini -v
