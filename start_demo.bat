@echo off
echo Password Cracking Simulator Demo
echo ==================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting demo with 2 workers...
python start_pcs.py 2
pause