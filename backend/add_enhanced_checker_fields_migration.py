#!/usr/bin/env python3
"""
Add Enhanced Checker Fields Migration
Adds the missing advanced LLM enrichment fields to the questions table for Enhanced Checker compatibility
"""

import os
from sqlalchemy import create_engine, text, inspect

def run_enhanced_checker_fields_migration():
    """Add missing fields for Enhanced Enrichment Checker System"""
    
    # Database connection
    database_url = 'postgresql://postgres.itgusggwslnsbgonyicv:%24Sumedh_123@aws-1-ap-south-1.pooler.supabase.com:6543/postgres'
    engine = create_engine(database_url)
    inspector = inspect(engine)
    
    print("🔍 ENHANCED CHECKER FIELDS MIGRATION")
    print("=" * 50)
    print("Adding missing advanced LLM enrichment fields to questions table")
    
    try:
        with engine.begin() as conn:
            # Get current columns
            current_columns = [col['name'] for col in inspector.get_columns('questions')]
            print(f"📊 Current questions table has {len(current_columns)} columns")
            
            # Fields needed for Enhanced Checker
            new_fields = [
                ('quality_verified', 'BOOLEAN DEFAULT FALSE'),
                ('core_concepts', 'TEXT'),
                ('solution_method', 'VARCHAR(200)'),
                ('concept_difficulty', 'TEXT'),
                ('operations_required', 'TEXT'),
                ('problem_structure', 'VARCHAR(100)'),
                ('concept_keywords', 'TEXT')
            ]
            
            added_fields = []
            
            for field_name, field_type in new_fields:
                if field_name not in current_columns:
                    print(f"➕ Adding field: {field_name} ({field_type})")
                    
                    alter_sql = f"ALTER TABLE questions ADD COLUMN {field_name} {field_type}"
                    conn.execute(text(alter_sql))
                    added_fields.append(field_name)
                    
                    print(f"   ✅ {field_name} added successfully")
                else:
                    print(f"   ⏭️ {field_name} already exists, skipping")
            
            if added_fields:
                print(f"\n🎉 MIGRATION COMPLETED SUCCESSFULLY")
                print(f"   ✅ Added {len(added_fields)} new fields: {', '.join(added_fields)}")
                print(f"   📊 questions table now ready for Enhanced Checker System")
                
                # Update existing questions to have quality_verified=False by default
                if 'quality_verified' in added_fields:
                    print(f"   🔄 Setting quality_verified=FALSE for existing questions...")
                    conn.execute(text("UPDATE questions SET quality_verified = FALSE WHERE quality_verified IS NULL"))
                    print(f"   ✅ Existing questions updated for Enhanced Checker compatibility")
            else:
                print(f"\n✅ ALL FIELDS ALREADY EXIST")
                print(f"   📊 questions table is already ready for Enhanced Checker System")
            
    except Exception as e:
        print(f"❌ MIGRATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print(f"\n🚀 ENHANCED CHECKER MIGRATION COMPLETED")
    print(f"   Ready for 100% compliance validation!")
    return True

if __name__ == "__main__":
    success = run_enhanced_checker_fields_migration()
    if not success:
        exit(1)