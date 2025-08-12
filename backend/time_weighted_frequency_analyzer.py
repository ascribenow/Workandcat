#!/usr/bin/env python3
"""
Time-Weighted Frequency Analysis System
Handles 20-year PYQ data with 10-year relevance weighting and trend analysis
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import numpy as np
import logging

logger = logging.getLogger(__name__)

@dataclass
class TemporalFrequencyConfig:
    """Configuration for time-weighted frequency analysis"""
    total_data_years: int = 20        # Store last 20 years of data
    relevance_window_years: int = 10  # Use last 10 years for frequency calculation
    decay_rate: float = 0.1           # How fast older data loses relevance
    trend_analysis_years: int = 5     # Years to analyze for trend detection
    min_occurrences_threshold: int = 2 # Minimum occurrences to be considered relevant

@dataclass
class TemporalPattern:
    """Represents a pattern's temporal frequency data"""
    concept_id: str
    total_occurrences: int
    relevance_window_occurrences: int
    yearly_occurrences: Dict[int, int]  # year -> count
    weighted_frequency_score: float
    trend_direction: str  # "increasing", "stable", "decreasing", "emerging", "declining"
    trend_strength: float  # 0.0 to 1.0
    recency_score: float  # How recent the occurrences are
    
class TimeWeightedFrequencyAnalyzer:
    """
    Advanced frequency analysis with time weighting and trend detection
    """
    
    def __init__(self, config: TemporalFrequencyConfig = None):
        self.config = config or TemporalFrequencyConfig()
        self.current_year = datetime.now().year
        
    def calculate_time_weighted_frequency(self, 
                                        yearly_occurrences: Dict[int, int],
                                        total_pyq_count_per_year: Dict[int, int]) -> Dict[str, float]:
        """
        Calculate frequency with time weighting - emphasizes recent years
        
        Args:
            yearly_occurrences: {year: occurrence_count} for this concept
            total_pyq_count_per_year: {year: total_questions} for normalization
            
        Returns:
            Dictionary with various frequency metrics
        """
        try:
            # Calculate raw frequency for each year
            yearly_frequencies = {}
            for year, occurrences in yearly_occurrences.items():
                total_questions = total_pyq_count_per_year.get(year, 1)
                yearly_frequencies[year] = occurrences / total_questions
            
            # Apply time-based weighting (more recent = higher weight)
            weighted_sum = 0.0
            weight_sum = 0.0
            relevance_sum = 0.0
            relevance_weight_sum = 0.0
            
            for year, frequency in yearly_frequencies.items():
                years_ago = self.current_year - year
                
                # Exponential decay weighting
                time_weight = math.exp(-self.config.decay_rate * years_ago)
                
                # Add to overall weighted calculation
                weighted_sum += frequency * time_weight
                weight_sum += time_weight
                
                # Separate calculation for relevance window (last 10 years)
                if years_ago <= self.config.relevance_window_years:
                    relevance_sum += frequency * time_weight
                    relevance_weight_sum += time_weight
            
            # Calculate final scores
            overall_weighted_frequency = weighted_sum / weight_sum if weight_sum > 0 else 0.0
            relevance_weighted_frequency = relevance_sum / relevance_weight_sum if relevance_weight_sum > 0 else 0.0
            
            # Calculate recency score (how recent are the occurrences)
            recency_score = self._calculate_recency_score(yearly_occurrences)
            
            return {
                "overall_weighted_frequency": overall_weighted_frequency,
                "relevance_weighted_frequency": relevance_weighted_frequency,  # This is the main score
                "recency_score": recency_score,
                "temporal_consistency": self._calculate_consistency(yearly_frequencies),
                "peak_year": max(yearly_occurrences, key=yearly_occurrences.get) if yearly_occurrences else None
            }
            
        except Exception as e:
            logger.error(f"Error in time-weighted frequency calculation: {e}")
            return {
                "overall_weighted_frequency": 0.0,
                "relevance_weighted_frequency": 0.0,
                "recency_score": 0.0,
                "temporal_consistency": 0.0,
                "peak_year": None
            }
    
    def detect_trend_pattern(self, yearly_occurrences: Dict[int, int]) -> Tuple[str, float]:
        """
        Detect trend patterns in question frequency over time
        
        Returns:
            Tuple of (trend_direction, trend_strength)
        """
        try:
            if len(yearly_occurrences) < 3:
                return "insufficient_data", 0.0
            
            # Get last N years for trend analysis
            trend_years = self.config.trend_analysis_years
            recent_years = sorted(yearly_occurrences.keys())[-trend_years:]
            
            if len(recent_years) < 3:
                return "insufficient_recent_data", 0.0
            
            # Prepare data for trend analysis
            years = np.array(recent_years)
            counts = np.array([yearly_occurrences[year] for year in recent_years])
            
            # Linear regression to detect trend
            if len(years) > 1:
                slope, intercept = np.polyfit(years - years[0], counts, 1)
                correlation = np.corrcoef(years, counts)[0, 1]
                
                # Determine trend direction and strength
                if abs(correlation) < 0.3:
                    return "stable", abs(correlation)
                elif slope > 0.5:  # Increasing trend
                    if max(counts[-2:]) > max(counts[:-2]):  # Recent uptick
                        return "increasing", abs(correlation)
                    else:
                        return "emerging", abs(correlation) * 0.8
                elif slope < -0.5:  # Decreasing trend
                    if min(counts[-2:]) < min(counts[:-2]):  # Recent decline
                        return "decreasing", abs(correlation)
                    else:
                        return "declining", abs(correlation) * 0.8
                else:
                    return "stable", abs(correlation)
            
            return "stable", 0.0
            
        except Exception as e:
            logger.error(f"Error in trend detection: {e}")
            return "error", 0.0
    
    def _calculate_recency_score(self, yearly_occurrences: Dict[int, int]) -> float:
        """Calculate how recent the occurrences are (0.0 = old, 1.0 = very recent)"""
        if not yearly_occurrences:
            return 0.0
        
        total_occurrences = sum(yearly_occurrences.values())
        weighted_recency = 0.0
        
        for year, count in yearly_occurrences.items():
            years_ago = self.current_year - year
            # Recent years get higher scores
            year_recency = max(0, 1.0 - (years_ago / self.config.total_data_years))
            weighted_recency += (count / total_occurrences) * year_recency
        
        return weighted_recency
    
    def _calculate_consistency(self, yearly_frequencies: Dict[int, float]) -> float:
        """Calculate temporal consistency (how evenly distributed are occurrences)"""
        if len(yearly_frequencies) < 2:
            return 0.0
        
        frequencies = list(yearly_frequencies.values())
        mean_freq = np.mean(frequencies)
        
        if mean_freq == 0:
            return 0.0
        
        # Coefficient of variation (lower = more consistent)
        cv = np.std(frequencies) / mean_freq
        # Convert to consistency score (higher = more consistent)
        consistency = max(0.0, 1.0 - min(cv, 2.0) / 2.0)
        
        return consistency
    
    def generate_frequency_insights(self, pattern: TemporalPattern) -> Dict[str, str]:
        """Generate human-readable insights about frequency patterns"""
        insights = []
        
        # Trend insights
        if pattern.trend_direction == "increasing" and pattern.trend_strength > 0.6:
            insights.append("📈 This topic is becoming more frequent in recent CAT exams")
        elif pattern.trend_direction == "decreasing" and pattern.trend_strength > 0.6:
            insights.append("📉 This topic is becoming less frequent in recent CAT exams")
        elif pattern.trend_direction == "emerging":
            insights.append("🆕 This is an emerging topic in CAT - started appearing recently")
        elif pattern.trend_direction == "declining":
            insights.append("⚠️ This topic was frequent before but declining recently")
        
        # Recency insights
        if pattern.recency_score > 0.8:
            insights.append("⭐ Very recent appearances - high current relevance")
        elif pattern.recency_score < 0.3:
            insights.append("⏳ Mostly historical appearances - lower current relevance")
        
        # Frequency insights
        if pattern.weighted_frequency_score > 0.7:
            insights.append("🔥 High frequency topic - appears very regularly")
        elif pattern.weighted_frequency_score < 0.2:
            insights.append("💎 Rare topic - appears infrequently")
        
        return {
            "summary": "; ".join(insights) if insights else "Standard frequency pattern",
            "trend_description": f"{pattern.trend_direction.title()} trend (strength: {pattern.trend_strength:.2f})",
            "recency_description": f"Recency score: {pattern.recency_score:.2f}",
            "frequency_category": self._categorize_frequency(pattern.weighted_frequency_score)
        }
    
    def _categorize_frequency(self, frequency_score: float) -> str:
        """Categorize frequency score into human-readable categories"""
        if frequency_score >= 0.7:
            return "Very High"
        elif frequency_score >= 0.5:
            return "High"
        elif frequency_score >= 0.3:
            return "Medium"
        elif frequency_score >= 0.1:
            return "Low"
        else:
            return "Very Low"
    
    def create_temporal_pattern(self, 
                              concept_id: str,
                              yearly_occurrences: Dict[int, int],
                              total_pyq_count_per_year: Dict[int, int]) -> TemporalPattern:
        """Create a complete temporal pattern analysis"""
        
        # Calculate time-weighted frequencies
        frequency_metrics = self.calculate_time_weighted_frequency(
            yearly_occurrences, total_pyq_count_per_year
        )
        
        # Detect trends
        trend_direction, trend_strength = self.detect_trend_pattern(yearly_occurrences)
        
        # Calculate totals
        total_occurrences = sum(yearly_occurrences.values())
        
        # Calculate occurrences in relevance window (last 10 years)
        relevance_window_start = self.current_year - self.config.relevance_window_years
        relevance_occurrences = sum(
            count for year, count in yearly_occurrences.items() 
            if year >= relevance_window_start
        )
        
        return TemporalPattern(
            concept_id=concept_id,
            total_occurrences=total_occurrences,
            relevance_window_occurrences=relevance_occurrences,
            yearly_occurrences=yearly_occurrences,
            weighted_frequency_score=frequency_metrics["relevance_weighted_frequency"],
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            recency_score=frequency_metrics["recency_score"]
        )


# Configuration presets for different analysis needs
CAT_ANALYSIS_CONFIG = TemporalFrequencyConfig(
    total_data_years=20,        # Store 20 years of PYQ data
    relevance_window_years=10,  # Emphasize last 10 years for scoring
    decay_rate=0.08,           # Moderate decay (recent years matter more)
    trend_analysis_years=5,     # Look at 5-year trends
    min_occurrences_threshold=2 # Need at least 2 occurrences to be relevant
)

RECENT_EMPHASIS_CONFIG = TemporalFrequencyConfig(
    total_data_years=20,
    relevance_window_years=8,   # Even more recent emphasis
    decay_rate=0.15,           # Faster decay
    trend_analysis_years=4,
    min_occurrences_threshold=1
)

CONSERVATIVE_CONFIG = TemporalFrequencyConfig(
    total_data_years=20,
    relevance_window_years=12,  # Longer relevance window
    decay_rate=0.05,           # Slower decay
    trend_analysis_years=6,
    min_occurrences_threshold=3  # Higher threshold
)