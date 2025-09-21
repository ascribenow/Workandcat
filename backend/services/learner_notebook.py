"""
Learner Notebook Service
Manages a user's Learner Notebook (skill statuses) with backup to session_summary_llm
"""

import asyncio
import json
import logging
import psycopg2
from typing import Dict, List, Optional
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class LearnerNotebookService:
    """
    Manages user skill proficiencies with backup mechanism
    Stores latest skill statuses: weak/moderate/strong
    """
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    async def read_or_default(self, user_id: str) -> Dict:
        """
        Get current notebook or return empty default
        
        Args:
            user_id: User identifier
            
        Returns:
            Dictionary with notebook data or default empty structure
        """
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Get latest notebook from learner_notebook table
            cur.execute("""
                SELECT notebook_json, version, updated_at 
                FROM learner_notebook 
                WHERE user_id = %s
                ORDER BY updated_at DESC
                LIMIT 1
            """, (user_id,))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if result:
                notebook_json = result[0]
                # Handle both string and dict formats
                if isinstance(notebook_json, str):
                    return json.loads(notebook_json)
                else:
                    return notebook_json
            else:
                # Default: empty skills (treated as Moderate=ALL in digest)
                logger.info(f"No notebook found for user {user_id[:8]}, returning default")
                return {
                    "skills": [],
                    "notes": "New learner - no skill history yet"
                }
                
        except Exception as e:
            logger.error(f"Failed to read notebook for user {user_id[:8]}: {e}")
            # Return safe default on error
            return {
                "skills": [],
                "notes": "Error loading notebook - using default"
            }
    
    async def update_notebook_with_backup(self, user_id: str, sess_seq: int, 
                                        notebook_before: Dict, notebook_after: Dict) -> bool:
        """
        Upsert notebook with before/after backup to session_summary_llm
        
        Args:
            user_id: User identifier
            sess_seq: Session sequence number
            notebook_before: Notebook state before update
            notebook_after: Notebook state after update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # 1. Update latest notebook (upsert)
            cur.execute("""
                INSERT INTO learner_notebook (user_id, notebook_json, updated_at) 
                VALUES (%s, %s, NOW())
                ON CONFLICT (user_id) DO UPDATE SET 
                    notebook_json = EXCLUDED.notebook_json,
                    version = learner_notebook.version + 1,
                    updated_at = NOW()
            """, (user_id, json.dumps(notebook_after)))
            
            # 2. Write before/after snapshot to session_summary_llm table for backup
            backup_data = {
                "notebook_before": notebook_before,
                "notebook_after": notebook_after,
                "backup_timestamp": datetime.utcnow().isoformat(),
                "backup_type": "coverage_notebook_update",
                "skill_changes": self._calculate_skill_changes(notebook_before, notebook_after)
            }
            
            cur.execute("""
                INSERT INTO session_summary_llm (user_id, session_id, concept_alias_map, dominance, readiness_reasons, coverage_labels, llm_model_used, created_at)
                VALUES (%s, %s, %s, '{}', '[]', '[]', 'coverage_notebook_backup', NOW())
                ON CONFLICT (user_id, session_id) DO UPDATE SET
                    concept_alias_map = EXCLUDED.concept_alias_map,
                    llm_model_used = 'coverage_notebook_backup',
                    created_at = NOW()
            """, (user_id, f"coverage_session_{sess_seq}", json.dumps(backup_data)))
            
            conn.commit()
            cur.close()
            conn.close()
            
            logger.info(f"✅ Updated notebook for user {user_id[:8]}, sess_seq {sess_seq}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update notebook for user {user_id[:8]}: {e}")
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            return False
    
    def _calculate_skill_changes(self, notebook_before: Dict, notebook_after: Dict) -> List[Dict]:
        """Calculate what skills changed between notebook versions"""
        changes = []
        
        # Convert skills to dictionaries for easier comparison
        before_skills = {skill.get('label', ''): skill for skill in notebook_before.get('skills', [])}
        after_skills = {skill.get('label', ''): skill for skill in notebook_after.get('skills', [])}
        
        # Check for new skills
        for label, skill in after_skills.items():
            if label not in before_skills:
                changes.append({
                    "type": "new_skill",
                    "skill": label,
                    "status": skill.get('status', 'moderate')
                })
            elif before_skills[label].get('status') != skill.get('status'):
                changes.append({
                    "type": "status_change",
                    "skill": label,
                    "from": before_skills[label].get('status', 'moderate'),
                    "to": skill.get('status', 'moderate')
                })
        
        return changes
    
    async def get_notebook_history(self, user_id: str, limit: int = 5) -> List[Dict]:
        """
        Get recent notebook update history from backups
        
        Args:
            user_id: User identifier
            limit: Maximum number of history entries
            
        Returns:
            List of historical notebook states
        """
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT sess_seq, summary_json, generated_at
                FROM session_summary_llm
                WHERE user_id = %s 
                AND model_used = 'coverage_notebook_backup'
                ORDER BY generated_at DESC
                LIMIT %s
            """, (user_id, limit))
            
            results = cur.fetchall()
            cur.close()
            conn.close()
            
            history = []
            for sess_seq, summary_json, generated_at in results:
                if isinstance(summary_json, str):
                    backup_data = json.loads(summary_json)
                else:
                    backup_data = summary_json
                    
                history.append({
                    "sess_seq": sess_seq,
                    "timestamp": generated_at.isoformat() if generated_at else None,
                    "skill_changes": backup_data.get('skill_changes', []),
                    "notebook_after": backup_data.get('notebook_after', {})
                })
            
            return history
            
        except Exception as e:
            logger.error(f"Failed to get notebook history for user {user_id[:8]}: {e}")
            return []
    
    async def get_service_status(self) -> Dict:
        """Get service statistics and health status"""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Get notebook statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_notebooks,
                    COUNT(*) FILTER (WHERE updated_at > NOW() - INTERVAL '7 days') as recent_updates,
                    AVG(version) as avg_version
                FROM learner_notebook
            """)
            
            notebook_stats = cur.fetchone()
            
            # Get backup statistics
            cur.execute("""
                SELECT 
                    COUNT(*) as total_backups,
                    COUNT(*) FILTER (WHERE generated_at > NOW() - INTERVAL '24 hours') as recent_backups
                FROM session_summary_llm
                WHERE model_used = 'coverage_notebook_backup'
            """)
            
            backup_stats = cur.fetchone()
            cur.close()
            conn.close()
            
            return {
                "status": "healthy",
                "total_notebooks": notebook_stats[0] if notebook_stats else 0,
                "recent_updates": notebook_stats[1] if notebook_stats else 0,
                "avg_version": float(notebook_stats[2]) if notebook_stats and notebook_stats[2] else 0,
                "total_backups": backup_stats[0] if backup_stats else 0,
                "recent_backups": backup_stats[1] if backup_stats else 0
            }
            
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {"status": "error", "error": str(e)}

# Global instance
learner_notebook_service = LearnerNotebookService()

# Test function
async def test_learner_notebook_service():
    """Test the learner notebook service"""
    service = learner_notebook_service
    
    print("🧪 Testing Learner Notebook Service...")
    
    # Test 1: Read default notebook for new user
    test_user = "test_user_123"
    notebook = await service.read_or_default(test_user)
    print(f"✅ Default notebook: {notebook}")
    
    # Test 2: Update notebook with backup
    notebook_before = notebook.copy()
    notebook_after = {
        "skills": [
            {"label": "relative speed", "status": "weak", "counts": {"correct": 1, "incorrect": 3, "skipped": 1, "mh_correct": 0}},
            {"label": "ratio scaling", "status": "moderate", "counts": {"correct": 2, "incorrect": 1, "skipped": 0, "mh_correct": 1}}
        ],
        "notes": "Updated after session 1"
    }
    
    success = await service.update_notebook_with_backup(test_user, 1, notebook_before, notebook_after)
    print(f"✅ Update successful: {success}")
    
    # Test 3: Read updated notebook
    updated_notebook = await service.read_or_default(test_user)
    print(f"✅ Updated notebook: {updated_notebook}")
    
    # Test 4: Get service status
    status = await service.get_service_status()
    print(f"✅ Service status: {status}")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_learner_notebook_service())