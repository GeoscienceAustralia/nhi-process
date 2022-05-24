@echo off
REM Process ACCESS-NQ data
CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python

python C:\workspace\bin\process\access\process_windgust.py -c C:\workspace\bin\process\access\process_windgust_nq.ini -v
python C:\workspace\bin\process\access\process_helicity.py -c C:\workspace\bin\process\access\process_helicity_nq.ini -v
python C:\workspace\bin\process\access\process_rainfall.py -c C:\workspace\bin\process\access\process_rainfall_nq.ini -v
