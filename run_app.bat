@echo off
TITLE DataTalk AI - Enterprise NL2SQL Agent
echo =====================================================================
echo Starting DataTalk AI: Enterprise NL2SQL Database Agent...
echo =====================================================================
echo.

cd /d "%~dp0"
python -m streamlit run app.py

pause
