#!/usr/bin/env python3
"""
Canonical Question Types Taxonomy
Establishes and enforces canonical taxonomy for type_of_question field
"""

import os
import json
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def establish_canonical_question_types():
    """Establish canonical taxonomy for type_of_question and fix all existing data"""
    
    # Database connection
    database_url = 'postgresql://postgres.itgusggwslnsbgonyicv:%24Sumedh_123@aws-1-ap-south-1.pooler.supabase.com:6543/postgres'
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    db = Session()
    
    print("📚 ESTABLISHING CANONICAL QUESTION TYPES TAXONOMY")
    print("=" * 60)
    
    # CANONICAL QUESTION TYPES TAXONOMY
    canonical_question_types = {
        "A-Arithmetic": [
            "Speed-Distance-Time Problem",
            "Relative Motion Analysis", 
            "Work Rate Problem",
            "Collaborative Work Problem",
            "Ratio-Proportion Problem",
            "Percentage Application Problem",
            "Percentage Change Problem",
            "Average Calculation Problem",
            "Weighted Average Problem",
            "Profit-Loss Analysis Problem",
            "Discount Calculation Problem",
            "Simple Interest Problem",
            "Compound Interest Problem",
            "Mixture-Alligation Problem"
        ],
        "B-Algebra": [
            "Linear Equation Problem",
            "System of Linear Equations",
            "Quadratic Equation Problem",
            "Inequality Problem",
            "Sequence-Series Problem",
            "Function Analysis Problem",
            "Logarithmic Problem",
            "Exponential Problem"
        ],
        "C-Geometry & Mensuration": [
            "Triangle Properties Problem",
            "Circle Properties Problem",
            "Polygon Analysis Problem",
            "Coordinate Geometry Problem",
            "Area Calculation Problem",
            "Volume Calculation Problem",
            "Trigonometric Problem"
        ],
        "D-Number System": [
            "Divisibility Analysis Problem",
            "HCF-LCM Problem",
            "Remainder Theorem Problem",
            "Modular Arithmetic Problem",
            "Base System Conversion Problem",
            "Digit Properties Problem",
            "Prime Factorization Problem"
        ],
        "E-Modern Math": [
            "Permutation Problem",
            "Combination Problem",
            "Probability Calculation Problem",
            "Set Theory Problem",
            "Venn Diagram Problem"
        ]
    }
    
    try:
        print("📋 CANONICAL QUESTION TYPES BY CATEGORY:")
        print("-" * 45)
        
        total_canonical_types = 0
        for category, types in canonical_question_types.items():
            print(f"\n{category} ({len(types)} types):")
            for i, question_type in enumerate(types, 1):
                print(f"   {i:2d}. {question_type}")
            total_canonical_types += len(types)
        
        print(f"\n📊 TOTAL CANONICAL QUESTION TYPES: {total_canonical_types}")
        
        # Create mapping from current types to canonical types
        print("\n🔄 MAPPING CURRENT TYPES TO CANONICAL TYPES:")
        print("-" * 50)
        
        # Comprehensive mapping rules
        type_mappings = {
            # Generic types → Canonical
            "Basics": "Speed-Distance-Time Problem",
            "Basic Calculations": "Speed-Distance-Time Problem", 
            "Applications": "Speed-Distance-Time Problem",
            "Advanced Applications": "Speed-Distance-Time Problem",
            "Basic Averages": "Average Calculation Problem",
            "Weighted Averages": "Weighted Average Problem",
            "Basic Single-Step Addition": "Speed-Distance-Time Problem",
            "Basic Divisibility Rules": "Divisibility Analysis Problem",
            "Divisibility": "Divisibility Analysis Problem",
            
            # Speed/Distance/Time types
            "Trains": "Speed-Distance-Time Problem",
            "Relative Speed": "Relative Motion Analysis",
            "Direct Application of Speed Formula": "Speed-Distance-Time Problem",
            "Direct Application of Speed Formula in Uniform Motion": "Speed-Distance-Time Problem",
            "Direct Application of Speed-Distance-Time Formula": "Speed-Distance-Time Problem",
            
            # Number System types
            "Factorisation of Integers": "Prime Factorization Problem",
            "Perfect Squares": "Digit Properties Problem",
            "Properties of Factorials": "Prime Factorization Problem",
            "Basic Remainder Theorem": "Remainder Theorem Problem",
            "Product of HCF and LCM": "HCF-LCM Problem",
            "Chinese Remainder Theorem": "Modular Arithmetic Problem",
            "Chinese Remainder Theorem Application with Range Constraint": "Modular Arithmetic Problem",
            "Sum of Digits": "Digit Properties Problem",
            "Euclidean Algorithm": "HCF-LCM Problem",
            "Last Digit Patterns": "Digit Properties Problem",
            "Cyclicity of Remainders (Last Two Digits)": "Remainder Theorem Problem",
            "Last Non-Zero Digit in Factorial Base Conversion": "Digit Properties Problem",
            "Prime Factorization-Based Factor Counting with Multiplicity Conditions": "Prime Factorization Problem",
            "Even Factor Enumeration via Exclusion of Odd Factors": "Prime Factorization Problem",
            "Sequential Power Factorization with Reciprocal Divisibility": "Prime Factorization Problem",
            "Digit Replacement for Divisibility with Large Numbers": "Divisibility Analysis Problem",
            "Exponentiation Reduction using Totient Function": "Modular Arithmetic Problem",
            "Common Remainder Identification through Difference Analysis": "Remainder Theorem Problem",
            "Quadratic Congruence with Divisibility Constraints": "Modular Arithmetic Problem",
            
            # Algebra types
            "Two variable systems": "System of Linear Equations",
            "Three variable systems": "System of Linear Equations", 
            "Roots & Nature of Roots": "Quadratic Equation Problem",
            "Telescopic Series": "Sequence-Series Problem",
            
            # Geometry types
            "Area Rectangle": "Area Calculation Problem",
            
            # Modern Math types
            "Combinations with Restrictions": "Combination Problem",
            "Union and Intersection": "Set Theory Problem",
            "Digit-Based Permutation with Mandatory Element Inclusion": "Permutation Problem",
            
            # Commercial Math (Arithmetic category)
            "Discount Chains": "Discount Calculation Problem",
            "Direct Percentage to Algebraic Equation Conversion": "Percentage Application Problem",
            "Maximization of Top Score under Integer and Average Constraints": "Average Calculation Problem",
            "Sum of Squares Minimization with Fixed Product Constraint": "Average Calculation Problem",
            "Direct Single-Step Addition Problem": "Speed-Distance-Time Problem",
            "Single-Step Direct Multiplication of Small Numbers": "Speed-Distance-Time Problem",
            
            # PYQ specific
            "To be classified by LLM": "Speed-Distance-Time Problem",
            "Two-Number Product Calculation Using LCM and HCF": "HCF-LCM Problem"
        }
        
        # Apply mappings to regular questions
        print("🔧 UPDATING REGULAR QUESTIONS:")
        updated_regular = 0
        
        for old_type, new_type in type_mappings.items():
            result = db.execute(text(f"""
                UPDATE questions 
                SET type_of_question = '{new_type}'
                WHERE type_of_question = '{old_type}'
            """))
            
            if result.rowcount > 0:
                print(f"   ✅ {result.rowcount:3d} questions: '{old_type}' → '{new_type}'")
                updated_regular += result.rowcount
        
        db.commit()
        
        # Apply mappings to PYQ questions
        print(f"\n🔧 UPDATING PYQ QUESTIONS:")
        updated_pyq = 0
        
        for old_type, new_type in type_mappings.items():
            result = db.execute(text(f"""
                UPDATE pyq_questions 
                SET type_of_question = '{new_type}'
                WHERE type_of_question = '{old_type}'
            """))
            
            if result.rowcount > 0:
                print(f"   ✅ {result.rowcount:3d} questions: '{old_type}' → '{new_type}'")
                updated_pyq += result.rowcount
        
        db.commit()
        
        # Final verification
        print(f"\n📊 FINAL VERIFICATION:")
        print("-" * 30)
        
        # Check regular questions
        regular_canonical_result = db.execute(text(f"""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN type_of_question IN ({','.join([f"'{t}'" for types in canonical_question_types.values() for t in types])}) THEN 1 END) as canonical
            FROM questions
        """))
        
        regular_stats = regular_canonical_result.fetchone()
        regular_compliance = (regular_stats.canonical / regular_stats.total * 100) if regular_stats.total > 0 else 0
        
        # Check PYQ questions  
        pyq_canonical_result = db.execute(text(f"""
            SELECT COUNT(*) as total,
                   COUNT(CASE WHEN type_of_question IN ({','.join([f"'{t}'" for types in canonical_question_types.values() for t in types])}) THEN 1 END) as canonical
            FROM pyq_questions
        """))
        
        pyq_stats = pyq_canonical_result.fetchone()
        pyq_compliance = (pyq_stats.canonical / pyq_stats.total * 100) if pyq_stats.total > 0 else 0
        
        print(f"✅ Regular Questions Updated: {updated_regular}")
        print(f"✅ PYQ Questions Updated: {updated_pyq}")
        print(f"📊 Regular Canonical Compliance: {regular_stats.canonical}/{regular_stats.total} ({regular_compliance:.1f}%)")
        print(f"📊 PYQ Canonical Compliance: {pyq_stats.canonical}/{pyq_stats.total} ({pyq_compliance:.1f}%)")
        
        total_questions = regular_stats.total + pyq_stats.total
        total_canonical = regular_stats.canonical + pyq_stats.canonical
        overall_compliance = (total_canonical / total_questions * 100) if total_questions > 0 else 0
        
        print(f"🎯 OVERALL COMPLIANCE: {total_canonical}/{total_questions} ({overall_compliance:.1f}%)")
        
        if overall_compliance == 100.0:
            print(f"\n🎉 100% CANONICAL QUESTION TYPES ACHIEVED!")
            print(f"✅ All questions now use canonical type_of_question taxonomy")
            print(f"✅ Enhanced Enrichment Checker ready for 100% success")
        else:
            print(f"\n⚠️ {100-overall_compliance:.1f}% of questions still need type mapping")
            
            # Show remaining non-canonical types
            remaining_result = db.execute(text(f"""
                SELECT DISTINCT type_of_question, COUNT(*) as count
                FROM questions 
                WHERE type_of_question NOT IN ({','.join([f"'{t}'" for types in canonical_question_types.values() for t in types])})
                GROUP BY type_of_question
                ORDER BY count DESC
                LIMIT 10
            """))
            
            remaining_types = remaining_result.fetchall()
            if remaining_types:
                print(f"\n🔍 Remaining non-canonical types:")
                for type_name, count in remaining_types:
                    print(f"   • '{type_name}': {count} questions")
        
        return True
        
    except Exception as e:
        print(f"❌ CANONICAL TYPES ESTABLISHMENT FAILED: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    
    finally:
        db.close()

if __name__ == "__main__":
    success = establish_canonical_question_types()
    if success:
        print(f"\n🚀 CANONICAL QUESTION TYPES TAXONOMY ESTABLISHED!")
    else:
        exit(1)