@echo off
cd /d "%~dp0"

echo Instalando dependencias...
py -m pip install -q opencv-python pillow pytesseract pynput numpy python-docx openpyxl

echo Iniciando app...
py app_word_ocr.py

echo Iniciando app...

py -m pip install openpyxl
pause
