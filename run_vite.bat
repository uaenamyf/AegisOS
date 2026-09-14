@echo off
cd /d "E:\???\2026???\AegisOS-prd-9-11\AegisOS-prd\frontend"
"C:\Program Files\nodejs\node.exe" node_modules\vite\bin\vite.js --port 5173 > vite.out.log 2>&1
echo EXIT=%ERRORLEVEL% >> vite.out.log
