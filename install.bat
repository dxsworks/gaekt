@echo off
cd /d "%~dp0"
pip install -r requirements.txt
if not exist config.json copy config.example.json config.json
python scripts\make_shortcut.py
pause
