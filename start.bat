@echo off
REM ============================================================
REM Digital FTE — Quick Start Script (Windows)
REM Usage: Double-click start.bat  OR  run from cmd/PowerShell
REM ============================================================

title Digital FTE — Starting Up

echo.
echo  +======================================+
echo  ^|       Digital FTE — Starting Up     ^|
echo  +======================================+
echo.

REM ── 1. Check Docker ──────────────────────────────────────
where docker >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker not found.
    echo         Install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

docker info >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker daemon is not running.
    echo         Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [OK] Docker is running

REM ── 2. Check .env ────────────────────────────────────────
if not exist ".env" (
    echo [WARN] No .env file found — creating from template...
    copy .env.example .env >nul
    echo.
    echo  Please open .env in a text editor, add your API keys,
    echo  then run this script again.
    echo  See SETUP.md for instructions on getting API keys.
    echo.
    pause
    exit /b 1
)

echo [OK] .env file found

REM ── 3. Build and start ───────────────────────────────────
echo.
echo  Building containers (first run: 5-10 min for AI model downloads)...
echo.

docker compose up --build -d
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] docker compose up failed. Check output above.
    pause
    exit /b 1
)

REM ── 4. Wait for backend ──────────────────────────────────
echo.
echo  Waiting for backend to be ready...
set RETRIES=30
:wait_loop
    curl -sf http://localhost:8080/health >nul 2>&1
    if %ERRORLEVEL% EQU 0 goto ready
    set /a RETRIES-=1
    if %RETRIES% EQU 0 (
        echo [ERROR] Backend did not start in time.
        echo         Check logs: docker compose logs backend
        pause
        exit /b 1
    )
    timeout /t 3 /nobreak >nul
    goto wait_loop

:ready
echo.
echo  +========================================+
echo  ^|         Digital FTE is Ready!         ^|
echo  +========================================+
echo  ^|  Frontend:  http://localhost:5173      ^|
echo  ^|  Backend:   http://localhost:8080      ^|
echo  ^|  API Docs:  http://localhost:8080/docs ^|
echo  +========================================+
echo.
echo  To stop:  docker compose down
echo  Logs:     docker compose logs -f
echo.
pause
