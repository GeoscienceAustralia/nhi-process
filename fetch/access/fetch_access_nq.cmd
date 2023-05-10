@echo off
title Fetch ACCESS-C3 for North Queensland domain
REM Fetch ACCESS-C3 from the BoM using FTP client and script
REM Make sure you have set the PYTHONPATH variable to point to
REM the location of the nhi-pylib scripts
CALL conda.bat activate process
setlocal EnableDelayedExpansion


set "pathlist=%PYTHONPATH%"
set "scriptname=sftpscriptrunner.py"
set "args=-c %CD%\fetch_access_nq.ini -v%"

for %%i in ("%pathlist:;=" "%") do (
    set "fullpath=%%~i\%scriptname%"
    if exist "!fullpath!" (
        echo !fullpath! exists, running script with arguments: !args!
        python "!fullpath!" !args!
        goto :done
    ) else (
        echo %fullpath% does not exist
    )
)
:done
