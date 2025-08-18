#!/usr/bin/env python3
"""
Script to create canonical taxonomy topics directly in the database
This bypasses the existing topic check and creates all missing topics
"""

import asyncio
import sys
import os
import uuid
from pathlib import Path

# Add backend to path
sys.path.append('/app/backend')

from database import get_async_compatible_db, Topic
from sqlalchemy import select
from llm_enrichment import CANONICAL_TAXONOMY

async def create_canonical_topics():
    """Create all canonical taxonomy topics"""
    
    print("🎯 CREATING CANONICAL TAXONOMY TOPICS")
    print("=" * 60)
    print("This will create all missing parent topics and subcategories")
    print("from the canonical taxonomy structure")
    print("=" * 60)
    
    try:
        async for db in get_async_compatible_db():
            # Get existing topics
            result = await db.execute(select(Topic))
            existing_topics = result.scalars().all()
            existing_names = {topic.name for topic in existing_topics}
            
            print(f"📋 Found {len(existing_topics)} existing topics:")
            for topic in existing_topics:
                print(f"   - {topic.name} (Category: {topic.category}, ID: {topic.id})")
            
            print(f"\n🏗️ CREATING MISSING TOPICS FROM CANONICAL TAXONOMY")
            print("-" * 50)
            
            topics_created = 0
            subcategories_created = 0
            
            # Create main categories and subcategories
            for category, subcategories in CANONICAL_TAXONOMY.items():
                print(f"\n📝 Processing category: {category}")
                
                # Check if main category exists
                main_topic = None
                for topic in existing_topics:
                    if topic.name == category and topic.parent_id is None:
                        main_topic = topic
                        print(f"   ✅ Main category '{category}' already exists")
                        break
                
                if not main_topic:
                    # Create main category
                    main_topic = Topic(
                        id=str(uuid.uuid4()),
                        name=category,
                        slug=category.lower().replace(" ", "_").replace("&", "and"),
                        centrality=0.8,  # Main categories are central
                        section="QA",
                        category={"Arithmetic": "A", "Algebra": "B", "Geometry and Mensuration": "C", "Number System": "D", "Modern Math": "E"}.get(category, "A")
                    )
                    db.add(main_topic)
                    await db.flush()  # Get ID
                    topics_created += 1
                    print(f"   ✅ Created main category: {category}")
                
                # Create subcategories
                for subcategory, details in subcategories.items():
                    # Check if subcategory exists
                    subcategory_exists = False
                    for topic in existing_topics:
                        if topic.name == subcategory and topic.parent_id == main_topic.id:
                            subcategory_exists = True
                            print(f"      ✅ Subcategory '{subcategory}' already exists")
                            break
                    
                    if not subcategory_exists:
                        sub_topic = Topic(
                            id=str(uuid.uuid4()),
                            name=subcategory,
                            parent_id=main_topic.id,
                            slug=subcategory.lower().replace(" ", "_").replace("–", "_").replace("(", "").replace(")", "").replace("-", "_"),
                            centrality=0.6,  # Subcategories are moderately central
                            section="QA",
                            category=main_topic.category
                        )
                        db.add(sub_topic)
                        subcategories_created += 1
                        print(f"      ✅ Created subcategory: {subcategory}")
            
            # Commit all changes
            await db.commit()
            
            print(f"\n📊 CREATION SUMMARY:")
            print(f"   ✅ Main categories created: {topics_created}")
            print(f"   ✅ Subcategories created: {subcategories_created}")
            print(f"   📊 Total new topics: {topics_created + subcategories_created}")
            
            # Verify final state
            result = await db.execute(select(Topic))
            all_topics = result.scalars().all()
            
            print(f"\n🔍 FINAL VERIFICATION:")
            print(f"   📊 Total topics in database: {len(all_topics)}")
            
            # Group by category
            categories = {}
            for topic in all_topics:
                if topic.parent_id is None:  # Main category
                    categories[topic.name] = []
                    
            for topic in all_topics:
                if topic.parent_id is not None:  # Subcategory
                    parent = next((t for t in all_topics if t.id == topic.parent_id), None)
                    if parent:
                        if parent.name not in categories:
                            categories[parent.name] = []
                        categories[parent.name].append(topic.name)
            
            print("\n📋 FINAL TOPIC STRUCTURE:")
            for category, subcategories in categories.items():
                print(f"   📁 {category} ({len(subcategories)} subcategories)")
                for subcat in subcategories:
                    print(f"      - {subcat}")
            
            print(f"\n🎉 CANONICAL TAXONOMY CREATION COMPLETE!")
            print(f"   ✅ All missing topics have been added to the database")
            print(f"   ✅ Question classification should now work properly")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating canonical topics: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function"""
    success = await create_canonical_topics()
    if success:
        print("\n🎯 SUCCESS: Canonical taxonomy topics created!")
        print("   The database now contains all required parent topics and subcategories")
        print("   Question classification system should work properly")
    else:
        print("\n❌ FAILED: Could not create canonical taxonomy topics")
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)