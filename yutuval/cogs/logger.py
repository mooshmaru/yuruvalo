import discord
from discord.ext import commands
from discord import option
import os
from datetime import datetime, timezone
from typing import Optional

class LogColor:
    """ログ用のカラーパレット"""
    SUCCESS = 0x00D26A      # 緑 - 成功/参加
    WARNING = 0xFFA500      # オレンジ - 警告
    ERROR = 0xFF4757        # 赤 - エラー/退出/削除
    INFO = 0x5865F2         # 青 - 情報
    VOICE = 0x9B59B6        # 紫 - VC関連
    MODERATION = 0xE91E63   # ピンク - モデレーション
    MESSAGE = 0x3498DB      # 水色 - メッセージ
    ROLE = 0xF39C12         # 黄色 - ロール
    RECRUIT = 0x1ABC9C      # ターコイズ - 募集

class LogCategory:
    """ログカテゴリ"""
    MEMBER = "member"           # メンバー参加/退出
    VOICE = "voice"             # VC関連
    MESSAGE = "message"         # メッセージ編集/削除
    ROLE = "role"               # ロール変更
    RECRUIT = "recruit"         # 募集関連
    MODERATION = "moderation"   # モデレーション

class Logger(commands.Cog):
    """📋 高度なログ機能"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.log_channel_id = int(os.getenv("LOG_CHANNEL_ID", 0))
        # メッセージキャッシュ（削除ログ用）
        self.message_cache = {}
        self.max_cache_size = 1000
        
    def get_log_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """ログチャンネルを取得（テキストチャンネルのみ）"""
        if self.log_channel_id:
            channel = guild.get_channel(self.log_channel_id)
            # テキストチャンネルかどうかをチェック
            if isinstance(channel, discord.TextChannel):
                return channel
            elif channel is not None:
                print(f"⚠️ LOG_CHANNEL_ID ({self.log_channel_id}) はテキストチャンネルではありません。タイプ: {type(channel).__name__}")
        return None
    
    def create_base_embed(
        self, 
        title: str, 
        description: str, 
        color: int,
        category: str = None
    ) -> discord.Embed:
        """ベースとなるEmbedを作成"""
        embed = discord.Embed(
            title=title,
            description=description,
            color=color,
            timestamp=datetime.now(timezone.utc)
        )
        
        # カテゴリ別のフッター
        category_labels = {
            LogCategory.MEMBER: "👥 メンバーログ",
            LogCategory.VOICE: "🔊 VCログ",
            LogCategory.MESSAGE: "💬 メッセージログ",
            LogCategory.ROLE: "🏷️ ロールログ",
            LogCategory.RECRUIT: "📣 募集ログ",
            LogCategory.MODERATION: "🛡️ モデレーションログ",
        }
        
        footer_text = category_labels.get(category, "📋 システムログ")
        embed.set_footer(text=footer_text)
        
        return embed
    
    def cache_message(self, message: discord.Message):
        """メッセージをキャッシュに追加"""
        if message.author.bot:
            return
            
        # キャッシュサイズ制限
        if len(self.message_cache) >= self.max_cache_size:
            # 最も古いメッセージを削除
            oldest_id = min(self.message_cache.keys())
            del self.message_cache[oldest_id]
        
        self.message_cache[message.id] = {
            "content": message.content,
            "author": message.author,
            "channel": message.channel,
            "created_at": message.created_at,
            "attachments": [a.filename for a in message.attachments]
        }
    
    # ==================== メンバーイベント ====================
    
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """メンバー参加時のログ"""
        log_channel = self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        # アカウント年齢の計算
        account_age = (datetime.now(timezone.utc) - member.created_at.replace(tzinfo=timezone.utc)).days
        age_warning = "⚠️ **新規アカウント!**" if account_age < 7 else ""
        
        embed = self.create_base_embed(
            title="📥 メンバーが参加しました",
            description=f"{member.mention} がサーバーに参加しました\n{age_warning}",
            color=LogColor.SUCCESS,
            category=LogCategory.MEMBER
        )
        
        embed.add_field(
            name="👤 ユーザー情報",
            value=f"```\n"
                  f"名前: {member}\n"
                  f"ID: {member.id}\n"
                  f"```",
            inline=True
        )
        
        embed.add_field(
            name="📅 アカウント情報",
            value=f"```\n"
                  f"作成日: {member.created_at.strftime('%Y-%m-%d')}\n"
                  f"経過日数: {account_age}日\n"
                  f"```",
            inline=True
        )
        
        # 現在のメンバー数
        embed.add_field(
            name="📊 サーバー統計",
            value=f"現在のメンバー数: **{member.guild.member_count}人**",
            inline=False
        )
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await log_channel.send(embed=embed)
        
        # 統計データを記録
        await self._record_stat(member.guild.id, "member_join", user_id=member.id)
    
    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        """メンバー退出時のログ"""
        log_channel = self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        # 在籍期間の計算
        if member.joined_at:
            stay_duration = (datetime.now(timezone.utc) - member.joined_at.replace(tzinfo=timezone.utc)).days
            stay_text = f"約{stay_duration}日間"
        else:
            stay_text = "不明"
        
        embed = self.create_base_embed(
            title="📤 メンバーが退出しました",
            description=f"{member.mention} がサーバーから退出しました",
            color=LogColor.ERROR,
            category=LogCategory.MEMBER
        )
        
        embed.add_field(
            name="👤 ユーザー情報",
            value=f"```\n"
                  f"名前: {member}\n"
                  f"ID: {member.id}\n"
                  f"```",
            inline=True
        )
        
        embed.add_field(
            name="📅 在籍情報",
            value=f"```\n"
                  f"参加日: {member.joined_at.strftime('%Y-%m-%d') if member.joined_at else '不明'}\n"
                  f"在籍期間: {stay_text}\n"
                  f"```",
            inline=True
        )
        
        # ロール一覧
        roles = [r.mention for r in member.roles if r != member.guild.default_role]
        if roles:
            embed.add_field(
                name="🏷️ 所持していたロール",
                value=" ".join(roles[:10]) + ("..." if len(roles) > 10 else ""),
                inline=False
            )
        
        # 現在のメンバー数
        embed.add_field(
            name="📊 サーバー統計",
            value=f"現在のメンバー数: **{member.guild.member_count}人**",
            inline=False
        )
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await log_channel.send(embed=embed)
        
        # 統計データを記録
        await self._record_stat(member.guild.id, "member_leave", user_id=member.id)
    
    # ==================== VCイベント ====================
    
    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState
    ):
        """VC状態変更時のログ"""
        log_channel = self.get_log_channel(member.guild)
        if not log_channel:
            return
        
        # VC参加
        if before.channel is None and after.channel is not None:
            embed = self.create_base_embed(
                title="🔊 VCに参加",
                description=f"{member.mention} が **{after.channel.name}** に参加しました",
                color=LogColor.SUCCESS,
                category=LogCategory.VOICE
            )
            
            # チャンネル情報
            member_count = len(after.channel.members)
            limit_text = f"/{after.channel.user_limit}" if after.channel.user_limit > 0 else ""
            embed.add_field(
                name="📊 チャンネル情報",
                value=f"```\n"
                      f"チャンネル: {after.channel.name}\n"
                      f"現在の人数: {member_count}{limit_text}人\n"
                      f"```",
                inline=False
            )
            
            # メンバーリスト
            members_list = ", ".join([m.display_name for m in after.channel.members[:5]])
            if len(after.channel.members) > 5:
                members_list += f" 他{len(after.channel.members) - 5}人"
            embed.add_field(
                name="👥 参加中メンバー",
                value=members_list,
                inline=False
            )
            
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            
            await log_channel.send(embed=embed)
            await self._record_stat(member.guild.id, "vc_join", user_id=member.id)
        
        # VC退出
        elif before.channel is not None and after.channel is None:
            embed = self.create_base_embed(
                title="🔇 VCから退出",
                description=f"{member.mention} が **{before.channel.name}** から退出しました",
                color=LogColor.ERROR,
                category=LogCategory.VOICE
            )
            
            member_count = len(before.channel.members)
            embed.add_field(
                name="📊 チャンネル情報",
                value=f"```\n"
                      f"チャンネル: {before.channel.name}\n"
                      f"残り人数: {member_count}人\n"
                      f"```",
                inline=False
            )
            
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            
            await log_channel.send(embed=embed)
            await self._record_stat(member.guild.id, "vc_leave", user_id=member.id)
        
        # VC移動
        elif before.channel is not None and after.channel is not None and before.channel != after.channel:
            embed = self.create_base_embed(
                title="🔀 VCを移動",
                description=f"{member.mention} がVCを移動しました",
                color=LogColor.VOICE,
                category=LogCategory.VOICE
            )
            
            embed.add_field(
                name="🔸 移動元",
                value=f"**{before.channel.name}**\n残り: {len(before.channel.members)}人",
                inline=True
            )
            
            embed.add_field(
                name="🔹 移動先",
                value=f"**{after.channel.name}**\n現在: {len(after.channel.members)}人",
                inline=True
            )
            
            if member.avatar:
                embed.set_thumbnail(url=member.avatar.url)
            
            await log_channel.send(embed=embed)
    
    # ==================== メッセージイベント ====================
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """メッセージをキャッシュに追加"""
        if message.guild and not message.author.bot:
            self.cache_message(message)
            await self._record_stat(message.guild.id, "message_sent", user_id=message.author.id)
    
    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        """メッセージ削除時のログ"""
        if not message.guild or message.author.bot:
            return
            
        log_channel = self.get_log_channel(message.guild)
        if not log_channel:
            return
        
        # 同じログチャンネルのメッセージは記録しない
        if message.channel.id == log_channel.id:
            return
        
        embed = self.create_base_embed(
            title="🗑️ メッセージが削除されました",
            description=f"{message.channel.mention} でメッセージが削除されました",
            color=LogColor.ERROR,
            category=LogCategory.MESSAGE
        )
        
        embed.add_field(
            name="👤 送信者",
            value=f"{message.author.mention}\n({message.author})",
            inline=True
        )
        
        embed.add_field(
            name="📍 チャンネル",
            value=f"{message.channel.mention}",
            inline=True
        )
        
        # メッセージ内容（1024文字まで）
        content = message.content if message.content else "*（テキストなし）*"
        if len(content) > 1000:
            content = content[:1000] + "..."
        
        embed.add_field(
            name="💬 削除されたメッセージ",
            value=f"```\n{content}\n```" if message.content else content,
            inline=False
        )
        
        # 添付ファイル
        if message.attachments:
            attachment_names = ", ".join([a.filename for a in message.attachments])
            embed.add_field(
                name="📎 添付ファイル",
                value=attachment_names[:500],
                inline=False
            )
        
        if message.author.avatar:
            embed.set_thumbnail(url=message.author.avatar.url)
        
        await log_channel.send(embed=embed)
        await self._record_stat(message.guild.id, "message_deleted", user_id=message.author.id)
    
    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        """メッセージ編集時のログ"""
        if not after.guild or after.author.bot:
            return
        
        # 内容が変わっていない場合はスキップ（埋め込みの追加など）
        if before.content == after.content:
            return
            
        log_channel = self.get_log_channel(after.guild)
        if not log_channel:
            return
        
        # ログチャンネル自体の編集は記録しない
        if after.channel.id == log_channel.id:
            return
        
        embed = self.create_base_embed(
            title="✏️ メッセージが編集されました",
            description=f"{after.channel.mention} でメッセージが編集されました\n[メッセージへジャンプ]({after.jump_url})",
            color=LogColor.MESSAGE,
            category=LogCategory.MESSAGE
        )
        
        embed.add_field(
            name="👤 送信者",
            value=f"{after.author.mention}\n({after.author})",
            inline=True
        )
        
        embed.add_field(
            name="📍 チャンネル",
            value=f"{after.channel.mention}",
            inline=True
        )
        
        # 編集前の内容
        before_content = before.content if before.content else "*（テキストなし）*"
        if len(before_content) > 500:
            before_content = before_content[:500] + "..."
        
        embed.add_field(
            name="📝 編集前",
            value=f"```\n{before_content}\n```" if before.content else before_content,
            inline=False
        )
        
        # 編集後の内容
        after_content = after.content if after.content else "*（テキストなし）*"
        if len(after_content) > 500:
            after_content = after_content[:500] + "..."
        
        embed.add_field(
            name="📝 編集後",
            value=f"```\n{after_content}\n```" if after.content else after_content,
            inline=False
        )
        
        if after.author.avatar:
            embed.set_thumbnail(url=after.author.avatar.url)
        
        await log_channel.send(embed=embed)
        await self._record_stat(after.guild.id, "message_edited", user_id=after.author.id)
    
    # ==================== ロールイベント ====================
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """メンバー更新時のログ（ロール変更など）"""
        log_channel = self.get_log_channel(after.guild)
        if not log_channel:
            return
        
        # ロール変更をチェック
        before_roles = set(before.roles)
        after_roles = set(after.roles)
        
        added_roles = after_roles - before_roles
        removed_roles = before_roles - after_roles
        
        if added_roles or removed_roles:
            embed = self.create_base_embed(
                title="🏷️ ロールが変更されました",
                description=f"{after.mention} のロールが変更されました",
                color=LogColor.ROLE,
                category=LogCategory.ROLE
            )
            
            embed.add_field(
                name="👤 ユーザー",
                value=f"{after.mention}\n({after})",
                inline=True
            )
            
            if added_roles:
                added_text = " ".join([r.mention for r in added_roles])
                embed.add_field(
                    name="➕ 追加されたロール",
                    value=added_text,
                    inline=False
                )
            
            if removed_roles:
                removed_text = " ".join([r.mention for r in removed_roles])
                embed.add_field(
                    name="➖ 削除されたロール",
                    value=removed_text,
                    inline=False
                )
            
            if after.avatar:
                embed.set_thumbnail(url=after.avatar.url)
            
            await log_channel.send(embed=embed)
            
            if added_roles:
                await self._record_stat(after.guild.id, "role_added", len(added_roles), user_id=after.id)
            if removed_roles:
                await self._record_stat(after.guild.id, "role_removed", len(removed_roles), user_id=after.id)
    
    # ==================== 募集ログ用のヘルパーメソッド ====================
    
    async def log_recruitment_created(
        self, 
        guild: discord.Guild, 
        author: discord.Member,
        mode: str,
        max_members: int,
        rank_range: str
    ):
        """募集作成ログを記録"""
        log_channel = self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = self.create_base_embed(
            title="📣 新しい募集が作成されました",
            description=f"{author.mention} が募集を開始しました",
            color=LogColor.RECRUIT,
            category=LogCategory.RECRUIT
        )
        
        embed.add_field(name="🎮 モード", value=mode, inline=True)
        embed.add_field(name="👥 募集人数", value=f"{max_members}人", inline=True)
        embed.add_field(name="🏆 ランク範囲", value=rank_range, inline=True)
        
        if author.avatar:
            embed.set_thumbnail(url=author.avatar.url)
        
        await log_channel.send(embed=embed)
        await self._record_stat(guild.id, "recruit_created", user_id=author.id)
    
    async def log_recruitment_joined(
        self, 
        guild: discord.Guild, 
        member: discord.Member,
        recruitment_author: discord.Member
    ):
        """募集参加ログを記録"""
        log_channel = self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = self.create_base_embed(
            title="✅ 募集に参加しました",
            description=f"{member.mention} が {recruitment_author.mention} の募集に参加しました",
            color=LogColor.SUCCESS,
            category=LogCategory.RECRUIT
        )
        
        if member.avatar:
            embed.set_thumbnail(url=member.avatar.url)
        
        await log_channel.send(embed=embed)
        await self._record_stat(guild.id, "recruit_joined", user_id=member.id)
    
    async def log_recruitment_closed(
        self, 
        guild: discord.Guild, 
        author: discord.Member,
        participant_count: int
    ):
        """募集終了ログを記録"""
        log_channel = self.get_log_channel(guild)
        if not log_channel:
            return
        
        embed = self.create_base_embed(
            title="🔒 募集が終了しました",
            description=f"{author.mention} の募集が終了しました",
            color=LogColor.WARNING,
            category=LogCategory.RECRUIT
        )
        
        embed.add_field(
            name="👥 最終参加人数",
            value=f"{participant_count}人",
            inline=True
        )
        
        if author.avatar:
            embed.set_thumbnail(url=author.avatar.url)
        
        await log_channel.send(embed=embed)
        await self._record_stat(guild.id, "recruit_closed", user_id=author.id)
    
    # ==================== 統計データ記録 ====================
    
    async def _record_stat(self, guild_id: int, event_type: str, count: int = 1, user_id: Optional[int] = None):
        """統計データをデータベースに記録"""
        from utils.db_manager import db
        
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        
        try:
            # サーバー全体の統計
            existing = await db.fetchrow(
                """
                SELECT count FROM statistics 
                WHERE guild_id = ? AND event_type = ? AND date = ?
                """,
                (guild_id, event_type, today)
            )
            
            if existing:
                await db.execute(
                    """
                    UPDATE statistics SET count = count + ? 
                    WHERE guild_id = ? AND event_type = ? AND date = ?
                    """,
                    (count, guild_id, event_type, today)
                )
            else:
                await db.execute(
                    """
                    INSERT INTO statistics (guild_id, event_type, date, count)
                    VALUES (?, ?, ?, ?)
                    """,
                    (guild_id, event_type, today, count)
                )
            
            # ユーザー個別の統計
            if user_id:
                existing_user = await db.fetchrow(
                    """
                    SELECT count FROM user_statistics 
                    WHERE guild_id = ? AND user_id = ? AND event_type = ? AND date = ?
                    """,
                    (guild_id, user_id, event_type, today)
                )
                
                if existing_user:
                    await db.execute(
                        """
                        UPDATE user_statistics SET count = count + ? 
                        WHERE guild_id = ? AND user_id = ? AND event_type = ? AND date = ?
                        """,
                        (count, guild_id, user_id, event_type, today)
                    )
                else:
                    await db.execute(
                        """
                        INSERT INTO user_statistics (guild_id, user_id, event_type, date, count)
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (guild_id, user_id, event_type, today, count)
                    )
                
        except Exception as e:
            print(f"統計記録エラー: {e}")

def setup(bot: commands.Bot):
    bot.add_cog(Logger(bot))
