# Botセットアップガイド

## 1. Discord Developer Portalでの設定

### Botの作成
1. [Discord Developer Portal](https://discord.com/developers/applications) にアクセス
2. 「New Application」をクリック
3. アプリケーション名を入力（例: Valorant Bot）
4. 「Bot」タブに移動 → 「Add Bot」をクリック

### Bot設定
1. **Token取得**
   - 「Reset Token」→ Tokenをコピー
   - `.env`ファイルの`DISCORD_TOKEN`に貼り付け

2. **Privileged Gateway Intents**
   - `SERVER MEMBERS INTENT` ✅
   - `MESSAGE CONTENT INTENT` ✅
   - `PRESENCE INTENT` （オプション）

3. **OAuth2 URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions:
     - Administrator（推奨）または以下の権限：
       - Manage Channels
       - Manage Roles
       - Kick Members
       - Ban Members
       - Moderate Members
       - Manage Messages
       - Read Messages/View Channels
       - Send Messages
       - Manage Threads
       - Create Public Threads
       - Embed Links
       - Attach Files
       - Read Message History
       - Add Reactions
       - Connect
       - Speak
       - Move Members

4. **招待URLをコピー**してサーバーに招待

## 2. サーバーIDとチャンネルIDの取得

### Developer Modeを有効化
1. Discord設定 → 詳細設定 → Developer Mode をON

### ID取得方法
- **サーバーID**: サーバー名を右クリック → IDをコピー
- **チャンネルID**: チャンネル名を右クリック → IDをコピー

## 3. .envファイルの設定

```env
# Botトークン（必須）
DISCORD_TOKEN=your_bot_token_here

# サーバーID（推奨 - コマンド同期が速くなります）
GUILD_ID=123456789012345678

# ログチャンネルID（推奨）
LOG_CHANNEL_ID=123456789012345678

# VCを作成するカテゴリID（推奨）
VC_CATEGORY_ID=123456789012345678
```

## 4. Pythonのインストール

1. [Python公式サイト](https://www.python.org/downloads/)からPython 3.10以上をダウンロード
2. インストール時に「Add Python to PATH」にチェック

## 5. 依存関係のインストール

PowerShellまたはコマンドプロンプトで：
```powershell
pip install -r requirements.txt
```

## 6. Bot起動

### 方法1: 起動スクリプト（推奨）
```powershell
# PowerShell
.\run_bot.ps1

# またはバッチファイル
run_bot.bat
```

### 方法2: 直接実行
```powershell
python main.py
```

## トラブルシューティング

### 「python: コマンドが見つかりません」
- Pythonのインストール時にPATHに追加されているか確認
- `py main.py` または `python3 main.py` を試してください

### 「No module named 'discord'」
- `pip install -r requirements.txt` を実行してください

### Botがオンラインにならない
- `.env`のトークンが正しいか確認
- Developer PortalでTokenをリセットして再度設定

## 次のステップ

1. Botがオンラインになったら、Discordで `/valorant_help` を入力
2. コマンド一覧が表示されます
3. `/recruit 5 ゴールド ランク` などで募集を作成してテスト
