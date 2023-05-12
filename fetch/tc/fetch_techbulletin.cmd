@echo off
REM Fetch TC technical Bulletin from the BoM using FTP client and script
CALL conda.bat activate process
setlocal EnableDelayedExpansion


set "pathlist=%PYTHONPATH%"
set "scriptname=ftpscriptrunner.py"
set "args=-c %CD%\fetch_techbulletin.ini -v%"

for %%i in ("%pathlist:;=" "%") do (
    set "fullpath=%%~i\%scriptname%"
    if exist "!fullpath!" (
        echo !fullpath! exists, running script with arguments: !args!
        python "!fullpath!" !args!
        goto :done
    ) else (
        echo !fullpath! does not exist
    )
)
:done
