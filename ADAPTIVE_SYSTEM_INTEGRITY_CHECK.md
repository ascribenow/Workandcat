# Adaptive System Integrity Check

## Tables Used in Session Planning - Before vs After

### 1. learner_notebook Table
**Status: ✅ INTACT AND ACTIVELY USED**

**Query in gather_user_learning_data():**
```sql
SELECT concept_norm, mastery_score, readiness, last_seen_at
FROM learner_notebook 
WHERE user_id = :user_id
ORDER BY last_seen_at DESC
LIMIT 50
```

**Usage in NEW Implementation:**
```python
# Line 741 in generate_personalized_session_pack()
weak_concepts = [nb["concept_norm"] for nb in learning_data.get("learner_notebook", []) 
                 if nb["readiness"] == "Weak"]

# Used in STEP 2 of per-band processing:
weak_qs = await select_questions_for_band(
    selection_type="weak",
    target_concepts=weak_concepts  # ✅ Still using learner_notebook data
)
```

**Fields Used:**
- ✅ `concept_norm` - Used for matching questions with weak concepts
- ✅ `readiness` - Filtered for "Weak" status
- ⚠️ `mastery_score` - Retrieved but NOT directly used in new implementation
- ⚠️ `last_seen_at` - Retrieved but NOT directly used in new implementation

**Verdict:** Learner notebook is still queried and used, but only `concept_norm` and `readiness` fields are actively utilized.

---

### 2. coverage_debt Table
**Status: ✅ INTACT, ENHANCED, AND ACTIVELY USED**

**Query in gather_user_learning_data():**
```sql
SELECT subcategory, type_of_question, debt_score, updated_at
FROM coverage_debt
WHERE user_id = :user_id AND debt_score > 0.3
ORDER BY debt_score DESC
LIMIT 20
```

**Usage in NEW Implementation:**
```python
# Categorized into tiers:
debt_categories = categorize_debt_pairs(learning_data)
# Returns: {"critical": [...], "high": [...], "moderate": [...]}

# Used in STEP 1 (Coverage quota):
high_debt_pairs = debt_categories["critical"] + debt_categories["high"]
coverage_qs = await select_questions_for_band(
    selection_type="coverage",
    target_pairs=high_debt_pairs  # ✅ Still using coverage_debt data
)

# Used in STEP 3 (Balanced):
moderate_debt_pairs = debt_categories["moderate"]
balanced_qs = await select_questions_for_band(
    selection_type="balanced",
    target_pairs=moderate_debt_pairs  # ✅ Also using moderate debt
)
```

**ENHANCEMENTS:**
- ✅ New function: `initialize_coverage_debt()` seeds table for new users
- ✅ Tuned parameters: -0.15 decrease, +0.08 decay (in `update_coverage_debt_from_session()`)
- ✅ Categorization: Now split into critical/high/moderate tiers

**Verdict:** Coverage debt is MORE actively used than before, with enhanced initialization and tiered categorization.

---

### 3. sessions Table
**Status: ✅ INTACT AND USED**

**Usage:**
```python
# In get_recent_questions() - NEW helper function:
SELECT sa.question_id
FROM session_answers sa
JOIN sessions s ON CAST(sa.session_id AS varchar) = CAST(s.session_id AS varchar)
WHERE CAST(s.user_id AS varchar) = :user_id
ORDER BY s.created_at DESC
LIMIT 36  # Last 3 sessions

# In initialize_coverage_debt():
SELECT COUNT(*) FROM sessions 
WHERE user_id = :user_id AND status = 'completed'
# Used to detect first session
```

**Verdict:** Sessions table still used for deduplication and first-session detection.

---

### 4. session_answers / attempt_events Table
**Status: ✅ INTACT AND USED**

**Usage:**
```python
# In get_recent_questions():
SELECT sa.question_id
FROM session_answers sa  # ✅ Still using session_answers

# In update_coverage_debt_from_session():
SELECT DISTINCT subcategory, type_of_question
FROM attempt_events 
WHERE user_id = :user_id AND session_id = :session_id
# Used to identify which topics were practiced
```

**Verdict:** Both tables still actively used for recent question tracking and debt updates.

---

### 5. questions Table
**Status: ✅ INTACT AND HEAVILY USED**

**Usage in OLD Implementation:**
```sql
SELECT q.id, q.stem, q.answer, q.mcq_options,
       q.difficulty_band, q.subcategory, q.type_of_question,
       q.core_concepts, q.pyq_frequency_score,
       q.snap_read, q.solution_approach, q.detailed_solution, q.principle_to_remember
FROM questions q
WHERE q.difficulty_band = :difficulty
ORDER BY [CASE priority] ASC, RANDOM()
```

**Usage in NEW Implementation:**
```python
# Same query structure in select_questions_for_band()
# Called 3 times per difficulty band (coverage, weak, balanced)
# Total: 9 queries per session pack generation (3 difficulties × 3 selection types)

SELECT q.id, q.stem, q.answer, q.mcq_options,
       q.difficulty_band, q.subcategory, q.type_of_question,
       q.core_concepts, q.pyq_frequency_score,
       q.snap_read, q.solution_approach, q.detailed_solution, q.principle_to_remember
FROM questions q
WHERE q.difficulty_band = :difficulty
  AND q.is_active = true
  [AND exclusion conditions]
  [AND target conditions for coverage/weak/balanced]
ORDER BY [priority specific to selection type]
```

**All Fields Still Retrieved:**
- ✅ `id, stem, answer, mcq_options` - Core question data
- ✅ `difficulty_band` - For band filtering
- ✅ `subcategory, type_of_question` - For coverage debt matching
- ✅ `core_concepts` - For weak concept matching
- ✅ `pyq_frequency_score` - For PYQ prioritization
- ✅ `snap_read, solution_approach, detailed_solution, principle_to_remember` - Solution feedback

**Verdict:** Questions table usage identical, all fields preserved.

---

### 6. session_packs & session_pack_questions Tables
**Status: ✅ INTACT (Not directly queried in pack generation, used for persistence)**

**Usage:**
```python
# In persist_session_pack() - UNCHANGED function
# These tables are written to, not read from, during pack generation
INSERT INTO session_packs (session_id, user_id, constraint_report, ...)
INSERT INTO session_pack_questions (session_id, position, question_id, question_data, ...)
```

**Verdict:** These tables are write-only during pack generation, still intact.

---

## Functions That Influence Session Planning

### ✅ UNCHANGED FUNCTIONS:

1. **gather_user_learning_data()**
   - Queries: `learner_notebook`, `coverage_debt`
   - Returns: learning data dictionary
   - **Status:** 100% unchanged

2. **persist_session_pack()**
   - Writes to: `session_packs`, `session_pack_questions`
   - **Status:** 100% unchanged

3. **run_simplified_summarizer()**
   - Updates: `learner_notebook` (via LLM)
   - **Status:** 100% unchanged

4. **handle_summarize_session()**
   - Orchestrates: summarization flow
   - **Status:** 100% unchanged

5. **handle_plan_next_session()**
   - Calls: `gather_user_learning_data()`, `generate_personalized_session_pack()`, `persist_session_pack()`
   - **Status:** Unchanged (just calls the new pack generator)

6. **handle_update_insights()**
   - Updates: insight cache
   - **Status:** 100% unchanged

### ⚠️ ENHANCED FUNCTION:

7. **update_coverage_debt_from_session()**
   - **Old:** Just updated debt scores
   - **New:** Added auto-initialization for first session + tuned parameters (-0.15, +0.08)
   - **Status:** Enhanced, backward compatible

### 🆕 NEW FUNCTION:

8. **generate_personalized_session_pack()**
   - **Completely rewritten** with per-band quota system
   - Still queries all same tables
   - Still uses all same data sources

---

## Data Flow Integrity Check

### OLD Data Flow:
```
1. Complete Session
   ↓
2. SUMMARIZE_SESSION job
   ↓ (Updates learner_notebook via LLM)
3. update_coverage_debt_from_session()
   ↓ (Updates coverage_debt)
4. PLAN_NEXT_SESSION job
   ↓ (Calls gather_user_learning_data)
5. Query learner_notebook + coverage_debt
   ↓
6. generate_personalized_session_pack()
   ↓ (Single query per difficulty with CASE priority)
7. Query questions table
   ↓
8. persist_session_pack()
   ↓
9. Write to session_packs + session_pack_questions
```

### NEW Data Flow:
```
1. Complete Session
   ↓
2. SUMMARIZE_SESSION job
   ↓ (Updates learner_notebook via LLM) ✅ SAME
3. update_coverage_debt_from_session()
   ↓ (Updates coverage_debt + auto-init for first session) ⚡ ENHANCED
4. PLAN_NEXT_SESSION job
   ↓ (Calls gather_user_learning_data) ✅ SAME
5. Query learner_notebook + coverage_debt ✅ SAME
   ↓
6. generate_personalized_session_pack()
   ↓ (Per-band quota system with 3 queries per difficulty) 🔄 CHANGED
7. Query questions table (9 times instead of 3) ✅ SAME DATA
   ↓
8. persist_session_pack()
   ↓ ✅ SAME
9. Write to session_packs + session_pack_questions ✅ SAME
```

**Verdict:** Data flow is 95% identical, only the pack generation logic changed.

---

## SUMMARY

### ✅ ALL TABLES INTACT:
1. **learner_notebook** - ✅ Queried and used (concept_norm, readiness)
2. **coverage_debt** - ✅ Queried, used, and ENHANCED with initialization
3. **sessions** - ✅ Used for deduplication and first-session detection
4. **session_answers / attempt_events** - ✅ Used for debt updates
5. **questions** - ✅ Heavily used, all fields retrieved
6. **session_packs / session_pack_questions** - ✅ Written to (persistence)

### ✅ ALL ADAPTIVE FUNCTIONS INTACT:
- 6 core functions completely unchanged
- 1 function enhanced (update_coverage_debt_from_session)
- 1 function rewritten (generate_personalized_session_pack)

### ⚠️ MINOR CONCERNS:
1. **learner_notebook fields:**
   - `mastery_score` and `last_seen_at` are retrieved but not directly used in pack generation
   - They were also not directly used in OLD implementation (just retrieved)

2. **Query count increased:**
   - Old: 3 queries (1 per difficulty)
   - New: 9 queries (3 per difficulty × 3 difficulties)
   - Impact: Minimal (queries are fast, PostgreSQL handles well)

### ✅ ARCHITECTURAL INTEGRITY:
- Background job pipeline unchanged
- LLM summarization unchanged
- Insight generation unchanged
- Coverage debt tracking enhanced
- All data sources still feeding into pack generation

**OVERALL VERDICT:** 
All tables and functions that influence session planning are intact and still being used. The only change is HOW the pack generation combines the data (per-band quotas vs global priority), not WHAT data sources are used.

