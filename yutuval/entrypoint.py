import os
from keep_alive import keep_alive
from main import bot, TOKEN

# KoyebなどのPaaSで常時起動するためのエントリーポイント
if __name__ == "__main__":
    # Webサーバーをバックグラウンドで起動
    keep_alive()
    
    # Botを起動
    if not TOKEN:
        print("❌ エラー: DISCORD_TOKENが.envファイルに見つかりません")
    else:
        print("🔐 Tokenを検出しました。起動中... (Hosted Mode)")
        bot.run(TOKEN)
