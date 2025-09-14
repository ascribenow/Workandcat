-- Medium Fill Selection Query (Cold Start)  
SELECT id, subcategory, difficulty_band, pyq_frequency_score, stem,
       mcq_option_a, mcq_option_b, mcq_option_c, mcq_option_d, right_answer
FROM questions  
WHERE difficulty_band = 'Medium' 
  AND pyq_frequency_score < 1.0
ORDER BY RANDOM()
LIMIT 30;