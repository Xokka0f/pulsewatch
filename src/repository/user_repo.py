from sqlalchemy import select
from src.repository.base_repo import BaseRepository
from src.models.user import User


class UserRepository(BaseRepository):
    model = User

    async def get_by_email(self, email: str):
        result = await self.session.scalars(select(self.model).where(self.model.email == email))
        return result.one_or_none()