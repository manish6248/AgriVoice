@echo off
echo Installing ngrok...
mkdir %USERPROFILE%\ngrok
cd %USERPROFILE%\ngrok
curl -o ngrok.zip https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip
tar -xf ngrok.zip
echo Adding ngrok to PATH...
setx PATH "%PATH%;%USERPROFILE%\ngrok"
echo Installation complete. Please restart your command prompt.
echo Run 'ngrok --version' to verify installation.
pause