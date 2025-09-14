-- Insert Pack Query
INSERT INTO session_pack_plan 
(user_id, session_id, pack, constraint_report, status, created_at, llm_model_used, processing_time_ms)
VALUES 
(:user_id, :session_id, :pack, :constraint_report, 'planned', NOW(), :llm_model_used, :processing_time_ms)
ON CONFLICT (session_id) DO UPDATE SET
pack = EXCLUDED.pack,
constraint_report = EXCLUDED.constraint_report,
updated_at = NOW();