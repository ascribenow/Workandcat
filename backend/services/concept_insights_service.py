"""
Concept-Level Insights Service
Uses concept_alias_map_latest to provide actionable, granular insights about student strengths and weaknesses
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from database import SessionLocal

logger = logging.getLogger(__name__)


class ConceptInsightsService:
    """Generate insights from concept-level mastery data"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def get_concept_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Generate comprehensive concept-level insights for a user
        
        Returns insights about:
        - Strongest concepts (mastery >= 7.0)
        - Weakest concepts (mastery <= 3.0)
        - Neglected concepts (not practiced recently)
        - Improving concepts (positive trend)
        - Total concept coverage
        """
        db = SessionLocal()
        
        try:
            # Fetch all concept data from learner_notebook (the correct table with mastery data)
            concepts_result = db.execute(text("""
                SELECT 
                    concept_norm,
                    mastery_score,
                    readiness,
                    last_seen_at
                FROM learner_notebook
                WHERE user_id = :user_id
                ORDER BY mastery_score DESC
            """), {"user_id": user_id}).fetchall()
            
            if not concepts_result:
                return self._generate_no_data_insights()
            
            # Parse concept data
            concepts = []
            for row in concepts_result:
                concepts.append({
                    "concept": row[0],
                    "mastery": float(row[1]) if row[1] is not None else 0.0,
                    "readiness": row[2],
                    "last_seen": row[3]
                })
            
            # Analyze concepts
            analysis = self._analyze_concepts(concepts)
            
            # Generate markdown insights
            all_time_markdown = self._generate_all_time_markdown(analysis, concepts)
            recent_markdown = self._generate_recent_markdown(analysis, concepts)
            
            return {
                "all_time_markdown": all_time_markdown,
                "recent_markdown": recent_markdown,
                "last_updated_at": datetime.now(timezone.utc).isoformat(),
                "total_concepts": len(concepts),
                "analysis": analysis,
                "source": "concept_level"
            }
            
        except Exception as e:
            self.logger.error(f"Error generating concept insights for user {user_id[:8]}: {e}")
            return self._generate_error_insights()
        finally:
            db.close()
    
    def _analyze_concepts(self, concepts: List[Dict]) -> Dict[str, Any]:
        """Analyze concept data to extract key insights"""
        now = datetime.now(timezone.utc)
        
        # Categorize concepts
        strong = [c for c in concepts if c["mastery"] >= 7.0]
        moderate = [c for c in concepts if 3.0 < c["mastery"] < 7.0]
        weak = [c for c in concepts if c["mastery"] <= 3.0]
        
        # Find neglected concepts (not seen in last 14 days)
        neglected = []
        for c in concepts:
            if c["last_seen"]:
                days_since = (now - c["last_seen"]).days
                if days_since > 14:
                    neglected.append({**c, "days_since": days_since})
        
        # Sort neglected by days
        neglected.sort(key=lambda x: x["days_since"], reverse=True)
        
        # Find high coverage debt concepts (underserved)
        underserved = [c for c in concepts if c["coverage_debt"] >= 5.0]
        underserved.sort(key=lambda x: x["coverage_debt"], reverse=True)
        
        # Calculate average mastery
        avg_mastery = sum(c["mastery"] for c in concepts) / len(concepts) if concepts else 0.0
        
        return {
            "total_concepts": len(concepts),
            "strong_concepts": strong[:5],  # Top 5
            "weak_concepts": weak[:5],      # Bottom 5
            "moderate_concepts": moderate[:5],
            "neglected_concepts": neglected[:5],
            "underserved_concepts": underserved[:5],
            "avg_mastery": round(avg_mastery, 1),
            "strong_count": len(strong),
            "moderate_count": len(moderate),
            "weak_count": len(weak),
            "neglected_count": len(neglected)
        }
    
    def _generate_all_time_markdown(self, analysis: Dict, concepts: List[Dict]) -> str:
        """Generate all-time journey markdown with concept-level insights"""
        total = analysis["total_concepts"]
        strong_count = analysis["strong_count"]
        weak_count = analysis["weak_count"]
        avg_mastery = analysis["avg_mastery"]
        
        # Build concept distribution text
        if total == 0:
            distribution = "You haven't started practicing yet. Begin your first session to build your concept map!"
        else:
            distribution = f"You've practiced **{total} concepts** so far. "
            
            if strong_count > 0:
                distribution += f"**{strong_count} concepts** are strong (mastery ≥ 7.0), "
            
            distribution += f"**{analysis['moderate_count']} concepts** are moderate, "
            
            if weak_count > 0:
                distribution += f"and **{weak_count} concepts** need attention (mastery ≤ 3.0). "
            
            distribution += f"Your average mastery score is **{avg_mastery}/10**."
        
        # Highlight strongest concepts
        strengths_text = ""
        if analysis["strong_concepts"]:
            strong_list = ", ".join([
                f"**{c['concept']}** ({c['mastery']}/10)"
                for c in analysis["strong_concepts"][:3]
            ])
            strengths_text = f"\n\n🎯 **Your Strongest Concepts:** {strong_list}"
        
        # Highlight weakest concepts
        weaknesses_text = ""
        if analysis["weak_concepts"]:
            weak_list = ", ".join([
                f"**{c['concept']}** ({c['mastery']}/10)"
                for c in analysis["weak_concepts"][:3]
            ])
            weaknesses_text = f"\n\n⚠️ **Concepts Needing Attention:** {weak_list}"
        
        return f"{distribution}{strengths_text}{weaknesses_text}"
    
    def _generate_recent_markdown(self, analysis: Dict, concepts: List[Dict]) -> str:
        """Generate recent momentum markdown focusing on actionable items"""
        
        # Focus on neglected concepts
        neglected_text = ""
        if analysis["neglected_concepts"]:
            neglected = analysis["neglected_concepts"][:3]
            neglected_items = []
            for c in neglected:
                neglected_items.append(
                    f"**{c['concept']}** (last practiced {c['days_since']} days ago, mastery: {c['mastery']}/10)"
                )
            neglected_text = "📅 **Concepts to Revisit:**\n" + "\n".join([f"- {item}" for item in neglected_items])
        
        # Focus on underserved concepts
        underserved_text = ""
        if analysis["underserved_concepts"]:
            underserved = analysis["underserved_concepts"][:3]
            underserved_items = []
            for c in underserved:
                underserved_items.append(
                    f"**{c['concept']}** (coverage debt: {c['coverage_debt']}/10)"
                )
            underserved_text = "\n\n🎯 **Underserved Topics:**\n" + "\n".join([f"- {item}" for item in underserved_items])
        
        # Provide actionable recommendations
        recommendations = self._generate_recommendations(analysis)
        
        if neglected_text or underserved_text:
            return f"{neglected_text}{underserved_text}\n\n{recommendations}"
        else:
            return f"Keep up the consistent practice! {recommendations}"
    
    def _generate_recommendations(self, analysis: Dict) -> str:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        if analysis["weak_count"] > 0:
            recommendations.append("💡 **Focus on weak concepts** in your next sessions to build foundational strength")
        
        if analysis["neglected_count"] > 3:
            recommendations.append("♻️ **Revisit older concepts** to prevent skill decay")
        
        if analysis["avg_mastery"] < 5.0:
            recommendations.append("📚 **Build breadth** by practicing diverse concepts")
        elif analysis["avg_mastery"] >= 7.0:
            recommendations.append("🚀 **Challenge yourself** with harder questions to deepen mastery")
        
        if recommendations:
            return "\n".join([f"- {rec}" for rec in recommendations])
        else:
            return "Continue your consistent practice to maintain momentum!"
    
    def _generate_no_data_insights(self) -> Dict[str, Any]:
        """Generate insights when no concept data exists"""
        return {
            "all_time_markdown": "Start your learning journey! Complete your first practice session to see personalized insights about your strengths and areas for improvement.",
            "recent_markdown": "Your adaptive insights will appear here after you complete a few practice sessions. Each session helps us understand your learning patterns better!",
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
            "total_concepts": 0,
            "source": "no_data"
        }
    
    def _generate_error_insights(self) -> Dict[str, Any]:
        """Generate fallback insights on error"""
        return {
            "all_time_markdown": "We're having trouble loading your insights right now. Please try refreshing the page.",
            "recent_markdown": "Your learning data is being processed. Check back in a moment!",
            "last_updated_at": datetime.now(timezone.utc).isoformat(),
            "source": "error"
        }


# Global singleton instance
concept_insights_service = ConceptInsightsService()
