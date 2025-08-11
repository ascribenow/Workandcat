#!/usr/bin/env python3
"""
Implement Canonical Taxonomy and add type_of_question column
"""

import os
import sys
import asyncio
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_path))

from database import engine
from sqlalchemy import text

# Canonical Taxonomy Data Structure
CANONICAL_TAXONOMY = {
    "A": {
        "name": "Arithmetic",
        "subcategories": {
            "1": {
                "name": "Time–Speed–Distance (TSD)",
                "types": [
                    "Basic TSD",
                    "Relative Speed (opposite & same direction)",
                    "Circular Track Motion", 
                    "Boats & Streams",
                    "Trains",
                    "Races & Games of Chase"
                ]
            },
            "2": {
                "name": "Time & Work", 
                "types": [
                    "Work–Time–Efficiency Basics",
                    "Pipes & Cisterns (Inlet/Outlet)",
                    "Work Equivalence (men/women/children/machines)"
                ]
            },
            "3": {
                "name": "Ratio–Proportion–Variation",
                "types": [
                    "Simple Ratios",
                    "Compound Ratios", 
                    "Direct & Inverse Variation",
                    "Partnership Problems"
                ]
            },
            "4": {
                "name": "Percentages",
                "types": [
                    "Basic Percentages",
                    "Percentage Change (Increase/Decrease)",
                    "Successive Percentage Change"
                ]
            },
            "5": {
                "name": "Averages & Alligation",
                "types": [
                    "Basic Averages",
                    "Weighted Averages",
                    "Alligation Rule (Mixture of 2 or more entities)"
                ]
            },
            "6": {
                "name": "Profit–Loss–Discount (PLD)",
                "types": [
                    "Basic PLD",
                    "Successive PLD",
                    "Marked Price & Cost Price Relations",
                    "Discount Chains"
                ]
            },
            "7": {
                "name": "Simple & Compound Interest (SI–CI)",
                "types": [
                    "Basic SI & CI",
                    "Difference between SI & CI",
                    "Fractional Time Period CI"
                ]
            },
            "8": {
                "name": "Mixtures & Solutions",
                "types": [
                    "Replacement Problems",
                    "Concentration Change",
                    "Solid–Liquid–Gas Mixtures"
                ]
            }
        }
    },
    "B": {
        "name": "Algebra",
        "subcategories": {
            "1": {
                "name": "Linear Equations",
                "types": [
                    "Two-variable systems",
                    "Three-variable systems",
                    "Special cases (dependent/inconsistent systems)"
                ]
            },
            "2": {
                "name": "Quadratic Equations",
                "types": [
                    "Roots & Nature of Roots",
                    "Sum & Product of Roots",
                    "Maximum/Minimum values"
                ]
            },
            "3": {
                "name": "Inequalities",
                "types": [
                    "Linear Inequalities",
                    "Quadratic Inequalities",
                    "Modulus/Absolute Value"
                ]
            },
            "4": {
                "name": "Progressions",
                "types": [
                    "Arithmetic Progression (AP)",
                    "Geometric Progression (GP)",
                    "Harmonic Progression (HP)",
                    "Mixed Progressions"
                ]
            },
            "5": {
                "name": "Functions & Graphs",
                "types": [
                    "Types of Functions (linear, quadratic, polynomial, modulus, step)",
                    "Transformations (shifts, reflections, stretches)",
                    "Domain–Range",
                    "Composition & Inverse Functions"
                ]
            },
            "6": {
                "name": "Logarithms & Exponents",
                "types": [
                    "Basic Properties of Logs",
                    "Change of Base Formula",
                    "Solving Log Equations",
                    "Surds & Indices"
                ]
            },
            "7": {
                "name": "Special Algebraic Identities",
                "types": [
                    "Expansion & Factorisation",
                    "Cubes & Squares",
                    "Binomial Theorem (Basic)"
                ]
            }
        }
    },
    "C": {
        "name": "Geometry & Mensuration",
        "subcategories": {
            "1": {
                "name": "Triangles",
                "types": [
                    "Properties (Angles, Sides, Medians, Bisectors)",
                    "Congruence & Similarity",
                    "Pythagoras & Converse",
                    "Inradius, Circumradius, Orthocentre"
                ]
            },
            "2": {
                "name": "Circles",
                "types": [
                    "Tangents & Chords",
                    "Angles in a Circle",
                    "Cyclic Quadrilaterals"
                ]
            },
            "3": {
                "name": "Polygons",
                "types": [
                    "Regular Polygons",
                    "Interior/Exterior Angles"
                ]
            },
            "4": {
                "name": "Coordinate Geometry",
                "types": [
                    "Distance, Section Formula, Midpoint",
                    "Equation of a Line",
                    "Slope & Intercepts",
                    "Circles in Coordinate Plane",
                    "Parabola, Ellipse, Hyperbola (basic properties only)"
                ]
            },
            "5": {
                "name": "Mensuration (2D & 3D)",
                "types": [
                    "Areas (triangle, rectangle, trapezium, circle, sector)",
                    "Volumes (cube, cuboid, cylinder, cone, sphere, hemisphere)",
                    "Surface Areas"
                ]
            },
            "6": {
                "name": "Trigonometry in Geometry",
                "types": [
                    "Heights & Distances",
                    "Basic Trigonometric Ratios"
                ]
            }
        }
    },
    "D": {
        "name": "Number System",
        "subcategories": {
            "1": {
                "name": "Divisibility",
                "types": [
                    "Basic Divisibility Rules",
                    "Factorisation of Integers"
                ]
            },
            "2": {
                "name": "HCF–LCM",
                "types": [
                    "Euclidean Algorithm",
                    "Product of HCF & LCM"
                ]
            },
            "3": {
                "name": "Remainders & Modular Arithmetic",
                "types": [
                    "Basic Remainder Theorem",
                    "Chinese Remainder Theorem",
                    "Cyclicity of Remainders"
                ]
            },
            "4": {
                "name": "Base Systems",
                "types": [
                    "Conversion between bases",
                    "Arithmetic in different bases"
                ]
            },
            "5": {
                "name": "Digit Properties",
                "types": [
                    "Sum of Digits, Last Digit Patterns",
                    "Palindromes, Repetitive Digits"
                ]
            }
        }
    },
    "E": {
        "name": "Modern Math",
        "subcategories": {
            "1": {
                "name": "Permutation–Combination (P&C)",
                "types": [
                    "Basic Counting Principles",
                    "Circular Permutations",
                    "Permutations with Repetition/Restrictions",
                    "Combinations with Repetition/Restrictions"
                ]
            },
            "2": {
                "name": "Probability",
                "types": [
                    "Classical Probability",
                    "Conditional Probability",
                    "Bayes' Theorem"
                ]
            },
            "3": {
                "name": "Set Theory & Venn Diagrams",
                "types": [
                    "Union–Intersection",
                    "Complement & Difference of Sets",
                    "Problems on 2–3 sets"
                ]
            }
        }
    }
}

async def main():
    print("🔧 Implementing Canonical Taxonomy and Database Schema Updates...")
    
    async with engine.begin() as connection:
        # Step 1: Add type_of_question column to questions table
        print("1. Adding type_of_question column to questions table...")
        try:
            await connection.execute(text(
                "ALTER TABLE questions ADD COLUMN type_of_question VARCHAR(150)"
            ))
            print("   ✅ Added type_of_question column")
        except Exception as e:
            if "already exists" in str(e):
                print("   ✅ type_of_question column already exists")
            else:
                raise e
        
        # Step 2: Add type_of_question column to pyq_questions table
        print("2. Adding type_of_question column to pyq_questions table...")
        try:
            await connection.execute(text(
                "ALTER TABLE pyq_questions ADD COLUMN type_of_question VARCHAR(150)"
            ))
            print("   ✅ Added type_of_question column to pyq_questions")
        except Exception as e:
            if "already exists" in str(e):
                print("   ✅ type_of_question column already exists in pyq_questions")
            else:
                raise e
        
        # Step 3: Add category column to topics table for canonical taxonomy
        print("3. Adding category column to topics table...")
        try:
            await connection.execute(text(
                "ALTER TABLE topics ADD COLUMN category VARCHAR(50)"
            ))
            print("   ✅ Added category column")
        except Exception as e:
            if "already exists" in str(e):
                print("   ✅ category column already exists")
            else:
                raise e
        
        # Step 4: Implement canonical taxonomy structure (preserving existing data)
        print("4. Implementing canonical taxonomy structure...")
        
        # First, check existing topics count
        existing_count = await connection.scalar(text("SELECT COUNT(*) FROM topics"))
        print(f"   📊 Found {existing_count} existing topics")
        
        # Get all existing topics to map them
        existing_topics = await connection.execute(text("SELECT id, name FROM topics"))
        existing_topic_names = {row.name: row.id for row in existing_topics.fetchall()}
        
        # Insert canonical taxonomy (skip if already exists)
        topic_count = 0
        updated_count = 0
        
        for category_code, category_data in CANONICAL_TAXONOMY.items():
            # Insert/Update main category
            category_id = f"cat-{category_code.lower()}"
            category_name = category_data['name']
            
            if category_name in existing_topic_names:
                # Update existing category
                await connection.execute(text("""
                    UPDATE topics SET category = :category, parent_id = NULL 
                    WHERE id = :id
                """), {
                    'category': category_code,
                    'id': existing_topic_names[category_name]
                })
                updated_count += 1
            else:
                # Insert new category
                await connection.execute(text("""
                    INSERT INTO topics (id, name, slug, section, centrality, category, parent_id)
                    VALUES (:id, :name, :slug, 'Quantitative Aptitude', 1.0, :category, NULL)
                """), {
                    'id': category_id,
                    'name': category_name,
                    'slug': category_name.lower().replace(' ', '-').replace('&', 'and'),
                    'category': category_code
                })
                topic_count += 1
            
            # Insert/Update subcategories
            for subcat_code, subcat_data in category_data['subcategories'].items():
                subcat_id = f"subcat-{category_code.lower()}-{subcat_code}"
                subcat_name = subcat_data['name']
                
                # Use existing category ID if it was found, otherwise use new category_id
                parent_topic_id = existing_topic_names.get(category_name, category_id)
                
                if subcat_name in existing_topic_names:
                    # Update existing subcategory
                    await connection.execute(text("""
                        UPDATE topics SET category = :category, parent_id = :parent_id 
                        WHERE id = :id
                    """), {
                        'category': category_code,
                        'parent_id': parent_topic_id,
                        'id': existing_topic_names[subcat_name]
                    })
                    updated_count += 1
                else:
                    # Insert new subcategory
                    await connection.execute(text("""
                        INSERT INTO topics (id, name, slug, section, centrality, category, parent_id)
                        VALUES (:id, :name, :slug, 'Quantitative Aptitude', 0.8, :category, :parent_id)
                    """), {
                        'id': subcat_id,
                        'name': subcat_name,
                        'slug': subcat_name.lower().replace(' ', '-').replace('&', 'and').replace('–', '-'),
                        'category': category_code,
                        'parent_id': parent_topic_id
                    })
                    topic_count += 1
        
        print(f"   ✅ Inserted {topic_count} new topics, updated {updated_count} existing topics")
        
        # Step 5: Create lookup table for type_of_question mapping
        print("5. Creating type_of_question lookup data...")
        
        # Create a simple JSON structure for type_of_question mapping
        type_mapping = {}
        for category_code, category_data in CANONICAL_TAXONOMY.items():
            for subcat_code, subcat_data in category_data['subcategories'].items():
                subcat_id = f"subcat-{category_code.lower()}-{subcat_code}"
                type_mapping[subcat_id] = subcat_data['types']
        
        print(f"   ✅ Prepared type_of_question mapping for {len(type_mapping)} subcategories")
        
        # Step 6: Verify the structure
        print("6. Verifying canonical taxonomy structure...")
        result = await connection.execute(text("""
            SELECT category, COUNT(*) as count
            FROM topics 
            GROUP BY category
            ORDER BY category
        """))
        
        print("   📊 Topics by category:")
        for row in result.fetchall():
            print(f"      {row.category}: {row.count} topics")
            
        print("\n✅ Canonical Taxonomy Implementation Complete!")
        print("\n📋 Summary:")
        print("   • Added type_of_question column to questions and pyq_questions tables")
        print("   • Added category column to topics table")
        print("   • Implemented complete canonical taxonomy with 5 categories:")
        print("     - A: Arithmetic (8 subcategories)")
        print("     - B: Algebra (7 subcategories)")
        print("     - C: Geometry & Mensuration (6 subcategories)") 
        print("     - D: Number System (5 subcategories)")
        print("     - E: Modern Math (3 subcategories)")
        print("   • Each subcategory includes detailed type_of_question options")

if __name__ == "__main__":
    asyncio.run(main())