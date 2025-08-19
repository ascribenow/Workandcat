#!/usr/bin/env python3
"""
Question Mathematical Enhancement
Converts question stems to human-friendly Unicode mathematical notation
Follows the Master Directive: Human-Friendly Presentation
"""

import sys
import os
sys.path.append('/app/backend')

from database import *
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionMathematicalEnhancer:
    """Enhance questions with human-friendly Unicode mathematical notation"""
    
    def __init__(self):
        # Superscript mapping for exponents
        self.superscript_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
            '10': '¹⁰', '11': '¹¹', '12': '¹²', '13': '¹³', '14': '¹⁴',
            '15': '¹⁵', '16': '¹⁶', '17': '¹⁷', '18': '¹⁸', '19': '¹⁹',
            '20': '²⁰', '21': '²¹', '22': '²²', '23': '²³', '24': '²⁴',
            '25': '²⁵', '30': '³⁰', '100': '¹⁰⁰'
        }
        
    def convert_to_superscript(self, num_str: str) -> str:
        """Convert number string to superscript Unicode"""
        # Handle common exponents directly
        if num_str in self.superscript_map:
            return self.superscript_map[num_str]
        
        # Handle other numbers digit by digit
        digit_map = {
            '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
            '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹'
        }
        return ''.join(digit_map.get(d, d) for d in num_str)
    
    def enhance_mathematical_notation(self, text: str) -> str:
        """Convert text to human-friendly mathematical notation"""
        if not text:
            return text
            
        enhanced = text
        
        # Convert exponents: 2^20 → 2²⁰
        enhanced = re.sub(r'(\d+)\^(\d+)', lambda m: f'{m.group(1)}{self.convert_to_superscript(m.group(2))}', enhanced)
        
        # Convert variables with exponents: n^2 → n², x^3 → x³
        enhanced = re.sub(r'([a-zA-Z])\^(\d+)', lambda m: f'{m.group(1)}{self.convert_to_superscript(m.group(2))}', enhanced)
        
        # Convert multiplication symbols: * → ×
        enhanced = enhanced.replace(' * ', ' × ')
        enhanced = enhanced.replace('*', '×')
        
        # Convert division expressions where appropriate
        enhanced = enhanced.replace(' / ', ' ÷ ')
        enhanced = enhanced.replace(' divided by ', ' ÷ ')
        
        # Convert square root expressions
        enhanced = re.sub(r'sqrt\(([^)]+)\)', r'√\1', enhanced)
        enhanced = enhanced.replace('square root of ', '√')
        
        # Convert common mathematical terms
        enhanced = enhanced.replace(' times ', ' × ')
        enhanced = enhanced.replace(' multiply by ', ' × ')
        
        # Clean up any LaTeX that might exist
        enhanced = enhanced.replace('\\frac', '')
        enhanced = enhanced.replace('\\begin{matrix}', '')
        enhanced = enhanced.replace('\\end{matrix}', '')
        enhanced = enhanced.replace('\\times', '×')
        enhanced = enhanced.replace('\\div', '÷')
        enhanced = enhanced.replace('$', '')
        enhanced = enhanced.replace('\\(', '').replace('\\)', '')
        enhanced = enhanced.replace('\\[', '').replace('\\]', '')
        
        # Clean up excessive spaces
        enhanced = re.sub(r'\s+', ' ', enhanced)
        enhanced = enhanced.strip()
        
        return enhanced
    
    def analyze_question_formatting(self) -> dict:
        """Analyze current question formatting in database"""
        init_database()
        db = SessionLocal()
        
        try:
            all_questions = db.query(Question).filter(Question.is_active == True).all()
            
            analysis = {
                'total_questions': len(all_questions),
                'needs_enhancement': 0,
                'has_latex': 0,
                'has_exponents': 0,
                'has_multiplication': 0,
                'samples': []
            }
            
            for q in all_questions:
                stem = q.stem or ''
                
                # Check for LaTeX
                if any(x in stem for x in ['\\frac', '\\begin', '$', '\\(']):
                    analysis['has_latex'] += 1
                
                # Check for exponents  
                if '^' in stem:
                    analysis['has_exponents'] += 1
                
                # Check for multiplication
                if '*' in stem or ' times ' in stem:
                    analysis['has_multiplication'] += 1
                
                # Check if needs enhancement
                if any(x in stem for x in ['^', '*', 'sqrt', '\\frac', '$']):
                    analysis['needs_enhancement'] += 1
                    if len(analysis['samples']) < 5:
                        analysis['samples'].append({
                            'id': q.id,
                            'original': stem[:100] + '...' if len(stem) > 100 else stem,
                            'enhanced': self.enhance_mathematical_notation(stem)[:100] + '...'
                        })
            
            return analysis
            
        finally:
            db.close()
    
    def enhance_all_questions(self) -> bool:
        """Enhance all questions with mathematical notation"""
        try:
            logger.info("🚀 Starting Question Mathematical Enhancement...")
            
            init_database()
            db = SessionLocal()
            
            # Get all active questions
            questions = db.query(Question).filter(Question.is_active == True).all()
            
            logger.info(f"📊 Found {len(questions)} questions to enhance")
            
            enhanced_count = 0
            no_change_count = 0
            
            for i, question in enumerate(questions):
                try:
                    logger.info(f"\n🔄 [{i+1}/{len(questions)}] Processing: {question.stem[:60]}...")
                    
                    # Enhance the question stem
                    original_stem = question.stem or ''
                    enhanced_stem = self.enhance_mathematical_notation(original_stem)
                    
                    # Check if changes were made
                    if enhanced_stem != original_stem:
                        question.stem = enhanced_stem
                        db.commit()
                        enhanced_count += 1
                        
                        logger.info(f"  ✅ Enhanced mathematical notation")
                        logger.info(f"  📝 Before: {original_stem[:80]}...")
                        logger.info(f"  📝 After:  {enhanced_stem[:80]}...")
                    else:
                        no_change_count += 1
                        logger.info(f"  ℹ️ No mathematical enhancement needed")
                
                except Exception as e:
                    logger.error(f"  ❌ Failed to enhance question {i+1}: {e}")
                    continue
            
            # Final summary
            logger.info(f"\n🎉 QUESTION MATHEMATICAL ENHANCEMENT COMPLETED!")
            logger.info(f"✅ Enhanced: {enhanced_count}")
            logger.info(f"ℹ️ No changes needed: {no_change_count}")
            logger.info(f"📊 Total processed: {len(questions)}")
            
            success_rate = (enhanced_count + no_change_count) / len(questions) if questions else 0
            logger.info(f"📈 Success rate: {success_rate:.1%}")
            
            return success_rate > 0.95
            
        except Exception as e:
            logger.error(f"❌ Question enhancement failed: {e}")
            return False
        finally:
            db.close()


def main():
    enhancer = QuestionMathematicalEnhancer()
    
    # First analyze current state
    logger.info("🔍 Analyzing current question formatting...")
    analysis = enhancer.analyze_question_formatting()
    
    logger.info("\n📊 QUESTION FORMATTING ANALYSIS:")
    logger.info(f"Total questions: {analysis['total_questions']}")
    logger.info(f"Questions with LaTeX: {analysis['has_latex']}")
    logger.info(f"Questions with exponents: {analysis['has_exponents']}")
    logger.info(f"Questions with multiplication: {analysis['has_multiplication']}")
    logger.info(f"Questions needing enhancement: {analysis['needs_enhancement']}")
    
    if analysis['samples']:
        logger.info("\n📋 SAMPLE ENHANCEMENTS:")
        for i, sample in enumerate(analysis['samples']):
            logger.info(f"\n--- Sample {i+1} ---")
            logger.info(f"Original: {sample['original']}")
            logger.info(f"Enhanced: {sample['enhanced']}")
    
    if analysis['needs_enhancement'] > 0:
        logger.info(f"\n⚡ Starting enhancement of {analysis['needs_enhancement']} questions...")
        success = enhancer.enhance_all_questions()
        
        if success:
            logger.info("\n🎉 SUCCESS: All questions enhanced with human-friendly mathematical notation!")
            logger.info("📚 Questions now use Unicode symbols (²⁰, ×, ÷) instead of raw text (^20, *, /)")
        else:
            logger.info("\n❌ Some issues occurred during enhancement")
    else:
        logger.info("\n✅ All questions already have clean formatting!")

if __name__ == "__main__":
    main()