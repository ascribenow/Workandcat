#!/usr/bin/env python3
"""
CRITICAL: Add Missing Subcategories from Canonical Taxonomy
Simple script to add the 8 missing subcategories identified in testing
"""

import os
import sys
from dotenv import load_dotenv
import sqlite3

# Load environment
load_dotenv('/app/backend/.env')

# Configuration 
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./twelvr.db")
if DATABASE_URL.startswith("sqlite:///"):
    db_path = DATABASE_URL.replace("sqlite:///", "")
    if not db_path.startswith("/"):
        db_path = f"/app/backend/{db_path}"
else:
    print("❌ This script only works with SQLite databases")
    sys.exit(1)

def add_missing_subcategories():
    """Add the 8 missing subcategories identified in testing"""
    
    print("🎯 ADDING MISSING CANONICAL TAXONOMY SUBCATEGORIES")
    print("=" * 60)
    print(f"Database: {db_path}")
    
    # Missing subcategories identified by testing agent
    missing_subcategories = [
        ("Partnerships", "Arithmetic"),
        ("Maxima and Minima", "Algebra"),
        ("Special Polynomials", "Algebra"),
        ("Mensuration 2D", "Geometry and Mensuration"),
        ("Mensuration 3D", "Geometry and Mensuration"),
        ("Number Properties", "Number System"),
        ("Number Series", "Number System"),
        ("Factorials", "Number System")
    ]
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print(f"📊 Adding {len(missing_subcategories)} missing subcategories...")
        
        added_count = 0
        existing_count = 0
        
        for subcategory, category in missing_subcategories:
            try:
                # Check if subcategory already exists
                cursor.execute("""
                    SELECT COUNT(*) FROM topics 
                    WHERE name = ? AND category = ?
                """, (subcategory, category))
                
                if cursor.fetchone()[0] > 0:
                    existing_count += 1
                    print(f"   ✅ {subcategory} (already exists)")
                    continue
                
                # Add new subcategory
                import uuid
                topic_id = str(uuid.uuid4())
                slug = subcategory.lower().replace(' ', '_').replace('-', '_')
                
                cursor.execute("""
                    INSERT INTO topics (id, section, name, slug, category, centrality)
                    VALUES (?, 'QA', ?, ?, ?, 0.5)
                """, (topic_id, subcategory, slug, category))
                
                added_count += 1
                print(f"   ✅ Added {subcategory} (under {category})")
                
            except Exception as e:
                print(f"   ❌ Failed to add {subcategory}: {e}")
                continue
        
        # Commit changes
        conn.commit()
        conn.close()
        
        # Print results
        print("\n" + "=" * 60)
        print("🎉 SUBCATEGORY UPDATE COMPLETE!")
        print("=" * 60)
        print(f"📊 Results:")
        print(f"   Added: {added_count} subcategories")
        print(f"   Already existed: {existing_count} subcategories")
        print(f"   Total processed: {added_count + existing_count}")
        
        if added_count > 0:
            print("\n🚀 SUCCESS: Missing subcategories have been added!")
            print("   - Question classification now supports all canonical subcategories")
            print("   - LLM enrichment can use the complete taxonomy")
            print("   - Session creation supports full canonical structure")
        else:
            print("\n✅ All subcategories were already present in the database")
            
        return True
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        return False

if __name__ == "__main__":
    success = add_missing_subcategories()
    if success:
        print("\n🎯 Database is now ready for canonical taxonomy operations!")
    else:
        print("\n❌ Failed to update database with missing subcategories")
        sys.exit(1)