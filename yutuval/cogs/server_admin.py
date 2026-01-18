import discord
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from typing import Optional

class ServerAdmin(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @discord.slash_command(name="kick", description="メンバーをキックします（モデレーター限定）")
    @commands.has_permissions(kick_members=True)
    async def kick(
        self,
        ctx: discord.ApplicationContext,
        メンバー: discord.Member = discord.Option(discord.Member, "キックするメンバー", required=True),
        理由: str = discord.Option(str, "理由", required=False, default="理由なし")
    ):
        """メンバーをキック"""
        if メンバー.top_role >= ctx.author.top_role:
            await ctx.respond("自分より上位のメンバーをキックできません。", ephemeral=True)
            return
        
        try:
            await メンバー.kick(reason=f"{ctx.author} による実行: {理由}")
            
            embed = discord.Embed(
                title="👢 メンバーをキックしました",
                color=discord.Color.orange(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="対象", value=メンバー.mention, inline=True)
            embed.add_field(name="実行者", value=ctx.author.mention, inline=True)
            embed.add_field(name="理由", value=理由, inline=False)
            
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"キックに失敗しました: {str(e)}", ephemeral=True)
    
    @discord.slash_command(name="ban", description="メンバーをBANします（モデレーター限定）")
    @commands.has_permissions(ban_members=True)
    async def ban(
        self,
        ctx: discord.ApplicationContext,
        メンバー: discord.Member = discord.Option(discord.Member, "BANするメンバー", required=True),
        理由: str = discord.Option(str, "理由", required=False, default="理由なし"),
        メッセージ削除日数: int = discord.Option(int, "削除するメッセージの日数", min_value=0, max_value=7, default=0)
    ):
        """メンバーをBAN"""
        if メンバー.top_role >= ctx.author.top_role:
            await ctx.respond("自分より上位のメンバーをBANできません。", ephemeral=True)
            return
        
        try:
            await メンバー.ban(reason=f"{ctx.author} による実行: {理由}", delete_message_days=メッセージ削除日数)
            
            embed = discord.Embed(
                title="🔨 メンバーをBANしました",
                color=discord.Color.red(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="対象", value=メンバー.mention, inline=True)
            embed.add_field(name="実行者", value=ctx.author.mention, inline=True)
            embed.add_field(name="理由", value=理由, inline=False)
            
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"BANに失敗しました: {str(e)}", ephemeral=True)
    
    @discord.slash_command(name="timeout", description="メンバーをタイムアウトします（モデレーター限定）")
    @commands.has_permissions(moderate_members=True)
    async def timeout(
        self,
        ctx: discord.ApplicationContext,
        メンバー: discord.Member = discord.Option(discord.Member, "タイムアウトするメンバー", required=True),
        時間_分: int = discord.Option(int, "タイムアウト時間（分）", min_value=1, max_value=40320, required=True),
        理由: str = discord.Option(str, "理由", required=False, default="理由なし")
    ):
        """メンバーをタイムアウト"""
        if メンバー.top_role >= ctx.author.top_role:
            await ctx.respond("自分より上位のメンバーをタイムアウトできません。", ephemeral=True)
            return
        
        try:
            duration = timedelta(minutes=時間_分)
            await メンバー.timeout_for(duration, reason=f"{ctx.author} による実行: {理由}")
            
            embed = discord.Embed(
                title="⏰ メンバーをタイムアウトしました",
                color=discord.Color.yellow(),
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="対象", value=メンバー.mention, inline=True)
            embed.add_field(name="実行者", value=ctx.author.mention, inline=True)
            embed.add_field(name="期間", value=f"{時間_分}分", inline=True)
            embed.add_field(name="理由", value=理由, inline=False)
            
            await ctx.respond(embed=embed)
        except Exception as e:
            await ctx.respond(f"タイムアウトに失敗しました: {str(e)}", ephemeral=True)
    
    @discord.slash_command(name="serverstats", description="サーバーの統計情報を表示します")
    async def serverstats(self, ctx: discord.ApplicationContext):
        """サーバー統計を表示"""
        guild = ctx.guild
        
        # 統計計算
        total_members = guild.member_count
        bots = len([m for m in guild.members if m.bot])
        humans = total_members - bots
        
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        roles = len(guild.roles)
        
        embed = discord.Embed(
            title=f"📊 {guild.name} サーバー統計",
            color=discord.Color.blue(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.add_field(name="👥 総メンバー数", value=f"{total_members}", inline=True)
        embed.add_field(name="🧑 人間", value=f"{humans}", inline=True)
        embed.add_field(name="🤖 Bot", value=f"{bots}", inline=True)
        
        embed.add_field(name="💬 テキストチャンネル", value=f"{text_channels}", inline=True)
        embed.add_field(name="🔊 ボイスチャンネル", value=f"{voice_channels}", inline=True)
        embed.add_field(name="📁 カテゴリ", value=f"{categories}", inline=True)
        
        embed.add_field(name="🎭 ロール数", value=f"{roles}", inline=True)
        embed.add_field(name="📅 作成日", value=guild.created_at.strftime("%Y-%m-%d"), inline=True)
        embed.add_field(name="👑 オーナー", value=guild.owner.mention if guild.owner else "不明", inline=True)
        
        await ctx.respond(embed=embed)
    
    @discord.slash_command(name="clear", description="メッセージを一括削除します（モデレーター限定）")
    @commands.has_permissions(manage_messages=True)
    async def clear(
        self,
        ctx: discord.ApplicationContext,
        数: int = discord.Option(int, "削除するメッセージ数", min_value=1, max_value=100, required=True)
    ):
        """メッセージを一括削除"""
        try:
            await ctx.defer(ephemeral=True)
            deleted = await ctx.channel.purge(limit=数)
            await ctx.followup.send(f"✅ {len(deleted)}件のメッセージを削除しました。", ephemeral=True)
        except Exception as e:
            await ctx.followup.send(f"削除に失敗しました: {str(e)}", ephemeral=True)

def setup(bot: commands.Bot):
    bot.add_cog(ServerAdmin(bot))
