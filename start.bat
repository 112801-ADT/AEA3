@echo off
cd /d "%~dp0"
echo Starting AI Accounting Tool...
C:\Users\cwe93\anaconda3\envs\EE\python.exe -m streamlit run app_keyloop.py
pause
