import discord
from discord.ext import commands
from discord.ui import Button, View, Select, Modal, InputText
from typing import List, Dict
import json

# ロールカテゴリのプリセット
ROLE_CATEGORIES = {
    "ランク帯": {
        "emoji": "🏆",
        "description": "自分のランク帯を選択",
        "color": discord.Color.gold(),
        "roles": ["アイアン", "ブロンズ", "シルバー", "ゴールド", "プラチナ", "ダイヤ", "アセンダント", "イモータル", "レディアント"]
    },
    "エージェント": {
        "emoji": "🎯",
        "description": "得意なエージェントロールを選択",
        "color": discord.Color.red(),
        "roles": ["デュエリスト", "イニシエーター", "コントローラー", "センチネル"]
    },
    "通知": {
        "emoji": "🔔",
        "description": "受け取りたい通知を選択",
        "color": discord.Color.blue(),
        "roles": ["募集通知", "イベント通知", "アップデート通知"]
    }
}


class RoleSelect(Select):
    """ロール選択用のSelectメニュー"""
    def __init__(self, roles: List[discord.Role], category: str):
        options = [
            discord.SelectOption(
                label=role.name,
                value=str(role.id),
                emoji=self._get_emoji(role.name)
            ) for role in roles
        ]
        super().__init__(
            placeholder=f"🎭 ロールを選択してください",
            min_values=0,
            max_values=len(options),
            options=options,
            custom_id=f"role_select_{category}"
        )
        self.roles = {str(role.id): role for role in roles}
    
    def _get_emoji(self, name: str) -> str:
        emoji_map = {
            "アイアン": "🔩", "ブロンズ": "🥉", "シルバー": "🥈", "ゴールド": "🥇",
            "プラチナ": "💎", "ダイヤ": "💠", "アセンダント": "⭐", "イモータル": "👑", "レディアント": "🔥",
            "デュエリスト": "⚔️", "イニシエーター": "🎯", "コントローラー": "🌫️", "センチネル": "🛡️",
            "募集通知": "📢", "イベント通知": "🎉", "アップデート通知": "📰"
        }
        return emoji_map.get(name, "🎭")
    
    async def callback(self, interaction: discord.Interaction):
        selected_ids = set(self.values)
        member = interaction.user
        
        added = []
        removed = []
        
        for role_id, role in self.roles.items():
            if role_id in selected_ids:
                if role not in member.roles:
                    await member.add_roles(role)
                    added.append(role.name)
            else:
                if role in member.roles:
                    await member.remove_roles(role)
                    removed.append(role.name)
        
        messages = []
        if added:
            messages.append(f"✅ 付与: {', '.join(added)}")
        if removed:
            messages.append(f"❌ 削除: {', '.join(removed)}")
        
        if messages:
            await interaction.response.send_message("\n".join(messages), ephemeral=True)
        else:
            await interaction.response.send_message("変更はありません。", ephemeral=True)


class RolePanelView(View):
    """ロールパネル用のView"""
    def __init__(self, roles: List[discord.Role], category: str):
        super().__init__(timeout=None)
        self.add_item(RoleSelect(roles, category))


class RolePanelSetupModal(Modal):
    """ロールパネル設定用のModal"""
    def __init__(self, category: str):
        super().__init__(title=f"ロールパネル設定: {category}")
        self.category = category
        
        self.add_item(InputText(
            label="ロールID（カンマ区切り）",
            placeholder="123456789012345678, 234567890123456789, ...",
            style=discord.InputTextStyle.paragraph,
            required=True
        ))
    
    async def callback(self, interaction: discord.Interaction):
        role_ids_str = self.children[0].value
        role_ids = [int(rid.strip()) for rid in role_ids_str.split(",") if rid.strip().isdigit()]
        
        roles = []
        not_found = []
        for rid in role_ids:
            role = interaction.guild.get_role(rid)
            if role:
                roles.append(role)
            else:
                not_found.append(str(rid))
        
        if not roles:
            await interaction.response.send_message("有効なロールが見つかりませんでした。", ephemeral=True)
            return
        
        category_info = ROLE_CATEGORIES.get(self.category, {})
        embed = discord.Embed(
            title=f"{category_info.get('emoji', '🎭')} {self.category}ロール",
            description=f"{category_info.get('description', 'ロールを選択してください')}\n\n**選択可能なロール:**\n" + "\n".join([f"• {role.mention}" for role in roles]),
            color=category_info.get('color', discord.Color.purple())
        )
        embed.set_footer(text="ドロップダウンから選択してロールを取得/削除できます")
        
        view = RolePanelView(roles, self.category)
        
        await interaction.channel.send(embed=embed, view=view)
        
        response_msg = f"✅ ロールパネルを作成しました！\n登録したロール: {len(roles)}個"
        if not_found:
            response_msg += f"\n⚠️ 見つからなかったID: {', '.join(not_found)}"
        
        await interaction.response.send_message(response_msg, ephemeral=True)


class RolePanelCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Bot再起動時にViewを再登録"""
        # RolePanelViewは動的なロールを使うため、永続化が難しい
        # 代わりに、on_interactionでcustom_idを解析して処理する方法を使う
        pass
    
    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """SelectMenuのインタラクションをキャッチして処理"""
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get("custom_id", "")
        if not custom_id.startswith("role_select_"):
            return
        
        # すでにViewCallbackで処理されている場合はスキップ
        if interaction.response.is_done():
            return
        
        # インタラクションがロールパネルのものかどうかを確認
        # メッセージにEmbedがあり、タイトルに「ロール」が含まれているかチェック
        if not interaction.message or not interaction.message.embeds:
            return
        
        embed = interaction.message.embeds[0]
        if not embed.title or "ロール" not in embed.title:
            return
        
        # 選択されたロールIDを取得
        selected_ids = set(interaction.data.get("values", []))
        member = interaction.user
        
        # パネルに登録されているロールを取得（Embedから解析）
        available_role_ids = []
        if embed.description:
            import re
            # <@&123456789> の形式からロールIDを抽出
            matches = re.findall(r'<@&(\d+)>', embed.description)
            available_role_ids = [int(m) for m in matches]
        
        if not available_role_ids:
            await interaction.response.send_message("ロール情報を取得できませんでした。", ephemeral=True)
            return
        
        added = []
        removed = []
        
        for role_id in available_role_ids:
            role = interaction.guild.get_role(role_id)
            if not role:
                continue
            
            if str(role_id) in selected_ids:
                if role not in member.roles:
                    try:
                        await member.add_roles(role)
                        added.append(role.name)
                    except discord.Forbidden:
                        pass
            else:
                if role in member.roles:
                    try:
                        await member.remove_roles(role)
                        removed.append(role.name)
                    except discord.Forbidden:
                        pass
        
        messages = []
        if added:
            messages.append(f"✅ 付与: {', '.join(added)}")
        if removed:
            messages.append(f"❌ 削除: {', '.join(removed)}")
        
        if messages:
            await interaction.response.send_message("\n".join(messages), ephemeral=True)
        else:
            await interaction.response.send_message("変更はありません。", ephemeral=True)
    
    @discord.slash_command(
        name="rolepanel",
        description="ロールパネルを作成します（管理者のみ）"
    )
    @commands.has_permissions(administrator=True)
    async def rolepanel(
        self,
        ctx: discord.ApplicationContext,
        カテゴリ: str = discord.Option(
            str,
            "パネルのカテゴリ",
            choices=["ランク帯", "エージェント", "通知", "カスタム"],
            required=True
        )
    ):
        """ロールパネルを作成"""
        if カテゴリ == "カスタム":
            modal = RolePanelSetupModal("カスタム")
            await ctx.send_modal(modal)
        else:
            # プリセットカテゴリの場合もロールIDを指定させる
            modal = RolePanelSetupModal(カテゴリ)
            await ctx.send_modal(modal)
    
    @discord.slash_command(
        name="rolepanel_quick",
        description="サーバーの既存ロールから自動でパネルを作成（管理者のみ）"
    )
    @commands.has_permissions(administrator=True)
    async def rolepanel_quick(
        self,
        ctx: discord.ApplicationContext,
        ロール1: discord.Role = discord.Option(discord.Role, "ロール1", required=True),
        ロール2: discord.Role = discord.Option(discord.Role, "ロール2", required=False, default=None),
        ロール3: discord.Role = discord.Option(discord.Role, "ロール3", required=False, default=None),
        ロール4: discord.Role = discord.Option(discord.Role, "ロール4", required=False, default=None),
        ロール5: discord.Role = discord.Option(discord.Role, "ロール5", required=False, default=None),
        タイトル: str = discord.Option(str, "パネルのタイトル", required=False, default="🎭 ロール選択")
    ):
        """既存ロールを選択してパネルを作成"""
        roles = [r for r in [ロール1, ロール2, ロール3, ロール4, ロール5] if r]
        
        embed = discord.Embed(
            title=タイトル,
            description="ドロップダウンからロールを選択してください\n\n**選択可能なロール:**\n" + "\n".join([f"• {role.mention}" for role in roles]),
            color=discord.Color.purple()
        )
        embed.set_footer(text="複数選択可能 • 再度選択で解除")
        
        view = RolePanelView(roles, "custom")
        
        await ctx.respond("✅ ロールパネルを作成しました！", ephemeral=True)
        await ctx.channel.send(embed=embed, view=view)


def setup(bot: commands.Bot):
    bot.add_cog(RolePanelCog(bot))
