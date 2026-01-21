from typing import Generic, List, Optional, Type, TypeVar
from uuid import UUID
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.base import Base
ModelType = TypeVar("ModelType", bound=Base)
class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    async def get(self, id: UUID) -> Optional[ModelType]:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()
    async def get_all(self, limit: int = 100, offset: int = 0) -> List[ModelType]:
        result = await self.session.execute(select(self.model).limit(limit).offset(offset))
        return list(result.scalars().all())
    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    async def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        return await self.get(id)
    async def delete(self, id: UUID) -> bool:
        result = await self.session.execute(delete(self.model).where(self.model.id == id))
        return result.rowcount > 0
