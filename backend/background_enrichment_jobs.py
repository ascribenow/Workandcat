#!/usr/bin/env python3
"""
Background Enrichment Jobs System
Handles long-running enrichment tasks with email notifications
"""

import asyncio
import threading
import time
import json
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from sqlalchemy.orm import Session

from database import SessionLocal, Question, PYQQuestion
from enhanced_enrichment_checker_service import EnhancedEnrichmentCheckerService
from gmail_service import GmailService

# Initialize Gmail service
gmail_service = GmailService()

def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Send email using Gmail service
    """
    try:
        # Authenticate service if not already done
        if not gmail_service.service:
            if not gmail_service.authenticate_service():
                logger.error("Failed to authenticate Gmail service")
                return False
        
        return gmail_service.send_generic_email(to_email, subject, body)
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BackgroundEnrichmentJobs:
    """
    Background job processor for enrichment tasks with email notifications
    """
    
    def __init__(self):
        self.running_jobs = {}  # Track running jobs
        self.job_results = {}   # Store completed job results
        
    def start_regular_questions_enrichment(self, admin_email: str, total_questions: int = None) -> str:
        """
        Start background enrichment job for regular questions
        
        Args:
            admin_email: Email to send results to
            total_questions: Number of questions to process (None = all)
            
        Returns:
            str: Job ID for tracking
        """
        job_id = f"regular_enrichment_{int(time.time())}"
        
        # Start background thread
        thread = threading.Thread(
            target=self._run_regular_enrichment_job,
            args=(job_id, admin_email, total_questions),
            daemon=True
        )
        thread.start()
        
        self.running_jobs[job_id] = {
            "type": "regular_questions",
            "started_at": datetime.utcnow(),
            "admin_email": admin_email,
            "total_questions": total_questions,
            "status": "running"
        }
        
        logger.info(f"🚀 Started background regular questions enrichment job: {job_id}")
        return job_id
    
    def start_pyq_questions_enrichment(self, admin_email: str, total_questions: int = None) -> str:
        """
        Start background enrichment job for PYQ questions
        
        Args:
            admin_email: Email to send results to
            total_questions: Number of questions to process (None = all)
            
        Returns:
            str: Job ID for tracking
        """
        job_id = f"pyq_enrichment_{int(time.time())}"
        
        # Start background thread
        thread = threading.Thread(
            target=self._run_pyq_enrichment_job,
            args=(job_id, admin_email, total_questions),
            daemon=True
        )
        thread.start()
        
        self.running_jobs[job_id] = {
            "type": "pyq_questions",
            "started_at": datetime.utcnow(),
            "admin_email": admin_email,
            "total_questions": total_questions,
            "status": "running"
        }
        
        logger.info(f"🚀 Started background PYQ questions enrichment job: {job_id}")
        return job_id
    
    def _run_regular_enrichment_job(self, job_id: str, admin_email: str, total_questions: Optional[int]):
        """
        Background worker for regular questions enrichment
        """
        try:
            logger.info(f"🔄 Starting regular questions enrichment job {job_id}")
            
            # Use asyncio in the background thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._process_regular_questions_with_retries(job_id, total_questions)
            )
            
            # Mark job as completed
            self.running_jobs[job_id]["status"] = "completed"
            self.job_results[job_id] = result
            
            # Send email notification
            self._send_completion_email(job_id, admin_email, result, "Regular Questions")
            
            logger.info(f"✅ Completed regular questions enrichment job {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Regular questions enrichment job {job_id} failed: {e}")
            
            # Mark job as failed
            self.running_jobs[job_id]["status"] = "failed"
            self.job_results[job_id] = {"error": str(e)}
            
            # Send failure email
            self._send_failure_email(job_id, admin_email, str(e), "Regular Questions")
    
    def _run_pyq_enrichment_job(self, job_id: str, admin_email: str, total_questions: Optional[int]):
        """
        Background worker for PYQ questions enrichment
        """
        try:
            logger.info(f"🔄 Starting PYQ questions enrichment job {job_id}")
            
            # Use asyncio in the background thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                self._process_pyq_questions_with_retries(job_id, total_questions)
            )
            
            # Mark job as completed
            self.running_jobs[job_id]["status"] = "completed"
            self.job_results[job_id] = result
            
            # Send email notification
            self._send_completion_email(job_id, admin_email, result, "PYQ Questions")
            
            logger.info(f"✅ Completed PYQ questions enrichment job {job_id}")
            
        except Exception as e:
            logger.error(f"❌ PYQ questions enrichment job {job_id} failed: {e}")
            
            # Mark job as failed
            self.running_jobs[job_id]["status"] = "failed"
            self.job_results[job_id] = {"error": str(e)}
            
            # Send failure email
            self._send_failure_email(job_id, admin_email, str(e), "PYQ Questions")
    
    async def _process_regular_questions_with_retries(self, job_id: str, total_questions: Optional[int]) -> Dict[str, Any]:
        """
        Process regular questions with automatic retries and progress tracking
        """
        db = SessionLocal()
        enrich_checker = EnhancedEnrichmentCheckerService()
        
        try:
            # Process in batches with retries
            batch_size = 10
            total_processed = 0
            total_improved = 0
            total_failed = 0
            batch_count = 0
            max_retries = 3
            
            while True:
                batch_count += 1
                logger.info(f"📦 Processing batch {batch_count} for job {job_id}")
                
                # Process batch with retries
                for attempt in range(max_retries):
                    try:
                        result = await enrich_checker.check_and_enrich_regular_questions(
                            db, limit=batch_size
                        )
                        
                        if result["success"]:
                            batch_results = result["check_results"]
                            total_processed += batch_results["total_questions_checked"]
                            total_improved += batch_results["re_enrichment_successful"]
                            total_failed += batch_results["re_enrichment_failed"]
                            
                            logger.info(f"✅ Batch {batch_count} completed: {batch_results['total_questions_checked']} processed")
                            break
                        else:
                            raise Exception(result.get("error", "Batch processing failed"))
                            
                    except Exception as e:
                        logger.warning(f"⚠️ Batch {batch_count} attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            logger.error(f"❌ Batch {batch_count} failed after {max_retries} attempts")
                            total_failed += batch_size
                        else:
                            await asyncio.sleep(30)  # Wait before retry
                
                # Check if we should continue
                if total_questions and total_processed >= total_questions:
                    break
                
                # Check if there are more questions to process
                if batch_results["total_questions_checked"] < batch_size:
                    logger.info(f"🏁 No more questions to process. Job {job_id} complete.")
                    break
                
                # Wait between batches to avoid overwhelming the system
                await asyncio.sleep(10)
            
            return {
                "total_processed": total_processed,
                "total_improved": total_improved,
                "total_failed": total_failed,
                "batches_processed": batch_count,
                "completion_time": datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    async def _process_pyq_questions_with_retries(self, job_id: str, total_questions: Optional[int]) -> Dict[str, Any]:
        """
        Process PYQ questions with automatic retries and progress tracking
        """
        db = SessionLocal()
        enrich_checker = EnhancedEnrichmentCheckerService()
        
        try:
            # Process in batches with retries
            batch_size = 10
            total_processed = 0
            total_improved = 0
            total_failed = 0
            batch_count = 0
            max_retries = 3
            
            while True:
                batch_count += 1
                logger.info(f"📦 Processing PYQ batch {batch_count} for job {job_id}")
                
                # Process batch with retries
                for attempt in range(max_retries):
                    try:
                        result = await enrich_checker.check_and_enrich_pyq_questions(
                            db, limit=batch_size
                        )
                        
                        if result["success"]:
                            batch_results = result["check_results"]
                            total_processed += batch_results["total_questions_checked"]
                            total_improved += batch_results["re_enrichment_successful"]
                            total_failed += batch_results["re_enrichment_failed"]
                            
                            logger.info(f"✅ PYQ Batch {batch_count} completed: {batch_results['total_questions_checked']} processed")
                            break
                        else:
                            raise Exception(result.get("error", "PYQ batch processing failed"))
                            
                    except Exception as e:
                        logger.warning(f"⚠️ PYQ Batch {batch_count} attempt {attempt + 1} failed: {e}")
                        if attempt == max_retries - 1:
                            logger.error(f"❌ PYQ Batch {batch_count} failed after {max_retries} attempts")
                            total_failed += batch_size
                        else:
                            await asyncio.sleep(30)  # Wait before retry
                
                # Check if we should continue
                if total_questions and total_processed >= total_questions:
                    break
                
                # Check if there are more questions to process
                if batch_results["total_questions_checked"] < batch_size:
                    logger.info(f"🏁 No more PYQ questions to process. Job {job_id} complete.")
                    break
                
                # Wait between batches
                await asyncio.sleep(10)
            
            return {
                "total_processed": total_processed,
                "total_improved": total_improved,
                "total_failed": total_failed,
                "batches_processed": batch_count,
                "completion_time": datetime.utcnow().isoformat()
            }
            
        finally:
            db.close()
    
    def _send_completion_email(self, job_id: str, admin_email: str, result: Dict[str, Any], job_type: str):
        """
        Send completion email with results
        """
        try:
            subject = f"✅ {job_type} Enrichment Job Completed - {job_id}"
            
            body = f"""
🎉 **{job_type} Enrichment Job Completed Successfully!**

**Job Details:**
• Job ID: {job_id}
• Job Type: {job_type} Enrichment
• Completion Time: {result.get('completion_time', 'Unknown')}

**Processing Results:**
• 📊 Total Questions Processed: {result.get('total_processed', 0)}
• ✅ Questions Successfully Improved: {result.get('total_improved', 0)}
• ❌ Questions Failed Processing: {result.get('total_failed', 0)}
• 📦 Batches Processed: {result.get('batches_processed', 0)}

**Quality Standards:**
• 🎯 100% Quality Standards Enforced
• 🤖 Intelligent GPT-4o/GPT-4o-mini Model Switching
• 🔄 Automatic Retries for Failed Batches
• 🧠 Ultra-Sophisticated Content Generation

**Next Steps:**
• Log into the admin dashboard to see the enriched questions
• Run additional enrichment jobs if needed
• Monitor question quality improvements

**System Performance:**
The background job system successfully processed your enrichment request without timeouts or user interface blocking.

---
**Twelvr Admin System**
CAT Preparation Platform v2.0
            """
            
            send_email(
                to_email=admin_email,
                subject=subject,
                body=body
            )
            
            logger.info(f"📧 Completion email sent to {admin_email} for job {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send completion email for job {job_id}: {e}")
    
    def _send_failure_email(self, job_id: str, admin_email: str, error: str, job_type: str):
        """
        Send failure email with error details
        """
        try:
            subject = f"❌ {job_type} Enrichment Job Failed - {job_id}"
            
            body = f"""
❌ **{job_type} Enrichment Job Failed**

**Job Details:**
• Job ID: {job_id}
• Job Type: {job_type} Enrichment
• Failure Time: {datetime.utcnow().isoformat()}

**Error Details:**
{error}

**Recommended Actions:**
• Check the backend logs for detailed error information
• Verify OpenAI API key and rate limits
• Try running the enrichment job again
• Contact system administrator if the issue persists

**System Status:**
The background job system attempted to process your enrichment request but encountered an error. The system remains operational for other tasks.

---
**Twelvr Admin System**
CAT Preparation Platform v2.0
            """
            
            send_email(
                to_email=admin_email,
                subject=subject,
                body=body
            )
            
            logger.info(f"📧 Failure email sent to {admin_email} for job {job_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send failure email for job {job_id}: {e}")
    
    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """
        Get status of a running or completed job
        """
        if job_id in self.running_jobs:
            job_info = self.running_jobs[job_id].copy()
            if job_id in self.job_results:
                job_info["results"] = self.job_results[job_id]
            return job_info
        else:
            return {"error": "Job not found"}
    
    def list_running_jobs(self) -> Dict[str, Any]:
        """
        List all currently running jobs
        """
        return {
            job_id: job_info for job_id, job_info in self.running_jobs.items()
            if job_info["status"] == "running"
        }

# Global job manager instance
background_jobs = BackgroundEnrichmentJobs()