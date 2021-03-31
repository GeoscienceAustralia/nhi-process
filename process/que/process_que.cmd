@echo off
REM Start process_que.pl
title Process incoming que

c:

CALL conda.bat activate base

cd \WorkSpace\bin\process\que
python process_que.py -c process_que.ini
