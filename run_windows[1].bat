@echo off
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
set ADMIN_USERNAME=admin
set ADMIN_PASSWORD=ChangeMe123!
set SECRET_KEY=replace-this-with-a-long-random-secret
python app.py
pause
