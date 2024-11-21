from aiosqlite import connect

# Создание таблицы пользователей
async def create_users_table():
    async with connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                username VARCHAR,
                number INTEGER,
                city VARCHAR
            )
        """)
        await db.commit()

# Добавление пользователя
async def add_user_info(tg_id, username, name, number=None, city=None):
    async with connect("database.db") as db:
        await db.execute("""
            INSERT INTO users (tg_id, name, username, number, city)
            VALUES (?, ?, ?, ?, ?)
        """, (tg_id, name, username, number, city))
        await db.commit()

        # Получение автоматически созданного ID
        cursor = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

import aiosqlite

async def get_user_by_tg_id(tg_id: int):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        user = await cursor.fetchone()
        return user

async def get_info_profil(tg_id):
    async with aiosqlite.connect("database.db") as db:
        cursor = await db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,))
        user = await cursor.fetchone()
        return user
        # Нужно дописать