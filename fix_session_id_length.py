#!/usr/bin/env python3
"""
Fix session_id column length in session_pack_plan table
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        # Fix session_id column length
        conn.execute(text("ALTER TABLE session_pack_plan ALTER COLUMN session_id TYPE VARCHAR(50);"))
        conn.commit()
        print("✅ Successfully updated session_id column to VARCHAR(50)")
        
        # Verify the change
        result = conn.execute(text("""
            SELECT column_name, data_type, character_maximum_length 
            FROM information_schema.columns 
            WHERE table_name = 'session_pack_plan' AND column_name = 'session_id';
        """))
        
        for row in result:
            print(f"📊 Column: {row.column_name}, Type: {row.data_type}, Max Length: {row.character_maximum_length}")
            
except Exception as e:
    print(f"❌ Error updating session_id column: {e}")