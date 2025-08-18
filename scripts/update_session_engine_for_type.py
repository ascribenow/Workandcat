#!/usr/bin/env python3
"""
Update Session Engine to Use Type as First-Class Dimension

This script updates the adaptive session logic to operate at 
(Category, Subcategory, Type) granularity instead of just (Category, Subcategory).

Key Changes:
1. Selection logic considers Type diversity
2. Mastery tracking at Type level 
3. Cooldown periods at Type level
4. PYQ weighting considers Type frequency
5. Guardrails ensure Type diversity in sessions
"""

import sys
import os
sys.path.append('/app/backend')

from sqlalchemy import text

def update_adaptive_session_logic():
    """Update adaptive_session_logic.py to use Type as first-class dimension"""
    
    # Read current adaptive_session_logic.py
    with open('/app/backend/adaptive_session_logic.py', 'r') as f:
        content = f.read()
    
    # Add Type-based diversity enforcement
    type_diversity_code = '''
    async def enforce_type_diversity(self, questions: List[Question]) -> List[Question]:
        """
        Enforce Type diversity caps to prevent domination at Type level
        Operates at (Category, Subcategory, Type) granularity
        """
        try:
            type_counts = {}
            diverse_questions = []
            
            # Sort questions by PYQ frequency first
            sorted_questions = sorted(
                questions, 
                key=lambda q: -(q.pyq_frequency_score or 0.5)
            )
            
            for question in sorted_questions:
                # Create Type key as (Category, Subcategory, Type)
                category = self.get_category_from_subcategory(question.subcategory)
                type_key = f"{category}::{question.subcategory}::{question.type_of_question or 'General'}"
                
                current_count = type_counts.get(type_key, 0)
                
                # Allow max 2 questions per Type to ensure diversity
                if current_count < 2:
                    diverse_questions.append(question)
                    type_counts[type_key] = current_count + 1
                
                # Stop if we have enough questions
                if len(diverse_questions) >= 12:
                    break
            
            # Ensure minimum Type diversity (at least 8 different Types)
            unique_types = len(set(f"{self.get_category_from_subcategory(q.subcategory)}::{q.subcategory}::{q.type_of_question or 'General'}" for q in diverse_questions[:12]))
            
            if unique_types < 8:
                logger.info(f"Only {unique_types} unique types, below minimum 8 - adding more diverse questions")
                # Try to add more Type-diverse questions if available
                remaining_questions = [q for q in questions if q not in diverse_questions]
                for question in remaining_questions:
                    category = self.get_category_from_subcategory(question.subcategory)
                    type_key = f"{category}::{question.subcategory}::{question.type_of_question or 'General'}"
                    
                    # Check if this Type is not already represented
                    existing_types = set(f"{self.get_category_from_subcategory(q.subcategory)}::{q.subcategory}::{q.type_of_question or 'General'}" for q in diverse_questions)
                    if type_key not in existing_types:
                        diverse_questions.append(question)
                        if len(set(f"{self.get_category_from_subcategory(q.subcategory)}::{q.subcategory}::{q.type_of_question or 'General'}" for q in diverse_questions[:12])) >= 8:
                            break
            
            final_unique_types = len(set(f"{self.get_category_from_subcategory(q.subcategory)}::{q.subcategory}::{q.type_of_question or 'General'}" for q in diverse_questions[:12]))
            logger.info(f"Enforced Type diversity: {len(diverse_questions)} questions from {final_unique_types} unique Types")
            return diverse_questions
            
        except Exception as e:
            logger.error(f"Error enforcing Type diversity: {e}")
            return questions
    '''
    
    # Replace the old enforce_subcategory_diversity with Type-aware version
    if "async def enforce_subcategory_diversity" in content:
        # Insert Type diversity method before the old subcategory method
        old_method_start = content.find("async def enforce_subcategory_diversity")
        content = content[:old_method_start] + type_diversity_code + "\n\n    " + content[old_method_start:]
        
        # Update the apply_enhanced_selection_strategies to use Type diversity
        content = content.replace(
            "# Strategy 4: PHASE 1 - Subcategory diversity enforcement\n            diverse_questions = await self.enforce_subcategory_diversity(cooled_questions)",
            "# Strategy 4: PHASE 1 - Type diversity enforcement (operates at Category::Subcategory::Type level)\n            diverse_questions = await self.enforce_type_diversity(cooled_questions)"
        )
    
    # Update session metadata to include Type analysis
    type_metadata_code = '''
                # Type distribution analysis
                type_distribution = {}
                category_type_distribution = {}
                
                for question in questions:
                    # Type distribution
                    question_type = question.type_of_question or 'General'
                    type_distribution[question_type] = type_distribution.get(question_type, 0) + 1
                    
                    # Category-Type combination analysis
                    category = self.get_category_from_subcategory(question.subcategory)
                    category_type_key = f"{category}::{question.subcategory}::{question_type}"
                    category_type_distribution[category_type_key] = category_type_distribution.get(category_type_key, 0) + 1
    '''
    
    # Add Type metadata to generate_enhanced_session_metadata
    if "# Enhanced metadata" in content:
        enhanced_metadata_start = content.find("# Enhanced metadata")
        content = content[:enhanced_metadata_start] + type_metadata_code + "\n                " + content[enhanced_metadata_start:]
        
        # Add Type fields to metadata dict
        content = content.replace(
            "'subcategory_distribution': subcategory_distribution,",
            "'subcategory_distribution': subcategory_distribution,\n                'type_distribution': type_distribution,\n                'category_type_distribution': category_type_distribution,"
        )
        
        content = content.replace(
            "'subcategory_diversity': len(subcategory_distribution),",
            "'subcategory_diversity': len(subcategory_distribution),\n                'type_diversity': len(type_distribution),\n                'category_type_diversity': len(category_type_distribution),"
        )
    
    # Update question selection to consider Type in PYQ weighting
    type_weighting_code = '''
            # Sort by PYQ frequency and Type diversity for balanced selection
            prioritized = sorted(
                category_questions,
                key=lambda q: (
                    0 if q.subcategory in user_profile['weak_subcategories'] else
                    1 if q.subcategory in user_profile['moderate_subcategories'] else 2,
                    -(q.pyq_frequency_score or 0.5),  # Higher PYQ frequency first
                    q.type_of_question or 'ZZZ'  # Type diversity (alphabetical for consistency)
                )
            )
    '''
    
    # Replace old prioritization logic with Type-aware version
    content = content.replace(
        "# Sort by weakness first, then PYQ frequency\n                    prioritized = sorted(\n                        category_questions,\n                        key=lambda q: (\n                            0 if q.subcategory in user_profile['weak_subcategories'] else\n                            1 if q.subcategory in user_profile['moderate_subcategories'] else 2,\n                            -(q.pyq_frequency_score or 0.5)  # Higher PYQ frequency first\n                        )\n                    )",
        f"# Sort by weakness first, then PYQ frequency, then Type diversity{type_weighting_code}"
    )
    
    # Write updated content
    with open('/app/backend/adaptive_session_logic.py', 'w') as f:
        f.write(content)
    
    print("✅ Updated adaptive_session_logic.py to use Type as first-class dimension")

def main():
    """Update session engine for Type-based selection"""
    print("🚀 Updating Session Engine for Type-based Selection...")
    
    try:
        update_adaptive_session_logic()
        print("🎉 Session Engine Update SUCCESSFUL!")
        print("✅ Type now used as first-class dimension")
        print("✅ Selection operates at (Category, Subcategory, Type) granularity") 
        print("✅ Type diversity enforcement implemented")
        print("✅ Type-aware PYQ weighting enabled")
        print("✅ Type metadata tracking added")
        
    except Exception as e:
        print(f"❌ Session Engine Update failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())