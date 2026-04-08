@echo off
REM Quick Start Script for Greenhouse Crop Growth Monitoring
REM Automates: Dataset preparation → Model training → Results visualization

echo.
echo ========================================================
echo  GREENHOUSE CROP GROWTH MONITORING - QUICK START
echo  Algorithm: Frame Differencing + Contour Area Growth Rate
echo  Dataset: CVPPP2017_LCC_training
echo ========================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Step 1: Install dependencies
echo [STEP 1] Checking dependencies...
pip show opencv-python >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing required packages...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
    echo [SUCCESS] Dependencies installed
) else (
    echo [OK] Dependencies already installed
)

echo.

REM Step 2: Prepare dataset
echo [STEP 2] Preparing CVPPP2017 dataset...
if not exist "dataset\CVPPP2017_LCC_training_extracted" (
    python prepare_cvppp_dataset.py
    if errorlevel 1 (
        echo [ERROR] Dataset preparation failed
        pause
        exit /b 1
    )
    echo [SUCCESS] Dataset prepared
) else (
    echo [OK] Dataset already extracted
)

echo.

REM Step 3: Run the model
echo [STEP 3] Running Frame Differencing model...
python greenhouse_growth_monitor_cvppp.py
if errorlevel 1 (
    echo [ERROR] Model execution failed
    pause
    exit /b 1
)

echo.
echo ========================================================
echo [SUCCESS] Model execution completed!
echo ========================================================
echo.
echo Results saved to: output\results\
echo.
echo Next steps:
echo   1. Check output\results\ for annotated frames and plots
echo   2. Review growth_analysis.png for growth curves
echo   3. Check results.json for numerical results
echo.
pause
