@echo off
echo Fixing GitHub push by removing credentials from git history...

REM Remove the .env file from git tracking
git rm --cached .env 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo .env file was not tracked by git, which is good.
) else (
    echo Removed .env file from git tracking.
)

REM Amend the last commit to remove credentials
echo Amending the last commit to remove credentials...
git add .
git commit --amend -m "Initial commit of AGRIVOICE project (credentials moved to environment variables)"

echo.
echo Now try pushing to GitHub again with:
echo git push -u origin main --force
echo.
echo NOTE: Using --force will overwrite the remote repository history.
echo Only use this if you're sure it's okay to replace the remote history.
echo.

pause