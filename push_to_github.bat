@echo off
TITLE Push NL2SQL Agent to GitHub
echo =====================================================================
echo Pushing DataTalk AI (NL2SQL Agent) to GitHub...
echo Repository: https://github.com/Vivek-295/nl2sql-database-agent
echo =====================================================================
echo.
echo Make sure you have created the empty repo 'nl2sql-database-agent'
echo on https://github.com/new first!
echo.
pause

git branch -M main
git push -u origin main

echo.
echo =====================================================================
echo Done! Visit: https://github.com/Vivek-295/nl2sql-database-agent
echo =====================================================================
pause
