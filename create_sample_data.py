#!/usr/bin/env python3

import asyncio
import requests
import json

BACKEND_URL = "http://localhost:8001/api"

sample_questions = [
    {
        "text": "A train travels at 60 km/h and covers a distance of 240 km. How much time does it take?",
        "options": ["3 hours", "4 hours", "5 hours", "6 hours"],
        "correct_answer": "4 hours",
        "explanation": "Time = Distance / Speed = 240 / 60 = 4 hours",
        "category": "Arithmetic",
        "sub_category": "Time–Speed–Distance (TSD)",
        "year": 2023
    },
    {
        "text": "If 20% of a number is 80, what is 25% of that number?",
        "options": ["90", "100", "110", "120"],
        "correct_answer": "100",
        "explanation": "If 20% = 80, then 100% = 400. So 25% of 400 = 100",
        "category": "Arithmetic",
        "sub_category": "Percentages",
        "year": 2023
    },
    {
        "text": "Solve for x: 2x + 5 = 13",
        "options": ["2", "3", "4", "5"],
        "correct_answer": "4",
        "explanation": "2x = 13 - 5 = 8, so x = 4",
        "category": "Algebra",
        "sub_category": "Linear Equations",
        "year": 2023
    },
    {
        "text": "Find the area of a triangle with base 10 cm and height 8 cm.",
        "options": ["30 cm²", "40 cm²", "50 cm²", "80 cm²"],
        "correct_answer": "40 cm²",
        "explanation": "Area = (1/2) × base × height = (1/2) × 10 × 8 = 40 cm²",
        "category": "Geometry & Mensuration",
        "sub_category": "Triangles",
        "year": 2023
    },
    {
        "text": "What is the HCF of 24 and 36?",
        "options": ["6", "8", "12", "18"],
        "correct_answer": "12",
        "explanation": "Factors of 24: 1, 2, 3, 4, 6, 8, 12, 24. Factors of 36: 1, 2, 3, 4, 6, 9, 12, 18, 36. HCF = 12",
        "category": "Number System",
        "sub_category": "HCF–LCM",
        "year": 2023
    },
    {
        "text": "In how many ways can 5 people be arranged in a row?",
        "options": ["60", "120", "240", "480"],
        "correct_answer": "120",
        "explanation": "5! = 5 × 4 × 3 × 2 × 1 = 120",
        "category": "Modern Math",
        "sub_category": "Permutation–Combination (P&C)",
        "year": 2023
    },
    {
        "text": "A man can complete a job in 12 days. A woman can complete the same job in 18 days. How long will it take if they work together?",
        "options": ["6.5 days", "7.2 days", "8.4 days", "9.6 days"],
        "correct_answer": "7.2 days",
        "explanation": "Combined rate = 1/12 + 1/18 = 3/36 + 2/36 = 5/36 jobs per day. Time = 36/5 = 7.2 days",
        "category": "Arithmetic",
        "sub_category": "Time & Work",
        "year": 2023
    },
    {
        "text": "If x² - 7x + 12 = 0, find the sum of the roots.",
        "options": ["5", "6", "7", "12"],
        "correct_answer": "7",
        "explanation": "For ax² + bx + c = 0, sum of roots = -b/a = -(-7)/1 = 7",
        "category": "Algebra",
        "sub_category": "Quadratic Equations",
        "year": 2023
    },
    {
        "text": "The probability of getting a head when a coin is tossed is:",
        "options": ["0.25", "0.5", "0.75", "1"],
        "correct_answer": "0.5",
        "explanation": "A coin has 2 equally likely outcomes: Head or Tail. P(Head) = 1/2 = 0.5",
        "category": "Modern Math",
        "sub_category": "Probability",
        "year": 2023
    },
    {
        "text": "Simple Interest on ₹1000 at 10% per annum for 2 years is:",
        "options": ["₹100", "₹150", "₹200", "₹250"],
        "correct_answer": "₹200",
        "explanation": "SI = (P × R × T) / 100 = (1000 × 10 × 2) / 100 = ₹200",
        "category": "Arithmetic",
        "sub_category": "Simple & Compound Interest (SI–CI)",
        "year": 2023
    }
]

def create_questions():
    """Create sample questions in the database"""
    for question in sample_questions:
        try:
            response = requests.post(f"{BACKEND_URL}/questions", json=question)
            if response.status_code == 200:
                print(f"✓ Created question: {question['text'][:50]}...")
            else:
                print(f"✗ Failed to create question: {response.status_code}")
                print(response.text)
        except Exception as e:
            print(f"Error creating question: {e}")

def create_admin_user():
    """Create an admin user"""
    admin_data = {
        "email": "admin@catprep.com",
        "name": "Admin User",
        "password": "admin123",
        "is_admin": True
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/register", json=admin_data)
        if response.status_code == 200:
            print("✓ Created admin user: admin@catprep.com / admin123")
        else:
            print(f"✗ Failed to create admin user: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error creating admin user: {e}")

def create_student_user():
    """Create a student user"""
    student_data = {
        "email": "student@catprep.com",
        "name": "Test Student",
        "password": "student123",
        "is_admin": False
    }
    
    try:
        response = requests.post(f"{BACKEND_URL}/register", json=student_data)
        if response.status_code == 200:
            print("✓ Created student user: student@catprep.com / student123")
        else:
            print(f"✗ Failed to create student user: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"Error creating student user: {e}")

if __name__ == "__main__":
    print("Creating sample data for CAT Preparation App...")
    print("=" * 50)
    
    # Create users
    create_admin_user()
    create_student_user()
    
    print("\nCreating sample questions...")
    create_questions()
    
    print("\n" + "=" * 50)
    print("Sample data creation completed!")
    print("\nLogin credentials:")
    print("Admin: admin@catprep.com / admin123")
    print("Student: student@catprep.com / student123")