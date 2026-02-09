import aiosqlite

DB_NAME = "checks.db"

async def init_db():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            file_id TEXT,
            channel_msg_id INTEGER,
            status TEXT
        )
        """)
        await db.commit()

async def add_check(user_id, username, file_id, channel_msg_id):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "INSERT INTO checks (user_id, username, file_id, channel_msg_id, status) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, file_id, channel_msg_id, "pending")
        )
        await db.commit()

async def update_status(check_id, status):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute(
            "UPDATE checks SET status = ? WHERE id = ?",
            (status, check_id)
        )
        await db.commit()

async def get_check(check_id):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT user_id FROM checks WHERE id = ?",
            (check_id,)
        ) as cursor:
            return await cursor.fetchone()
