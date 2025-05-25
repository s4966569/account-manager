@echo off
chcp 65001 >nul
echo Starting to build exe file...
echo.

REM Check if PyInstaller is installed
python -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo Error: PyInstaller is not installed!
    echo Please install it with: pip install pyinstaller
    goto :end
)

REM Check if Pillow is installed
python -c "import PIL" 2>nul
if %errorlevel% neq 0 (
    echo Warning: Pillow is not installed. Installing it now...
    pip install Pillow
    if %errorlevel% neq 0 (
        echo Error: Failed to install Pillow!
        goto :end
    )
)

echo All dependencies are ready. Starting build...
echo.

REM Execute PyInstaller build command
pyinstaller build.spec

REM Check if build was successful
if %errorlevel% equ 0 (
    echo.
    echo ================================
    echo Build completed successfully!
    echo Exe file has been generated in the dist directory
    echo ================================
) else (
    echo.
    echo ================================
    echo Build failed with error code: %errorlevel%
    echo Please check the error messages above
    echo ================================
)

:end
echo.
echo Press any key to exit...
pause >nul 