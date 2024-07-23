@echo off
chcp 65001 > nul
echo Установка зависимостей
pip install -r requirements.txt
echo Зависимости успешно установлены!
echo Пожалуйста отредактируйте config.py, пример заполнения можно найти в example_config.py
pause
