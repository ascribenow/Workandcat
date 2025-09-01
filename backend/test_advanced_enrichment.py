#!/usr/bin/env python3
"""
Test Advanced LLM Enrichment Service with detailed error logging
"""

import asyncio
import json
import os
import openai
from dotenv import load_dotenv
import logging

# Setup detailed logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

async def test_detailed_enrichment():
    """Test with detailed error logging"""
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print("❌ No OpenAI API key found")
        return
    
    print("🧠 DETAILED ADVANCED ENRICHMENT TEST")
    print("=" * 60)
    
    # Test question
    question = "Two trains start from stations A and B respectively at the same time. Train X travels from A to B at 60 km/h, while train Y travels from B to A at 40 km/h. If the distance between A and B is 300 km, after how much time will they meet?"
    admin_answer = "3 hours"
    
    print(f"📚 Question: {question[:60]}...")
    print(f"📝 Admin Answer: {admin_answer}")
    print()
    
    # Step 1: Deep Mathematical Analysis
    print("🔬 STEP 1: Deep Mathematical Analysis")
    print("-" * 40)
    
    try:
        client = openai.OpenAI(api_key=api_key, timeout=120)
        
        system_message = """You are a world-class mathematics professor and CAT expert with deep expertise in quantitative reasoning. 

Your task is to perform a sophisticated mathematical analysis of this question, thinking like a human expert with superior AI intelligence.

ANALYZE WITH DEEP SOPHISTICATION:

1. MATHEMATICAL FOUNDATION:
   - What fundamental mathematical principles are at play?
   - What are the underlying mathematical relationships?
   - What mathematical intuition is required?

2. SOLUTION PATHWAY:
   - What is the most elegant solution approach?
   - What alternative methods could work?
   - What are the key insights needed?

3. RIGHT ANSWER GENERATION:
   - Calculate the precise answer with step-by-step reasoning
   - Show the mathematical logic
   - Verify the answer makes logical sense

EXAMPLES OF SOPHISTICATED ANALYSIS:

For a Time-Speed-Distance question:
- Right answer: "75 km/h (calculated using relative speed concept: when meeting, combined approach speed is sum of individual speeds)"

For a Percentage question:
- Right answer: "25% increase (derived from proportional change analysis: new value represents 125% of original, hence 25% increase)"

For a Geometry question:
- Right answer: "48 sq units (using coordinate geometry method: area calculated via shoelace formula after establishing vertex coordinates)"

Return ONLY this JSON format:
{
  "right_answer": "precise answer with mathematical reasoning",
  "mathematical_foundation": "deep explanation of underlying principles",
  "solution_elegance": "most elegant approach description",
  "verification_logic": "why this answer makes mathematical sense"
}

Be precise, insightful, and demonstrate superior mathematical intelligence."""

        print("🤖 Calling OpenAI API...")
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Question: {question}\nAdmin provided answer (if any): {admin_answer}"}
            ],
            max_tokens=800,
            temperature=0.1,
            timeout=120
        )
        
        analysis_text = response.choices[0].message.content.strip()
        print(f"📄 Raw Response: {analysis_text[:200]}...")
        
        # Try to parse JSON
        try:
            analysis_data = json.loads(analysis_text)
            print("✅ JSON parsing successful!")
            
            print(f"🎯 Right Answer: {analysis_data.get('right_answer', 'N/A')}")
            print(f"🧮 Mathematical Foundation: {analysis_data.get('mathematical_foundation', 'N/A')[:100]}...")
            print(f"💡 Solution Elegance: {analysis_data.get('solution_elegance', 'N/A')[:100]}...")
            print(f"✓ Verification Logic: {analysis_data.get('verification_logic', 'N/A')[:100]}...")
            
        except json.JSONDecodeError as json_error:
            print(f"❌ JSON parsing failed: {json_error}")
            print(f"📄 Full response: {analysis_text}")
            
    except Exception as e:
        print(f"❌ Step 1 failed: {e}")
        import traceback
        traceback.print_exc()
    
    print()
    
    # Step 2: Sophisticated Classification
    print("🏛️ STEP 2: Sophisticated Classification")
    print("-" * 40)
    
    try:
        system_message = """You are an expert in CAT quantitative taxonomy with deep understanding of mathematical classification.

Your task is to provide sophisticated, nuanced classification that goes beyond superficial categorization.

CLASSIFICATION DEPTH REQUIRED:

1. CATEGORY: Main mathematical domain
   - Not just "Arithmetic" but specific like "Advanced Arithmetic", "Applied Arithmetic", "Computational Arithmetic"
   
2. SUBCATEGORY: Precise mathematical area
   - Not just "Time Speed Distance" but "Relative Motion Analysis", "Multi-stage Journey Problems", "Meeting Point Calculations"
   
3. TYPE_OF_QUESTION: Very specific question archetype
   - Not just "Word Problem" but "Two-Train Meeting Problem with Different Departure Times", "Percentage Change in Sequential Operations"

EXAMPLES OF SOPHISTICATED CLASSIFICATION:

Instead of generic:
- Category: "Arithmetic"
- Subcategory: "Percentages" 
- Type: "Word Problem"

Provide nuanced:
- Category: "Applied Arithmetic with Business Context"
- Subcategory: "Sequential Percentage Changes in Sales Data"
- Type: "Multi-stage Percentage Calculation with Compound Effects"

Another example:
Instead of:
- Category: "Algebra"
- Subcategory: "Linear Equations"
- Type: "Basic"

Provide:
- Category: "Applied Algebraic Modeling"
- Subcategory: "Age-Based Linear Relationship Problems"
- Type: "Two-Person Age Differential with Future State Analysis"

Return ONLY this JSON:
{
  "category": "sophisticated main category",
  "subcategory": "nuanced subcategory", 
  "type_of_question": "very specific question archetype"
}

Be precise, specific, and demonstrate deep mathematical understanding."""

        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": f"Question: {question}"}
            ],
            max_tokens=300,
            temperature=0.1,
            timeout=120
        )
        
        classification_text = response.choices[0].message.content.strip()
        print(f"📄 Raw Response: {classification_text}")
        
        try:
            classification_data = json.loads(classification_text)
            print("✅ JSON parsing successful!")
            
            print(f"🏛️ Category: {classification_data.get('category', 'N/A')}")
            print(f"📂 Subcategory: {classification_data.get('subcategory', 'N/A')}")
            print(f"🔢 Type: {classification_data.get('type_of_question', 'N/A')}")
            
        except json.JSONDecodeError as json_error:
            print(f"❌ JSON parsing failed: {json_error}")
            
    except Exception as e:
        print(f"❌ Step 2 failed: {e}")
    
    print()
    print("🎉 Test completed!")

if __name__ == '__main__':
    asyncio.run(test_detailed_enrichment())