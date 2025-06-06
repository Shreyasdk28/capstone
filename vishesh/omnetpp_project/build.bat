@echo off
set VEINS_ROOT=C:\veins
set OMNETPP_ROOT=C:\omnetpp

echo Building VANET project...

cd %~dp0
opp_makemake -f --deep -O out -DVEINS_IMPORT -I. -I%VEINS_ROOT%\src -L%VEINS_ROOT%\src -lveins
make

echo Build complete!
pause 