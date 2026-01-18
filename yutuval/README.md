# Valorant Discord Bot

ValorantサーバーのためのDiscord Bot。募集機能、VC自動管理、ロール管理、ログ機能を搭載。

## 機能一覧

### 🎮 募集・VC管理
- `/recruit` - 募集パネルを作成（設定されたチャンネルに自動投稿）
- `/menu` - **機能統合ダッシュボード**（ここから全機能にアクセス可能）
  - 参加/辞退ボタン
  - 定員到達で自動〆切・VC作成
- VC自動管理
  - ロック/アンロック機能
  - パーティーコード設定
  - 空VC自動削除（60秒後）

### 📊 Valorant情報
- `/agent [名前]` - エージェント情報表示
- `/map [名前]` - マップ情報表示
- `/valorant_help` - コマンドヘルプ

### 🛡️ サーバー管理
- `/kick` - メンバーをキック
- `/ban` - メンバーをBAN
- `/timeout` - メンバーをタイムアウト
- `/moveall [移動先]` - VCメンバー一括移動（管理者のみ）
- `/serverstats` - サーバー統計表示
- `/stats ranking` - サーバー内ランキング表示（管理者のみ）
- `/clear` - メッセージ一括削除
- `/rolepanel_create` - ロールパネル作成

### 🎲 ミニゲーム
- `/coinflip` - コイントス
- `/dice [個数] [面数]` - サイコロを振る
- `/random_team [メンバー] [チーム数]` - ランダムチーム分け
- `/choose [選択肢]` - ランダム選択

### 🔧 ユーティリティ
- `/poll [質問] [選択肢...]` - 投票作成
- `/remind [時間_分] [メッセージ]` - リマインダー設定
- `/avatar [ユーザー]` - アバター表示
- `/userinfo [ユーザー]` - ユーザー情報表示

### 📝 ログ機能（強化版）
- **メンバーログ**: 参加/退出時の詳細情報
  - アカウント年齢表示（新規アカウント警告付き）
  - 在籍期間・所持ロール表示
- **VCログ**: 入退出/移動の詳細ログ
  - 現在の参加者リスト表示
  - チャンネル情報・人数表示
- **メッセージログ**: 編集/削除の追跡
  - 編集前後の内容比較
  - 添付ファイル情報
- **ロールログ**: ロール追加/削除の追跡
- **募集ログ**: 募集作成/参加/終了の追跡
- カテゴリ別のカラー分け・視認性向上

### 📊 統計トラッキング
- `/stats overview` - サーバー全体の統計ダッシュボード
- `/stats messages [days]` - メッセージ統計（送信/編集/削除）
- `/stats voice [days]` - VC利用統計
- `/stats recruitment [days]` - 募集統計
- `/stats members [days]` - メンバー増減統計
- `/stats roles [days]` - ロール変更統計

## セットアップ

### 1. 必要な環境
- Python 3.10以上
- Discord Bot Token

### 2. インストール
```powershell
# 依存関係をインストール
pip install -r requirements.txt
```

### 3. 環境変数設定
`.env` ファイルを編集：
```env
DISCORD_TOKEN=your_bot_token_here
GUILD_ID=your_guild_id_here
LOG_CHANNEL_ID=your_log_channel_id_here
VC_CATEGORY_ID=your_vc_category_id_here
```

### 4. Bot権限設定
Discord Developer Portalで以下の権限を有効化：
- `Intents`: Server Members, Message Content, Voice States
- `Permissions`: 管理者権限、またはメッセージ・VC・ロール管理権限

### 5. 起動
```powershell
# PowerShellの場合
.\run_bot.ps1

# バッチファイルの場合
run_bot.bat

# または直接
python main.py
```

## プロジェクト構成
```
root/
├── .env                  # 環境変数（要設定）
├── main.py               # Bot起動ファイル
├── requirements.txt      # Python依存関係
├── run_bot.ps1           # PowerShell起動スクリプト
├── run_bot.bat           # バッチ起動スクリプト
├── database/
│   └── bot_data.db       # SQLiteデータベース（自動生成）
├── utils/
│   ├── __init__.py
│   └── db_manager.py     # DB管理モジュール
└── cogs/                 # 機能モジュール
    ├── recruiting.py     # 募集システム
    ├── vc_manager.py     # VC管理
    ├── role_panel.py     # ロールパネル
    ├── logger.py         # ログ機能（強化版）
    ├── statistics.py     # 統計トラッキング
    ├── valorant_info.py  # Valorant情報
    ├── server_admin.py   # サーバー管理
    ├── mini_games.py     # ミニゲーム
    └── utility.py        # ユーティリティ
```

## 技術スタック
- **言語**: Python 3.10+
- **ライブラリ**: py-cord
- **データベース**: SQLite (aiosqlite)
- **設定管理**: python-dotenv

## トラブルシューティング

### スラッシュコマンドが表示されない
- **解決済み**: `main.py`で`debug_guilds`パラメータを追加したため、`.env`に`GUILD_ID`を設定すれば即座に反映されます
- `.env`の`GUILD_ID`が正しく設定されているか確認してください
- Bot再起動後、数秒でコマンドが表示されるはずです

### VCが作成されない
- `.env`の`VC_CATEGORY_ID`が正しく設定されているか確認
- Botにチャンネル作成権限があるか確認

### ログが送信されない
- `.env`の`LOG_CHANNEL_ID`が正しく設定されているか確認
- Botにそのチャンネルへのアクセス権限があるか確認

## ライセンス
MIT License

## 作成者
Valorant Community Bot Development Team
