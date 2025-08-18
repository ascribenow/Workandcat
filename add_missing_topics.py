#!/usr/bin/env python3
"""
Script to add missing canonical taxonomy topics to the database
"""

import asyncio
import sys
import os
sys.path.append('/app/backend')

from database import get_async_compatible_db, Topic, Question
from sqlalchemy import select
import uuid

async def add_missing_topics():
    """Add the missing canonical taxonomy topics"""
    
    print("🔄 ADDING MISSING CANONICAL TAXONOMY TOPICS")
    print("=" * 60)
    
    # Get database session
    async for db in get_async_compatible_db():
        try:
            # Check existing topics
            result = await db.execute(select(Topic))
            existing_topics = result.scalars().all()
            
            existing_names = {topic.name for topic in existing_topics}
            print(f"📋 Existing topics: {list(existing_names)}")
            
            # Define missing parent topics needed for canonical taxonomy
            missing_topics = [
                {
                    "name": "Geometry and Mensuration",
                    "slug": "geometry-and-mensuration",
                    "category": "C",
                    "centrality": 0.7
                },
                {
                    "name": "Number System", 
                    "slug": "number-system",
                    "category": "D",
                    "centrality": 0.6
                },
                {
                    "name": "Modern Math",
                    "slug": "modern-math", 
                    "category": "E",
                    "centrality": 0.5
                },
                {
                    "name": "Algebra",
                    "slug": "algebra",
                    "category": "B", 
                    "centrality": 0.8
                }
            ]
            
            # Add missing topics
            added_topics = []
            for topic_data in missing_topics:
                if topic_data["name"] not in existing_names:
                    new_topic = Topic(
                        id=str(uuid.uuid4()),
                        name=topic_data["name"],
                        slug=topic_data["slug"],
                        category=topic_data["category"],
                        centrality=topic_data["centrality"],
                        section="QA"
                    )
                    
                    db.add(new_topic)
                    added_topics.append(topic_data["name"])
                    print(f"✅ Added topic: {topic_data['name']} (Category: {topic_data['category']})")
                else:
                    print(f"⚠️ Topic already exists: {topic_data['name']}")
            
            if added_topics:
                await db.commit()
                print(f"\n🎉 Successfully added {len(added_topics)} topics to database")
                print(f"✅ Added topics: {added_topics}")
            else:
                print("\n✅ All required topics already exist")
            
            # Verify topics were added
            result = await db.execute(select(Topic))
            all_topics = result.scalars().all()
            
            print(f"\n📊 Total topics in database: {len(all_topics)}")
            print("📋 All topics:")
            for topic in all_topics:
                print(f"   - {topic.name} (Category: {topic.category}, ID: {topic.id})")
            
            return True
            
        except Exception as e:
            print(f"❌ Error adding topics: {e}")
            await db.rollback()
            return False
        finally:
            await db.close()
            break

async def main():
    """Main function"""
    success = await add_missing_topics()
    if success:
        print("\n🎯 TOPICS SUCCESSFULLY ADDED - Ready for subcategory creation!")
    else:
        print("\n❌ FAILED TO ADD TOPICS")
    return success

if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)