from sqlite3 import Row

from aiosqlite import connect

# Создание таблицы пользователей
async def recreate_users_table():
    async with connect("database.db") as db:
        await db.execute("DROP TABLE IF EXISTS users")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                username VARCHAR,
                phone VARCHAR,
                address VARCHAR
            )
        """)
        await db.commit()

# Добавление пользователя
async def add_user_info(tg_id, username, name, phone=None, address=None):
    async with connect("database.db") as db:
        await db.execute("""
            INSERT INTO users (tg_id, name, username, phone, address)
            VALUES (?, ?, ?, ?, ?)
        """, (tg_id, name, username, phone, address))
        await db.commit()

        # Получение автоматически созданного ID
        cursor = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        result = await cursor.fetchone()
        return result[0] if result else None


async def get_user_by_tg_id(tg_id: int):
    async with connect("database.db") as db:
        cursor = await db.execute("SELECT id FROM users WHERE tg_id = ?", (tg_id,))
        user = await cursor.fetchone()
        return user

async def get_info_profile(tg_id):
    async with connect("database.db") as db:
        db.row_factory = Row
        async with db.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def update_user_info(tg_id: int, field: str, value: str):
    async with connect("database.db") as db:
        query = f"UPDATE users SET {field} = ? WHERE tg_id = ?"
        await db.execute(query, (value, tg_id))
        await db.commit()