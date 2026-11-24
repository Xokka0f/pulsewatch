from src.config import settings
from src.service.auth import AuthService
from src.repository.user_repo import UserRepository
from fastapi import Depends
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

engine = create_async_engine(url=settings.database_url)
session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_session():
    async with session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(UserRepository(session))