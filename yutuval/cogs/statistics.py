import discord
from discord.ext import commands
from discord import option
from datetime import datetime, timezone, timedelta
from typing import Optional
import json

class Statistics(commands.Cog):
    """📊 統計データトラッキング・表示機能"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    stats_group = discord.SlashCommandGroup(
        name="stats",
        description="📊 サーバー統計を表示します",
        default_member_permissions=discord.Permissions(administrator=True)
    )
    
    # ==================== 統計表示コマンド ====================
    
    @stats_group.command(name="overview", description="📊 サーバー全体の統計概要を表示")
    async def stats_overview(self, ctx: discord.ApplicationContext):
        """サーバー統計の概要を表示"""
        await ctx.defer()
        
        from utils.db_manager import db
        
        guild = ctx.guild
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
        month_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        
        # 今日の統計
        today_stats = await self._get_stats_for_period(guild.id, today, today)
        # 週間統計
        week_stats = await self._get_stats_for_period(guild.id, week_ago, today)
        # 月間統計
        month_stats = await self._get_stats_for_period(guild.id, month_ago, today)
        
        embed = discord.Embed(
            title="📊 サーバー統計ダッシュボード",
            description=f"**{guild.name}** の統計情報\n最終更新: <t:{int(datetime.now(timezone.utc).timestamp())}:R>",
            color=0x5865F2,
            timestamp=datetime.now(timezone.utc)
        )
        
        # サーバー基本情報
        total_members = guild.member_count
        online_members = sum(1 for m in guild.members if m.status != discord.Status.offline)
        bot_count = sum(1 for m in guild.members if m.bot)
        human_count = total_members - bot_count
        
        embed.add_field(
            name="👥 メンバー統計",
            value=f"```yaml\n"
                  f"総メンバー数: {total_members:,}人\n"
                  f"人間: {human_count:,}人\n"
                  f"BOT: {bot_count:,}個\n"
                  f"オンライン: {online_members:,}人\n"
                  f"```",
            inline=True
        )
        
        # チャンネル情報
        text_channels = len([c for c in guild.channels if isinstance(c, discord.TextChannel)])
        voice_channels = len([c for c in guild.channels if isinstance(c, discord.VoiceChannel)])
        categories = len(guild.categories)
        
        embed.add_field(
            name="📁 チャンネル統計",
            value=f"```yaml\n"
                  f"テキスト: {text_channels:,}個\n"
                  f"ボイス: {voice_channels:,}個\n"
                  f"カテゴリ: {categories:,}個\n"
                  f"ロール数: {len(guild.roles):,}個\n"
                  f"```",
            inline=True
        )
        
        # 今日のアクティビティ
        embed.add_field(
            name=f"📈 今日のアクティビティ ({today})",
            value=self._format_activity_stats(today_stats),
            inline=False
        )
        
        # 週間アクティビティ
        embed.add_field(
            name="📅 週間アクティビティ (7日間)",
            value=self._format_activity_stats(week_stats),
            inline=True
        )
        
        # 月間アクティビティ
        embed.add_field(
            name="📆 月間アクティビティ (30日間)",
            value=self._format_activity_stats(month_stats),
            inline=True
        )
        
        # グラフ風表示（メンバー増減）
        member_join = week_stats.get('member_join', 0)
        member_leave = week_stats.get('member_leave', 0)
        net_change = member_join - member_leave
        trend_emoji = "📈" if net_change > 0 else "📉" if net_change < 0 else "➡️"
        
        embed.add_field(
            name=f"{trend_emoji} 週間メンバー変動",
            value=f"```diff\n"
                  f"+ 参加: {member_join:,}人\n"
                  f"- 退出: {member_leave:,}人\n"
                  f"{'+ ' if net_change >= 0 else ''}{net_change:,}人 (純増減)\n"
                  f"```",
            inline=False
        )
        
        # サーバーアイコン
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        embed.set_footer(text="📊 統計システム | データは毎日自動集計されます")
        
        await ctx.respond(embed=embed)
    
    @stats_group.command(name="messages", description="💬 メッセージ統計を表示")
    @option("days", description="表示する日数", required=False, default=7, min_value=1, max_value=30)
    async def stats_messages(self, ctx: discord.ApplicationContext, days: int = 7):
        """メッセージ統計を表示"""
        await ctx.defer()
        
        from utils.db_manager import db
        
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        stats = await self._get_stats_for_period(ctx.guild.id, start_date, end_date)
        daily_stats = await self._get_daily_stats(ctx.guild.id, start_date, end_date, 'message_sent')
        
        embed = discord.Embed(
            title="💬 メッセージ統計",
            description=f"過去 **{days}日間** のメッセージ統計",
            color=0x3498DB,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 合計統計
        total_sent = stats.get('message_sent', 0)
        total_deleted = stats.get('message_deleted', 0)
        total_edited = stats.get('message_edited', 0)
        
        embed.add_field(
            name="📊 合計統計",
            value=f"```yaml\n"
                  f"送信: {total_sent:,}件\n"
                  f"削除: {total_deleted:,}件\n"
                  f"編集: {total_edited:,}件\n"
                  f"日平均: {total_sent // days if days > 0 else 0:,}件/日\n"
                  f"```",
            inline=False
        )
        
        # 日別グラフ（簡易版）
        if daily_stats:
            graph = self._create_bar_graph(daily_stats, max_width=15)
            embed.add_field(
                name="📈 日別推移（直近7日）",
                value=f"```\n{graph}\n```",
                inline=False
            )
        
        embed.set_footer(text="📊 メッセージ統計")
        
        await ctx.respond(embed=embed)
    
    @stats_group.command(name="voice", description="🔊 VC統計を表示")
    @option("days", description="表示する日数", required=False, default=7, min_value=1, max_value=30)
    async def stats_voice(self, ctx: discord.ApplicationContext, days: int = 7):
        """VC統計を表示"""
        await ctx.defer()
        
        from utils.db_manager import db
        
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        stats = await self._get_stats_for_period(ctx.guild.id, start_date, end_date)
        
        embed = discord.Embed(
            title="🔊 ボイスチャンネル統計",
            description=f"過去 **{days}日間** のVC統計",
            color=0x9B59B6,
            timestamp=datetime.now(timezone.utc)
        )
        
        # VC統計
        vc_join = stats.get('vc_join', 0)
        vc_leave = stats.get('vc_leave', 0)
        
        embed.add_field(
            name="📊 VC利用統計",
            value=f"```yaml\n"
                  f"参加回数: {vc_join:,}回\n"
                  f"退出回数: {vc_leave:,}回\n"
                  f"日平均参加: {vc_join // days if days > 0 else 0:,}回/日\n"
                  f"```",
            inline=True
        )
        
        # 現在のVC状況
        active_vcs = []
        for vc in ctx.guild.voice_channels:
            if len(vc.members) > 0:
                active_vcs.append(f"• {vc.name}: {len(vc.members)}人")
        
        if active_vcs:
            embed.add_field(
                name="🟢 現在アクティブなVC",
                value="\n".join(active_vcs[:10]) + ("\n..." if len(active_vcs) > 10 else ""),
                inline=False
            )
        else:
            embed.add_field(
                name="🟢 現在アクティブなVC",
                value="*現在利用中のVCはありません*",
                inline=False
            )
        
        embed.set_footer(text="📊 VC統計")
        
        await ctx.respond(embed=embed)
    
    @stats_group.command(name="recruitment", description="📣 募集統計を表示")
    @option("days", description="表示する日数", required=False, default=7, min_value=1, max_value=30)
    async def stats_recruitment(self, ctx: discord.ApplicationContext, days: int = 7):
        """募集統計を表示"""
        await ctx.defer()
        
        from utils.db_manager import db
        
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        stats = await self._get_stats_for_period(ctx.guild.id, start_date, end_date)
        
        embed = discord.Embed(
            title="📣 募集統計",
            description=f"過去 **{days}日間** の募集統計",
            color=0x1ABC9C,
            timestamp=datetime.now(timezone.utc)
        )
        
        # 募集統計
        recruit_created = stats.get('recruit_created', 0)
        recruit_joined = stats.get('recruit_joined', 0)
        recruit_closed = stats.get('recruit_closed', 0)
        
        avg_participants = recruit_joined / recruit_created if recruit_created > 0 else 0
        
        embed.add_field(
            name="📊 募集統計",
            value=f"```yaml\n"
                  f"作成数: {recruit_created:,}件\n"
                  f"参加総数: {recruit_joined:,}人\n"
                  f"終了数: {recruit_closed:,}件\n"
                  f"平均参加者: {avg_participants:.1f}人/募集\n"
                  f"```",
            inline=True
        )
        
        # 日別平均
        daily_avg = recruit_created / days if days > 0 else 0
        
        embed.add_field(
            name="📈 日別統計",
            value=f"```yaml\n"
                  f"日平均募集: {daily_avg:.1f}件/日\n"
                  f"日平均参加: {recruit_joined / days if days > 0 else 0:.1f}人/日\n"
                  f"```",
            inline=True
        )
        
        embed.set_footer(text="📊 募集統計")
        
        await ctx.respond(embed=embed)
    
    @stats_group.command(name="members", description="👥 メンバー増減統計を表示")
    @option("days", description="表示する日数", required=False, default=30, min_value=1, max_value=90)
    async def stats_members(self, ctx: discord.ApplicationContext, days: int = 30):
        """メンバー増減統計を表示"""
        await ctx.defer()
        
        from utils.db_manager import db
        
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        stats = await self._get_stats_for_period(ctx.guild.id, start_date, end_date)
        daily_join = await self._get_daily_stats(ctx.guild.id, start_date, end_date, 'member_join')
        daily_leave = await self._get_daily_stats(ctx.guild.id, start_date, end_date, 'member_leave')
        
        embed = discord.Embed(
            title="👥 メンバー増減統計",
            description=f"過去 **{days}日間** のメンバー変動",
            color=0x00D26A,
            timestamp=datetime.now(timezone.utc)
        )
        
        # メンバー統計
        member_join = stats.get('member_join', 0)
        member_leave = stats.get('member_leave', 0)
        net_change = member_join - member_leave
        retention_rate = ((member_join - member_leave) / member_join * 100) if member_join > 0 else 0
        
        trend_emoji = "📈" if net_change > 0 else "📉" if net_change < 0 else "➡️"
        
        embed.add_field(
            name=f"{trend_emoji} 増減サマリー",
            value=f"```diff\n"
                  f"+ 参加: {member_join:,}人\n"
                  f"- 退出: {member_leave:,}人\n"
                  f"{'+ ' if net_change >= 0 else ''}{net_change:,}人 (純増減)\n"
                  f"```",
            inline=True
        )
        
        embed.add_field(
            name="📊 分析",
            value=f"```yaml\n"
                  f"日平均参加: {member_join / days if days > 0 else 0:.1f}人\n"
                  f"日平均退出: {member_leave / days if days > 0 else 0:.1f}人\n"
                  f"定着率: {max(0, retention_rate):.1f}%\n"
                  f"```",
            inline=True
        )
        
        # 現在のメンバー構成
        guild = ctx.guild
        new_members = sum(1 for m in guild.members if m.joined_at and (datetime.now(timezone.utc) - m.joined_at.replace(tzinfo=timezone.utc)).days < 7)
        
        embed.add_field(
            name="📋 現在のメンバー構成",
            value=f"```yaml\n"
                  f"総メンバー: {guild.member_count:,}人\n"
                  f"新規(7日以内): {new_members:,}人\n"
                  f"BOT: {sum(1 for m in guild.members if m.bot):,}個\n"
                  f"```",
            inline=False
        )
        
        embed.set_footer(text="📊 メンバー統計")
        
        await ctx.respond(embed=embed)
    
    @stats_group.command(name="roles", description="🏷️ ロール変更統計を表示")
    @option("days", description="表示する日数", required=False, default=7, min_value=1, max_value=30)
    async def stats_roles(self, ctx: discord.ApplicationContext, days: int = 7):
        """ロール変更統計を表示"""
        await ctx.defer()
        
        from utils.db_manager import db
        
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        stats = await self._get_stats_for_period(ctx.guild.id, start_date, end_date)
        
        embed = discord.Embed(
            title="🏷️ ロール変更統計",
            description=f"過去 **{days}日間** のロール変更統計",
            color=0xF39C12,
            timestamp=datetime.now(timezone.utc)
        )
        
        # ロール統計
        roles_added = stats.get('role_added', 0)
        roles_removed = stats.get('role_removed', 0)
        
        embed.add_field(
            name="📊 ロール変更統計",
            value=f"```yaml\n"
                  f"追加: {roles_added:,}回\n"
                  f"削除: {roles_removed:,}回\n"
                  f"合計変更: {roles_added + roles_removed:,}回\n"
                  f"```",
            inline=True
        )
        
        # サーバーのロール情報
        guild = ctx.guild
        top_roles = sorted(guild.roles, key=lambda r: len(r.members), reverse=True)[:5]
        if top_roles:
            role_list = "\n".join([
                f"• {r.name}: {len(r.members)}人" 
                for r in top_roles 
                if r != guild.default_role
            ][:5])
            embed.add_field(
                name="👑 メンバー数上位ロール",
                value=role_list if role_list else "*データなし*",
                inline=True
            )
        
        embed.set_footer(text="📊 ロール統計")
        
        await ctx.respond(embed=embed)
    
    @stats_group.command(name="ranking", description="🏆 サーバー内ランキングを表示")
    @option("category", description="ランキングのカテゴリ", choices=[
        discord.OptionChoice("💬 メッセージ送信数", "message_sent"),
        discord.OptionChoice("🔊 VC参加回数", "vc_join"),
        discord.OptionChoice("📣 募集参加回数", "recruit_joined"),
        discord.OptionChoice("🎮 募集作成回数", "recruit_created")
    ])
    @option("days", description="集計期間（日数）", required=False, default=7, min_value=1, max_value=90)
    async def stats_ranking(self, ctx: discord.ApplicationContext, category: str, days: int = 7):
        """サーバー内ランキングを表示"""
        await ctx.defer()
        
        from utils.db_manager import db
        
        end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # ランキングデータ取得
        ranking_data = await self._get_ranking_stats(ctx.guild.id, category, start_date, end_date)
        
        category_names = {
            "message_sent": "💬 メッセージ送信数",
            "vc_join": "🔊 VC参加回数",
            "recruit_joined": "📣 募集参加回数",
            "recruit_created": "🎮 募集作成回数"
        }
        
        title = category_names.get(category, "ランキング")
        
        embed = discord.Embed(
            title=f"🏆 {title} ランキング",
            description=f"過去 **{days}日間** の集計結果",
            color=discord.Color.gold(),
            timestamp=datetime.now(timezone.utc)
        )
        
        if not ranking_data:
            embed.description += "\n\n⚠️ データがありません"
        else:
            rank_text = ""
            for i, (user_id, count) in enumerate(ranking_data[:10], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                user = ctx.guild.get_member(user_id)
                user_name = user.display_name if user else f"Unknown User ({user_id})"
                
                rank_text += f"**{medal} {user_name}**: {count:,}回\n"
            
            embed.add_field(name="Top 10", value=rank_text, inline=False)
            
            # 自分の順位
            my_rank = next((i for i, (uid, _) in enumerate(ranking_data, 1) if uid == ctx.author.id), None)
            if my_rank:
                count = next((c for u, c in ranking_data if u == ctx.author.id), 0)
                embed.set_footer(text=f"あなたの順位: {my_rank}位 ({count}回)")
            else:
                embed.set_footer(text="あなたはランク外です")
                
        await ctx.respond(embed=embed)

    # ==================== ヘルパーメソッド ====================
    
    async def _get_ranking_stats(self, guild_id: int, event_type: str, start_date: str, end_date: str) -> list:
        """期間内のユーザー別ランキングを取得"""
        from utils.db_manager import db
        
        try:
            rows = await db.fetchall(
                """
                SELECT user_id, SUM(count) as total
                FROM user_statistics
                WHERE guild_id = ? AND event_type = ? AND date >= ? AND date <= ?
                GROUP BY user_id
                ORDER BY total DESC
                LIMIT 50
                """,
                (guild_id, event_type, start_date, end_date)
            )
            return [(row[0], row[1]) for row in rows] if rows else []
        except Exception as e:
            print(f"ランキング取得エラー: {e}")
            return []

    async def _get_stats_for_period(self, guild_id: int, start_date: str, end_date: str) -> dict:
        """指定期間の統計を取得"""
        from utils.db_manager import db
        
        try:
            rows = await db.fetchall(
                """
                SELECT event_type, SUM(count) as total
                FROM statistics
                WHERE guild_id = ? AND date >= ? AND date <= ?
                GROUP BY event_type
                """,
                (guild_id, start_date, end_date)
            )
            
            return {row[0]: row[1] for row in rows} if rows else {}
        except Exception as e:
            print(f"統計取得エラー: {e}")
            return {}
    
    async def _get_daily_stats(self, guild_id: int, start_date: str, end_date: str, event_type: str) -> list:
        """日別統計を取得"""
        from utils.db_manager import db
        
        try:
            rows = await db.fetchall(
                """
                SELECT date, count
                FROM statistics
                WHERE guild_id = ? AND event_type = ? AND date >= ? AND date <= ?
                ORDER BY date DESC
                LIMIT 7
                """,
                (guild_id, event_type, start_date, end_date)
            )
            
            return [(row[0], row[1]) for row in rows] if rows else []
        except Exception as e:
            print(f"日別統計取得エラー: {e}")
            return []
    
    def _format_activity_stats(self, stats: dict) -> str:
        """アクティビティ統計をフォーマット"""
        messages = stats.get('message_sent', 0)
        vc_joins = stats.get('vc_join', 0)
        recruits = stats.get('recruit_created', 0)
        
        return f"```yaml\n" \
               f"💬 メッセージ: {messages:,}件\n" \
               f"🔊 VC参加: {vc_joins:,}回\n" \
               f"📣 募集作成: {recruits:,}件\n" \
               f"```"
    
    def _create_bar_graph(self, daily_stats: list, max_width: int = 15) -> str:
        """簡易バーグラフを作成"""
        if not daily_stats:
            return "データなし"
        
        max_value = max(count for _, count in daily_stats) if daily_stats else 1
        max_value = max(max_value, 1)  # 0除算防止
        
        lines = []
        for date_str, count in reversed(daily_stats):
            # 日付を短縮
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                short_date = date_obj.strftime("%m/%d")
            except:
                short_date = date_str[-5:]
            
            bar_length = int((count / max_value) * max_width)
            bar = "█" * bar_length + "░" * (max_width - bar_length)
            lines.append(f"{short_date} {bar} {count:,}")
        
        return "\n".join(lines)

def setup(bot: commands.Bot):
    bot.add_cog(Statistics(bot))
