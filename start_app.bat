@echo off
echo Starting Shadow Bookmaker Enterprise Edition...
cd /d %~dp0
set PYTHONPATH=%cd%
call venv\Scripts\activate
streamlit run src/shadow_bookmaker/presentation/app.py
pause