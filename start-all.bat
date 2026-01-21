@echo off
echo ========================================
echo Starting Social Analytics Dashboard
echo ========================================
echo.

REM Проверить PostgreSQL
echo [1/4] Checking PostgreSQL...
docker ps | findstr postgres-social-analytics >nul
if errorlevel 1 (
    echo PostgreSQL not running. Starting...
    docker start postgres-social-analytics
    if errorlevel 1 (
        echo Creating new PostgreSQL container...
        docker run -d --name postgres-social-analytics -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=social_analytics -v postgres-data:/var/lib/postgresql/data postgres:16
    )
    timeout /t 5 >nul
) else (
    echo PostgreSQL already running
)
echo.

REM Запустить API в новом окне
echo [2/4] Starting FastAPI...
start "FastAPI" cmd /k "cd /d C:\Users\Admin\dashboard_v2 && .venv\Scripts\activate && uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload"
timeout /t 3 >nul
echo.

REM Запустить Dashboard в новом окне
echo [3/4] Starting Streamlit Dashboard...
start "Streamlit" cmd /k "cd /d C:\Users\Admin\dashboard_v2 && .venv\Scripts\activate && streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0"
timeout /t 3 >nul
echo.

REM Запустить Cloudflare Tunnel в новом окне (если настроен)
echo [4/4] Starting Cloudflare Tunnel...
cloudflared --version >nul 2>&1
if errorlevel 1 (
    echo Cloudflare Tunnel not installed. Skipping...
    echo Install with: winget install Cloudflare.cloudflared
) else (
    start "Cloudflare Tunnel" cmd /k "cloudflared tunnel run social-analytics-dashboard"
    timeout /t 2 >nul
)
echo.

echo ========================================
echo All services started!
========================================
echo.
echo Local Access:
echo Dashboard: http://localhost:8501
echo API: http://localhost:8000
echo API Docs: http://localhost:8000/docs
echo.
echo Public Access (after Cloudflare Tunnel setup):
echo Dashboard: https://dashboard.your-domain.com
echo API: https://api.your-domain.com
echo.
echo Press any key to exit...
pause >nul
