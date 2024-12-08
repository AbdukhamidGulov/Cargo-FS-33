from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
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
                phone VARCHAR
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
async def add_user_info(tg_id, username, name, phone=None):
    async with connect("database.db") as db:
        await db.execute("""
            INSERT INTO users (tg_id, name, username, phone)
            VALUES (?, ?, ?, ?)
        """, (tg_id, name, username, phone,))
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


async def get_user_by_id(user_id: str) -> dict | None:
    if user_id.startswith("FS"):
        user_id = int(user_id[2:])
    else:
        user_id = int(user_id)

    async with connect("database.db") as db:
        query = "SELECT * FROM users WHERE id = ?"
        async with db.execute(query, (user_id,)) as cursor:
            result = await cursor.fetchone()
            if result:
                return {
                    "id": result[0],
                    "tg_id": result[1],
                    "name": result[2],
                    "username": result[3],
                    "phone": result[4],
                }
    return None


## РАБОТА С ТРЕК-КОДАМИ
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
async def add_or_update_track_codes_list(track_codes: list[str], status: str, bot, message: Message):
    async with connect("database.db") as db:
        for track in track_codes:
            result = await db.execute("""
                INSERT INTO track_codes (track_code, status, tg_id)
                VALUES (?, ?, NULL)
                ON CONFLICT(track_code) DO UPDATE SET status=excluded.status
                RETURNING track_code, tg_id, status
            """, (track, status))
            row = await result.fetchone()
            if row and row[1]:
                track_code, tg_id, status = row
                status_text = "на складе" if status == "in_stock" else "отправлен"
                try:
                    await bot.send_message(tg_id, f"Ваш товар с трек-кодом <code>{track_code}</code> {status_text}.")
                except TelegramBadRequest as e:
                    if "chat not found" in str(e):
                        bot.send_message(message.from_user.id, f"Не удалось отправить сообщение пользователю {tg_id}: {e}")
                        # Обновление или удаление невалидного tg_id
                        await db.execute("""
                                            UPDATE track_codes 
                                            SET tg_id = NULL 
                                            WHERE track_code = ? AND tg_id = ?
                                        """, (track_code, tg_id))
                    else:
                        bot.send_message(message.from_user.id, f"Ошибка при отправке сообщения: {e}")
                except Exception as e:
                    bot.send_message(message.from_user.id, f"Неизвестная ошибка при отправке сообщения: {e}")

        await db.commit()


# Проверка или добавление трек-кода для пользователя
async def check_or_add_track_code(track_code: str, tg_id: int, bot: Bot):
    async with connect("database.db") as db:
        db.row_factory = Row
        async with db.execute("SELECT * FROM track_codes WHERE track_code = ?", (track_code,)) as cursor:
            row = await cursor.fetchone()

        if row:
            old_status = row["status"]
            if row["tg_id"] is None:
                await db.execute("""
                    UPDATE track_codes
                    SET tg_id = ?
                    WHERE track_code = ?
                """, (tg_id, track_code))
                await db.commit()

            if old_status != "in_stock" and old_status != "shipped":
                status = "in_stock" if row["status"] == "in_stock" else "shipped"
                await db.execute("""
                    UPDATE track_codes
                    SET status = ?
                    WHERE track_code = ?
                """, (status, track_code))
                await db.commit()

                # Отправка уведомления
                if row["tg_id"]:
                    status_message = "Ваш товар уже на складе." if status == "in_stock" else "Ваш товар уже был отправлен."
                    await bot.send_message(row["tg_id"], status_message)
            return row["status"]
        else:
            await db.execute("""
                INSERT INTO track_codes (track_code, status, tg_id)
                VALUES (?, ?, ?)
            """, (track_code, "out_of_stock", tg_id))
            await db.commit()
            return "out_of_stock"
