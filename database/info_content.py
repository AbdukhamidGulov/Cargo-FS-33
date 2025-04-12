from logging import getLogger
from sqlalchemy import VARCHAR, UniqueConstraint
from sqlalchemy.future import select
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, async_session


logger = getLogger(__name__)

class InfoContent(Base):
    __tablename__ = 'info_content'
    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(VARCHAR(255), unique=True, nullable=False)
    value: Mapped[str] = mapped_column(VARCHAR(2000), nullable=False)
    __table_args__ = (UniqueConstraint('key', name='unique_key'),)

async def get_info_content(key: str):
    """Получает значение по ключу из таблицы info_content."""
    async with async_session() as session:
        result = await session.execute(select(InfoContent).where(InfoContent.key == key))
        content = result.scalar_one_or_none()
        return content.value if content else None


async def update_info_content(key: str, value: str) -> None:
    """Обновляет или добавляет значение по ключу в таблицу info_content."""
    async with async_session() as session:
        async with session.begin():
            stmt = select(InfoContent).where(InfoContent.key == key)
            result = await session.execute(stmt)
            content = result.scalar_one_or_none()
            if content:
                content.value = value
            else:
                new_content = InfoContent(key=key, value=value)
                session.add(new_content)
            await session.commit()
