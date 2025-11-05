@echo off
REM Start Celery Worker for GabeDA Backend
REM This must be running to process uploaded CSV files

echo ========================================
echo Starting Celery Worker for GabeDA
echo ========================================
echo.
echo IMPORTANT: Keep this window open!
echo Celery worker must run to process uploads.
echo.
echo Press Ctrl+C to stop the worker.
echo ========================================
echo.

cd /d C:\Projects\play\gabeda_backend
celery -A config worker -l INFO --pool=solo
