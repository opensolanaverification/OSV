import aiosqlite
import time
from .config import DB_PATH

class Database:
    def __init__(self):
        self.db_path = DB_PATH

    async def init_db(self):
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    discord_id INTEGER PRIMARY KEY,
                    wallet_address TEXT UNIQUE,
                    verified_at REAL,
                    last_checked REAL
                );
                
                CREATE TABLE IF NOT EXISTS wallet_challenges (
                    discord_id INTEGER,
                    wallet TEXT,
                    amount REAL,
                    expires_at REAL,
                    tx_signature TEXT,
                    status TEXT,
                    PRIMARY KEY (discord_id, wallet)
                );
                
                CREATE TABLE IF NOT EXISTS collections (
                    collection_address TEXT PRIMARY KEY,
                    name TEXT
                );
                
                CREATE TABLE IF NOT EXISTS tiers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    collection_address TEXT,
                    min_amount INTEGER,
                    role_id INTEGER,
                    FOREIGN KEY(collection_address) REFERENCES collections(collection_address) ON DELETE CASCADE
                );
                
                CREATE TABLE IF NOT EXISTS nft_cache (
                    wallet TEXT,
                    collection TEXT,
                    amount INTEGER,
                    last_updated REAL,
                    PRIMARY KEY (wallet, collection)
                );
            """)
            await db.commit()

    async def get_user(self, discord_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,)) as cursor:
                return await cursor.fetchone()

    async def add_user(self, discord_id: int, wallet_address: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO users (discord_id, wallet_address, verified_at, last_checked) VALUES (?, ?, ?, ?)",
                (discord_id, wallet_address, time.time(), time.time())
            )
            await db.commit()

    async def remove_user(self, discord_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM users WHERE discord_id = ?", (discord_id,))
            await db.commit()

    async def create_challenge(self, discord_id: int, wallet: str, amount: float, expires_at: float):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO wallet_challenges (discord_id, wallet, amount, expires_at, status) VALUES (?, ?, ?, ?, 'PENDING')",
                (discord_id, wallet, amount, expires_at)
            )
            await db.commit()

    async def get_challenge(self, discord_id: int, wallet: str):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM wallet_challenges WHERE discord_id = ? AND wallet = ?", 
                (discord_id, wallet)
            ) as cursor:
                return await cursor.fetchone()

    async def delete_challenge(self, discord_id: int, wallet: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM wallet_challenges WHERE discord_id = ? AND wallet = ?",
                (discord_id, wallet)
            )
            await db.commit()

    async def add_collection(self, address: str, name: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR IGNORE INTO collections (collection_address, name) VALUES (?, ?)",
                (address, name)
            )
            await db.commit()

    async def remove_collection(self, address: str):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("DELETE FROM collections WHERE collection_address = ?", (address,))
            await db.commit()

    async def get_all_collections(self):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM collections") as cursor:
                return await cursor.fetchall()

    async def get_collection(self, address: str):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM collections WHERE collection_address = ?", (address,)) as cursor:
                return await cursor.fetchone()

    async def add_tier(self, collection: str, min_amount: int, role_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT INTO tiers (collection_address, min_amount, role_id) VALUES (?, ?, ?)",
                (collection, min_amount, role_id)
            )
            await db.commit()

    async def remove_tier(self, collection: str, role_id: int):
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "DELETE FROM tiers WHERE collection_address = ? AND role_id = ?",
                (collection, role_id)
            )
            await db.commit()

    async def get_tiers(self, collection: str):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT * FROM tiers WHERE collection_address = ? ORDER BY min_amount DESC",
                (collection,)
            ) as cursor:
                return await cursor.fetchall()
                
    async def get_all_tiers(self):
         async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM tiers") as cursor:
                 return await cursor.fetchall()
