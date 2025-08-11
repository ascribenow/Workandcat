#!/usr/bin/env python3
"""
Check and fix diagnostic system issues
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database import get_database, Question, Topic, DiagnosticSet, DiagnosticSetQuestion
from sqlalchemy import select, func
from diagnostic_system import DiagnosticSystem

async def main():
    print("🔍 Checking diagnostic system...")
    
    async for db in get_database():
        # Check total questions
        total_questions = await db.scalar(select(func.count(Question.id)))
        print(f"📊 Total questions in database: {total_questions}")
        
        if total_questions == 0:
            print("❌ No questions found! Need to populate database first.")
            break
        
        # Check difficulty distribution
        diff_result = await db.execute(
            select(Question.difficulty_band, func.count(Question.id))
            .group_by(Question.difficulty_band)
        )
        print("📈 Questions by difficulty:")
        for diff, count in diff_result.fetchall():
            print(f"   {diff or 'None'}: {count}")
        
        # Check subcategory distribution
        subcat_result = await db.execute(
            select(Question.subcategory, func.count(Question.id))
            .group_by(Question.subcategory)
            .limit(10)
        )
        print("📂 Top subcategories:")
        for subcat, count in subcat_result.fetchall():
            print(f"   {subcat}: {count}")
        
        # Check diagnostic set
        diag_set_result = await db.execute(select(DiagnosticSet))
        diag_set = diag_set_result.scalar_one_or_none()
        
        if diag_set:
            # Count questions in diagnostic set
            diag_questions = await db.scalar(
                select(func.count(DiagnosticSetQuestion.id))
                .where(DiagnosticSetQuestion.set_id == diag_set.id)
            )
            print(f"🎯 Diagnostic set questions: {diag_questions}")
            
            if diag_questions == 0:
                print("⚠️ Diagnostic set exists but has no questions!")
                print("🔧 Attempting to recreate diagnostic set...")
                
                # Delete empty diagnostic set
                await db.delete(diag_set)
                await db.commit()
                
                # Recreate with questions
                diagnostic_system = DiagnosticSystem()
                new_set = await diagnostic_system.create_diagnostic_set(db)
                
                if new_set:
                    new_count = await db.scalar(
                        select(func.count(DiagnosticSetQuestion.id))
                        .where(DiagnosticSetQuestion.set_id == new_set.id)
                    )
                    print(f"✅ New diagnostic set created with {new_count} questions")
                else:
                    print("❌ Failed to create new diagnostic set")
            else:
                print(f"✅ Diagnostic set has {diag_questions} questions")
        else:
            print("❌ No diagnostic set found!")
            print("🔧 Creating diagnostic set...")
            diagnostic_system = DiagnosticSystem()
            new_set = await diagnostic_system.create_diagnostic_set(db)
            if new_set:
                print("✅ Diagnostic set created")
            else:
                print("❌ Failed to create diagnostic set")
        
        break

if __name__ == "__main__":
    asyncio.run(main())