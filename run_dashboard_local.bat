@echo off
title Menjalankan Public Policy Dashboard (Lokal)
cd /d "%~dp0"
echo ========================================================
echo   MENJALANKAN STREAMLIT DASHBOARD SECARA LOKAL
echo ========================================================
echo.
echo Membuka aplikasi di peramban (http://localhost:8501)...
echo Tekan CTRL + C di jendela ini untuk mematikan server.
echo.
python -m streamlit run app.py
pause

