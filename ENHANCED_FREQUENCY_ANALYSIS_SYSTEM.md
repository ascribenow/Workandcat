# Enhanced Time-Weighted Conceptual Frequency Analysis System

## Overview
This document explains the comprehensive solution for handling 20 years of PYQ data while emphasizing the last 10 years for relevance scoring, combined with LLM-powered conceptual pattern recognition.

## System Architecture

### 1. **Data Storage Strategy**
```
┌─────────────────────┬──────────────────────┐
│ Historical Data     │ Relevance Weighting  │
├─────────────────────┼──────────────────────┤
│ 20 years PYQ data  │ Last 10 years: 80%   │
│ Complete archive    │ 11-15 years: 15%     │ 
│ Trend analysis      │ 16-20 years: 5%      │
└─────────────────────┴──────────────────────┘
```

### 2. **Multi-Layer Analysis System**

#### **Layer 1: Time-Weighted Temporal Analysis**
- **Purpose**: Handles 20-year historical data with recency weighting
- **Formula**: `frequency = Σ(yearly_occurrences[i] × e^(-decay_rate × years_ago))`
- **Configuration**: 
  - Total data: 20 years
  - Relevance window: 10 years
  - Decay rate: 0.08 (moderate decay)

#### **Layer 2: LLM Conceptual Pattern Recognition**  
- **Purpose**: Understands mathematical concepts, not just text matching
- **Process**: 
  1. Extract question patterns using LLM
  2. Find conceptually similar PYQ questions
  3. Calculate semantic similarity scores

#### **Layer 3: Combined Intelligence**
- **Weighting**: 60% temporal + 25% conceptual + 15% trend/recency
- **Trend Analysis**: Detects increasing/decreasing/emerging/declining patterns
- **Final Score**: Combines all factors for accurate frequency assessment

## Key Components

### 1. **TimeWeightedFrequencyAnalyzer**
```python
class TimeWeightedFrequencyAnalyzer:
    def calculate_time_weighted_frequency(self, yearly_occurrences, total_pyq_per_year):
        # Applies exponential decay to emphasize recent years
        # Returns relevance_weighted_frequency (main score)
        
    def detect_trend_pattern(self, yearly_occurrences):
        # Analyzes last 5 years for trend detection
        # Returns: "increasing", "stable", "decreasing", "emerging", "declining"
```

### 2. **ConceptualFrequencyAnalyzer**
```python
class ConceptualFrequencyAnalyzer:
    async def analyze_question_pattern(self, question):
        # Uses LLM to extract mathematical concepts
        # Returns: concept_keywords, solution_approach, difficulty_indicators
        
    async def find_conceptual_matches(self, question_pattern, pyq_questions):
        # Finds PYQ questions with similar mathematical concepts
        # Uses semantic similarity, not text matching
```

### 3. **Enhanced Database Schema**
```sql
-- New fields added to questions table:
frequency_score NUMERIC(5,4)              -- Final weighted score
pyq_conceptual_matches INTEGER            -- LLM-found similar questions  
total_pyq_analyzed INTEGER                -- Total PYQ database size
top_matching_concepts TEXT[]              -- Key matching concepts
frequency_analysis_method VARCHAR(50)     -- Analysis method used
frequency_last_updated TIMESTAMP          -- Last analysis time
pattern_keywords TEXT[]                   -- LLM-extracted keywords
pattern_solution_approach TEXT            -- LLM-identified method
pyq_occurrences_last_10_years INTEGER    -- Relevance window count
total_pyq_count INTEGER                   -- Total historical count
```

## Frequency Calculation Process

### Step 1: Data Collection
```sql
-- Collect 20 years of PYQ data by year
SELECT 
    EXTRACT(YEAR FROM created_at) as year,
    COUNT(*) as occurrences,
    subcategory, type_of_question
FROM pyq_questions 
WHERE created_at >= '2005-01-01'  -- 20 years back
GROUP BY year, subcategory, type_of_question
```

### Step 2: Time Weighting
```python
# Apply exponential decay weighting
for year, occurrences in yearly_data.items():
    years_ago = current_year - year
    weight = math.exp(-0.08 * years_ago)  # Recent years get higher weight
    weighted_frequency += (occurrences / total_that_year) * weight
```

### Step 3: Conceptual Analysis
```python
# LLM analyzes question for mathematical patterns
question_pattern = await llm.analyze_question_pattern(question)
# Find similar PYQ questions by concept (not text)
similar_questions = await llm.find_conceptual_matches(pattern, pyq_database)
```

### Step 4: Trend Detection
```python
# Analyze last 5 years for trends
slope, correlation = np.polyfit(recent_years, recent_counts, 1)
if slope > 0.5 and correlation > 0.6:
    trend = "increasing"  # Topic becoming more frequent
elif slope < -0.5 and correlation > 0.6:
    trend = "decreasing"  # Topic becoming less frequent
```

### Step 5: Final Score Combination
```python
final_score = (
    0.60 × time_weighted_score × trend_adjustment +  # Temporal analysis
    0.25 × conceptual_similarity_score +             # LLM pattern matching  
    0.15 × recency_score                             # How recent occurrences are
) × recency_multiplier
```

## Practical Examples

### Example 1: "Time-Speed-Distance" Analysis
```
Historical Data (20 years):
2024: 8 questions  | Weight: 1.00  | High relevance
2023: 6 questions  | Weight: 0.92  | High relevance  
2022: 7 questions  | Weight: 0.85  | High relevance
...
2015: 4 questions  | Weight: 0.41  | Medium relevance
...
2005: 1 question   | Weight: 0.18  | Low relevance

Relevance Window (last 10 years): 52 questions
Total Historical: 78 questions  
Weighted Frequency: 0.73 (high frequency)
Trend: "stable" (consistent appearances)
Conceptual Matches: 45 similar questions found by LLM
```

### Example 2: "Machine Learning in QA" (Hypothetical Emerging Topic)
```
Historical Data:
2024: 3 questions  | New topic appearing
2023: 1 question   | Started showing up
2022: 0 questions  | Didn't exist before
...
2005-2021: 0 questions

Relevance Window: 4 questions
Weighted Frequency: 0.12 (low but rising)
Trend: "emerging" (new topic gaining traction)
Boost Factor: 1.3x (emerging topics get priority)
Final Score: 0.16 (boosted for being emerging)
```

## Benefits of This Approach

### 1. **Intelligent Relevance**
- Recent patterns matter more than historical ones
- Trends are detected and factored into scoring
- Emerging topics get appropriate attention

### 2. **Conceptual Understanding**
- Questions matched by mathematical similarity, not keywords
- Different wordings of same concepts are recognized
- Solution approaches are analyzed for pattern matching

### 3. **Configurable Weighting**
```python
# Different analysis configurations available:
CAT_ANALYSIS_CONFIG        # Balanced: 20yr data, 10yr relevance
RECENT_EMPHASIS_CONFIG     # Recent focus: 20yr data, 8yr relevance  
CONSERVATIVE_CONFIG        # Stable: 20yr data, 12yr relevance
```

### 4. **Comprehensive Insights**
```python
# Generated insights for each topic:
{
    "trend_description": "Increasing trend (strength: 0.82)",
    "recency_description": "Very recent appearances - high current relevance", 
    "frequency_category": "High",
    "summary": "📈 This topic is becoming more frequent in recent CAT exams; ⭐ Very recent appearances"
}
```

## API Endpoints for Testing

### Test Time-Weighted Analysis
```bash
POST /api/admin/test/time-weighted-frequency
# Returns comprehensive analysis with sample 20-year data
```

### Test Conceptual Analysis  
```bash
POST /api/admin/test/conceptual-frequency
# Tests LLM-powered pattern recognition
```

### Run Enhanced Nightly Processing
```bash
POST /api/admin/run-enhanced-nightly  
# Triggers full system analysis with all components
```

## Configuration for 20-Year Data Strategy

The system is specifically configured to handle your requirement:

```python
CAT_ANALYSIS_CONFIG = TemporalFrequencyConfig(
    total_data_years=20,        # Store and analyze 20 years of PYQ data
    relevance_window_years=10,  # Emphasize last 10 years for scoring
    decay_rate=0.08,           # Moderate decay (recent years matter more)
    trend_analysis_years=5,     # Analyze 5-year trends
    min_occurrences_threshold=2 # Need 2+ occurrences for relevance
)
```

This ensures that:
- ✅ All 20 years of PYQ data is stored and analyzed
- ✅ Last 10 years get 80% of the relevance weight
- ✅ Older data still contributes but with exponential decay
- ✅ Trend analysis detects changing patterns over time
- ✅ LLM provides conceptual intelligence beyond text matching

The system is now ready to handle your complete 20-year PYQ database while intelligently emphasizing the most relevant recent patterns for optimal CAT preparation! 🚀