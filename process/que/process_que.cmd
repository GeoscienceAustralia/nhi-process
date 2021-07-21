@echo off
REM Start process_que.py
title Process incoming que

c:

CALL conda.bat activate process
set PYTHONPATH=C:\Workspace\lib\python
cd \WorkSpace\bin\process\que
python process_que.py -c process_que.ini
