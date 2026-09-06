@echo off
title Launch Google Chrome for CurioKraft AI Studio Automation (Port 9222)
echo ====================================================================
echo  Launching Google Chrome with Remote Debugging on Port 9222
echo  Profile: CurioKraft Data (saiprince87@gmail.com)
echo ====================================================================
echo.

set "CHROME_EXE=C:\Program Files\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
if not exist "%CHROME_EXE%" set "CHROME_EXE=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"

if not exist "%CHROME_EXE%" (
    echo [ERROR] Google Chrome executable not found!
    pause
    exit /b 1
)

set "DATA_DIR=%LOCALAPPDATA%\Google\Chrome\CurioKraft Data"
set "SRC_DIR=%LOCALAPPDATA%\Google\Chrome\User Data"
set "CHAT_URL=https://aistudio.google.com/prompts/new_chat"

:: Sync profile if not exists
if not exist "%DATA_DIR%\Default\Preferences" (
    echo [INFO] First-time setup: Syncing profile from User Data to CurioKraft Data...
    mkdir "%DATA_DIR%\Default" 2>nul
    copy /y "%SRC_DIR%\Local State" "%DATA_DIR%\Local State" >nul 2>nul
    copy /y "%SRC_DIR%\Default\Preferences" "%DATA_DIR%\Default\Preferences" >nul 2>nul
    xcopy /e /i /y "%SRC_DIR%\Default\Network" "%DATA_DIR%\Default\Network" >nul 2>nul
    xcopy /e /i /y "%SRC_DIR%\Default\Local Storage" "%DATA_DIR%\Default\Local Storage" >nul 2>nul
)

echo Starting Google Chrome on port 9222...
start "" "%CHROME_EXE%" --remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir="%DATA_DIR%" --profile-directory=Default "%CHAT_URL%"

echo.
echo ====================================================================
echo  Chrome launched successfully on port 9222!
echo  Keep this Chrome window open.
echo  You can now run in your terminal:
echo    npm start -- --pages P010
echo ====================================================================
echo.
