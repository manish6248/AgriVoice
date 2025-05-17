@echo off
echo Starting ngrok for AGRIVOICE...

REM Check if ngrok is installed
where ngrok >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ngrok not found. Installing ngrok...
    mkdir %USERPROFILE%\ngrok
    cd %USERPROFILE%\ngrok
    curl -o ngrok.zip https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip
    tar -xf ngrok.zip
    echo Adding ngrok to PATH...
    setx PATH "%PATH%;%USERPROFILE%\ngrok"
    echo Installation complete. Please restart this script.
    pause
    exit /b
)

REM Start Flask app in background
start cmd /k "python app.py"

REM Wait for Flask to start
echo Waiting for Flask app to start...
timeout /t 5

REM Start ngrok to expose port 5000 (default Flask port)
echo Starting ngrok tunnel...
ngrok http 5000

echo Done.
pause