@echo off
rem AegisOS backend starter (ASCII only, dp0-relative)
cd /d "%~dp0..\.."
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 >> "%~dp0..\..\logs\backend.out.log" 2>&1