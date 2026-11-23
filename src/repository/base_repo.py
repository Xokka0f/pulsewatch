from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository:
    model = None

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, id: int):
        return await self.session.get(self.model, id)

    async def get_all(self):
        result = await self.session.scalars(select(self.model))
        return result.all()

    async def create(self, **kwargs):
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def update(self, id: int,  **kwargs):
        obj = await self.get_by_id(id)
        for key, value in kwargs.items():
            setattr(obj, key, value)
        await self.session.flush()
        return obj

    async def delete(self, id: int):
        obj = await self.get_by_id(id)
        await self.session.delete(obj)
        await self.session.flush()