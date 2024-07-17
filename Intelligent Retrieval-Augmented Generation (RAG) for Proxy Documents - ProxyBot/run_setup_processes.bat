@echo off
cls
REM Execution time capture
for /f "tokens=1-4 delims=:. " %%a in ("%time%") do (
    set /a "start_hour=%%a"
    set /a "start_minute=%%b"
    set /a "start_second=%%c"
    set /a "start_millisecond=%%d"
)

REM Time taken variables
set step01_time_taken=0
set step02_time_taken=0
set step03_time_taken=0

REM Runs step 0 - AOSS creation
echo [93mRunning[0m [92m '01_run_aoss.py'[0m [93mfor permissions, buckets creation and aoss creation...[0m
set "start_time=%time%"
echo "python 01_run_aoss.py"
if %errorlevel% neq 0 (
    echo [91m'01_run_aoss.py' failed. Exiting.[0m
    exit /b 1
)
set "end_time=%time%"
set /a step01_time_taken=((%end_time:~0,2% * 3600) + (%end_time:~3,2% * 60) + (%end_time:~6,2%)) - ((%start_time:~0,2% * 3600) + (%start_time:~3,2% * 60) + (%start_time:~6,2%))
echo [92m'01_run_aoss.py'[0m [93mrun, completed[0m

REM Waiting for few seconds
echo [104mWaiting briefly before next step...[0m
timeout /t 20 > nul

REM Runs step 1 - Textract
echo [93mRunning[0m [92m '02_run_textract.py'[0m [93mfor file upload and text extraction using Textract...[0m
set "start_time=%time%"
echo "python 02_run_textract.py"
if %errorlevel% neq 0 (
    echo [91m'02_run_textract.py' failed. Exiting.[0m
    exit /b 1
)
timeout /t 70 > nul
set "end_time=%time%"
set /a step02_time_taken=((%end_time:~0,2% * 3600) + (%end_time:~3,2% * 60) + (%end_time:~6,2%)) - ((%start_time:~0,2% * 3600) + (%start_time:~3,2% * 60) + (%start_time:~6,2%))
echo [92m'02_run_textract.py'[0m [93mrun, completed[0m

REM Cooling off for few seconds
echo [104mCooling off from before next step...[0m
timeout /t 30 > nul

REM Runs step 2 - Data Ingestion into AOSS
echo [93mRunning[0m [92m'03_run_ingestion.py'[0m [93mfor permissions, buckets creation and aoss creation...[0m
set "start_time=%time%"
echo "python 03_run_ingestion.py"
if %errorlevel% neq 0 (
    echo [91m'03_run_ingestion.py' failed. Exiting.[0m
    exit /b 1
)
set "end_time=%time%"
set /a step03_time_taken=((%end_time:~0,2% * 3600) + (%end_time:~3,2% * 60) + (%end_time:~6,2%)) - ((%start_time:~0,2% * 3600) + (%start_time:~3,2% * 60) + (%start_time:~6,2%))
echo [92m'03_run_ingestion.py'[0m [93mrun, completed[0m

REM Cooling off for few seconds
echo [104mCooling off for ingestion to finish...[0m
timeout /t 35 > nul

echo [101mTotal Execution Time for all processes.[0m
echo [92mStep 01, for file 03_run_aoss.py: %step01_time_taken% seconds.[0m
echo [92mStep 02, for file 02_run_textract.py: %step02_time_taken% seconds.[0m
echo [92mStep 03, for file 03_run_ingestion.py: %step03_time_taken% seconds.[0m