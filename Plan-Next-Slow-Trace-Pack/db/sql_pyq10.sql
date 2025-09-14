-- PYQ 1.0 Selection Query (Cold Start)
SELECT id, subcategory, difficulty_band, pyq_frequency_score, stem, mcq_options, right_answer  
FROM questions
WHERE pyq_frequency_score = 1.0 
  AND difficulty_band IN ('Easy', 'Medium', 'Hard')
ORDER BY RANDOM()
LIMIT 50;