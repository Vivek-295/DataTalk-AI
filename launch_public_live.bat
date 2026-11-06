@echo off
TITLE DataTalk AI - Launch Live Public Tunnel
echo =====================================================================
echo Launching DataTalk AI with Instant Live Public URL...
echo =====================================================================
echo.

cd /d "%~dp0"

echo [1/2] Starting Streamlit App locally...
start "DataTalk Streamlit Engine" cmd /k "python -m streamlit run app.py --server.headless true --server.port 8501"

echo [2/2] Generating Free Public HTTPS URL via Cloudflare Tunnel...
timeout /t 3 >nul

"..\cloudflared.exe" tunnel --url http://localhost:8501

pause
