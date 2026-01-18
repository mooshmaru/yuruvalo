import discord
from discord.ext import commands
from discord.ui import Button, View, Select
from typing import Optional
import random

class MiniGame(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @discord.slash_command(name="random_team", description="ランダムにチームを分けます")
    async def random_team(
        self,
        ctx: discord.ApplicationContext,
        メンバー: str = discord.Option(str, "メンバー名（カンマ区切り）", required=True),
        チーム数: int = discord.Option(int, "チーム数", min_value=2, max_value=5, default=2)
    ):
        members = [m.strip() for m in メンバー.split(",")]
        if len(members) < チーム数:
            await ctx.respond("メンバー数がチーム数より少ないです。", ephemeral=True)
            return
        
        random.shuffle(members)
        teams = [[] for _ in range(チーム数)]
        
        for i, member in enumerate(members):
            teams[i % チーム数].append(member)
        
        embed = discord.Embed(
            title="👥 ランダムチーム分け",
            color=discord.Color.purple()
        )
        
        for i, team in enumerate(teams, 1):
            embed.add_field(
                name=f"チーム {i}",
                value="\n".join(team) if team else "なし",
                inline=True
            )
        
        await ctx.respond(embed=embed)
    
    @discord.slash_command(name="choose", description="選択肢からランダムに選びます")
    async def choose(
        self,
        ctx: discord.ApplicationContext,
        選択肢: str = discord.Option(str, "選択肢（カンマ区切り）", required=True)
    ):
        choices = [c.strip() for c in 選択肢.split(",")]
        if len(choices) < 2:
            await ctx.respond("2つ以上の選択肢を入力してください。", ephemeral=True)
            return
        
        result = random.choice(choices)
        
        embed = discord.Embed(
            title="🎯 ランダム選択",
            description=f"選択肢: {', '.join(choices)}",
            color=discord.Color.green()
        )
        embed.add_field(name="結果", value=f"**{result}**", inline=False)
        
        await ctx.respond(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(MiniGame(bot))
