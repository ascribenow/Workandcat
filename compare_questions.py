#!/usr/bin/env python3
"""
Script to compare CSV questions with database questions and identify missing ones
"""

import csv
import psycopg2
import os
from dotenv import load_dotenv
import requests

def normalize_question(question):
    """Normalize a question stem for comparison"""
    # Remove extra whitespace and normalize
    normalized = ' '.join(question.strip().split())
    # Replace common variations
    normalized = normalized.replace('*', '×')
    normalized = normalized.replace('^', '')
    return normalized

def download_csv_from_url(url):
    """Download CSV content from URL"""
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"Error downloading CSV: {e}")
        return None

def main():
    # Load environment
    load_dotenv('backend/.env')
    DATABASE_URL = os.getenv('DATABASE_URL')
    
    # Download CSV from the URL
    csv_url = "https://customer-assets.emergentagent.com/job_unicode-math-adapt/artifacts/igip7y6m_Questions_16Aug25_Fixed.csv"
    print("Downloading CSV file...")
    csv_content = download_csv_from_url(csv_url)
    
    if not csv_content:
        print("Failed to download CSV file")
        return
    
    # Parse CSV content
    csv_lines = csv_content.strip().split('\n')
    csv_reader = csv.reader(csv_lines)
    
    # Skip header and get all CSV questions
    next(csv_reader)  # Skip header
    csv_questions = []
    for row in csv_reader:
        if len(row) >= 1 and row[0].strip():
            csv_questions.append(normalize_question(row[0]))
    
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
        return
    
    # Find missing questions
    csv_set = set(csv_questions)
    db_set = set(db_questions)
    
    missing_questions = csv_set - db_set
    extra_questions = db_set - csv_set
    
    print(f"\nComparison Results:")
    print(f"Questions in CSV: {len(csv_questions)}")
    print(f"Questions in Database: {len(db_questions)}")
    print(f"Missing from Database: {len(missing_questions)}")
    print(f"Extra in Database (not in CSV): {len(extra_questions)}")
    
    if missing_questions:
        print(f"\nMissing questions from database:")
        for i, q in enumerate(sorted(missing_questions), 1):
            print(f"{i}. {q[:100]}...")
    
    if extra_questions:
        print(f"\nExtra questions in database (not in CSV):")
        for i, q in enumerate(sorted(extra_questions), 1):
            print(f"{i}. {q[:100]}...")
    
    # Save missing questions to a file
    if missing_questions:
        with open('/tmp/missing_questions.txt', 'w') as f:
            for q in sorted(missing_questions):
                f.write(q + '\n')
        print(f"\nMissing questions saved to /tmp/missing_questions.txt")
    
    # Find original questions from CSV that are missing
    original_missing = []
    for i, original_q in enumerate(csv_questions):
        if original_q in missing_questions:
            # Find the original question from CSV
            csv_lines = csv_content.strip().split('\n')
            csv_reader = csv.reader(csv_lines)
            next(csv_reader)  # Skip header
            for j, row in enumerate(csv_reader):
                if j == i and len(row) >= 1:
                    original_missing.append((row[0], row[1] if len(row) > 1 else ""))
                    break
    
    if original_missing:
        print(f"\nOriginal missing questions (with image URLs):")
        for i, (stem, image_url) in enumerate(original_missing, 1):
            print(f"{i}. Stem: {stem[:80]}...")
            if image_url:
                print(f"   Image: {image_url}")
        
        # Save to CSV for import
        with open('/tmp/missing_questions.csv', 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['stem', 'image_url'])
            for stem, image_url in original_missing:
                writer.writerow([stem, image_url])
        print(f"\nMissing questions saved to /tmp/missing_questions.csv for import")

if __name__ == "__main__":
    main()