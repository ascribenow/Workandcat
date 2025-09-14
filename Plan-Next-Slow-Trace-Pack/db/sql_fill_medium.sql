-- Medium Fill Selection Query (Cold Start)  
SELECT id, subcategory, difficulty_band, pyq_frequency_score, stem, mcq_options, right_answer
FROM questions  
WHERE difficulty_band = 'Medium' 
  AND pyq_frequency_score < 1.0
ORDER BY RANDOM()
LIMIT 30;