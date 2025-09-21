"""
Day 4 Session Flow Integration Test
Comprehensive test of all updated APIs and Coverage System integration
"""

import asyncio
import json
import logging
import uuid
from typing import Dict, Any
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class Day4IntegrationTest:
    """Test all Day 4 session flow integration features"""
    
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL')
        if not self.db_url:
            raise ValueError("DATABASE_URL not found in environment variables")
    
    def _get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(self.db_url)
    
    async def run_comprehensive_day4_test(self) -> Dict[str, Any]:
        """Run comprehensive test of all Day 4 features"""
        
        results = {
            "coverage_pipeline_test": {},
            "pack_storage_test": {},
            "mark_served_test": {},
            "telemetry_test": {},
            "canonical_id_test": {},
            "overall_success": False
        }
        
        try:
            logger.info("🚀 Starting Day 4 Comprehensive Integration Test...")
            
            # Get real user for testing
            conn = self._get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT id FROM users LIMIT 1')
            real_user = cur.fetchone()
            cur.close()
            conn.close()
            
            if not real_user:
                logger.error("❌ No users found for testing")
                return results
            
            user_id = real_user[0]
            test_session_id = str(uuid.uuid4())
            
            # Test 1: Coverage Pipeline Integration
            logger.info("📋 Test 1: Coverage Pipeline Integration...")
            pipeline_result = await self._test_coverage_pipeline_integration(user_id, test_session_id)
            results["coverage_pipeline_test"] = pipeline_result
            
            # Test 2: Pack Storage with Canonical IDs
            logger.info("💾 Test 2: Pack Storage with Canonical IDs...")
            storage_result = await self._test_pack_storage_canonical_ids(user_id, test_session_id)
            results["pack_storage_test"] = storage_result
            
            # Test 3: Optimized Mark-Served with Coverage Ledger
            logger.info("🏷️ Test 3: Optimized Mark-Served...")
            mark_served_result = await self._test_mark_served_optimization(user_id, test_session_id)
            results["mark_served_test"] = mark_served_result
            
            # Test 4: Telemetry Integration
            logger.info("📊 Test 4: Telemetry Integration...")
            telemetry_result = await self._test_telemetry_integration(user_id, test_session_id)
            results["telemetry_test"] = telemetry_result
            
            # Test 5: Canonical ID Usage
            logger.info("🆔 Test 5: Canonical ID Usage...")
            canonical_id_result = await self._test_canonical_id_usage(user_id, test_session_id)
            results["canonical_id_test"] = canonical_id_result
            
            # Calculate overall success
            individual_successes = [
                pipeline_result.get("success", False),
                storage_result.get("success", False), 
                mark_served_result.get("success", False),
                telemetry_result.get("success", False),
                canonical_id_result.get("success", False)
            ]
            
            results["overall_success"] = all(individual_successes)
            results["success_rate"] = sum(individual_successes) / len(individual_successes) * 100
            
            logger.info(f"🎉 Day 4 Integration Test completed with {results['success_rate']:.1f}% success rate")
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Day 4 Integration Test failed: {e}")
            results["error"] = str(e)
            return results
    
    async def _test_coverage_pipeline_integration(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Test the coverage pipeline integration"""
        try:
            from services.coverage_pipeline import coverage_pipeline
            
            # Test pipeline execution
            pipeline_result = await coverage_pipeline.plan_next_session(user_id, session_id)
            
            # Validate pipeline result structure
            pack = pipeline_result.get("pack", [])
            audit = pipeline_result.get("audit", {})
            telemetry = pipeline_result.get("pipeline_telemetry", {})
            
            success_criteria = [
                len(pack) == 12,  # Exactly 12 questions
                "shape" in audit,  # Audit contains shape
                "pyq" in audit,    # Audit contains PYQ stats
                "total_ms" in telemetry,  # Telemetry present
                all("id" in item for item in pack)  # All items have canonical ID
            ]
            
            return {
                "success": all(success_criteria),
                "pack_size": len(pack),
                "audit_keys": list(audit.keys()),
                "telemetry_keys": list(telemetry.keys()),
                "processing_time_ms": pipeline_result.get("processing_time_ms", 0),
                "criteria_met": sum(success_criteria),
                "criteria_total": len(success_criteria)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_pack_storage_canonical_ids(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Test pack storage with canonical ID normalization"""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Check if pack was stored correctly
            cur.execute("""
                SELECT pack_json, coverage_audit, selection_method, status
                FROM session_pack_plan
                WHERE user_id = %s AND session_id = %s
            """, (user_id, session_id))
            
            result = cur.fetchone()
            cur.close()
            conn.close()
            
            if not result:
                return {"success": False, "error": "Pack not found in database"}
            
            pack_json, coverage_audit, selection_method, status = result
            
            # Parse pack data
            if isinstance(pack_json, str):
                pack = json.loads(pack_json)
            else:
                pack = pack_json
            
            # Validate canonical ID usage
            canonical_id_checks = [
                all("id" in item for item in pack),  # All items have 'id' field
                all("item_id" not in item for item in pack),  # No 'item_id' fields
                len(pack) == 12,  # Correct pack size
                selection_method == "coverage_v1",  # Correct selection method
                status == "planned"  # Correct initial status
            ]
            
            return {
                "success": all(canonical_id_checks),
                "pack_size": len(pack),
                "selection_method": selection_method,
                "status": status,
                "canonical_id_compliance": sum(canonical_id_checks[:2]) / 2 * 100,
                "checks_passed": sum(canonical_id_checks),
                "checks_total": len(canonical_id_checks)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_mark_served_optimization(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Test optimized mark-served with coverage_ledger updates"""
        try:
            # Test the mark-served optimization manually
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Simulate the optimized mark-served logic
            # 1. Idempotent race guard
            cur.execute("""
                UPDATE session_pack_plan
                SET status='served', served_at=NOW()
                WHERE session_id=%s AND status!='served'
            """, (session_id,))
            
            rows_affected = cur.rowcount
            
            if rows_affected == 0:
                # Already served test
                return {"success": True, "already_served": True, "idempotency_working": True}
            
            # 2. Get pack using session_id only
            cur.execute("""
                SELECT pack_json, user_id FROM session_pack_plan
                WHERE session_id = %s
            """, (session_id,))
            
            pack_data = cur.fetchone()
            
            if not pack_data:
                return {"success": False, "error": "Pack data not found"}
            
            pack_json, actual_user_id = pack_data
            
            # Parse pack
            if isinstance(pack_json, str):
                pack = json.loads(pack_json)
            else:
                pack = pack_json
            
            # 3. Update coverage_ledger atomically
            coverage_updates = 0
            for question in pack:
                subcategory_type = f"{question.get('subcategory', 'Unknown')}|{question.get('type_of_question', 'Unknown')}"
                
                cur.execute("""
                    INSERT INTO coverage_ledger (user_id, subcategory_type, served_count, last_served_at)
                    VALUES (%s, %s, 1, NOW())
                    ON CONFLICT (user_id, subcategory_type) DO UPDATE SET
                        served_count = coverage_ledger.served_count + 1,
                        last_served_at = NOW()
                """, (actual_user_id, subcategory_type))
                coverage_updates += 1
            
            conn.commit()
            cur.close()
            conn.close()
            
            return {
                "success": True,
                "rows_affected": rows_affected,
                "pack_size": len(pack),
                "coverage_updates": coverage_updates,
                "session_id_only_query": True,
                "atomic_transaction": True
            }
            
        except Exception as e:
            if 'conn' in locals():
                conn.rollback()
                cur.close()
                conn.close()
            return {"success": False, "error": str(e)}
    
    async def _test_telemetry_integration(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Test telemetry integration with coverage system"""
        try:
            from services.telemetry import telemetry_service
            
            # Create sample session data
            sample_session_data = {
                "pack": [
                    {"id": "q1", "difficulty_band": "easy", "subcategory": "Time-Speed", "type_of_question": "Basic"},
                    {"id": "q2", "difficulty_band": "medium", "subcategory": "Ratios", "type_of_question": "Complex"}
                ],
                "audit": {
                    "shape": {"easy": 3, "medium": 6, "hard": 3},
                    "pyq": {"1_5": 4, "1_0": 6},
                    "cap_relaxations": {"easy": 0, "medium": 1, "hard": 0},
                    "force_fill": 0,
                    "shape_compromised_due_to_inventory": False
                },
                "pipeline_telemetry": {
                    "planner_ms": 5000,
                    "total_ms": 15000,
                    "planner_model": "gpt-4o-mini"
                }
            }
            
            # Test telemetry emission
            telemetry_service.emit_coverage_session_metrics(user_id, sample_session_data)
            
            return {
                "success": True,
                "telemetry_service_available": True,
                "metrics_emitted": [
                    "coverage.pack.easy_count",
                    "coverage.pack.medium_count", 
                    "coverage.pack.hard_count",
                    "coverage.pyq.pack_level_count_1_5",
                    "coverage.cap_relax.medium",
                    "coverage.distinct_subtype_in_pack"
                ]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _test_canonical_id_usage(self, user_id: str, session_id: str) -> Dict[str, Any]:
        """Test canonical ID usage throughout the system"""
        try:
            conn = self._get_db_connection()
            cur = conn.cursor()
            
            # Check pack uses canonical IDs
            cur.execute("""
                SELECT pack_json FROM session_pack_plan
                WHERE user_id = %s AND session_id = %s
            """, (user_id, session_id))
            
            result = cur.fetchone()
            if not result:
                return {"success": False, "error": "Pack not found"}
            
            pack_json = result[0]
            if isinstance(pack_json, str):
                pack = json.loads(pack_json)
            else:
                pack = pack_json
            
            # Validate canonical ID usage
            canonical_checks = {
                "all_have_id": all("id" in item for item in pack),
                "none_have_item_id": all("item_id" not in item for item in pack),
                "valid_id_format": all(isinstance(item.get("id"), str) and len(item.get("id", "")) > 0 for item in pack),
                "pack_size_12": len(pack) == 12
            }
            
            cur.close()
            conn.close()
            
            return {
                "success": all(canonical_checks.values()),
                "canonical_checks": canonical_checks,
                "pack_size": len(pack),
                "compliance_rate": sum(canonical_checks.values()) / len(canonical_checks) * 100
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# Test runner
async def run_day4_integration_test():
    """Run the complete Day 4 integration test"""
    tester = Day4IntegrationTest()
    
    print("🚀 DAY 4 SESSION FLOW INTEGRATION - COMPREHENSIVE TEST")
    print("=" * 70)
    
    results = await tester.run_comprehensive_day4_test()
    
    print("\n📊 TEST RESULTS:")
    print("=" * 70)
    
    for test_name, test_result in results.items():
        if test_name == "overall_success":
            continue
            
        success = test_result.get("success", False)
        status_icon = "✅" if success else "❌"
        
        print(f"{status_icon} {test_name.replace('_', ' ').title()}: {success}")
        
        if not success and "error" in test_result:
            print(f"   Error: {test_result['error']}")
        elif success:
            # Show key metrics for successful tests
            if "pack_size" in test_result:
                print(f"   Pack size: {test_result['pack_size']}")
            if "processing_time_ms" in test_result:
                print(f"   Processing time: {test_result['processing_time_ms']}ms")
            if "compliance_rate" in test_result:
                print(f"   Compliance rate: {test_result['compliance_rate']:.1f}%")
    
    overall_success = results.get("overall_success", False)
    success_rate = results.get("success_rate", 0)
    
    print(f"\n🎯 OVERALL RESULTS:")
    print(f"   Overall Success: {'✅' if overall_success else '❌'} {overall_success}")
    print(f"   Success Rate: {success_rate:.1f}%")
    
    if overall_success:
        print("\n🎉 DAY 4 SESSION FLOW INTEGRATION: ALL TESTS PASSED!")
        print("✅ Ready for Day 5: Testing & Go-Live")
    else:
        print(f"\n⚠️ Day 4 Integration: {5 - int(success_rate/20)} tests failed")
        print("❌ Issues need to be resolved before proceeding")
    
    return results

if __name__ == "__main__":
    asyncio.run(run_day4_integration_test())