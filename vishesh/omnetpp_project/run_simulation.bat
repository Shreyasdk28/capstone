@echo off
set VEINS_ROOT=C:\veins
set OMNETPP_ROOT=C:\omnetpp
set SUMO_HOME=C:\Program Files (x86)\Eclipse\Sumo

echo Starting VANET simulation...

cd %~dp0

REM Start SUMO with the configuration
start /B "%SUMO_HOME%\bin\sumo-gui.exe" -c "..\vishesh_original - Copy\myConfig.sumocfg" --remote-port=9999

REM Wait for SUMO to start
timeout /t 5

REM Start OMNeT++ simulation
cd out
omnetpp.exe -r VANETWithPQC

echo Simulation complete!
pause 