import discord
from discord.ext import commands
from discord.ui import Button, View, Select
import asyncio
from typing import Optional, List

# デザイン定数
COLOR_PRIMARY = 0x5865F2  # Blurple
COLOR_SUCCESS = 0x00D26A  # Green
COLOR_DANGER = 0xFF4757  # Red
COLOR_WARNING = 0xFFA500  # Orange
COLOR_INFO = 0x3498DB     # Blue

class DashboardView(View):
    """メインダッシュボードのView"""
    def __init__(self, bot: commands.Bot):
        super().__init__(timeout=None)
        self.bot = bot

    # ==================== 第1段目: 主要機能 ====================
    
    @discord.ui.button(label="募集を作成する", style=discord.ButtonStyle.success, emoji="🎮", row=0, custom_id="dashboard_recruit")
    async def create_recruit(self, button: Button, interaction: discord.Interaction):
        try:
            # Recruiting Cogの募集ウィザードを呼び出す
            recruiting_cog = self.bot.get_cog("Recruiting")
            if recruiting_cog:
                config = await recruiting_cog.get_guild_rank_config(interaction.guild.id)
                from cogs.recruiting import RecruitmentWizard
                view = RecruitmentWizard(interaction.user.id, config)
                await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)
            else:
                await interaction.response.send_message("❌ 募集機能がロードされていません。", ephemeral=True)
        except Exception as e:
            print(f"Dashboard recruit error: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ エラーが発生しました: {str(e)[:100]}", ephemeral=True)

    @discord.ui.button(label="Valorant情報", style=discord.ButtonStyle.secondary, emoji="📚", row=0, custom_id="dashboard_info")
    async def valo_info(self, button: Button, interaction: discord.Interaction):
        embed = discord.Embed(title="📚 Valorant情報メニュー", description="調べたい情報を選択してください", color=COLOR_INFO)
        view = ValoInfoSelectView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="便利ツール", style=discord.ButtonStyle.secondary, emoji="🛠️", row=0, custom_id="dashboard_tools")
    async def tools(self, button: Button, interaction: discord.Interaction):
        embed = discord.Embed(title="🛠️ 便利ツールメニュー", description="使用するツールを選択してください", color=COLOR_PRIMARY)
        view = ToolsView(self.bot)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    # ==================== 第2段目: 統計 ====================

    @discord.ui.button(label="サーバー統計", style=discord.ButtonStyle.primary, emoji="📊", row=1, custom_id="dashboard_stats")
    async def show_stats(self, button: Button, interaction: discord.Interaction):
        # 権限チェック
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("⚠️ この機能は管理者のみ使用可能です。", ephemeral=True)
            return

        stats_cog = self.bot.get_cog("Statistics")
        if stats_cog:
            # Overviewコマンドを内部的に実行するか、専用のViewを出す
            # ここではコマンドをシミュレートするのではなく、関数を直接呼び出すのは引数が必要で複雑なので
            # 統計用のサブメニューを表示する
            embed = discord.Embed(
                title="📊 統計詳細メニュー",
                description="確認したい統計データを選択してください",
                color=COLOR_PRIMARY
            )
            view = StatsMenuView(self.bot)
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
             await interaction.response.send_message("統計機能がロードされていません。", ephemeral=True)

class ValoInfoSelectView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.select(
        placeholder="情報を選択...",
        options=[
            discord.SelectOption(label="エージェント情報", value="agents", emoji="👤"),
            discord.SelectOption(label="マップ情報", value="maps", emoji="🗺️"),
            discord.SelectOption(label="武器情報", value="weapons", emoji="🔫"),
            discord.SelectOption(label="ランク分布", value="ranks", emoji="🏆"),
        ]
    )
    async def select_callback(self, select: Select, interaction: discord.Interaction):
        val = select.values[0]
        # 簡易的な応答（本来はValorantInfo Cogからデータ取得すべきだが、簡略化のためここに応答）
        await interaction.response.send_message(f"ℹ️ {val} の情報は現在準備中です。（外部API連携等が可能です）", ephemeral=True)

class ToolsView(View):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @discord.ui.button(label="チーム分け", style=discord.ButtonStyle.secondary, emoji="👥")
    async def team_divider(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message(
            "👥 **チーム分け機能**\n`/random_team メンバー1,メンバー2... チーム数`\nコマンドを使用してください。", 
            ephemeral=True
        )

    @discord.ui.button(label="コイントス", style=discord.ButtonStyle.secondary, emoji="🪙")
    async def coin_flip(self, button: Button, interaction: discord.Interaction):
        import random
        result = random.choice(["表 (Head)", "裏 (Tail)"])
        await interaction.response.send_message(f"🪙 **{result}** です！", ephemeral=True)
    
    @discord.ui.button(label="ユーザー情報", style=discord.ButtonStyle.secondary, emoji="👤")
    async def user_info(self, button: Button, interaction: discord.Interaction):
        # Utility Cogの関数を再利用するのはコンテキストが必要なので、簡易実装
        embed = discord.Embed(title="👤 あなたの情報", color=interaction.user.color)
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.add_field(name="名前", value=str(interaction.user))
        embed.add_field(name="ID", value=interaction.user.id)
        embed.add_field(name="アカウント作成", value=interaction.user.created_at.strftime("%Y/%m/%d"))
        await interaction.response.send_message(embed=embed, ephemeral=True)


class StatsMenuView(View):
    def __init__(self, bot):
        super().__init__()
        self.bot = bot

    @discord.ui.select(
        placeholder="統計カテゴリーを選択...",
        options=[
            discord.SelectOption(label="全体サマリー", value="overview", emoji="📈"),
            discord.SelectOption(label="メッセージ統計", value="messages", emoji="💬"),
            discord.SelectOption(label="VC利用統計", value="voice", emoji="🔊"),
            discord.SelectOption(label="募集統計", value="recruitment", emoji="🎮"),
            discord.SelectOption(label="メンバー推移", value="members", emoji="👥"),
        ]
    )
    async def select_callback(self, select: Select, interaction: discord.Interaction):
        val = select.values[0]
        stats_cog = self.bot.get_cog("Statistics")
        if not stats_cog: return
        
        # 本来はContextを作成してコマンドを呼び出すのが筋だが、
        # ここでは簡易メッセージで案内する（複雑さを避けるため）
        cmd_map = {
            "overview": "/stats overview",
            "messages": "/stats messages",
            "voice": "/stats voice",
            "recruitment": "/stats recruitment",
            "members": "/stats members"
        }
        await interaction.response.send_message(
            f"📊 **統計の表示方法**\n以下のコマンドを実行してください：\n`{cmd_map.get(val, '/stats')}`", 
            ephemeral=True
        )


class Dashboard(commands.Cog):
    """🎛️ 機能統合ダッシュボード"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @discord.slash_command(name="menu", description="機能統合メニューを表示します")
    async def menu(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(
            title="🎮 Bot メインメニュー",
            description="機能を選択してください。",
            color=COLOR_PRIMARY
        )
        embed.set_thumbnail(url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        
        embed.add_field(name="募集機能", value="ValorantのPT募集を作成します", inline=True)
        embed.add_field(name="Bot情報/設定", value="機能確認や管理者用設定", inline=True)
        
        view = DashboardView(self.bot)
        await ctx.respond(embed=embed, view=view, ephemeral=True) # メニューは自分だけに表示

    @commands.Cog.listener()
    async def on_ready(self):
        # 永続的なViewが必要ならここで追加するが、今回はmenuコマンドで都度生成する形式
        self.bot.add_view(DashboardView(self.bot))


def setup(bot: commands.Bot):
    bot.add_cog(Dashboard(bot))
