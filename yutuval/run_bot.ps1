# 実行ポリシーを変更してスクリプトの実行を許可（必要な場合）
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 文字コードをUTF-8に設定
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Botを起動しています..." -ForegroundColor Cyan

# 仮想環境がある場合はここで有効化（今回はグローバルまたはpipenv等を想定していますが、標準的なコマンドを記載）
# .\venv\Scripts\Activate.ps1

# Pythonの実効
# pythonコマンドが通っている前提です。うまくいかない場合はフルパスを指定してください。
python main.py

Write-Host "Botが終了しました。何かキーを押すと閉じます..." -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
