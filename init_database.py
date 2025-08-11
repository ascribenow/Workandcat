#!/usr/bin/env python3
"""
Initialize PostgreSQL database with all required tables
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database import engine, Base, get_database
from sqlalchemy import text

async def init_database():
    """Initialize database with all tables"""
    print("🔧 Initializing PostgreSQL database...")
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database tables created successfully!")
        
        # Test connection
        async for db in get_database():
            result = await db.execute(text("SELECT version();"))
            version = result.scalar()
            print(f"📊 PostgreSQL version: {version}")
            break
        
        return True
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)