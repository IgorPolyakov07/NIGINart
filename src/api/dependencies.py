from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
async def verify_database_connection(db: AsyncSession) -> bool:
    try:
        await db.execute(text("SELECT 1"))
        return True
    except Exception as e:
        print(f"Database connection error: {e}")
        return False
