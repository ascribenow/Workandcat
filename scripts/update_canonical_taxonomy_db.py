#!/usr/bin/env python3
"""
CRITICAL DATABASE UPDATE: Add New Canonical Taxonomy Subcategories
Updates the database to include all subcategories from the new canonical taxonomy CSV
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Add backend to path
sys.path.append('/app/backend')

from sqlalchemy import create_engine, text, select
from database import get_async_compatible_db, Topic

load_dotenv()

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL")

class CanonicalTaxonomyUpdater:
    def __init__(self):
        self.engine = create_engine(DATABASE_URL)
        self.stats = {
            'categories_created': 0,
            'subcategories_created': 0,
            'existing_categories': 0,
            'existing_subcategories': 0
        }

    # Complete canonical taxonomy from CSV document
    canonical_taxonomy = {
        "Arithmetic": [
            "Time-Speed-Distance", "Time-Work", "Ratios and Proportions", 
            "Percentages", "Averages and Alligation", "Profit-Loss-Discount",
            "Simple and Compound Interest", "Mixtures and Solutions", "Partnerships"
        ],
        "Algebra": [
            "Linear Equations", "Quadratic Equations", "Inequalities", "Progressions",
            "Functions and Graphs", "Logarithms and Exponents", "Special Algebraic Identities",
            "Maxima and Minima", "Special Polynomials"
        ],
        "Geometry and Mensuration": [
            "Triangles", "Circles", "Polygons", "Coordinate Geometry",
            "Mensuration 2D", "Mensuration 3D", "Trigonometry"
        ],
        "Number System": [
            "Divisibility", "HCF-LCM", "Remainders", "Base Systems",
            "Digit Properties", "Number Properties", "Number Series", "Factorials"
        ],
        "Modern Math": [
            "Permutation-Combination", "Probability", "Set Theory and Venn Diagram"
        ]
    }

    async def update_database_taxonomy(self):
        """Update database with complete canonical taxonomy"""
        print("🎯 CANONICAL TAXONOMY DATABASE UPDATE")
        print("=" * 60)
        print("Adding all categories and subcategories from CSV canonical taxonomy")
        print("=" * 60)
        
        try:
            async for db_session in get_async_compatible_db():
                # Update categories and subcategories
                for category_name, subcategories in self.canonical_taxonomy.items():
                    await self.ensure_category_exists(db_session, category_name)
                    
                    for subcategory_name in subcategories:
                        await self.ensure_subcategory_exists(db_session, category_name, subcategory_name)
                
                await db_session.commit()
                break  # Only process first session
            
            # Print final statistics
            print("\n" + "=" * 60)
            print("🎉 CANONICAL TAXONOMY UPDATE COMPLETE!")
            print("=" * 60)
            print(f"📊 Statistics:")
            print(f"   Categories created: {self.stats['categories_created']}")
            print(f"   Categories already existed: {self.stats['existing_categories']}")
            print(f"   Subcategories created: {self.stats['subcategories_created']}")
            print(f"   Subcategories already existed: {self.stats['existing_subcategories']}")
            
            total_categories = self.stats['categories_created'] + self.stats['existing_categories']
            total_subcategories = self.stats['subcategories_created'] + self.stats['existing_subcategories']
            
            print(f"\n📋 Database Now Contains:")
            print(f"   Total Categories: {total_categories}")
            print(f"   Total Subcategories: {total_subcategories}")
            
            if self.stats['categories_created'] > 0 or self.stats['subcategories_created'] > 0:
                print("\n🚀 SUCCESS: Database updated with canonical taxonomy!")
                print("   - Question classification will now work with all subcategories")
                print("   - LLM enrichment can use the complete taxonomy structure")
                print("   - Session creation supports all canonical categories")
            else:
                print("\n✅ Database was already up-to-date with canonical taxonomy")
            
        except Exception as e:
            print(f"❌ Critical error in taxonomy update: {e}")
            raise

    async def ensure_category_exists(self, db_session, category_name):
        """Ensure category exists in database as a parent Topic"""
        try:
            # Check if category exists as a parent topic
            result = await db_session.execute(
                select(Topic).where(Topic.name == category_name, Topic.parent_id.is_(None))
            )
            category = result.scalar_one_or_none()
            
            if not category:
                # Create new category as parent topic
                import uuid
                new_category = Topic(
                    name=category_name,
                    slug=category_name.lower().replace(' ', '_').replace('&', 'and'),
                    category=category_name,
                    parent_id=None
                )
                db_session.add(new_category)
                await db_session.flush()  # Get the ID
                
                print(f"   ✅ Created category: {category_name}")
                self.stats['categories_created'] += 1
            else:
                self.stats['existing_categories'] += 1
            
        except Exception as e:
            print(f"   ❌ Error creating category {category_name}: {e}")
            raise

    async def ensure_subcategory_exists(self, db_session, category_name, subcategory_name):
        """Ensure subcategory (Topic) exists in database"""
        try:
            # Get category (parent topic)
            result = await db_session.execute(
                select(Topic).where(Topic.name == category_name, Topic.parent_id.is_(None))
            )
            category = result.scalar_one_or_none()
            
            if not category:
                print(f"   ❌ Category {category_name} not found for subcategory {subcategory_name}")
                return
            
            # Check if subcategory exists
            result = await db_session.execute(
                select(Topic).where(
                    Topic.name == subcategory_name,
                    Topic.parent_id == category.id
                )
            )
            topic = result.scalar_one_or_none()
            
            if not topic:
                # Create new subcategory (Topic)
                import uuid
                new_topic = Topic(
                    name=subcategory_name,
                    slug=subcategory_name.lower().replace(' ', '_').replace('-', '_'),
                    category=category_name,
                    parent_id=category.id
                )
                db_session.add(new_topic)
                await db_session.flush()
                
                print(f"   ✅ Created subcategory: {subcategory_name} (under {category_name})")
                self.stats['subcategories_created'] += 1
            else:
                self.stats['existing_subcategories'] += 1
            
        except Exception as e:
            print(f"   ❌ Error creating subcategory {subcategory_name}: {e}")
            raise

async def main():
    """Main execution function"""
    updater = CanonicalTaxonomyUpdater()
    await updater.update_database_taxonomy()

if __name__ == "__main__":
    asyncio.run(main())