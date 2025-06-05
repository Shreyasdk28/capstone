@echo off
REM Set SUMO_HOME environment variable - replace this path with your SUMO installation path
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

REM Add SUMO tools to PATH
set PATH=%PATH%;%SUMO_HOME%\bin

REM Create logs directory if it doesn't exist
if not exist logs mkdir logs

REM Run the traffic controller with V2V communication
python traffic/controller.py

pause 