"""
Time-Weighted Frequency Analyzer
Handles 20 years of PYQ data with emphasis on the last 10 years
"""

import logging
import math
from typing import Dict, List, Optional, Any, NamedTuple
from dataclasses import dataclass
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)

@dataclass
class TemporalFrequencyConfig:
    """Configuration for time-weighted frequency analysis"""
    total_data_years: int = 20
    relevance_window_years: int = 10
    decay_rate: float = 0.08
    trend_analysis_years: int = 5
    min_occurrences_threshold: int = 2

# Predefined analysis configurations
CAT_ANALYSIS_CONFIG = TemporalFrequencyConfig(
    total_data_years=20,
    relevance_window_years=10, 
    decay_rate=0.08,
    trend_analysis_years=5,
    min_occurrences_threshold=2
)

RECENT_EMPHASIS_CONFIG = TemporalFrequencyConfig(
    total_data_years=20,
    relevance_window_years=8,
    decay_rate=0.12,
    trend_analysis_years=4,
    min_occurrences_threshold=1
)

CONSERVATIVE_CONFIG = TemporalFrequencyConfig(
    total_data_years=20,
    relevance_window_years=12,
    decay_rate=0.05,
    trend_analysis_years=6,
    min_occurrences_threshold=3
)

class TemporalPattern(NamedTuple):
    """Represents temporal frequency pattern for a concept"""
    concept_id: str
    total_occurrences: int
    relevance_window_occurrences: int
    weighted_frequency_score: float
    trend_direction: str  # "increasing", "stable", "decreasing", "emerging", "declining"
    trend_strength: float  # 0.0 to 1.0
    recency_score: float  # How recent the occurrences are
    yearly_breakdown: Dict[int, int]

class TimeWeightedFrequencyAnalyzer:
    """
    Analyzes 20 years of PYQ data with intelligent time weighting
    Emphasizes last 10 years while preserving historical context
    """
    
    def __init__(self, config: TemporalFrequencyConfig = CAT_ANALYSIS_CONFIG):
        self.config = config
        self.current_year = datetime.now().year
        
    def calculate_time_weighted_frequency(
        self, 
        yearly_occurrences: Dict[int, int], 
        total_pyq_per_year: Dict[int, int]
    ) -> Dict[str, float]:
        """
        Calculate time-weighted frequency with exponential decay
        
        Args:
            yearly_occurrences: {year: count} of question occurrences
            total_pyq_per_year: {year: total_questions} for normalization
            
        Returns:
            Dictionary with various frequency metrics
        """
        try:
            if not yearly_occurrences:
                return self._empty_frequency_result()
            
            # Calculate weighted frequency with time decay
            weighted_sum = 0.0
            weight_sum = 0.0
            relevance_window_sum = 0.0
            relevance_window_weight = 0.0
            
            relevance_cutoff_year = self.current_year - self.config.relevance_window_years
            
            for year, occurrences in yearly_occurrences.items():
                if year > self.current_year:
                    continue  # Skip future years
                    
                years_ago = self.current_year - year
                
                # Exponential decay weighting
                weight = math.exp(-self.config.decay_rate * years_ago)
                
                # Normalize by total questions that year
                total_that_year = total_pyq_per_year.get(year, 100)  # Default to 100
                normalized_frequency = occurrences / total_that_year if total_that_year > 0 else 0
                
                weighted_sum += normalized_frequency * weight
                weight_sum += weight
                
                # Separate calculation for relevance window
                if year >= relevance_cutoff_year:
                    relevance_window_sum += normalized_frequency * weight
                    relevance_window_weight += weight
            
            # Calculate final metrics
            overall_weighted_frequency = weighted_sum / weight_sum if weight_sum > 0 else 0.0
            relevance_weighted_frequency = (relevance_window_sum / relevance_window_weight 
                                          if relevance_window_weight > 0 else 0.0)
            
            # Calculate trend metrics
            trend_metrics = self.detect_trend_pattern(yearly_occurrences)
            
            # Calculate recency score
            recency_score = self.calculate_recency_score(yearly_occurrences)
            
            # Apply trend adjustment
            trend_adjustment = self.get_trend_adjustment(trend_metrics['direction'])
            final_frequency = relevance_weighted_frequency * trend_adjustment
            
            return {
                'overall_weighted_frequency': overall_weighted_frequency,
                'relevance_weighted_frequency': relevance_weighted_frequency,
                'final_frequency_score': final_frequency,
                'trend_direction': trend_metrics['direction'],
                'trend_strength': trend_metrics['strength'],
                'recency_score': recency_score,
                'total_occurrences': sum(yearly_occurrences.values()),
                'relevance_window_occurrences': sum(
                    count for year, count in yearly_occurrences.items() 
                    if year >= relevance_cutoff_year
                )
            }
            
        except Exception as e:
            logger.error(f"Error calculating time-weighted frequency: {e}")
            return self._empty_frequency_result()
    
    def detect_trend_pattern(self, yearly_occurrences: Dict[int, int]) -> Dict[str, Any]:
        """
        Detect trend pattern in the last N years
        """
        try:
            # Get recent years data for trend analysis
            trend_years = self.config.trend_analysis_years
            recent_years = sorted([y for y in yearly_occurrences.keys() 
                                 if y >= self.current_year - trend_years])
            
            if len(recent_years) < 3:
                return {'direction': 'stable', 'strength': 0.0, 'pattern': 'insufficient_data'}
            
            recent_counts = [yearly_occurrences.get(year, 0) for year in recent_years]
            
            # Linear regression for trend
            x = np.array(recent_years)
            y = np.array(recent_counts)
            
            if len(x) > 1 and np.std(x) > 0:
                slope, intercept = np.polyfit(x, y, 1)
                correlation = np.corrcoef(x, y)[0, 1] if len(x) > 2 else 0.0
                
                # Determine trend direction and strength
                if abs(slope) < 0.1:
                    direction = "stable"
                elif slope > 0.5 and correlation > 0.6:
                    direction = "increasing"
                elif slope < -0.5 and correlation < -0.6:
                    direction = "decreasing"
                elif slope > 0 and any(yearly_occurrences.get(y, 0) == 0 
                                     for y in range(self.current_year - 10, self.current_year - 5)):
                    direction = "emerging"
                elif slope < 0 and yearly_occurrences.get(self.current_year - 1, 0) == 0:
                    direction = "declining"
                else:
                    direction = "stable"
                
                strength = min(1.0, abs(correlation))
                
                return {
                    'direction': direction,
                    'strength': strength,
                    'slope': slope,
                    'correlation': correlation,
                    'pattern': 'trend_detected'
                }
            else:
                return {'direction': 'stable', 'strength': 0.0, 'pattern': 'no_variation'}
                
        except Exception as e:
            logger.error(f"Error detecting trend pattern: {e}")
            return {'direction': 'stable', 'strength': 0.0, 'pattern': 'error'}
    
    def calculate_recency_score(self, yearly_occurrences: Dict[int, int]) -> float:
        """
        Calculate how recent the occurrences are (0.0 to 1.0)
        """
        try:
            if not yearly_occurrences:
                return 0.0
            
            total_occurrences = sum(yearly_occurrences.values())
            if total_occurrences == 0:
                return 0.0
            
            # Weight more recent years higher
            weighted_recency_sum = 0.0
            
            for year, count in yearly_occurrences.items():
                if year > self.current_year:
                    continue
                    
                years_ago = self.current_year - year
                recency_weight = math.exp(-0.15 * years_ago)  # Steeper decay for recency
                weighted_recency_sum += count * recency_weight
            
            # Normalize by total occurrences
            recency_score = weighted_recency_sum / total_occurrences
            
            # Scale to 0-1 range
            return min(1.0, recency_score)
            
        except Exception as e:
            logger.error(f"Error calculating recency score: {e}")
            return 0.0
    
    def get_trend_adjustment(self, trend_direction: str) -> float:
        """
        Get multiplier based on trend direction
        """
        adjustments = {
            "increasing": 1.2,    # Boost increasing trends
            "emerging": 1.3,      # Boost new/emerging topics
            "stable": 1.0,        # No adjustment
            "decreasing": 0.9,    # Slight penalty for decreasing
            "declining": 0.8      # Penalty for declining topics
        }
        
        return adjustments.get(trend_direction, 1.0)
    
    def create_temporal_pattern(
        self, 
        concept_id: str, 
        yearly_occurrences: Dict[int, int],
        total_pyq_count_per_year: Dict[int, int]
    ) -> TemporalPattern:
        """
        Create comprehensive temporal pattern analysis
        """
        try:
            # Calculate metrics
            frequency_metrics = self.calculate_time_weighted_frequency(
                yearly_occurrences, total_pyq_count_per_year
            )
            
            trend_metrics = self.detect_trend_pattern(yearly_occurrences)
            recency_score = self.calculate_recency_score(yearly_occurrences)
            
            # Calculate relevance window occurrences
            relevance_cutoff_year = self.current_year - self.config.relevance_window_years
            relevance_window_occurrences = sum(
                count for year, count in yearly_occurrences.items() 
                if year >= relevance_cutoff_year
            )
            
            return TemporalPattern(
                concept_id=concept_id,
                total_occurrences=sum(yearly_occurrences.values()),
                relevance_window_occurrences=relevance_window_occurrences,
                weighted_frequency_score=frequency_metrics['final_frequency_score'],
                trend_direction=trend_metrics['direction'],
                trend_strength=trend_metrics['strength'],
                recency_score=recency_score,
                yearly_breakdown=yearly_occurrences.copy()
            )
            
        except Exception as e:
            logger.error(f"Error creating temporal pattern: {e}")
            return TemporalPattern(
                concept_id=concept_id,
                total_occurrences=0,
                relevance_window_occurrences=0,
                weighted_frequency_score=0.0,
                trend_direction="stable",
                trend_strength=0.0,
                recency_score=0.0,
                yearly_breakdown={}
            )
    
    def generate_frequency_insights(self, pattern: TemporalPattern) -> Dict[str, str]:
        """
        Generate human-readable insights from temporal pattern
        """
        try:
            insights = {}
            
            # Frequency category
            if pattern.weighted_frequency_score >= 0.7:
                frequency_cat = "High"
            elif pattern.weighted_frequency_score >= 0.4:
                frequency_cat = "Medium"
            elif pattern.weighted_frequency_score > 0:
                frequency_cat = "Low"
            else:
                frequency_cat = "None"
            
            insights['frequency_category'] = frequency_cat
            
            # Trend description
            trend_desc = f"{pattern.trend_direction.title()} trend"
            if pattern.trend_strength > 0.7:
                trend_desc += f" (strength: {pattern.trend_strength:.2f})"
            insights['trend_description'] = trend_desc
            
            # Recency description
            if pattern.recency_score > 0.8:
                recency_desc = "Very recent appearances - high current relevance"
            elif pattern.recency_score > 0.5:
                recency_desc = "Recent appearances - good current relevance"  
            elif pattern.recency_score > 0.2:
                recency_desc = "Some recent appearances - moderate relevance"
            else:
                recency_desc = "Mostly historical appearances - lower current relevance"
            
            insights['recency_description'] = recency_desc
            
            # Combined summary
            summary_parts = []
            
            if pattern.trend_direction == "increasing":
                summary_parts.append("📈 This topic is becoming more frequent in recent CAT exams")
            elif pattern.trend_direction == "emerging":
                summary_parts.append("🆕 This is an emerging topic gaining attention")
            elif pattern.trend_direction == "decreasing":
                summary_parts.append("📉 This topic has been appearing less frequently")
            elif pattern.trend_direction == "declining":
                summary_parts.append("⬇️ This topic is declining in importance")
            
            if pattern.recency_score > 0.7:
                summary_parts.append("⭐ Very recent appearances")
            elif pattern.recency_score > 0.4:
                summary_parts.append("🕒 Recent appearances")
            
            if pattern.relevance_window_occurrences >= 10:
                summary_parts.append(f"📊 {pattern.relevance_window_occurrences} occurrences in last {self.config.relevance_window_years} years")
            
            insights['summary'] = "; ".join(summary_parts) if summary_parts else "Standard frequency pattern"
            
            return insights
            
        except Exception as e:
            logger.error(f"Error generating insights: {e}")
            return {
                'frequency_category': 'Unknown',
                'trend_description': 'Analysis error',
                'recency_description': 'Analysis error',
                'summary': 'Error generating insights'
            }
    
    def _empty_frequency_result(self) -> Dict[str, float]:
        """Return empty/default frequency result"""
        return {
            'overall_weighted_frequency': 0.0,
            'relevance_weighted_frequency': 0.0,
            'final_frequency_score': 0.0,
            'trend_direction': 'stable',
            'trend_strength': 0.0,
            'recency_score': 0.0,
            'total_occurrences': 0,
            'relevance_window_occurrences': 0
        }
    
    def analyze_frequency_distribution(
        self, 
        temporal_patterns: List[TemporalPattern]
    ) -> Dict[str, Any]:
        """
        Analyze overall frequency distribution across multiple patterns
        """
        try:
            if not temporal_patterns:
                return {'error': 'No patterns provided'}
            
            # Categorize patterns
            categories = {'High': [], 'Medium': [], 'Low': [], 'None': []}
            
            for pattern in temporal_patterns:
                if pattern.weighted_frequency_score >= 0.7:
                    categories['High'].append(pattern)
                elif pattern.weighted_frequency_score >= 0.4:
                    categories['Medium'].append(pattern)
                elif pattern.weighted_frequency_score > 0:
                    categories['Low'].append(pattern)
                else:
                    categories['None'].append(pattern)
            
            # Trend analysis
            trend_counts = {}
            for pattern in temporal_patterns:
                trend = pattern.trend_direction
                trend_counts[trend] = trend_counts.get(trend, 0) + 1
            
            # Overall statistics
            total_occurrences = sum(p.total_occurrences for p in temporal_patterns)
            avg_frequency_score = sum(p.weighted_frequency_score for p in temporal_patterns) / len(temporal_patterns)
            
            return {
                'total_concepts_analyzed': len(temporal_patterns),
                'frequency_distribution': {cat: len(patterns) for cat, patterns in categories.items()},
                'trend_distribution': trend_counts,
                'total_pyq_occurrences': total_occurrences,
                'average_frequency_score': avg_frequency_score,
                'high_frequency_concepts': [p.concept_id for p in categories['High']],
                'emerging_concepts': [p.concept_id for p in temporal_patterns if p.trend_direction == 'emerging']
            }
            
        except Exception as e:
            logger.error(f"Error analyzing frequency distribution: {e}")
            return {'error': str(e)}