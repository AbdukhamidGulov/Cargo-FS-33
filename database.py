from aiosqlite import connect, Row

# Создание таблицы пользователей
async def create_users_table():
    async with connect("database.db") as db:
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


async def drop_users_table():
    async with connect("database.db") as db:
        await db.execute("DROP TABLE IF EXISTS users")
        await db.commit()


# Создание таблицы track_numbers
async def create_track_numbers_table():
    async with connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS track_numbers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_number VARCHAR UNIQUE,
                status VARCHAR,
                tg_id INTEGER 
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
        return await get_user_by_tg_id(tg_id)


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


# # Получение всех трек-номеров
# async def get_track_codes_list():
#     async with connect("database.db") as db:
#         db.row_factory = Row
#         async with db.execute("SELECT track_number, status FROM track_numbers") as cursor:
#             rows = await cursor.fetchall()
#             return {row["track_number"]: row["status"] for row in rows} if rows else {}


# Добавление трек-кодов списком (для администратора)
async def add_track_codes_list(track_codes: list[str], status: str = "in_stock"):
    async with connect("database.db") as db:
        for track in track_codes:
            await db.execute("""
                INSERT INTO track_numbers (track_number, status, tg_id)
                VALUES (?, ?, NULL)
                ON CONFLICT(track_number) DO UPDATE SET status=excluded.status
            """, (track, status))
        await db.commit()


# Проверка или добавление трек-кода для пользователя
async def check_or_add_track_code(track_number: str, tg_id: int):
    async with connect("database.db") as db:
        db.row_factory = Row
        async with db.execute("SELECT * FROM track_numbers WHERE track_number = ?", (track_number,)) as cursor:
            row = await cursor.fetchone()

        if row:
            return row["status"]  # Вернуть статус, если трек-код уже есть
        else:
            await db.execute("""
                INSERT INTO track_numbers (track_number, status, tg_id)
                VALUES (?, ?, ?)
            """, (track_number, "out_of_stock", tg_id))
            await db.commit()
            return "out_of_stock"
