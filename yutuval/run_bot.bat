@echo off
rem 文字コードをUTF-8に変更
chcp 65001 > nul

echo Botを起動しています...

rem 必要なライブラリのインストール確認（任意）
rem pip install -r requirements.txt

rem Pythonの実行
python main.py

echo Botが終了しました。
pause
