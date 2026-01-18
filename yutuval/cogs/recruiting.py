import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Select, Modal, InputText
from utils.db_manager import db
import json
from typing import Optional, List, Union
import datetime

# ---------------------------------------------------------
# デフォルト設定と定数
# ---------------------------------------------------------
DEFAULT_RANK_CONFIG = [
    {"name": "ランクなし",     "value": 0, "emoji": "🥚"},
    {"name": "アイアン",     "value": 1, "emoji": "🔩"}, 
    {"name": "ブロンズ",     "value": 2, "emoji": "🥉"}, 
    {"name": "シルバー",     "value": 3, "emoji": "🥈"}, 
    {"name": "ゴールド",     "value": 4, "emoji": "🥇"}, 
    {"name": "プラチナ",     "value": 5, "emoji": "💎"}, 
    {"name": "ダイヤ",       "value": 6, "emoji": "💠"}, 
    {"name": "アセンダント", "value": 7, "emoji": "⭐"}, 
    {"name": "イモータル",   "value": 8, "emoji": "👑"}, 
    {"name": "レディアント", "value": 9, "emoji": "🔥"}, 
]

MODE_CHOICES = [
    discord.SelectOption(label="コンペティティブ", value="コンペティティブ", emoji="🏆"),
    discord.SelectOption(label="アンレート", value="アンレート", emoji="🎮"),
    discord.SelectOption(label="スパイクラッシュ", value="スパイクラッシュ", emoji="💣"),
    discord.SelectOption(label="デスマッチ", value="デスマッチ", emoji="⚔️"),
    discord.SelectOption(label="スイフトプレイ", value="スイフトプレイ", emoji="⚡"),
    discord.SelectOption(label="チームデスマッチ", value="チームデスマッチ", emoji="🤝"),
    discord.SelectOption(label="カスタムゲーム", value="カスタムゲーム", emoji="🔧"),
    discord.SelectOption(label="プレミア", value="プレミア", emoji="💠"),
    discord.SelectOption(label="その他", value="その他", emoji="🎲"),
]

MEMBER_CHOICES = [
    discord.SelectOption(label="2人 (デュオ)", value="2", emoji="2️⃣", description="あと1人募集"),
    discord.SelectOption(label="3人 (トリオ)", value="3", emoji="3️⃣", description="あと2人募集"),
    discord.SelectOption(label="4人 (カルテット)", value="4", emoji="4️⃣", description="あと3人募集"),
    discord.SelectOption(label="5人 (フルパ)", value="5", emoji="5️⃣", description="あと4人募集"),
]

def get_discord_emoji(emoji_str: str) -> Union[discord.PartialEmoji, str, None]:
    if not emoji_str: return None
    if emoji_str.startswith('<') and emoji_str.endswith('>'):
        try:
            parts = emoji_str.strip('<>').split(':')
            if len(parts) == 3:
                return discord.PartialEmoji(name=parts[1], id=int(parts[2]), animated=parts[0] == 'a')
        except:
            return None
    # ASCII text cannot be a valid emoji (Discord requires unicode emojis or custom ones)
    # This prevents errors if garbage text is in the DB
    if emoji_str.isascii():
        return None
    return emoji_str

class RecruitmentWizard(View):
    """募集作成のGUIパネル - ボタンベースで直感的に操作"""
    
    # モード定義
    MODES = [
        ("コンペ", "🏆"), ("アンレ", "🎮"), ("スパイク", "💣"),
        ("デスマ", "⚔️"), ("スイフト", "⚡"), ("TDM", "🤝"),
        ("カスタム", "🔧"), ("プレミア", "💠"), ("その他", "🎲"),
    ]
    
    def __init__(self, author_id: int, rank_config: List[dict]):
        super().__init__(timeout=300)
        self.author_id = author_id
        self.rank_config = rank_config
        self.selected_modes = set()  # 複数選択可能
        self.mode = None
        self.total_members = 5
        self.needed_members = 4
        self.min_rank = "指定なし"
        self.max_rank = "指定なし"
        self.page = "main"  # main, rank_min, rank_max
        self.build_main_panel()

    async def update_view(self, interaction: discord.Interaction):
        self.clear_items()
        if self.page == "main":
            self.build_main_panel()
        elif self.page == "rank_min":
            self.build_rank_panel(is_min=True)
        elif self.page == "rank_max":
            self.build_rank_panel(is_min=False)
        embed = self.get_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    def get_embed(self) -> discord.Embed:
        if self.page == "main":
            embed = discord.Embed(
                title="🎮 Valorant 募集作成",
                description="ボタンをタップして設定してください",
                color=discord.Color.blurple()
            )
            
            # 選択中のモード
            modes_str = "・".join(self.selected_modes) if self.selected_modes else "❌ 未選択（タップして選択）"
            embed.add_field(name="📌 モード", value=modes_str, inline=False)
            
            # 人数
            embed.add_field(name="👥 人数", value=f"**{self.total_members}人** (あと{self.needed_members}人募集)", inline=True)
            
            # ランク
            rank_str = self.get_rank_display()
            embed.add_field(name="🏆 ランク帯", value=rank_str, inline=True)
            
            # 募集可能かチェック
            if self.selected_modes:
                embed.set_footer(text="✅ 設定完了！「🚀 募集開始」を押してください")
                embed.color = discord.Color.green()
            else:
                embed.set_footer(text="⚠️ モードを1つ以上タップしてください")
            
            return embed
        
        elif self.page == "rank_min":
            embed = discord.Embed(
                title="🔻 ランク下限を選択",
                description="募集するランク帯の**最低ランク**をタップしてください",
                color=discord.Color.orange()
            )
            embed.add_field(name="現在の設定", value=f"{self.get_rank_emoji(self.min_rank)} {self.min_rank}")
            return embed
        
        elif self.page == "rank_max":
            embed = discord.Embed(
                title="🔺 ランク上限を選択",
                description="募集するランク帯の**最高ランク**をタップしてください",
                color=discord.Color.orange()
            )
            embed.add_field(name="現在の設定", value=f"{self.get_rank_emoji(self.max_rank)} {self.max_rank}")
            return embed

    def get_rank_emoji(self, rank_name: str) -> str:
        if rank_name == "指定なし": return "⭕"
        for r in self.rank_config:
            if r["name"] == rank_name:
                return r["emoji"]
        return "❓"

    def get_rank_display(self):
        if self.min_rank == "指定なし" and self.max_rank == "指定なし":
            return "制限なし"
        start = self.min_rank if self.min_rank != "指定なし" else "ランクなし"
        end = self.max_rank if self.max_rank != "指定なし" else "レディアント"
        return f"{self.get_rank_emoji(start)} {start} 〜 {self.get_rank_emoji(end)} {end}"

    def build_main_panel(self):
        self.clear_items()
        
        # Row 0-1: モードボタン (トグル式)
        for i, (mode, emoji) in enumerate(self.MODES):
            is_selected = mode in self.selected_modes
            style = discord.ButtonStyle.primary if is_selected else discord.ButtonStyle.secondary
            btn = Button(
                label=mode, 
                emoji=emoji, 
                style=style,
                row=i // 5  # 5個ずつ配置
            )
            btn.callback = self.make_mode_callback(mode)
            self.add_item(btn)
        
        # Row 2: 人数ボタン
        for num in [2, 3, 4, 5]:
            is_selected = self.total_members == num
            style = discord.ButtonStyle.success if is_selected else discord.ButtonStyle.secondary
            btn = Button(
                label=f"{num}人",
                style=style,
                row=2
            )
            btn.callback = self.make_member_callback(num)
            self.add_item(btn)
        
        # Row 2: ランク設定ボタン
        rank_label = f"{self.min_rank[:4]}〜{self.max_rank[:4]}"
        rank_btn = Button(
            label=rank_label,
            emoji="🏆",
            style=discord.ButtonStyle.secondary,
            row=2
        )
        rank_btn.callback = self.cb_open_rank_min
        self.add_item(rank_btn)
        
        # Row 3: 募集開始・キャンセル
        can_start = len(self.selected_modes) > 0
        start_btn = Button(
            label="募集開始！",
            emoji="🚀",
            style=discord.ButtonStyle.success if can_start else discord.ButtonStyle.gray,
            disabled=not can_start,
            row=3
        )
        start_btn.callback = self.cb_confirm
        self.add_item(start_btn)
        
        cancel_btn = Button(label="キャンセル", emoji="❌", style=discord.ButtonStyle.danger, row=3)
        cancel_btn.callback = self.cb_cancel
        self.add_item(cancel_btn)

    def build_rank_panel(self, is_min: bool):
        self.clear_items()
        
        # 指定なしボタン
        current = self.min_rank if is_min else self.max_rank
        is_none_selected = current == "指定なし"
        no_limit = Button(
            label="指定なし", 
            emoji="⭕", 
            style=discord.ButtonStyle.primary if is_none_selected else discord.ButtonStyle.secondary, 
            row=0
        )
        no_limit.callback = self.make_rank_callback("指定なし", is_min)
        self.add_item(no_limit)
        
        # ランクボタン (2行に分割)
        for i, r in enumerate(self.rank_config):
            emoji_obj = get_discord_emoji(r["emoji"])
            is_selected = r["name"] == current
            style = discord.ButtonStyle.primary if is_selected else discord.ButtonStyle.secondary
            
            btn = Button(
                label=r["name"][:5],  # 長すぎる場合は切り詰め
                emoji=emoji_obj if emoji_obj else None,
                style=style,
                row=(i // 5) + 1  # Row 1-2
            )
            btn.callback = self.make_rank_callback(r["name"], is_min)
            self.add_item(btn)
        
        # 戻るボタン
        back_btn = Button(label="戻る", emoji="◀️", style=discord.ButtonStyle.gray, row=3)
        back_btn.callback = self.cb_back_to_main
        self.add_item(back_btn)

    def make_mode_callback(self, mode: str):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id: return
            if mode in self.selected_modes:
                self.selected_modes.remove(mode)
            else:
                self.selected_modes.add(mode)
            self.build_main_panel()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        return callback

    def make_member_callback(self, num: int):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id: return
            self.total_members = num
            self.needed_members = num - 1
            self.build_main_panel()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        return callback

    def make_rank_callback(self, rank: str, is_min: bool):
        async def callback(interaction: discord.Interaction):
            if interaction.user.id != self.author_id: return
            if is_min:
                self.min_rank = rank
                self.page = "rank_max"
                self.build_rank_panel(is_min=False)
            else:
                self.max_rank = rank
                self.page = "main"
                self.build_main_panel()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        return callback

    async def cb_open_rank_min(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id: return
        self.page = "rank_min"
        self.build_rank_panel(is_min=True)
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def cb_back_to_main(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id: return
        self.page = "main"
        self.build_main_panel()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def cb_cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id: return
        embed = discord.Embed(title="❌ キャンセルしました", color=discord.Color.default())
        await interaction.response.edit_message(embed=embed, view=None)
        
    async def cb_confirm(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id: return
        if not self.selected_modes:
            await interaction.response.send_message("モードを選択してください", ephemeral=True)
            return
        
        # モード文字列を設定
        self.mode = "・".join(self.selected_modes)
        
        # 処理中表示
        await interaction.response.defer(ephemeral=True)
        
        rank_display = self.get_rank_display()
        
        # VC作成
        vc_cog = interaction.client.get_cog("VCManager")
        invite_url = None
        vc_id = None
        
        if vc_cog:
            try:
                vc_id, text_ch_id = await vc_cog.create_vc(
                    interaction.guild, 
                    interaction.user.id, 
                    f"{self.mode}"[:99], 
                    self.total_members,
                    interaction.channel.id
                )
                vc_channel = interaction.guild.get_channel(vc_id)
                # 招待リンク作成
                invite = await vc_channel.create_invite(max_age=3600)
                invite_url = invite.url
            except Exception as e:
                print(f"Failed to create VC: {e}")
        
        embed = discord.Embed(
            title="🎮 Valorant 募集開始",
            description=f"<@{interaction.user.id}> さんがメンバーを募集しています！",
            color=discord.Color.brand_red()
        )
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        embed.add_field(name="🎮 モード", value=f"**{self.mode}**", inline=True)
        embed.add_field(name="🏆 ランク帯", value=f"**{rank_display}**", inline=True)
        embed.add_field(name="👥 募集内容", value=f"合計 **{self.total_members}人** (あと{self.needed_members}人)", inline=True)
        
        if invite_url:
            embed.add_field(name="🔊 VC", value=f"[参加して待機]({invite_url})", inline=False)
        
        progress = "⚫" * self.needed_members
        embed.add_field(name=f"現在の参加者 (0/{self.needed_members})", value=f"{progress}\n(募集中...)", inline=False)
        
        footer_text = "参加ボタンを押すと自動的にVCに入れます"
        embed.set_footer(text=footer_text)
        
        view = RecruitmentView(interaction.user.id, self.needed_members, rank_display, self.mode, vc_id)
        
        
        # 募集メッセージの送信先を決定
        target_channel = interaction.channel
        
        # 設定された募集チャンネルを確認
        conf_row = await db.fetchrow("SELECT recruit_channel_id FROM server_config WHERE guild_id = ?", (interaction.guild.id,))
        if conf_row and conf_row[0]:
            setting_channel = interaction.guild.get_channel(conf_row[0])
            if setting_channel:
                target_channel = setting_channel

        # 募集メッセージを送信
        msg = await target_channel.send(embed=embed, view=view)

        # メッセージ
        if target_channel.id != interaction.channel.id:
             await interaction.followup.send(f"✅ 募集パネルを {target_channel.mention} に作成しました！\nVCはこちら: {invite_url}", ephemeral=True)
        else:
             await interaction.followup.send(f"✅ 募集パネルとVCを作成しました！\nまずはVCに入って待機しましょう: {invite_url}", ephemeral=True)
        
        # DB登録
        await db.execute(
            """INSERT INTO recruitments (message_id, channel_id, author_id, max_members, rank_range, mode, joined_members, is_closed, vc_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg.id, target_channel.id, interaction.user.id, self.needed_members, rank_display, self.mode, json.dumps([]), 0, vc_id)
        )

        # ログを記録
        logger_cog = interaction.client.get_cog("Logger")
        if logger_cog:
            await logger_cog.log_recruitment_created(
                interaction.guild,
                interaction.user,
                self.mode,
                self.total_members,
                rank_display
            )

        # ダッシュボード再配置 (指定チャンネルの場合)
        recruiting_cog = interaction.client.get_cog("Recruiting")
        if recruiting_cog:
            await recruiting_cog.repost_dashboard(interaction.guild)

    async def cb_cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id: return
        embed = discord.Embed(title="❌ キャンセルしました", color=discord.Color.default())
        await interaction.response.edit_message(embed=embed, view=None)

class RecruitmentView(View):
    def __init__(self, author_id: int, max_members: int, rank_range: str, mode: str, vc_id: Optional[int] = None):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.max_members = max_members
        self.rank_range = rank_range
        self.mode = mode
        self.vc_id = vc_id
        self.joined_members = []
    
    def update_embed(self, embed: discord.Embed) -> discord.Embed:
        current = len(self.joined_members)
        remaining = self.max_members - current
        progress = "🟢" * current + "⚫" * remaining
        
        if self.joined_members:
            member_list = "\n".join([f"• <@{mid}>" for mid in self.joined_members])
        else:
            member_list = "(募集中...)"
        
        # Field index might shift if VC field exists. Logic needs to be robust.
        # Check field names to be safe, or assume fixed structure
        # Structure: Mode, Rank, RecruitCount, VC(Optional), Progress
        
        for i, field in enumerate(embed.fields):
            if "募集内容" in field.name:
                embed.set_field_at(i, name="👥 募集内容", value=f"あと **{remaining} 人**", inline=True)
            if "現在の参加者" in field.name:
                embed.set_field_at(i, name=f"現在の参加者 ({current}/{self.max_members})", value=f"{progress}\n{member_list}", inline=False)
        
        if remaining == 0:
            embed.color = discord.Color.green()
            embed.set_footer(text="満員になりました！")
        else:
            embed.color = discord.Color.brand_red()
            embed.set_footer(text="参加ボタンを押すと自動的にVCに入れます")

        return embed
    
    @discord.ui.button(label="参加", style=discord.ButtonStyle.primary, emoji="✋", custom_id="recruit_join")
    async def join_button(self, button: Button, interaction: discord.Interaction):
        try:
            if interaction.user.id == self.author_id:
                 await interaction.response.send_message("募集主は既に参加扱いですが、VCには入れます。", ephemeral=True)
                 return
            if interaction.user.id in self.joined_members:
                await interaction.response.send_message("既に参加済みです。", ephemeral=True)
                return
            if len(self.joined_members) >= self.max_members:
                await interaction.response.send_message("満員です。", ephemeral=True)
                return
            
            self.joined_members.append(interaction.user.id)
            await db.execute("UPDATE recruitments SET joined_members = ? WHERE message_id = ?", (json.dumps(self.joined_members), interaction.message.id))
            
            # VC権限付与
            if self.vc_id:
                vc_cog = interaction.client.get_cog("VCManager")
                if vc_cog:
                    await vc_cog.allow_user_to_vc(self.vc_id, interaction.user.id)
            
            embed = self.update_embed(interaction.message.embeds[0])
            await interaction.response.edit_message(embed=embed, view=self)
            
            # 通知
            if self.vc_id:
                await interaction.followup.send("✅ 参加しました！VCに入室できます。", ephemeral=True)
            
            # ログを記録
            logger_cog = interaction.client.get_cog("Logger")
            if logger_cog:
                author = interaction.guild.get_member(self.author_id)
                if author:
                    await logger_cog.log_recruitment_joined(
                        interaction.guild,
                        interaction.user,
                        author
                    )
            
            if len(self.joined_members) >= self.max_members:
                await self.close_recruitment(interaction)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)
            print(f"Error in join_button: {e}")
    
    @discord.ui.button(label="辞退", style=discord.ButtonStyle.secondary, emoji="👋", custom_id="recruit_leave")
    async def leave_button(self, button: Button, interaction: discord.Interaction):
        try:
            if interaction.user.id not in self.joined_members:
                await interaction.response.send_message("参加していません。", ephemeral=True)
                return
            
            self.joined_members.remove(interaction.user.id)
            await db.execute("UPDATE recruitments SET joined_members = ? WHERE message_id = ?", (json.dumps(self.joined_members), interaction.message.id))
            
            # VC権限剥奪はあえてしない（複雑になるため）。退出は自主的に。
            
            embed = self.update_embed(interaction.message.embeds[0])
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)
    
    @discord.ui.button(label="〆切", style=discord.ButtonStyle.danger, emoji="🔒", custom_id="recruit_close")
    async def close_button(self, button: Button, interaction: discord.Interaction):
        try:
            if interaction.user.id != self.author_id and not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("募集主または管理者のみ操作可能です。", ephemeral=True)
                return
            
            # VC削除確認
            if self.vc_id:
                vc = interaction.guild.get_channel(self.vc_id)
                if vc:
                    try:
                        # VCManagerのロジックを利用して削除
                        row = await db.fetchrow("SELECT text_channel_id FROM active_vcs WHERE vc_id = ?", (self.vc_id,))
                        if row and row[0]:
                            txt = interaction.guild.get_channel(row[0])
                            if txt: await txt.delete(reason="募集終了に伴う削除")
                        await vc.delete(reason="募集終了に伴う削除")
                        await db.execute("DELETE FROM active_vcs WHERE vc_id = ?", (self.vc_id,))
                    except:
                        pass
            
            await self.close_recruitment(interaction)
        except Exception as e:
            await interaction.response.send_message(f"エラーが発生しました: {e}", ephemeral=True)
    
    async def close_recruitment(self, interaction: discord.Interaction):
        await db.execute("UPDATE recruitments SET is_closed = 1 WHERE message_id = ?", (interaction.message.id,))
        for child in self.children: child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.default()
        embed.title = "🔒 募集終了"
        embed.set_footer(text="終了しました")
        
        if interaction.response.is_done():
            await interaction.message.edit(embed=embed, view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)
        
        if len(self.joined_members) > 0:
            mentions = [f"<@{uid}>" for uid in self.joined_members] + [f"<@{self.author_id}>"]
            # 既にVCはあるので通知のみ
            if self.vc_id:
                txt_ch_row = await db.fetchrow("SELECT text_channel_id FROM active_vcs WHERE vc_id = ?", (self.vc_id,))
                if txt_ch_row:
                    txt_ch = interaction.guild.get_channel(txt_ch_row[0])
                    if txt_ch:
                        await txt_ch.send(f"募集が締め切られました！メンバー: {' '.join(mentions)}")
            else:
                 await interaction.channel.send(f"募集終了！メンション: {' '.join(mentions)}")
        
        # ログを記録
        logger_cog = interaction.client.get_cog("Logger")
        if logger_cog:
            author = interaction.guild.get_member(self.author_id)
            if author:
                await logger_cog.log_recruitment_closed(
                    interaction.guild,
                    author,
                    len(self.joined_members) + 1  # +1 for author
                )

# --- Config UI (Existing Code) ---
# --- New Config UI ---

class RecruitDashboardView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="募集を作成する", style=discord.ButtonStyle.success, emoji="🎮", custom_id="persistent_recruit_create")
    async def create_recruit(self, button: Button, interaction: discord.Interaction):
        config = await interaction.client.get_cog("Recruiting").get_guild_rank_config(interaction.guild.id)
        view = RecruitmentWizard(interaction.user.id, config)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

class RecruitConfigView(View):
    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id

    @discord.ui.button(label="このチャンネルを募集用に設定", style=discord.ButtonStyle.primary, emoji="📍", row=0)
    async def set_channel(self, button: Button, interaction: discord.Interaction):
        await db.execute("UPDATE server_config SET recruit_channel_id = ? WHERE guild_id = ?", (interaction.channel.id, self.guild_id))
        await interaction.response.send_message(f"✅ このチャンネル (<#{interaction.channel.id}>) を募集ボタンの表示先に設定しました。\n募集が作成されると、自動的にボタンが一番下に再配置されます。", ephemeral=True)
        # Immediately post dashboard
        recruiting_cog = interaction.client.get_cog("Recruiting")
        if recruiting_cog: await recruiting_cog.repost_dashboard(interaction.guild)

    @discord.ui.button(label="ランク絵文字設定", style=discord.ButtonStyle.secondary, emoji="⚙️", row=0)
    async def config_emoji(self, button: Button, interaction: discord.Interaction):
        await interaction.response.send_message("変更したいランクを選んでください:", view=ConfigRankSelect(self.guild_id), ephemeral=True)

class EmojiInputModal(Modal):
    def __init__(self, rank_name: str, guild_id: int):
        super().__init__(title=f"{rank_name}の絵文字設定")
        self.rank_name = rank_name
        self.guild_id = guild_id
        self.add_item(InputText(label="絵文字ID または 絵文字そのもの", placeholder="例: <:iron:12345> または 12345"))

    async def callback(self, interaction: discord.Interaction):
        value = self.children[0].value.strip()
        if value.isdigit():
             config_str = f"<:rank:{value}>"
        else:
             config_str = value
        
        await db.update_rank_emoji(self.guild_id, self.rank_name, config_str)
        await interaction.response.send_message(f"✅ {self.rank_name} の絵文字を更新しました！\n確認: {config_str}", ephemeral=True)

class ConfigRankSelect(View):
    def __init__(self, guild_id: int):
        super().__init__()
        self.guild_id = guild_id
        options = []
        # Use module level DEFAULT_RANK_CONFIG
        for r in DEFAULT_RANK_CONFIG:
            options.append(discord.SelectOption(label=r["name"], value=r["name"], emoji=r["emoji"]))
        select = Select(placeholder="設定を変更したいランクを選択...", options=options)
        select.callback = self.select_rank
        # Add back button?
        self.add_item(select)
    
    async def select_rank(self, interaction: discord.Interaction):
        rank_name = interaction.data["values"][0]
        await interaction.response.send_modal(EmojiInputModal(rank_name, self.guild_id))

class Recruiting(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_recruitments.start()

    def cog_unload(self):
        self.cleanup_recruitments.cancel()

    async def get_guild_rank_config(self, guild_id: int):
        server_conf = await db.get_config(guild_id)
        custom_emojis = server_conf.get("rank_emojis", {})
        config = []
        for r in DEFAULT_RANK_CONFIG:
            new_r = r.copy()
            if r["name"] in custom_emojis:
                new_r["emoji"] = custom_emojis[r["name"]]
            config.append(new_r)
        return config
    
    @commands.Cog.listener()
    async def on_ready(self):
        try:
            # VC IDを特定するために active_vcs と recruitments を紐付けるのは難しい（テーブルにFKがないため）
            # 新しい募集では vc_id を紐付けられるが、既存は無理。
            # Persistence復元時は vc_id=None になる可能性があるが、それでも動くようにする。
            active_recruits = await db.fetchall("SELECT * FROM recruitments WHERE is_closed = 0")
            count = 0
            if active_recruits:
                for row in active_recruits:
                    # row: msg_id, ch_id, author, max, rank, mode, joined, closed, vc_id
                    vc_id = row[8] if len(row) > 8 else None
                    view = RecruitmentView(row[2], row[3], row[4], row[5], vc_id=vc_id)
                    try:
                        joined = json.loads(row[6]) if row[6] else []
                        view.joined_members = joined
                        self.bot.add_view(view, message_id=row[0])
                        count += 1
                    except Exception as e:
                        print(f"Failed to restore view for {row[0]}: {e}")
                print(f"🔄 復元された募集パネル: {count}件")

            # Dashboard Button Restore
            self.bot.add_view(RecruitDashboardView())
            
        except Exception as e:
            print(f"Error restoring views: {e}")

    @discord.slash_command(name="recruit", description="Valorantの募集を作成します")
    async def recruit(self, ctx: discord.ApplicationContext):
        await ctx.defer(ephemeral=True)
        config = await self.get_guild_rank_config(ctx.guild.id)
        view = RecruitmentWizard(ctx.author.id, config)
        embed = view.get_embed()
        await ctx.followup.send(embed=embed, view=view)

    @discord.slash_command(name="recruit_config", description="募集機能の設定メニューを開きます（管理者のみ）")
    @commands.has_permissions(administrator=True)
    async def recruit_config(self, ctx: discord.ApplicationContext):
        embed = discord.Embed(title="⚙️ 募集機能設定", description="設定を変更したい項目を選択してください。", color=discord.Color.dark_gray())
        config = await self.get_guild_rank_config(ctx.guild.id)
        
        # Current Config Summary
        summary = "現在の設定:\n"
        for r in config:
            summary += f"{r['emoji']} {r['name']} "
        embed.add_field(name="ランク絵文字", value=summary[:1000], inline=False)
        
        # Channel Config
        conf_row = await db.fetchrow("SELECT recruit_channel_id FROM server_config WHERE guild_id = ?", (ctx.guild.id,))
        ch_id = conf_row[0] if conf_row else None
        ch_mention = f"<#{ch_id}>" if ch_id else "未設定"
        embed.add_field(name="募集チャンネル (固定ボタン表示先)", value=ch_mention, inline=False)
        
        await ctx.respond(embed=embed, view=RecruitConfigView(ctx.guild.id), ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        # VC deleted manually -> Close recruitment
        if isinstance(channel, discord.VoiceChannel):
            row = await db.fetchrow("SELECT message_id, channel_id, author_id, joined_members, rank_range FROM recruitments WHERE vc_id = ?", (channel.id,))
            if row:
                msg_id, ch_id, author_id, joined_json, rank_range = row
                try:
                    ch = self.bot.get_channel(ch_id)
                    if ch:
                        msg = await ch.fetch_message(msg_id)
                        # Create closed view/embed
                        embed = msg.embeds[0]
                        embed.title = "🔒 募集終了 (VC削除済み)"
                        embed.color = discord.Color.default()
                        embed.set_footer(text="VCが削除されたため終了しました")
                        
                        # Disabled view
                        joined = json.loads(joined_json) if joined_json else []
                        view = RecruitmentView(author_id, 5, rank_range, "Unknown", vc_id=None) # params dont matter for disabled
                        view.joined_members = joined
                        for child in view.children: child.disabled = True
                        
                        await msg.edit(embed=embed, view=view)
                        await db.execute("UPDATE recruitments SET is_closed = 1 WHERE message_id = ?", (msg_id,))
                except:
                    pass

    async def repost_dashboard(self, guild: discord.Guild):
        """募集チャンネルの最後にダッシュボードを再配置"""
        row = await db.fetchrow("SELECT recruit_channel_id, last_recruit_msg_id FROM server_config WHERE guild_id = ?", (guild.id,))
        if not row or not row[0]: return

        channel_id, last_msg_id = row
        channel = guild.get_channel(channel_id)
        if not channel: return

        # Delete old
        if last_msg_id:
            try:
                old_msg = await channel.fetch_message(last_msg_id)
                await old_msg.delete()
            except:
                pass
        
        # Send new
        embed = discord.Embed(
            title="🎮 募集を作成する",
            description="下のボタンを押して募集を開始してください。",
            color=discord.Color.green()
        )
        view = RecruitDashboardView()
        msg = await channel.send(embed=embed, view=view)
        await db.execute("UPDATE server_config SET last_recruit_msg_id = ? WHERE guild_id = ?", (msg.id, guild.id))

    async def start_additional_recruitment(self, interaction: discord.Interaction, vc_id: int, needed: int):
        """追加募集を開始する"""
        # 元のチャンネルを探す
        row = await db.fetchrow("SELECT source_channel_id, party_code FROM active_vcs WHERE vc_id = ?", (vc_id,))
        if not row:
            await interaction.response.send_message("募集元のチャンネルが見つかりません。", ephemeral=True)
            return
        
        source_ch_id = row[0]
        party_code = row[1]
        
        channel = self.bot.get_channel(source_ch_id)
        if not channel:
            await interaction.response.send_message("募集元のチャンネルが存在しません。", ephemeral=True)
            return

        embed = discord.Embed(
            title="📢 追加募集",
            description=f"<@{interaction.user.id}> さんが追加メンバーを募集しています！",
            color=discord.Color.orange()
        )
        embed.add_field(name="👥 募集", value=f"あと **{needed}人**", inline=True)
        if party_code != "未設定":
             embed.add_field(name="🔑 コード", value=f"`{party_code}`", inline=True)

        # VCリンク
        vc_channel = interaction.guild.get_channel(vc_id)
        if vc_channel:
             invite = await vc_channel.create_invite(max_age=3600)
             embed.add_field(name="🔊 VC", value=f"[参加する]({invite.url})", inline=False)

        embed.set_footer(text="参加ボタンを押すと自動的にVCに入れます")
        
        # Additional recruitment view is simple: Join -> Grant Access -> Close if full
        view = RecruitmentView(interaction.user.id, needed, "追加募集", "追加募集", vc_id=vc_id)
        
        msg = await channel.send(embed=embed, view=view)
        
        # DB登録 (mode="追加募集")
        await db.execute(
            """INSERT INTO recruitments (message_id, channel_id, author_id, max_members, rank_range, mode, joined_members, is_closed)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (msg.id, channel.id, interaction.user.id, needed, "追加募集", "追加募集", json.dumps([]), 0)
        )
        
        await interaction.response.send_message(f"✅ 追加募集を <#{channel.id}> に送信しました。", ephemeral=True)

    @tasks.loop(minutes=10)
    async def cleanup_recruitments(self):
        """古くなった募集をクローズする"""
        pass # TODO: Implement comprehensive cleanup based on timestamp if needed

def setup(bot: commands.Bot):
    bot.add_cog(Recruiting(bot))
