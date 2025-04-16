import aiosqlite
from datetime import datetime

DB_PATH = "reminders.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            remind_at TEXT NOT NULL,
            done INTEGER DEFAULT 0,
            "repeat_type" TEXT
        )
        """)
        # Добавляем колонку category, если её ещё нет
        try:
            await db.execute('ALTER TABLE reminders ADD COLUMN category TEXT')
        except:
            pass  # уже существует

        try:
            await db.execute('ALTER TABLE reminders ADD COLUMN voice_file_id TEXT')
        except:
            pass  # если уже есть — пропускаем

        await db.commit()



async def add_reminder(user_id: int, text: str, remind_at: str, repeat_type: str = None, category: str = None, voice_file_id: str = None) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO reminders (user_id, text, remind_at, repeat_type, category, voice_file_id) VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, text, remind_at, repeat_type, category, voice_file_id)
        )
        await db.commit()
        return cursor.lastrowid





async def get_reminders():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, user_id, text, remind_at FROM reminders")
        return await cursor.fetchall()

async def delete_reminder(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM reminders WHERE id = ?", (reminder_id,))
        await db.commit()


async def get_user_reminders(user_id: int, category: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if category:
            cursor = await db.execute(
                """
                SELECT id, text, remind_at, category, voice_file_id
                FROM reminders
                WHERE user_id = ? AND done = 0 AND category = ?
                ORDER BY remind_at
                """,
                (user_id, category)
            )
        else:
            cursor = await db.execute(
                """
                SELECT id, text, remind_at, category, voice_file_id
                FROM reminders
                WHERE user_id = ? AND done = 0
                ORDER BY remind_at
                """,
                (user_id,)
            )
        return await cursor.fetchall()


async def get_reminder_by_id(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id, done, remind_at, repeat_type, voice_file_id FROM reminders WHERE id = ?", (reminder_id,))
        row = await cursor.fetchone()
        if row:
            return {
                "id": row[0],
                "done": bool(row[1]),
                "remind_at": row[2],
                "repeat_type": row[3],
                "voice_file_id": row[4]
            }
        return None



async def get_future_reminders():
    now_iso = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, user_id, text, remind_at FROM reminders WHERE remind_at > ?",
            (now_iso,))
        return await cursor.fetchall()


async def mark_done(reminder_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE reminders SET done = 1 WHERE id = ?", (reminder_id,))
        await db.commit()

async def get_done_reminders(user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT text, remind_at FROM reminders WHERE user_id = ? AND done = 1 ORDER BY remind_at DESC",
            (user_id,))
        return await cursor.fetchall()



