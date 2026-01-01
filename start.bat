# Quick Start Guide

@echo off
echo ================================================
echo Stock Market Watchlist API - Quick Start
echo ================================================
echo.

echo Step 1: Checking Docker...
docker --version
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

echo Step 2: Checking .env file...
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo.
    echo IMPORTANT: Edit .env and add your Alpha Vantage API key
    echo Get it free at: https://www.alphavantage.co/support/#api-key
    echo.
    pause
)

echo Step 3: Building Docker containers...
docker-compose build

echo Step 4: Starting services...
docker-compose up -d

echo Step 5: Waiting for database...
timeout /t 10

echo Step 6: Running migrations...
docker-compose exec web python manage.py migrate

echo Step 7: Creating superuser...
echo You'll be prompted for email and password
docker-compose exec web python manage.py createsuperuser

echo.
echo ================================================
echo Setup Complete!
echo ================================================
echo.
echo Access the application:
echo - API: http://localhost:8000/api/v1/
echo - Admin: http://localhost:8000/admin/
echo - API Docs: http://localhost:8000/api/docs/
echo - Health Check: http://localhost:8000/api/v1/health/
echo.
echo To view logs:
echo   docker-compose logs -f
echo.
echo To stop:
echo   docker-compose down
echo.
pause
