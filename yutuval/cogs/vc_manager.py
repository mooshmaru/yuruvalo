import discord
from discord.ext import commands, tasks
from discord.ui import Button, View, Modal, InputText, Select
from utils.db_manager import db
import os
import asyncio
from typing import Optional, List

# --- Modals & Sub-Views ---

class PartyCodeModal(Modal):
    def __init__(self, vc_id: int):
        super().__init__(title="パーティーコード設定")
        self.vc_id = vc_id
        self.add_item(InputText(label="パーティーコード", placeholder="例: VALORANT#JP1", required=True))
    
    async def callback(self, interaction: discord.Interaction):
        party_code = self.children[0].value
        await db.execute("UPDATE active_vcs SET party_code = ? WHERE vc_id = ?", (party_code, self.vc_id))
        await update_vc_panel(interaction.client, self.vc_id)
        await interaction.response.send_message(f"✅ パーティーコードを `{party_code}` に設定しました！", ephemeral=True)

class LimitSelect(View):
    def __init__(self, vc_id: int):
        super().__init__()
        self.vc_id = vc_id
        
        options = [
            discord.SelectOption(label="2人 (デュオ)", value="2"),
            discord.SelectOption(label="3人 (トリオ)", value="3"),
            discord.SelectOption(label="5人 (フルパ)", value="5"),
            discord.SelectOption(label="10人 (カスタム)", value="10"),
            discord.SelectOption(label="無制限", value="0"),
        ]
        select = Select(placeholder="人数制限を選択...", options=options)
        select.callback = self.callback
        self.add_item(select)

    async def callback(self, interaction: discord.Interaction):
        limit = int(interaction.data["values"][0])
        vc = interaction.guild.get_channel(self.vc_id)
        if vc:
            await vc.edit(user_limit=limit)
            await update_vc_panel(interaction.client, self.vc_id)
            await interaction.response.send_message(f"✅ 人数制限を {limit if limit > 0 else '無制限'} に変更しました。", ephemeral=True)
        else:
            await interaction.response.send_message("❌ VCが見つかりません。", ephemeral=True)

class OwnerSelect(View):
    def __init__(self, vc: discord.VoiceChannel):
        super().__init__()
        self.vc = vc
        
        options = []
        for member in vc.members:
            options.append(discord.SelectOption(label=member.display_name, value=str(member.id), emoji="👤"))
        
        if not options:
            options.append(discord.SelectOption(label="メンバーがいません", value="0", default=True))
        
        select = Select(placeholder="新しいオーナーを選択...", options=options, disabled=len(options)==0)
        select.callback = self.callback
        self.add_item(select)
        
    async def callback(self, interaction: discord.Interaction):
        new_owner_id = int(interaction.data["values"][0])
        if new_owner_id == 0: return
        
        await db.execute("UPDATE active_vcs SET owner_id = ? WHERE vc_id = ?", (new_owner_id, self.vc.id))
        await update_vc_panel(interaction.client, self.vc.id)
        
        await interaction.response.send_message(f"✅ オーナーを <@{new_owner_id}> に変更しました。", ephemeral=True)

class AdditionalRecruitSelect(View):
    def __init__(self, vc_id: int):
        super().__init__()
        self.vc_id = vc_id
        options = [
            discord.SelectOption(label="あと1人募集", value="1", emoji="1️⃣"),
            discord.SelectOption(label="あと2人募集", value="2", emoji="2️⃣"),
            discord.SelectOption(label="あと3人募集", value="3", emoji="3️⃣"),
            discord.SelectOption(label="あと4人募集", value="4", emoji="4️⃣"),
        ]
        select = Select(placeholder="追加で何人募集しますか？", options=options)
        select.callback = self.callback
        self.add_item(select)
    
    async def callback(self, interaction: discord.Interaction):
        needed = int(interaction.data["values"][0])
        vc = interaction.guild.get_channel(self.vc_id)
        if not vc: return
        
        # Recruiting Cogのメソッドを呼び出す
        recruit_cog = interaction.client.get_cog("Recruiting")
        if recruit_cog:
            await recruit_cog.start_additional_recruitment(interaction, self.vc_id, needed)
        else:
            await interaction.response.send_message("募集機能が見つかりません。", ephemeral=True)

# --- Main Control Panel ---

class VCControlPanel(View):
    def __init__(self, vc_id: int):
        super().__init__(timeout=None)
        self.vc_id = vc_id

    async def check_owner(self, interaction: discord.Interaction) -> bool:
        if interaction.user.guild_permissions.administrator:
            return True
        row = await db.fetchrow("SELECT owner_id FROM active_vcs WHERE vc_id = ?", (self.vc_id,))
        if not row or row[0] != interaction.user.id:
            await interaction.response.send_message("❌ この操作はVCオーナーまたは管理者のみ可能です。", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="📢 追加募集", style=discord.ButtonStyle.primary, emoji="📢", custom_id="vc_announce_btn", row=0)
    async def announce_button(self, button: Button, interaction: discord.Interaction):
        if not await self.check_owner(interaction): return
        await interaction.response.send_message("追加で何人募集しますか？", view=AdditionalRecruitSelect(self.vc_id), ephemeral=True)

    @discord.ui.button(label="✏️ コード設定", style=discord.ButtonStyle.success, emoji="📝", custom_id="vc_code_btn", row=0)
    async def code_button(self, button: Button, interaction: discord.Interaction):
        if not await self.check_owner(interaction): return
        await interaction.response.send_modal(PartyCodeModal(self.vc_id))

    @discord.ui.button(label="🔒 ロック切替", style=discord.ButtonStyle.secondary, emoji="🔒", custom_id="vc_lock_btn", row=0)
    async def lock_button(self, button: Button, interaction: discord.Interaction):
        if not await self.check_owner(interaction): return
        
        vc = interaction.guild.get_channel(self.vc_id)
        if not vc: return
        
        row = await db.fetchrow("SELECT is_locked FROM active_vcs WHERE vc_id = ?", (self.vc_id,))
        is_locked = bool(row[0])
        new_locked = not is_locked
        
        await vc.set_permissions(interaction.guild.default_role, connect=not new_locked)
        await db.execute("UPDATE active_vcs SET is_locked = ? WHERE vc_id = ?", (1 if new_locked else 0, self.vc_id))
        
        await update_vc_panel(interaction.client, self.vc_id)
        await interaction.response.send_message(f"✅ VCを{'ロック' if new_locked else 'アンロック'}しました。", ephemeral=True)

    @discord.ui.button(label="👥 人数変更", style=discord.ButtonStyle.primary, emoji="🔢", custom_id="vc_limit_btn", row=1)
    async def limit_button(self, button: Button, interaction: discord.Interaction):
        if not await self.check_owner(interaction): return
        await interaction.response.send_message("変更する人数を選択してください:", view=LimitSelect(self.vc_id), ephemeral=True)

    @discord.ui.button(label="👑 オーナー譲渡", style=discord.ButtonStyle.primary, emoji="👑", custom_id="vc_transfer_btn", row=1)
    async def transfer_button(self, button: Button, interaction: discord.Interaction):
        if not await self.check_owner(interaction): return
        vc = interaction.guild.get_channel(self.vc_id)
        if not vc: return
        await interaction.response.send_message("新しいオーナーを選択してください:", view=OwnerSelect(vc), ephemeral=True)

    @discord.ui.button(label="👋 解散", style=discord.ButtonStyle.danger, emoji="💣", custom_id="vc_disband_btn", row=1)
    async def disband_button(self, button: Button, interaction: discord.Interaction):
        if not await self.check_owner(interaction): return
        vc = interaction.guild.get_channel(self.vc_id)
        
        # Get text channel ID before deleting anything
        row = await db.fetchrow("SELECT text_channel_id FROM active_vcs WHERE vc_id = ?", (self.vc_id,))
        text_ch_id = row[0] if row else None
        
        if vc:
            try:
                await vc.delete(reason="オーナーによる解散")
            except:
                pass
        
        if text_ch_id:
            text_ch = interaction.guild.get_channel(text_ch_id)
            if text_ch:
                try:
                    await text_ch.delete(reason="VC解散に伴う削除")
                except:
                    pass

        await interaction.response.send_message("VCを解散しました。", ephemeral=True)
        await db.execute("DELETE FROM active_vcs WHERE vc_id = ?", (self.vc_id,))


# --- Helper Functions ---

async def update_vc_panel(bot, vc_id: int):
    """VC操作パネルの内容を更新する"""
    row = await db.fetchrow("SELECT * FROM active_vcs WHERE vc_id = ?", (vc_id,))
    if not row: return
    
    # Schema: vc_id, text_channel_id, owner_id, party_code, is_locked, panel_message_id, source_channel_id
    text_ch_id = row[1]
    owner_id = row[2]
    party_code = row[3]
    is_locked = bool(row[4])
    msg_id = row[5] if len(row) > 5 else None
    
    channel = bot.get_channel(text_ch_id)
    vc = bot.get_channel(vc_id)
    if not channel or not vc: return
    
    members_text = ""
    if vc.members:
        members_text = "\n".join([f"{'👑 ' if m.id == owner_id else '• '}{m.display_name}" for m in vc.members])
    else:
        members_text = "(なし)"

    embed = discord.Embed(
        title="🎮 VC 操作パネル",
        description=f"現在のVCステータスと操作を行えます。",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="🔑 パーティーコード", value=f"```\n{party_code}\n```", inline=False)
    embed.add_field(name="👑 オーナー", value=f"<@{owner_id}>", inline=True)
    embed.add_field(name="🔒 状態", value="ロック中" if is_locked else "オープン", inline=True)
    embed.add_field(name="👥 人数", value=f"{len(vc.members)} / {vc.user_limit if vc.user_limit else '∞'}", inline=True)
    embed.add_field(name="🗣️ 参加者一覧", value=f"```\n{members_text}\n```", inline=False)
    
    embed.set_footer(text="誰もいなくなると60秒後に自動削除されます")
    
    try:
        if msg_id:
            try:
                msg = await channel.fetch_message(msg_id)
                await msg.edit(embed=embed, view=VCControlPanel(vc_id))
                return
            except discord.NotFound:
                pass
        
        msg = await channel.send(embed=embed, view=VCControlPanel(vc_id))
        await db.execute("UPDATE active_vcs SET panel_message_id = ? WHERE vc_id = ?", (msg.id, vc_id))
    except Exception as e:
        print(f"Failed to update panel: {e}")

class VCManager(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cleanup_task.start()
    
    def cog_unload(self):
        self.cleanup_task.cancel()

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            vcs = await db.fetchall("SELECT vc_id FROM active_vcs")
            for row in vcs:
                self.bot.add_view(VCControlPanel(row[0]))
        except:
            pass
            
    async def create_vc(self, guild: discord.Guild, owner_id: int, vc_name: str, limit: int, source_channel_id: int):
        """VCを即時作成 (VC First)"""
        category_id = os.getenv("VC_CATEGORY_ID")
        category = guild.get_channel(int(category_id)) if category_id else None
        
        # 初期状態は全員接続不可、オーナーのみ接続可
        overwrites = {guild.default_role: discord.PermissionOverwrite(connect=False, view_channel=False)}
        owner = guild.get_member(owner_id)
        if owner:
            overwrites[owner] = discord.PermissionOverwrite(connect=True, view_channel=True)
        
        vc = await guild.create_voice_channel(name=f"🎮 {vc_name}", category=category, overwrites=overwrites, user_limit=limit)
        
        text_overwrites = overwrites.copy()
        text_channel = await guild.create_text_channel(name=f"💬-{vc_name}", category=category, overwrites=text_overwrites)
        
        await db.execute(
            "INSERT INTO active_vcs (vc_id, text_channel_id, owner_id, party_code, is_locked, panel_message_id, source_channel_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (vc.id, text_channel.id, owner_id, "未設定", 0, None, source_channel_id)
        )
        
        await text_channel.send(
            content=f"<@{owner_id}>\n"
                    f"**🎉 VCを作成しました！**\n\n"
                    f"1. **VCに参加** して待機してください。\n"
                    f"2. 元のチャンネルで募集パネルの「参加」ボタンが押されると、自動的にメンバーがVCに入ってきます。\n"
                    f"3. パーティーコードが決まったら下のパネルに入力してください。"
        )
        await update_vc_panel(self.bot, vc.id)
        
        return vc.id, text_channel.id
    
    async def allow_user_to_vc(self, vc_id: int, user_id: int):
        """ユーザーにVCアクセス権を付与"""
        row = await db.fetchrow("SELECT * FROM active_vcs WHERE vc_id = ?", (vc_id,))
        if not row: return
        
        # row: vc_id, text_channel_id, owner_id, party_code, is_locked, panel_message_id, source_channel_id
        vc = self.bot.get_channel(vc_id)
        text_ch = self.bot.get_channel(row[1])
        
        guild = vc.guild if vc else (text_ch.guild if text_ch else None)
        if not guild: return
        
        member = guild.get_member(user_id)
        if not member: return
        
        if vc:
            await vc.set_permissions(member, connect=True, view_channel=True)
        if text_ch:
            await text_ch.set_permissions(member, read_messages=True, send_messages=True)
        
        # update panel to show new member if they joined
        await update_vc_panel(self.bot, vc_id)

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        # 退出時の処理
        if before.channel:
            row = await db.fetchrow("SELECT vc_id FROM active_vcs WHERE vc_id = ?", (before.channel.id,))
            if row:
                if len(before.channel.members) == 0:
                    self.bot.loop.create_task(self.schedule_vc_deletion(before.channel.id))
                else:
                    await update_vc_panel(self.bot, before.channel.id)

        # 参加時の処理
        if after.channel:
            row = await db.fetchrow("SELECT vc_id FROM active_vcs WHERE vc_id = ?", (after.channel.id,))
            if row:
                await update_vc_panel(self.bot, after.channel.id)

    @discord.slash_command(name="moveall", description="現在のVCのメンバー全員を指定したVCに移動します（管理者のみ）")
    @commands.has_permissions(administrator=True)
    async def move_all(
        self,
        ctx: discord.ApplicationContext,
        destination: discord.VoiceChannel = discord.Option(discord.VoiceChannel, "移動先のチャンネル", required=True)
    ):
        """メンバー一括移動コマンド"""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.respond("まずあなたがボイスチャンネルに参加している必要があります。", ephemeral=True)
            return

        source_channel = ctx.author.voice.channel
        members = source_channel.members
        
        if not members:
            await ctx.respond("移動させるメンバーがいません。", ephemeral=True)
            return
            
        if source_channel.id == destination.id:
            await ctx.respond("移動元と移動先が同じです。", ephemeral=True)
            return

        await ctx.respond(f"🚚 **{len(members)}名** のメンバーを {source_channel.mention} から {destination.mention} に移動中...", ephemeral=True)
        
        count = 0
        for member in members:
            try:
                await member.move_to(destination, reason=f"Moveall by {ctx.author}")
                count += 1
                await asyncio.sleep(0.5) # Rate limit回避
            except Exception as e:
                print(f"Failed to move {member}: {e}")
        
        await ctx.followup.send(f"✅ 移動完了: {count}/{len(members)}名", ephemeral=True)

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        """VCが手動で削除された場合のクリーンアップ"""
        if isinstance(channel, discord.VoiceChannel):
            row = await db.fetchrow("SELECT text_channel_id FROM active_vcs WHERE vc_id = ?", (channel.id,))
            if row:
                text_ch_id = row[0]
                text_ch = channel.guild.get_channel(text_ch_id)
                if text_ch:
                    try:
                        await text_ch.delete(reason="VC削除に伴う自動削除")
                    except:
                        pass
                await db.execute("DELETE FROM active_vcs WHERE vc_id = ?", (channel.id,))

    async def schedule_vc_deletion(self, vc_id: int):
        await asyncio.sleep(60)
        vc = self.bot.get_channel(vc_id)
        if vc and len(vc.members) == 0:
            row = await db.fetchrow("SELECT text_channel_id FROM active_vcs WHERE vc_id = ?", (vc_id,))
            if row:
                txt = self.bot.get_channel(row[0])
                if txt: await txt.delete(reason="VC自動削除")
            await vc.delete(reason="自動削除")
            await db.execute("DELETE FROM active_vcs WHERE vc_id = ?", (vc_id,))

    @tasks.loop(hours=1)
    async def cleanup_task(self):
        rows = await db.fetchall("SELECT vc_id FROM active_vcs")
        for r in rows:
            if not self.bot.get_channel(r[0]):
                await db.execute("DELETE FROM active_vcs WHERE vc_id = ?", (r[0],))

def setup(bot: commands.Bot):
    bot.add_cog(VCManager(bot))
