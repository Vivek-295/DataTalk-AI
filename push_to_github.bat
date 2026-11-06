@echo off
TITLE Push NL2SQL Agent to GitHub
echo =====================================================================
echo Pushing DataTalk AI (NL2SQL Agent) to GitHub...
echo Repository: https://github.com/Vivek-295/DataTalk-AI
echo =====================================================================
echo.

git branch -M main
git push -u origin main

echo.
echo =====================================================================
echo Done! Visit: https://github.com/Vivek-295/DataTalk-AI
echo =====================================================================
pause
