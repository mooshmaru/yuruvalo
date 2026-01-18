# Python 3.10を使用
FROM python:3.10-slim

# 作業ディレクトリを /app に設定
WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# その他のソースコードをコピー
COPY . .

# Koyeb用にポート3000を開放
EXPOSE 3000

# BotとWebサーバーを起動するスクリプトを実行
CMD ["python", "entrypoint.py"]
