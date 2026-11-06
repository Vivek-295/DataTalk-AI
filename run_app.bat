@echo off
TITLE DataTalk - Natural Language to SQL Assistant
cd /d "%~dp0"
python -m streamlit run app.py
pause
