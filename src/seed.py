"""Database schema setup script."""

import asyncio

from sqlalchemy import text

from .database.connection import engine
from .database.models import Base


async def setup_schema():
    """Create all database tables based on SQLAlchemy models."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        print("✓ Database schema created successfully!")


async def main():
    """Main entry point."""
    await setup_schema()


if __name__ == "__main__":
    asyncio.run(main())
