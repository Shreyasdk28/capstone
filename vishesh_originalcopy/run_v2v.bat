@echo off
REM Set SUMO_HOME environment variable - replace this path with your SUMO installation path
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

REM Add SUMO tools to PATH
set PATH=%PATH%;%SUMO_HOME%\bin

REM Run the V2V communication script
python v2v_communication.py

pause 