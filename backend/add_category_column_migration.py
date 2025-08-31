#!/usr/bin/env python3
"""
Database Migration: Add category column to questions table
This migration adds the missing 'category' column needed for proper LLM enrichment and session logic
"""

import os
import asyncio
import logging
from sqlalchemy import text
from database import get_async_compatible_db

logger = logging.getLogger(__name__)

async def add_category_column_migration():
    """
    Add category column to questions table and populate from existing subcategory data
    """
    try:
        logger.info("🔧 Starting category column migration...")
        
        # Get database connection using the existing pattern
        from database import SessionLocal
        
        db = SessionLocal()
        try:
            # Step 1: Add category column
            logger.info("📝 Adding category column to questions table...")
            
            add_column_sql = text("""
                ALTER TABLE questions 
                ADD COLUMN IF NOT EXISTS category VARCHAR(100)
            """)
            
            db.execute(add_column_sql)
            db.commit()
            
            logger.info("✅ Category column added successfully")
            
            # Step 2: Populate category column based on subcategory mapping
            logger.info("📊 Populating category column with intelligent mapping...")
            
            # Subcategory to Category mapping based on CANONICAL_TAXONOMY
            subcategory_to_category_mapping = {
                # Arithmetic
                "Time-Speed-Distance": "Arithmetic",
                "Time–Speed–Distance (TSD)": "Arithmetic", 
                "Time-Work": "Arithmetic",
                "Time & Work": "Arithmetic",
                "Ratios and Proportions": "Arithmetic", 
                "Ratio–Proportion–Variation": "Arithmetic",
                "Percentages": "Arithmetic",
                "Averages and Alligation": "Arithmetic",
                "Averages & Alligation": "Arithmetic", 
                "Profit-Loss-Discount": "Arithmetic",
                "Profit–Loss–Discount (PLD)": "Arithmetic",
                "Simple and Compound Interest": "Arithmetic",
                "Simple & Compound Interest (SI–CI)": "Arithmetic",
                "Mixtures and Solutions": "Arithmetic",
                "Partnerships": "Arithmetic",
                
                # Algebra
                "Linear Equations": "Algebra", 
                "Quadratic Equations": "Algebra",
                "Inequalities": "Algebra",
                "Progressions": "Algebra",
                "Functions and Graphs": "Algebra",
                "Logarithms and Exponents": "Algebra",
                "Special Algebraic Identities": "Algebra",
                "Maxima and Minima": "Algebra",
                "Special Polynomials": "Algebra",
                
                # Geometry and Mensuration
                "Triangles": "Geometry and Mensuration",
                "Circles": "Geometry and Mensuration", 
                "Polygons": "Geometry and Mensuration",
                "Coordinate Geometry": "Geometry and Mensuration",
                "Mensuration 2D": "Geometry and Mensuration",
                "Mensuration 3D": "Geometry and Mensuration", 
                "Trigonometry": "Geometry and Mensuration",
                
                # Number System
                "Divisibility": "Number System",
                "HCF-LCM": "Number System",
                "Remainders": "Number System", 
                "Base Systems": "Number System",
                "Digit Properties": "Number System",
                "Number Properties": "Number System",
                "Number Series": "Number System",
                "Factorials": "Number System",
                
                # Modern Math
                "Permutation-Combination": "Modern Math",
                "Probability": "Modern Math",
                "Set Theory and Venn Diagram": "Modern Math"
            }
            
            # Update questions with category mapping
            update_count = 0
            for subcategory, category in subcategory_to_category_mapping.items():
                update_sql = text("""
                UPDATE questions 
                SET category = :category 
                WHERE (subcategory = :subcategory OR subcategory LIKE :subcategory_like) 
                AND category IS NULL
                """)
                
                result = await db.execute(update_sql, {
                    "category": category,
                    "subcategory": subcategory,
                    "subcategory_like": f"%{subcategory}%"
                })
                
                updated_rows = result.rowcount
                update_count += updated_rows
                
                if updated_rows > 0:
                    logger.info(f"   📝 Updated {updated_rows} questions: {subcategory} → {category}")
            
            # Handle any remaining unmapped questions with intelligent fallback
            fallback_sql = text("""
            UPDATE questions 
            SET category = 'Arithmetic' 
            WHERE category IS NULL
            """)
            
            fallback_result = await db.execute(fallback_sql)
            fallback_count = fallback_result.rowcount
            
            if fallback_count > 0:
                logger.info(f"   📝 Set {fallback_count} unmapped questions to 'Arithmetic' (fallback)")
                update_count += fallback_count
            
            await db.commit()
            
            # Step 3: Verify results
            verification_sql = text("SELECT category, COUNT(*) as count FROM questions GROUP BY category ORDER BY count DESC")
            verification_result = await db.execute(verification_sql)
            category_rows = verification_result.fetchall()
            
            logger.info("📊 Category distribution after migration:")
            for row in category_rows:
                logger.info(f"   {row.category}: {row.count} questions")
            
            logger.info(f"✅ Migration completed successfully!")
            logger.info(f"📈 Total questions updated: {update_count}")
            
            return {
                "success": True,
                "total_updated": update_count,
                "message": "Category column migration completed successfully"
            }
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "Category column migration failed"
        }

async def main():
    """Run the migration"""
    result = await add_category_column_migration()
    
    if result["success"]:
        print("✅ Migration completed successfully!")
        print(f"📈 Total questions updated: {result['total_updated']}")
    else:
        print("❌ Migration failed!")
        print(f"Error: {result['error']}")

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run migration
    asyncio.run(main())