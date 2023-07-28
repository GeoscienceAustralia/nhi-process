@echo off
CALL conda.bat activate process
setlocal EnableDelayedExpansion

set "scriptname=backup_repos.py"

for %%i in ("%pathlist:;=" "%") do (
    set "fullpath=%CD%\%scriptname%"
    if exist "!fullpath!" (
        echo !fullpath! exists, running script
        python "!fullpath!"
        goto :done
    ) else (
        echo %fullpath% does not exist
    )
)
:done