import aiosqlite
import os

DATABASE_PATH = "database/bot_data.db"

class DBManager:
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.connection = None

    async def connect(self):
        # Ensure directory exists
        folder = os.path.dirname(self.db_path)
        if not os.path.exists(folder):
            os.makedirs(folder)
            print(f"Created database directory: {folder}")

        self.connection = await aiosqlite.connect(self.db_path)
        await self.connection.execute("PRAGMA foreign_keys = ON")
        await self.create_tables()
        print("Database connected.")


    async def create_tables(self):
        # サーバー設定用テーブル
        await self.execute("""
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY,
                rank_emojis TEXT
            )
        """)

        # 募集管理用テーブル
        await self.execute("""
            CREATE TABLE IF NOT EXISTS recruitments (
                message_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                author_id INTEGER,
                max_members INTEGER,
                rank_range TEXT,
                mode TEXT,
                joined_members TEXT, -- JSON or comma separated IDs
                is_closed INTEGER DEFAULT 0
            )
        """)
        
        # VC管理用テーブル
        await self.execute("""
            CREATE TABLE IF NOT EXISTS active_vcs (
                vc_id INTEGER PRIMARY KEY,
                text_channel_id INTEGER,
                owner_id INTEGER,
                party_code TEXT,
                is_locked INTEGER DEFAULT 0,
                panel_message_id INTEGER,
                source_channel_id INTEGER
            )
        """)
        
        # 統計データ用テーブル (サーバー全体)
        await self.execute("""
            CREATE TABLE IF NOT EXISTS statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(guild_id, event_type, date)
            )
        """)

        # 統計データ用テーブル (ユーザー別・ランキング用)
        await self.execute("""
            CREATE TABLE IF NOT EXISTS user_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                date TEXT NOT NULL,
                count INTEGER DEFAULT 0,
                UNIQUE(guild_id, user_id, event_type, date)
            )
        """)
        
        # 統計テーブルのインデックス作成
        await self.execute("""
            CREATE INDEX IF NOT EXISTS idx_statistics_guild_date 
            ON statistics(guild_id, date)
        """)
        
        await self.execute("""
            CREATE INDEX IF NOT EXISTS idx_user_statistics_ranking
            ON user_statistics(guild_id, event_type, date)
        """)
        
        await self.execute("""
            CREATE INDEX IF NOT EXISTS idx_statistics_guild_event 
            ON statistics(guild_id, event_type)
        """)
        
        # カラム追加のマイグレーション
        try:
            await self.execute("ALTER TABLE active_vcs ADD COLUMN panel_message_id INTEGER")
        except:
            pass
            
        try:
            await self.execute("ALTER TABLE active_vcs ADD COLUMN source_channel_id INTEGER")
        except:
            pass

        try:
            await self.execute("ALTER TABLE recruitments ADD COLUMN vc_id INTEGER")
        except:
            pass

        try:
            await self.execute("ALTER TABLE server_config ADD COLUMN recruit_channel_id INTEGER")
        except:
            pass

        try:
            await self.execute("ALTER TABLE server_config ADD COLUMN last_recruit_msg_id INTEGER")
        except:
            pass
            
        await self.connection.commit()

    async def get_config(self, guild_id: int):
        """サーバー設定を取得"""
        row = await self.fetchrow("SELECT * FROM server_config WHERE guild_id = ?", (guild_id,))
        if row:
            import json
            try:
                rank_emojis = json.loads(row[1]) if row[1] else {}
            except:
                rank_emojis = {}
            return {"rank_emojis": rank_emojis}
        return {"rank_emojis": {}}

    async def update_rank_emoji(self, guild_id: int, rank_name: str, emoji_str: str):
        """ランク絵文字を更新"""
        import json
        config = await self.get_config(guild_id)
        current_emojis = config["rank_emojis"]
        current_emojis[rank_name] = emoji_str
        
        # UPSERT的な処理 (SQLite 3.24+ なら INSERT OR REPLACE や ON CONFLICT が使えるが汎用的に)
        exists = await self.fetchrow("SELECT 1 FROM server_config WHERE guild_id = ?", (guild_id,))
        if exists:
            await self.execute(
                "UPDATE server_config SET rank_emojis = ? WHERE guild_id = ?",
                (json.dumps(current_emojis), guild_id)
            )
        else:
            await self.execute(
                "INSERT INTO server_config (guild_id, rank_emojis) VALUES (?, ?)",
                (guild_id, json.dumps(current_emojis))
            )

    async def close(self):
        if self.connection:
            await self.connection.close()
            print("Database connection closed.")

    async def execute(self, query: str, parameters: tuple = ()):
        if not self.connection:
            await self.connect()
        async with self.connection.cursor() as cursor:
            await cursor.execute(query, parameters)
            await self.connection.commit()

    async def fetchrow(self, query: str, parameters: tuple = ()):
        if not self.connection:
            await self.connect()
        async with self.connection.execute(query, parameters) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, query: str, parameters: tuple = ()):
        if not self.connection:
            await self.connect()
        async with self.connection.execute(query, parameters) as cursor:
            return await cursor.fetchall()

db = DBManager()
