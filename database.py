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


# Создание таблицы track_code
async def create_track_codes_table():
    async with connect("database.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS track_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_code VARCHAR UNIQUE,
                status VARCHAR,
                tg_id INTEGER 
            )
        """)
        await db.commit()


async def drop_track_numbers_table():
    async with connect("database.db") as db:
        await db.execute("DROP TABLE IF EXISTS track_codes")
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
        return await cursor.fetchone()


async def get_users_tg_info():
    async with connect("database.db") as db:
        db.row_factory = Row
        async with db.execute("SELECT tg_id, username FROM users") as cursor:
            rows = await cursor.fetchall()
            return {row["tg_id"]: row["username"] for row in rows}

async def get_info_profile(tg_id) -> dict:
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


# Получение всех трек-кодов
async def get_track_codes_list():
    async with connect("database.db") as db:
        db.row_factory = Row
        async with db.execute("SELECT id, track_code, status, tg_id FROM track_codes") as cursor:
            return await cursor.fetchall()
    

# Получение трек-кодов пользователя
async def get_user_track_codes(tg_id: int):
    async with connect("database.db") as db:
        db.row_factory = Row
        async with db.execute(
            "SELECT track_code, status FROM track_codes WHERE tg_id = ?", (tg_id,)) as cursor:
            rows = await cursor.fetchall()
            return [(row["track_code"], row["status"]) for row in rows] if rows else []


# Добавление трек-кодов списком (для администратора)
async def add_track_codes_list(track_codes: list[str], status: str = "in_stock"):
    async with connect("database.db") as db:
        for track in track_codes:
            await db.execute("""
                INSERT INTO track_codes (track_code, status, tg_id)
                VALUES (?, ?, NULL)
                ON CONFLICT(track_code) DO UPDATE SET status=excluded.status
            """, (track, status))
        await db.commit()


# Проверка или добавление трек-кода для пользователя
async def check_or_add_track_code(track_code: str, tg_id: int):
    async with connect("database.db") as db:
        db.row_factory = Row
        async with db.execute("SELECT * FROM track_codes WHERE track_code = ?", (track_code,)) as cursor:
            row = await cursor.fetchone()

        if row:
            # Если трек-код уже существует, обновляем tg_id
            if row["tg_id"] is None:  # Если tg_id ещё не задан
                await db.execute("""
                    UPDATE track_codes
                    SET tg_id = ?
                    WHERE track_code = ?
                """, (tg_id, track_code))
                await db.commit()
            return row["status"]
        else:
            await db.execute("""
                INSERT INTO track_codes (track_code, status, tg_id)
                VALUES (?, ?, ?)
            """, (track_code, "out_of_stock", tg_id))
            await db.commit()
            return "out_of_stock"
