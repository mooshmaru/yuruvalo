import discord
from discord.ext import commands
from discord.ui import Button, View
import asyncio
from typing import Optional, List

class Poll(View):
    def __init__(self, options: List[str], author_id: int):
        super().__init__(timeout=None)
        self.options = options
        self.author_id = author_id
        self.votes = {i: [] for i in range(len(options))}
        
        for i, option in enumerate(options):
            button = Button(
                label=f"{option} (0票)",
                style=discord.ButtonStyle.blurple,
                custom_id=f"poll_{i}"
            )
            button.callback = self.make_callback(i)
            self.add_item(button)
        
        end_button = Button(
            label="📊 結果を表示",
            style=discord.ButtonStyle.green,
            custom_id="poll_end"
        )
        end_button.callback = self.end_poll
        self.add_item(end_button)
    
    def make_callback(self, option_index: int):
        async def callback(interaction: discord.Interaction):
            user_id = interaction.user.id
            
            for votes in self.votes.values():
                if user_id in votes:
                    votes.remove(user_id)
            
            self.votes[option_index].append(user_id)
            
            for i, child in enumerate(self.children[:-1]):
                child.label = f"{self.options[i]} ({len(self.votes[i])}票)"
            
            await interaction.response.edit_message(view=self)
            await interaction.followup.send(f"「{self.options[option_index]}」に投票しました！", ephemeral=True)
        
        return callback
    
    async def end_poll(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("投票の作成者のみが結果を表示できます。", ephemeral=True)
            return
        
        for child in self.children:
            child.disabled = True
        
        await interaction.response.edit_message(view=self)
        
        total_votes = sum(len(votes) for votes in self.votes.values())
        embed = discord.Embed(
            title="📊 投票結果",
            description=f"総投票数: {total_votes}票",
            color=discord.Color.gold()
        )
        
        for i, option in enumerate(self.options):
            vote_count = len(self.votes[i])
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            bar_length = int(percentage / 10)
            bar = "█" * bar_length + "░" * (10 - bar_length)
            
            embed.add_field(
                name=f"{option}",
                value=f"{bar} {vote_count}票 ({percentage:.1f}%)",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @discord.slash_command(name="poll", description="投票を作成します")
    async def poll(
        self,
        ctx: discord.ApplicationContext,
        質問: str = discord.Option(str, "投票の質問", required=True),
        選択肢1: str = discord.Option(str, "選択肢1", required=True),
        選択肢2: str = discord.Option(str, "選択肢2", required=True),
        選択肢3: str = discord.Option(str, "選択肢3", required=False, default=None),
        選択肢4: str = discord.Option(str, "選択肢4", required=False, default=None),
        選択肢5: str = discord.Option(str, "選択肢5", required=False, default=None)
    ):
        options = [選択肢1, 選択肢2]
        if 選択肢3:
            options.append(選択肢3)
        if 選択肢4:
            options.append(選択肢4)
        if 選択肢5:
            options.append(選択肢5)
        
        embed = discord.Embed(
            title="📊 " + 質問,
            description="下のボタンから選択してください",
            color=discord.Color.blue()
        )
        embed.set_footer(text=f"作成者: {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        view = Poll(options, ctx.author.id)
        await ctx.respond(embed=embed, view=view)
    
    @discord.slash_command(name="remind", description="指定時間後にリマインドします")
    async def remind(
        self,
        ctx: discord.ApplicationContext,
        時間_分: int = discord.Option(int, "何分後にリマインド", min_value=1, max_value=1440, required=True),
        メッセージ: str = discord.Option(str, "リマインド内容", required=True)
    ):
        await ctx.respond(f"✅ {時間_分}分後にリマインドします: {メッセージ}", ephemeral=True)
        
        await asyncio.sleep(時間_分 * 60)
        
        embed = discord.Embed(
            title="⏰ リマインダー",
            description=メッセージ,
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"{時間_分}分前に設定されました")
        
        try:
            await ctx.author.send(embed=embed)
        except:
            await ctx.channel.send(f"{ctx.author.mention}", embed=embed)
    
    @discord.slash_command(name="userinfo", description="ユーザー情報を表示します")
    async def userinfo(
        self,
        ctx: discord.ApplicationContext,
        ユーザー: discord.Member = discord.Option(discord.Member, "ユーザー", required=False, default=None)
    ):
        target = ユーザー or ctx.author
        
        embed = discord.Embed(
            title="👤 ユーザー情報",
            color=target.color
        )
        embed.set_thumbnail(url=target.avatar.url if target.avatar else target.default_avatar.url)
        
        embed.add_field(name="ユーザー名", value=str(target), inline=True)
        embed.add_field(name="ニックネーム", value=target.display_name, inline=True)
        embed.add_field(name="ID", value=target.id, inline=True)
        
        embed.add_field(name="アカウント作成日", value=target.created_at.strftime("%Y/%m/%d %H:%M"), inline=True)
        embed.add_field(name="サーバー参加日", value=target.joined_at.strftime("%Y/%m/%d %H:%M") if target.joined_at else "不明", inline=True)
        
        roles = [role.mention for role in target.roles[1:]]
        embed.add_field(
            name=f"ロール ({len(roles)}個)",
            value=" ".join(roles) if roles else "なし",
            inline=False
        )
        
        await ctx.respond(embed=embed)

def setup(bot: commands.Bot):
    bot.add_cog(Utility(bot))
