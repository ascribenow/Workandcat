#!/usr/bin/env python3
"""
Script to add missing questions from CSV to database and run enrichment
"""

import csv
import psycopg2
import os
import uuid
from dotenv import load_dotenv
import requests

def download_csv_from_url(url):
    """Download CSV content from URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return None

def normalize_question(question):
    """Normalize a question stem for comparison"""
    # Remove extra whitespace and normalize
    normalized = ' '.join(question.strip().split())
    # Replace common variations
    normalized = normalized.replace('*', '×')
    normalized = normalized.replace('^', '')
    return normalized

def get_missing_questions():
    """Get the list of questions that are in CSV but not in database"""
    # Load environment
    load_dotenv('backend/.env')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Download CSV from the URL
    csv_url = "https://customer-assets.emergentagent.com/job_unicode-math-adapt/artifacts/igip7y6m_Questions_16Aug25_Fixed.csv"
    print("Downloading CSV file...")
    csv_content = download_csv_from_url(csv_url)
    
    if not csv_content:
        print("Failed to download CSV file")
        return []
    
    # Parse CSV content
    csv_lines = csv_content.strip().split('\n')
    csv_reader = csv.reader(csv_lines)
    
    # Skip header and get all CSV questions
    next(csv_reader)  # Skip header
    csv_questions = []
    csv_lines_reset = csv_content.strip().split('\n')
    csv_reader_reset = csv.reader(csv_lines_reset)
    next(csv_reader_reset)  # Skip header
    
    for row in csv_reader_reset:
        if len(row) >= 1 and row[0].strip():
            stem = row[0].strip()
            image_url = row[1].strip() if len(row) > 1 else ""
            csv_questions.append((stem, image_url))
    
    print(f"CSV file contains {len(csv_questions)} questions")
    
    # Get database questions
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        cur.execute('SELECT stem FROM questions')
        db_questions = [normalize_question(row[0]) for row in cur.fetchall()]
        
        print(f"Database contains {len(db_questions)} questions")
        
        conn.close()
        
    except Exception as e:
        print(f"Database error: {e}")
        return []
    
    # Find missing questions (original CSV versions)
    db_set = set(db_questions)
    missing_questions = []
    
    for original_stem, image_url in csv_questions:
        normalized_stem = normalize_question(original_stem)
        if normalized_stem not in db_set:
            missing_questions.append((original_stem, image_url))
    
    print(f"Found {len(missing_questions)} missing questions")
    return missing_questions

def add_questions_to_database(missing_questions):
    """Add missing questions to database"""
    if not missing_questions:
        print("No missing questions to add")
        return []
    
    # Load environment
    load_dotenv('backend/.env')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        added_question_ids = []
        topic_id = "833c1d1f-da8c-4674-9a41-5777808880d4"  # Use the same topic_id as existing questions
        
        for i, (stem, image_url) in enumerate(missing_questions):
            question_id = str(uuid.uuid4())
            
            # Prepare data
            has_image = bool(image_url and image_url.strip())
            image_url_clean = image_url.strip() if image_url else None
            
            # Insert question with minimal required fields
            insert_query = """
            INSERT INTO questions (
                id, topic_id, stem, has_image, image_url, 
                subcategory, type_of_question, answer, solution_approach, detailed_solution,
                difficulty_score, difficulty_band, frequency_band, learning_impact, 
                learning_impact_band, importance_index, importance_band, frequency_score,
                is_active, created_at, version, source
            ) VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, NOW(), %s, %s
            )
            """
            
            values = (
                question_id, topic_id, stem, has_image, image_url_clean,
                'To Be Classified', 'To Be Classified', 'To Be Enriched', 'To Be Enriched', 'To Be Enriched',  # Will be enriched later
                5.0, 'Medium', 'Medium', 5.0,
                'Medium', 5.0, 'Medium', 5.0,
                True, 1, 'CSV Import - Missing Questions'
            )
            
            cur.execute(insert_query, values)
            added_question_ids.append(question_id)
            print(f"Added question {i+1}/{len(missing_questions)}: {stem[:60]}...")
        
        conn.commit()
        conn.close()
        
        print(f"Successfully added {len(added_question_ids)} questions to database")
        return added_question_ids
        
    except Exception as e:
        print(f"Database error adding questions: {e}")
        if conn:
            conn.rollback()
            conn.close()
        return []

def main():
    print("=== Adding Missing Questions from CSV ===")
    
    # Step 1: Get missing questions
    missing_questions = get_missing_questions()
    
    if not missing_questions:
        print("No missing questions found!")
        return
    
    print(f"\nFound {len(missing_questions)} missing questions:")
    for i, (stem, image_url) in enumerate(missing_questions[:5], 1):
        print(f"{i}. {stem[:80]}...")
        if image_url:
            print(f"   Image: {image_url}")
    
    if len(missing_questions) > 5:
        print(f"... and {len(missing_questions) - 5} more")
    
    # Step 2: Add questions to database
    print(f"\nAdding {len(missing_questions)} questions to database...")
    added_ids = add_questions_to_database(missing_questions)
    
    if added_ids:
        print(f"\n✅ Successfully added {len(added_ids)} questions to database!")
        print("These questions will need LLM enrichment to add answers, solutions, and classifications.")
        print("Question IDs:", added_ids[:3], "..." if len(added_ids) > 3 else "")
        
        # Check total count
        load_dotenv('backend/.env')
        DATABASE_URL = os.getenv('DATABASE_URL')
        
        try:
            conn = psycopg2.connect(DATABASE_URL)
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM questions')
            total_count = cur.fetchone()[0]
            conn.close()
            print(f"Total questions in database now: {total_count}")
        except Exception as e:
            print(f"Error getting final count: {e}")
    else:
        print("❌ Failed to add questions to database")

if __name__ == "__main__":
    main()