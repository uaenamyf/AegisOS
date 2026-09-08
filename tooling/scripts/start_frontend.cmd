@echo off
rem AegisOS frontend starter (ASCII only, dp0-relative)
cd /d "%~dp0..\..\frontend"
"C:\Program Files\nodejs\node.exe" node_modules\vite\bin\vite.js --port 5173 >> "%~dp0..\..\logs\frontend.out.log" 2>&1