import discord
from discord.ext import commands

class ValorantInfo(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @discord.slash_command(name="valorant_help", description="Valorant関連コマンドのヘルプを表示")
    async def valo_help(self, ctx: discord.ApplicationContext):
        """Valorantコマンドヘルプ"""
        embed = discord.Embed(
            title="📚 Valorant Bot コマンド一覧",
            description="利用可能なコマンド",
            color=discord.Color.red()
        )
        embed.add_field(
            name="🎮 募集・VC関連",
            value="`/recruit` - 募集パネル作成\nVC操作パネル - ロック/コード設定/解散",
            inline=False
        )
        embed.add_field(
            name="🛡️ 管理コマンド",
            value="`/rolepanel` - ロールパネル作成\n`/serverstats` - サーバー統計\n`/kick`, `/ban`, `/timeout` - モデレーション",
            inline=False
        )
        
        await ctx.respond(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(ValorantInfo(bot))
