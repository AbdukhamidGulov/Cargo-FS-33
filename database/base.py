from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from filters_and_config import DATABASE_URL

engine = create_async_engine(DATABASE_URL, echo=True)
async_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def setup_database():
    """Инициализирует базу данных, создавая все таблицы, определённые в моделях SQLAlchemy."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
