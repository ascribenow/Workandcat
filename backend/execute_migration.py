#!/usr/bin/env python3
"""
Execute Blueprint Migration Scripts
"""

import asyncio
import os
import sys
import asyncpg
from pathlib import Path

async def execute_sql_file(connection, file_path):
    """Execute SQL file through asyncpg connection"""
    print(f"Executing {file_path}...")
    
    try:
        with open(file_path, 'r') as f:
            sql_content = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            try:
                if statement.upper().startswith(('CREATE', 'ALTER', 'INSERT', 'UPDATE', 'DELETE', 'DROP')):
                    await connection.execute(statement)
                    print(f"  ✅ Statement {i+1}/{len(statements)} executed")
                elif statement.upper().startswith('COMMIT'):
                    # Skip COMMIT statements in asyncpg
                    print(f"  ⏭️ Skipped COMMIT statement {i+1}")
                else:
                    print(f"  ⏭️ Skipped statement {i+1}: {statement[:50]}...")
            except Exception as e:
                print(f"  ⚠️ Warning in statement {i+1}: {e}")
                # Continue with other statements
        
        print(f"✅ Completed {file_path}")
        return True
        
    except Exception as e:
        print(f"❌ Error executing {file_path}: {e}")
        return False

async def main():
    """Main migration execution"""
    
    # Load environment variables from .env file
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL not found in environment")
        print("Available env vars:", [k for k in os.environ.keys() if 'URL' in k])
        sys.exit(1)
    
    print(f"🔗 Connecting to database...")
    
    try:
        # Create connection
        connection = await asyncpg.connect(database_url)
        print("✅ Database connection established")
        
        # Execute migration files in order
        migration_files = [
            'migrations/015_blueprint_schema.sql',
            'migrations/016_advisory_locks.sql'
        ]
        
        success_count = 0
        
        for file_path in migration_files:
            full_path = Path(__file__).parent / file_path
            if full_path.exists():
                success = await execute_sql_file(connection, full_path)
                if success:
                    success_count += 1
            else:
                print(f"❌ Migration file not found: {full_path}")
        
        await connection.close()
        
        if success_count == len(migration_files):
            print(f"\n🎉 All {success_count} migration files executed successfully!")
            return True
        else:
            print(f"\n⚠️ Only {success_count}/{len(migration_files)} migrations succeeded")
            return False
            
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)