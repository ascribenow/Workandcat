#!/usr/bin/env python3
"""
Fix diagnostic system by cleaning up corrupt records
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database import get_database, Diagnostic
from sqlalchemy import select, func

async def main():
    print("🔧 Fixing diagnostic system...")
    
    async for db in get_database():
        # Delete all diagnostic records with null set_id
        corrupt_diagnostics = await db.execute(
            select(Diagnostic).where(Diagnostic.set_id.is_(None))
        )
        corrupt_records = corrupt_diagnostics.scalars().all()
        
        print(f"Found {len(corrupt_records)} corrupt diagnostic records")
        
        for diagnostic in corrupt_records:
            await db.delete(diagnostic)
        
        await db.commit()
        print(f"✅ Deleted {len(corrupt_records)} corrupt diagnostic records")
        
        # Count remaining diagnostics
        remaining = await db.scalar(select(db.func.count(Diagnostic.id)))
        print(f"Remaining diagnostic records: {remaining}")
        
        break

if __name__ == "__main__":
    asyncio.run(main())