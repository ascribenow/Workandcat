#!/usr/bin/env python3
"""
Create Sample PYQ Data for Testing Simplified Frequency System
"""

import asyncio
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from database import init_database, get_async_compatible_db, PYQPaper, PYQQuestion, PYQIngestion
from datetime import datetime

async def create_sample_pyq_data():
    """Create sample PYQ data to test simplified frequency calculation"""
    
    print("🗃️ Creating sample PYQ data for frequency testing...")
    
    # Initialize database
    init_database()
    
    # Sample subcategories with different frequency levels
    pyq_data = {
        # High frequency topics (6+ occurrences)
        "Percentages": 8,
        "Time–Speed–Distance (TSD)": 7,  
        "Simple & Compound Interest (SI–CI)": 6,
        
        # Medium frequency topics (3-5 occurrences)
        "Profit–Loss–Discount (PLD)": 5,
        "Time & Work": 4,
        "Ratio–Proportion–Variation": 3,
        
        # Low frequency topics (1-2 occurrences)
        "Mixtures & Solutions": 2,
        "Averages & Alligation": 1,
        
        # Topics with no PYQ data (will get 'None' frequency band)
        # Linear Equations, Quadratic Equations, etc. will have 0 occurrences
    }
    
    async for db in get_async_compatible_db():
        try:
            # Create sample PYQ papers for different years
            papers_created = 0
            questions_created = 0
            
            for year in range(2020, 2024):  # 2020-2023 papers
                # Create PYQ paper
                paper = PYQPaper(
                    title=f"CAT {year} PYQ Paper",
                    year=year,
                    exam_date=datetime(year, 11, 20),  # November CAT exam
                    source_url=f"https://sample-pyq-{year}.com",
                    is_processed=True,
                    total_questions=len(pyq_data) * 2,  # Approximate
                    metadata=f"Sample PYQ data for year {year}"
                )
                
                db.add(paper)
                await db.flush()  # Get the paper ID
                papers_created += 1
                
                # Create PYQ questions for each subcategory
                question_number = 1
                for subcategory, max_count in pyq_data.items():
                    # Create questions for this subcategory (some years might have more/less)
                    year_specific_count = min(max_count, (year - 2019) * 2)  # Vary by year
                    
                    for i in range(year_specific_count):
                        pyq_question = PYQQuestion(
                            paper_id=paper.id,
                            question_number=question_number,
                            subcategory=subcategory,
                            difficulty_level="Medium",  # Default
                            question_text=f"Sample {subcategory} question {i+1} from CAT {year}",
                            options=f"A) Option 1 B) Option 2 C) Option 3 D) Option 4",
                            correct_answer="A",
                            solution="Sample solution for this question",
                            marks=3,
                            is_active=True,
                            metadata=f"Created for frequency testing - {subcategory}"
                        )
                        
                        db.add(pyq_question)
                        questions_created += 1
                        question_number += 1
                
                print(f"   Created PYQ paper for {year} with questions")
            
            # Create PYQ ingestion record
            ingestion = PYQIngestion(
                filename="sample_pyq_data_creation.py",
                total_papers=papers_created,
                total_questions=questions_created,
                processed_papers=papers_created,
                processed_questions=questions_created,
                failed_papers=0,
                failed_questions=0,
                processing_status="completed",
                ingestion_method="script_generated",
                start_time=datetime.utcnow(),
                end_time=datetime.utcnow(),
                error_summary="",
                success_summary=f"Created {papers_created} papers and {questions_created} questions for frequency testing"
            )
            
            db.add(ingestion)
            
            # Commit all data
            await db.commit()
            
            print(f"✅ Sample PYQ data creation completed:")
            print(f"   - Papers created: {papers_created}")
            print(f"   - Questions created: {questions_created}")
            print(f"   - Frequency distribution will be:")
            
            for subcategory, count in pyq_data.items():
                if count >= 6:
                    band = "High"
                elif count >= 3:
                    band = "Medium"
                elif count >= 1:
                    band = "Low"
                else:
                    band = "None"
                print(f"     {subcategory}: {count} questions → {band} frequency")
            
            break
            
        except Exception as e:
            print(f"❌ Error creating sample PYQ data: {e}")
            import traceback
            traceback.print_exc()

async def test_frequency_calculation():
    """Test the frequency calculation with the new PYQ data"""
    
    print("\n🧮 Testing frequency calculation with sample PYQ data...")
    
    try:
        # Import the simple frequency calculator
        from simple_pyq_frequency import SimplePYQFrequencyCalculator
        
        calculator = SimplePYQFrequencyCalculator()
        
        async for db in get_async_compatible_db():
            # Run frequency calculation
            result = await calculator.calculate_simple_frequencies(db)
            
            if result.get('status') == 'completed':
                print(f"✅ Frequency calculation completed:")
                print(f"   - Questions updated: {result.get('updated_questions', 0)}")
                print(f"   - Distribution: {result.get('frequency_distribution', {})}")
                
                # Get high frequency topics
                high_freq_topics = await calculator.get_high_frequency_topics(db, limit=5)
                
                if high_freq_topics:
                    print(f"\n📈 Top high-frequency topics:")
                    for topic in high_freq_topics:
                        print(f"   - {topic['subcategory']}: {topic['frequency_band']} ({topic['average_pyq_count']:.1f} avg)")
                
            else:
                print(f"❌ Frequency calculation failed: {result.get('error', 'Unknown error')}")
            
            break
            
    except Exception as e:
        print(f"❌ Error testing frequency calculation: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🎯 Sample PYQ Data Creation for Simplified Frequency Testing")
    print("=" * 60)
    
    asyncio.run(create_sample_pyq_data())
    asyncio.run(test_frequency_calculation())
    
    print("\n✅ Sample PYQ data creation and frequency testing completed!")
    print("The simplified PYQ frequency system is now ready for testing.")