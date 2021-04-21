@echo off
title Fetch TC Technical Bulletins - repeat
CALL conda.bat activate base
set PYTHONPATH=C:\WorkSpace\lib\python
cd c:\workspace\bin\fetch\tc
python c:\workspace\bin\fetch\tc\fetch_tech_bulletin_repeat.py -c c:\workspace\bin\fetch\tc\fetch_tech_bulletin_repeat.ini -v

