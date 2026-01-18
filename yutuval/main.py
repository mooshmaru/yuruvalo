import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv
from utils.db_manager import db

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = os.getenv("GUILD_ID")

# Guild IDをリストに変換（デバッグ用の高速同期）
DEBUG_GUILDS = [int(GUILD_ID)] if GUILD_ID else None

class ValorantBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.voice_states = True
        
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None
            # debug_guilds=DEBUG_GUILDS # コンストラクタでの指定を廃止し、on_readyで手動同期する
        )
        self.synced = False  # 同期済みフラグ

    async def on_ready(self):
        # Prevent multiple executions
        if self.synced:
            return

        print("=" * 50)
        print("🚀 Bot起動処理を開始...")
        print("=" * 50)
        
        # Database connection
        await db.connect()
        print("✅ データベース接続完了")
        
        # Load extensions
        loaded_cogs = []
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    # Check if already loaded to avoid errors on reload
                    extension_name = f"cogs.{filename[:-3]}"
                    if extension_name not in self.extensions:
                        self.load_extension(extension_name)
                        loaded_cogs.append(filename[:-3])
                        print(f"✅ 拡張機能ロード: {filename}")
                except Exception as e:
                    print(f"❌ 拡張機能ロード失敗: {filename} - {e}")
        
        print(f"\n📦 ロード済みCog: {', '.join(loaded_cogs)}")
        
        # Sync commands
        try:
            if GUILD_ID:
                guild = discord.Object(id=int(GUILD_ID))
                print(f"🔄 コマンド同期を開始します... (Guild Sync: {GUILD_ID})")
                await self.sync_commands(guild_ids=[int(GUILD_ID)])
            else:
                print("🔄 コマンド同期を開始します... (Global Sync - 反映に最大1時間かかります)")
                await self.sync_commands()
            self.synced = True
            
            command_count = len(self.pending_application_commands)
            print(f"✅ コマンド登録数（概算）: {command_count} 個")
            
            if command_count > 0:
                print(f"\n📋 登録されたコマンド一覧:")
                for cmd in self.pending_application_commands:
                    print(f"  - /{cmd.name}: {cmd.description}")
            else:
                print("\n⚠️ 警告: 登録されたコマンドが0個です。")
                
        except Exception as e:
            print(f"❌ コマンド同期失敗: {e}")
            import traceback
            traceback.print_exc()

        print("\n" + "=" * 50)
        print(f"✅ ログイン成功!")
        print(f"👤 Bot名: {self.user}")
        print(f"🆔 Bot ID: {self.user.id}")
        print(f"🖥️ 参加サーバー数: {len(self.guilds)}")
        
        if self.guilds:
            print(f"\n📡 参加中のサーバー:")
            for guild in self.guilds:
                print(f"  - {guild.name} (ID: {guild.id})")
        
        print("=" * 50)
        print("✨ Botは正常に動作しています！")
        print("💡 スラッシュコマンドが表示されない場合は、チャンネルで !sync と入力してください")
        print("=" * 50 + "\n")

    async def on_application_command_error(self, ctx: discord.ApplicationContext, error):
        """グローバルエラーハンドラ"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.respond("❌ このコマンドを実行する権限がありません。", ephemeral=True)
        elif isinstance(error, commands.BotMissingPermissions):
            await ctx.respond("❌ Botに必要な権限がありません。", ephemeral=True)
        elif isinstance(error, commands.CommandOnCooldown):
            await ctx.respond(f"⏳ クールダウン中です。{error.retry_after:.1f}秒後に再試行してください。", ephemeral=True)
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.respond("❌ このコマンドはDMでは使用できません。", ephemeral=True)
        else:
            # 予期せぬエラー
            print(f"❌ コマンドエラー ({ctx.command.name if ctx.command else 'Unknown'}): {error}")
            import traceback
            traceback.print_exception(type(error), error, error.__traceback__)
            
            try:
                await ctx.respond(
                    f"❌ エラーが発生しました。\n```{str(error)[:200]}```",
                    ephemeral=True
                )
            except:
                pass

    async def close(self):
        await db.close()
        await super().close()

bot = ValorantBot()

# Test global command
@bot.slash_command(name="ping", description="Botの応答速度を確認します")
async def ping(ctx):
    await ctx.respond(f"🏓 Pong! Latency: {round(bot.latency * 1000)}ms")

@bot.command(name="sync")
@commands.is_owner()
async def sync_slash_commands(ctx):
    """手動でスラッシュコマンドを同期 (Bot所有者のみ)"""
    try:
        await ctx.send("🔄 コマンドを同期中...")
        await bot.sync_commands()
        command_count = len(bot.pending_application_commands)
        
        # List all commands
        cmd_list = "\n".join([f"  - /{cmd.name}" for cmd in bot.pending_application_commands])
        
        await ctx.send(
            f"✅ コマンド同期完了！\n"
            f"📊 登録済みコマンド数: {command_count}個\n"
            f"\n{cmd_list if cmd_list else '（コマンドなし）'}\n\n"
            f"💡 Discordクライアントを完全に再起動してください。"
        )
    except Exception as e:
        await ctx.send(f"❌ 同期失敗: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if not TOKEN:
        print("❌ エラー: DISCORD_TOKENが.envファイルに見つかりません")
    else:
        print("🔐 Tokenを検出しました。起動中...\n")
        bot.run(TOKEN)

