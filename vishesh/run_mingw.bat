@echo off
IF NOT EXIST D:\omnetpp-6.1 (
    echo Error: OMNeT++ directory not found at D:\omnetpp-6.1
    echo Please update OMNETPP_ROOT to point to your OMNeT++ installation
    pause
    exit /b 1
)

set OMNETPP_ROOT=D:\omnetpp-6.1
set PATH=%OMNETPP_ROOT%\bin;^
%OMNETPP_ROOT%\tools\win64\mingw64\bin;^
%OMNETPP_ROOT%\tools\win64\mingw64\opt\bin;^
%OMNETPP_ROOT%\tools\win64\usr\bin;^
%PATH%

IF NOT EXIST "%OMNETPP_ROOT%\mingwenv.cmd" (
    echo Error: mingwenv.cmd not found in %OMNETPP_ROOT%
    echo Please check your OMNeT++ installation
    pause
    exit /b 1
)

cd /d %OMNETPP_ROOT%
call mingwenv.cmd