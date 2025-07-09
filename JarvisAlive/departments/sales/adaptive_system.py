"""
Adaptive Learning System - Pattern Recognition and Workflow Intelligence
Provides machine learning-driven insights, pattern recognition, and adaptive optimization
"""
from typing import Dict, List, Optional, Any, Tuple, Union
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
from enum import Enum
import uuid
import asyncio
import logging
import json
import numpy as np
from collections import defaultdict, Counter
import statistics
from dataclasses import dataclass
import pickle
import hashlib


class PatternType(str, Enum):
    PERFORMANCE = "performance"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    OUTCOME = "outcome"
    ANOMALY = "anomaly"


class ConfidenceLevel(str, Enum):
    LOW = "low"        # 0.5-0.69
    MEDIUM = "medium"  # 0.7-0.84
    HIGH = "high"      # 0.85-0.94
    VERY_HIGH = "very_high"  # 0.95+


class RecommendationType(str, Enum):
    OPTIMIZATION = "optimization"
    WORKFLOW_CHANGE = "workflow_change"
    PARAMETER_TUNING = "parameter_tuning"
    RESOURCE_ALLOCATION = "resource_allocation"
    TIMING_ADJUSTMENT = "timing_adjustment"
    AGENT_SELECTION = "agent_selection"


@dataclass
class DataPoint:
    timestamp: datetime
    workflow_id: str
    step_id: str
    metric_name: str
    value: float
    context: Dict[str, Any]


class Pattern(BaseModel):
    pattern_id: str
    pattern_type: PatternType
    name: str
    description: str
    confidence: float
    discovered_at: datetime
    last_seen: datetime
    frequency: int
    context_conditions: Dict[str, Any]
    impact_metrics: Dict[str, float]
    recommendations: List[str]
    
    @validator('pattern_id')
    def validate_pattern_id(cls, v):
        if not v:
            return f"pattern_{uuid.uuid4().hex[:8]}"
        return v

    @property
    def confidence_level(self) -> ConfidenceLevel:
        if self.confidence >= 0.95:
            return ConfidenceLevel.VERY_HIGH
        elif self.confidence >= 0.85:
            return ConfidenceLevel.HIGH
        elif self.confidence >= 0.7:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW


class LearningInsight(BaseModel):
    insight_id: str
    title: str
    description: str
    insight_type: str
    priority: int  # 1-10
    confidence: float
    supporting_patterns: List[str]  # pattern_ids
    potential_impact: str
    implementation_effort: str  # "low", "medium", "high"
    created_at: datetime
    status: str = "new"  # "new", "reviewed", "implemented", "dismissed"
    
    @validator('insight_id')
    def validate_insight_id(cls, v):
        if not v:
            return f"insight_{uuid.uuid4().hex[:8]}"
        return v


class Recommendation(BaseModel):
    recommendation_id: str
    type: RecommendationType
    title: str
    description: str
    target_workflow: Optional[str] = None
    target_step: Optional[str] = None
    suggested_changes: Dict[str, Any]
    expected_improvement: Dict[str, float]
    confidence: float
    priority: int  # 1-10
    implementation_complexity: str  # "low", "medium", "high"
    created_at: datetime
    expires_at: Optional[datetime] = None
    
    @validator('recommendation_id')
    def validate_recommendation_id(cls, v):
        if not v:
            return f"rec_{uuid.uuid4().hex[:8]}"
        return v


class ABTest(BaseModel):
    test_id: str
    name: str
    description: str
    hypothesis: str
    workflow_id: str
    step_id: Optional[str] = None
    variants: Dict[str, Dict[str, Any]]  # variant_name -> parameters
    traffic_allocation: Dict[str, float]  # variant_name -> percentage
    success_metrics: List[str]
    start_date: datetime
    end_date: Optional[datetime] = None
    status: str = "draft"  # "draft", "running", "completed", "paused"
    results: Dict[str, Any] = {}
    statistical_significance: Optional[float] = None
    winner: Optional[str] = None
    
    @validator('test_id')
    def validate_test_id(cls, v):
        if not v:
            return f"test_{uuid.uuid4().hex[:8]}"
        return v


class ABTestResult(BaseModel):
    test_id: str
    variant: str
    metric: str
    value: float
    sample_size: int
    confidence_interval: Tuple[float, float]
    p_value: Optional[float] = None


class AdaptiveSystem:
    """Advanced adaptive learning and pattern recognition system"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Pattern storage
        self.patterns: Dict[str, Pattern] = {}
        self.insights: Dict[str, LearningInsight] = {}
        self.recommendations: Dict[str, Recommendation] = {}
        
        # A/B testing
        self.ab_tests: Dict[str, ABTest] = {}
        self.ab_results: Dict[str, List[ABTestResult]] = defaultdict(list)
        
        # Data storage
        self.historical_data: List[DataPoint] = []
        self.feature_cache: Dict[str, Any] = {}
        
        # Learning parameters
        self.min_pattern_frequency = self.config.get("min_pattern_frequency", 5)
        self.min_confidence_threshold = self.config.get("min_confidence_threshold", 0.6)
        self.data_retention_days = self.config.get("data_retention_days", 90)
        
        # Initialize pattern detectors
        self._setup_pattern_detectors()
    
    def _setup_pattern_detectors(self):
        """Setup pattern detection algorithms"""
        self.pattern_detectors = {
            PatternType.PERFORMANCE: self._detect_performance_patterns,
            PatternType.BEHAVIORAL: self._detect_behavioral_patterns,
            PatternType.TEMPORAL: self._detect_temporal_patterns,
            PatternType.OUTCOME: self._detect_outcome_patterns,
            PatternType.ANOMALY: self._detect_anomaly_patterns
        }
    
    def record_data_point(self, workflow_id: str, step_id: str, metric_name: str, 
                         value: float, context: Dict[str, Any] = None):
        """Record a new data point for analysis"""
        data_point = DataPoint(
            timestamp=datetime.now(),
            workflow_id=workflow_id,
            step_id=step_id,
            metric_name=metric_name,
            value=value,
            context=context or {}
        )
        
        self.historical_data.append(data_point)
        
        # Cleanup old data
        cutoff_date = datetime.now() - timedelta(days=self.data_retention_days)
        self.historical_data = [dp for dp in self.historical_data if dp.timestamp > cutoff_date]
        
        # Trigger pattern detection periodically
        if len(self.historical_data) % 100 == 0:
            asyncio.create_task(self.detect_patterns())
    
    async def detect_patterns(self) -> List[Pattern]:
        """Run pattern detection across all types"""
        self.logger.info("Starting pattern detection...")
        
        new_patterns = []
        
        for pattern_type, detector in self.pattern_detectors.items():
            try:
                patterns = await detector()
                new_patterns.extend(patterns)
                self.logger.info(f"Found {len(patterns)} {pattern_type.value} patterns")
            except Exception as e:
                self.logger.error(f"Pattern detection failed for {pattern_type}: {e}")
        
        # Store new patterns
        for pattern in new_patterns:
            self.patterns[pattern.pattern_id] = pattern
        
        # Generate insights and recommendations
        await self._generate_insights()
        await self._generate_recommendations()
        
        return new_patterns
    
    async def _detect_performance_patterns(self) -> List[Pattern]:
        """Detect performance-related patterns"""
        patterns = []
        
        # Group data by workflow and step
        workflow_data = defaultdict(lambda: defaultdict(list))
        for dp in self.historical_data:
            if dp.metric_name in ['duration', 'cost', 'success_rate']:
                workflow_data[dp.workflow_id][dp.step_id].append(dp)
        
        for workflow_id, steps in workflow_data.items():
            for step_id, data_points in steps.items():
                if len(data_points) < self.min_pattern_frequency:
                    continue
                
                # Detect duration trends
                duration_values = [dp.value for dp in data_points if dp.metric_name == 'duration']
                if len(duration_values) >= 10:
                    trend_pattern = self._analyze_trend(duration_values, 'duration')
                    if trend_pattern:
                        pattern = Pattern(
                            pattern_id=f"perf_{workflow_id}_{step_id}_{hashlib.md5(str(duration_values).encode()).hexdigest()[:8]}",
                            pattern_type=PatternType.PERFORMANCE,
                            name=f"Duration Trend in {step_id}",
                            description=f"Detected {trend_pattern['direction']} trend in step duration",
                            confidence=trend_pattern['confidence'],
                            discovered_at=datetime.now(),
                            last_seen=max(dp.timestamp for dp in data_points),
                            frequency=len(duration_values),
                            context_conditions={"workflow_id": workflow_id, "step_id": step_id},
                            impact_metrics={"duration_change": trend_pattern['magnitude']},
                            recommendations=[f"Investigate {trend_pattern['direction']} trend in {step_id}"]
                        )
                        patterns.append(pattern)
                
                # Detect cost anomalies
                cost_values = [dp.value for dp in data_points if dp.metric_name == 'cost']
                if len(cost_values) >= 5:
                    anomalies = self._detect_statistical_anomalies(cost_values)
                    if anomalies['count'] > 0:
                        pattern = Pattern(
                            pattern_id=f"cost_anom_{workflow_id}_{step_id}_{uuid.uuid4().hex[:8]}",
                            pattern_type=PatternType.PERFORMANCE,
                            name=f"Cost Anomalies in {step_id}",
                            description=f"Detected {anomalies['count']} cost anomalies",
                            confidence=anomalies['confidence'],
                            discovered_at=datetime.now(),
                            last_seen=max(dp.timestamp for dp in data_points),
                            frequency=anomalies['count'],
                            context_conditions={"workflow_id": workflow_id, "step_id": step_id},
                            impact_metrics={"anomaly_magnitude": anomalies['magnitude']},
                            recommendations=["Review cost drivers for this step"]
                        )
                        patterns.append(pattern)
        
        return patterns
    
    async def _detect_behavioral_patterns(self) -> List[Pattern]:
        """Detect behavioral patterns in workflow execution"""
        patterns = []
        
        # Analyze workflow execution patterns
        execution_sequences = defaultdict(list)
        for dp in self.historical_data:
            execution_sequences[dp.workflow_id].append((dp.step_id, dp.timestamp))
        
        for workflow_id, sequences in execution_sequences.items():
            if len(sequences) < 20:  # Need sufficient data
                continue
            
            # Sort by timestamp
            sequences.sort(key=lambda x: x[1])
            
            # Extract step sequences
            step_sequences = [step_id for step_id, _ in sequences]
            
            # Find common subsequences
            common_patterns = self._find_common_subsequences(step_sequences)
            
            for subsequence, frequency in common_patterns.items():
                if frequency >= self.min_pattern_frequency:
                    pattern = Pattern(
                        pattern_id=f"behav_{workflow_id}_{hashlib.md5(subsequence.encode()).hexdigest()[:8]}",
                        pattern_type=PatternType.BEHAVIORAL,
                        name=f"Common Execution Pattern",
                        description=f"Frequent execution sequence: {subsequence}",
                        confidence=min(0.9, frequency / len(step_sequences)),
                        discovered_at=datetime.now(),
                        last_seen=datetime.now(),
                        frequency=frequency,
                        context_conditions={"workflow_id": workflow_id},
                        impact_metrics={"sequence_frequency": frequency},
                        recommendations=["Consider optimizing this common execution path"]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def _detect_temporal_patterns(self) -> List[Pattern]:
        """Detect time-based patterns"""
        patterns = []
        
        # Group data by hour of day and day of week
        hourly_performance = defaultdict(list)
        daily_performance = defaultdict(list)
        
        for dp in self.historical_data:
            if dp.metric_name == 'duration':
                hour = dp.timestamp.hour
                day = dp.timestamp.weekday()
                hourly_performance[hour].append(dp.value)
                daily_performance[day].append(dp.value)
        
        # Analyze hourly patterns
        best_hours = []
        worst_hours = []
        
        for hour, durations in hourly_performance.items():
            if len(durations) >= 5:
                avg_duration = statistics.mean(durations)
                best_hours.append((hour, avg_duration))
                worst_hours.append((hour, avg_duration))
        
        if len(best_hours) >= 3:
            best_hours.sort(key=lambda x: x[1])
            worst_hours.sort(key=lambda x: x[1], reverse=True)
            
            best_hour = best_hours[0][0]
            worst_hour = worst_hours[0][0]
            improvement = (worst_hours[0][1] - best_hours[0][1]) / best_hours[0][1]
            
            if improvement > 0.2:  # 20% improvement potential
                pattern = Pattern(
                    pattern_id=f"temporal_hourly_{uuid.uuid4().hex[:8]}",
                    pattern_type=PatternType.TEMPORAL,
                    name="Optimal Execution Hours",
                    description=f"Performance varies by hour: best at {best_hour}:00, worst at {worst_hour}:00",
                    confidence=0.8,
                    discovered_at=datetime.now(),
                    last_seen=datetime.now(),
                    frequency=len(best_hours),
                    context_conditions={"time_pattern": "hourly"},
                    impact_metrics={"potential_improvement": improvement},
                    recommendations=[f"Schedule critical workflows during hour {best_hour}"]
                )
                patterns.append(pattern)
        
        return patterns
    
    async def _detect_outcome_patterns(self) -> List[Pattern]:
        """Detect patterns related to workflow outcomes"""
        patterns = []
        
        # Analyze success/failure patterns
        outcome_data = defaultdict(lambda: {"success": 0, "failure": 0, "contexts": []})
        
        for dp in self.historical_data:
            if dp.metric_name == 'success_rate':
                key = f"{dp.workflow_id}_{dp.step_id}"
                if dp.value > 0.8:
                    outcome_data[key]["success"] += 1
                else:
                    outcome_data[key]["failure"] += 1
                outcome_data[key]["contexts"].append(dp.context)
        
        for key, data in outcome_data.items():
            total = data["success"] + data["failure"]
            if total >= 10:
                success_rate = data["success"] / total
                
                if success_rate < 0.7:  # Poor success rate
                    # Analyze context patterns for failures
                    failure_contexts = [ctx for i, ctx in enumerate(data["contexts"]) 
                                      if i >= data["success"]]
                    
                    common_factors = self._find_common_context_factors(failure_contexts)
                    
                    pattern = Pattern(
                        pattern_id=f"outcome_{key}_{uuid.uuid4().hex[:8]}",
                        pattern_type=PatternType.OUTCOME,
                        name=f"Low Success Rate Pattern",
                        description=f"Success rate of {success_rate:.1%} with common factors: {common_factors}",
                        confidence=0.7,
                        discovered_at=datetime.now(),
                        last_seen=datetime.now(),
                        frequency=data["failure"],
                        context_conditions=common_factors,
                        impact_metrics={"success_rate": success_rate},
                        recommendations=["Address common failure factors"]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    async def _detect_anomaly_patterns(self) -> List[Pattern]:
        """Detect anomalous patterns that deviate from normal behavior"""
        patterns = []
        
        # Statistical anomaly detection
        metric_groups = defaultdict(list)
        for dp in self.historical_data:
            metric_groups[f"{dp.workflow_id}_{dp.step_id}_{dp.metric_name}"].append(dp.value)
        
        for group_key, values in metric_groups.items():
            if len(values) >= 20:
                anomalies = self._detect_statistical_anomalies(values)
                
                if anomalies['count'] >= 3 and anomalies['confidence'] > 0.7:
                    workflow_id, step_id, metric_name = group_key.split('_', 2)
                    
                    pattern = Pattern(
                        pattern_id=f"anomaly_{group_key}_{uuid.uuid4().hex[:8]}",
                        pattern_type=PatternType.ANOMALY,
                        name=f"Statistical Anomaly in {metric_name}",
                        description=f"Detected {anomalies['count']} statistical anomalies",
                        confidence=anomalies['confidence'],
                        discovered_at=datetime.now(),
                        last_seen=datetime.now(),
                        frequency=anomalies['count'],
                        context_conditions={"workflow_id": workflow_id, "step_id": step_id, "metric": metric_name},
                        impact_metrics={"anomaly_magnitude": anomalies['magnitude']},
                        recommendations=["Investigate root cause of anomalies"]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _analyze_trend(self, values: List[float], metric_name: str) -> Optional[Dict[str, Any]]:
        """Analyze trend in a series of values"""
        if len(values) < 5:
            return None
        
        # Simple linear regression
        x = list(range(len(values)))
        y = values
        
        n = len(values)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(x[i] * y[i] for i in range(n))
        sum_x2 = sum(x[i] * x[i] for i in range(n))
        
        # Calculate slope
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        # Calculate correlation coefficient
        mean_x = sum_x / n
        mean_y = sum_y / n
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
        denominator = (sum((x[i] - mean_x)**2 for i in range(n)) * 
                      sum((y[i] - mean_y)**2 for i in range(n)))**0.5
        
        if denominator == 0:
            return None
        
        correlation = numerator / denominator
        confidence = abs(correlation)
        
        if confidence < 0.6:
            return None
        
        direction = "increasing" if slope > 0 else "decreasing"
        magnitude = abs(slope)
        
        return {
            "direction": direction,
            "magnitude": magnitude,
            "confidence": confidence,
            "slope": slope
        }
    
    def _detect_statistical_anomalies(self, values: List[float]) -> Dict[str, Any]:
        """Detect statistical anomalies using IQR method"""
        if len(values) < 5:
            return {"count": 0, "confidence": 0, "magnitude": 0}
        
        sorted_values = sorted(values)
        n = len(sorted_values)
        
        q1 = sorted_values[n // 4]
        q3 = sorted_values[3 * n // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomalies = [v for v in values if v < lower_bound or v > upper_bound]
        anomaly_count = len(anomalies)
        
        if anomaly_count == 0:
            return {"count": 0, "confidence": 0, "magnitude": 0}
        
        # Calculate confidence based on how far anomalies are from bounds
        max_deviation = 0
        for anomaly in anomalies:
            if anomaly < lower_bound:
                deviation = (lower_bound - anomaly) / iqr if iqr > 0 else 0
            else:
                deviation = (anomaly - upper_bound) / iqr if iqr > 0 else 0
            max_deviation = max(max_deviation, deviation)
        
        confidence = min(0.95, 0.5 + (max_deviation * 0.1))
        
        return {
            "count": anomaly_count,
            "confidence": confidence,
            "magnitude": max_deviation,
            "lower_bound": lower_bound,
            "upper_bound": upper_bound
        }
    
    def _find_common_subsequences(self, sequences: List[str], min_length: int = 2) -> Dict[str, int]:
        """Find common subsequences in a list of sequences"""
        subsequence_counts = Counter()
        
        for i in range(len(sequences) - min_length + 1):
            for length in range(min_length, min(6, len(sequences) - i + 1)):
                subseq = " -> ".join(sequences[i:i+length])
                subsequence_counts[subseq] += 1
        
        # Return only subsequences that appear multiple times
        return {subseq: count for subseq, count in subsequence_counts.items() if count > 1}
    
    def _find_common_context_factors(self, contexts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Find common factors in failure contexts"""
        if not contexts:
            return {}
        
        common_factors = {}
        
        # Find keys that appear in most contexts
        all_keys = set()
        for ctx in contexts:
            all_keys.update(ctx.keys())
        
        for key in all_keys:
            values = [ctx.get(key) for ctx in contexts if key in ctx]
            if len(values) >= len(contexts) * 0.7:  # Appears in 70% of contexts
                # Find most common value
                value_counts = Counter(values)
                most_common = value_counts.most_common(1)[0]
                if most_common[1] >= len(values) * 0.6:  # Same value in 60% of cases
                    common_factors[key] = most_common[0]
        
        return common_factors
    
    async def _generate_insights(self):
        """Generate learning insights from detected patterns"""
        for pattern in self.patterns.values():
            if pattern.confidence < self.min_confidence_threshold:
                continue
            
            # Generate insights based on pattern type
            if pattern.pattern_type == PatternType.PERFORMANCE:
                await self._generate_performance_insights(pattern)
            elif pattern.pattern_type == PatternType.TEMPORAL:
                await self._generate_temporal_insights(pattern)
            elif pattern.pattern_type == PatternType.OUTCOME:
                await self._generate_outcome_insights(pattern)
    
    async def _generate_performance_insights(self, pattern: Pattern):
        """Generate insights from performance patterns"""
        if "duration_change" in pattern.impact_metrics:
            change = pattern.impact_metrics["duration_change"]
            if change > 0.2:  # 20% increase
                insight = LearningInsight(
                    insight_id=f"perf_insight_{pattern.pattern_id}",
                    title="Performance Degradation Detected",
                    description=f"Step performance has degraded by {change:.1%}",
                    insight_type="performance_alert",
                    priority=8,
                    confidence=pattern.confidence,
                    supporting_patterns=[pattern.pattern_id],
                    potential_impact="Increased execution time and costs",
                    implementation_effort="medium",
                    created_at=datetime.now()
                )
                self.insights[insight.insight_id] = insight
    
    async def _generate_temporal_insights(self, pattern: Pattern):
        """Generate insights from temporal patterns"""
        if "potential_improvement" in pattern.impact_metrics:
            improvement = pattern.impact_metrics["potential_improvement"]
            insight = LearningInsight(
                insight_id=f"temporal_insight_{pattern.pattern_id}",
                title="Optimal Timing Opportunity",
                description=f"Scheduling optimization could improve performance by {improvement:.1%}",
                insight_type="optimization_opportunity",
                priority=6,
                confidence=pattern.confidence,
                supporting_patterns=[pattern.pattern_id],
                potential_impact=f"Up to {improvement:.1%} performance improvement",
                implementation_effort="low",
                created_at=datetime.now()
            )
            self.insights[insight.insight_id] = insight
    
    async def _generate_outcome_insights(self, pattern: Pattern):
        """Generate insights from outcome patterns"""
        if "success_rate" in pattern.impact_metrics:
            success_rate = pattern.impact_metrics["success_rate"]
            if success_rate < 0.7:
                insight = LearningInsight(
                    insight_id=f"outcome_insight_{pattern.pattern_id}",
                    title="Low Success Rate Issue",
                    description=f"Success rate of {success_rate:.1%} indicates systemic issues",
                    insight_type="quality_alert",
                    priority=9,
                    confidence=pattern.confidence,
                    supporting_patterns=[pattern.pattern_id],
                    potential_impact="Improved reliability and user satisfaction",
                    implementation_effort="high",
                    created_at=datetime.now()
                )
                self.insights[insight.insight_id] = insight
    
    async def _generate_recommendations(self):
        """Generate actionable recommendations from patterns and insights"""
        for pattern in self.patterns.values():
            if pattern.confidence < 0.7:
                continue
            
            # Generate recommendations based on pattern type
            recommendations = await self._create_pattern_recommendations(pattern)
            for rec in recommendations:
                self.recommendations[rec.recommendation_id] = rec
    
    async def _create_pattern_recommendations(self, pattern: Pattern) -> List[Recommendation]:
        """Create specific recommendations for a pattern"""
        recommendations = []
        
        if pattern.pattern_type == PatternType.PERFORMANCE:
            if "duration_change" in pattern.impact_metrics and pattern.impact_metrics["duration_change"] > 0.15:
                rec = Recommendation(
                    recommendation_id=f"perf_rec_{pattern.pattern_id}",
                    type=RecommendationType.OPTIMIZATION,
                    title="Optimize Performance Bottleneck",
                    description=f"Address performance degradation in {pattern.context_conditions.get('step_id', 'unknown step')}",
                    target_workflow=pattern.context_conditions.get("workflow_id"),
                    target_step=pattern.context_conditions.get("step_id"),
                    suggested_changes={
                        "action": "performance_optimization",
                        "priority": "high",
                        "areas": ["caching", "parallelization", "resource_allocation"]
                    },
                    expected_improvement={"duration_reduction": 0.25, "cost_reduction": 0.15},
                    confidence=pattern.confidence,
                    priority=8,
                    implementation_complexity="medium",
                    created_at=datetime.now()
                )
                recommendations.append(rec)
        
        elif pattern.pattern_type == PatternType.TEMPORAL:
            if "potential_improvement" in pattern.impact_metrics:
                rec = Recommendation(
                    recommendation_id=f"temporal_rec_{pattern.pattern_id}",
                    type=RecommendationType.TIMING_ADJUSTMENT,
                    title="Optimize Execution Timing",
                    description="Schedule workflows during optimal time periods",
                    suggested_changes={
                        "action": "schedule_optimization",
                        "optimal_hours": pattern.context_conditions.get("optimal_hours", []),
                        "avoid_hours": pattern.context_conditions.get("avoid_hours", [])
                    },
                    expected_improvement={"performance_gain": pattern.impact_metrics["potential_improvement"]},
                    confidence=pattern.confidence,
                    priority=6,
                    implementation_complexity="low",
                    created_at=datetime.now()
                )
                recommendations.append(rec)
        
        return recommendations
    
    def create_ab_test(self, test: ABTest) -> str:
        """Create a new A/B test"""
        self.ab_tests[test.test_id] = test
        self.logger.info(f"Created A/B test: {test.name}")
        return test.test_id
    
    def record_ab_result(self, test_id: str, variant: str, metric: str, 
                        value: float, sample_size: int):
        """Record A/B test result"""
        if test_id not in self.ab_tests:
            raise ValueError(f"A/B test not found: {test_id}")
        
        # Calculate confidence interval (simplified)
        margin_of_error = 1.96 * (value * 0.1)  # Simplified calculation
        confidence_interval = (value - margin_of_error, value + margin_of_error)
        
        result = ABTestResult(
            test_id=test_id,
            variant=variant,
            metric=metric,
            value=value,
            sample_size=sample_size,
            confidence_interval=confidence_interval
        )
        
        self.ab_results[test_id].append(result)
    
    def analyze_ab_test(self, test_id: str) -> Dict[str, Any]:
        """Analyze A/B test results and determine winner"""
        if test_id not in self.ab_tests:
            raise ValueError(f"A/B test not found: {test_id}")
        
        test = self.ab_tests[test_id]
        results = self.ab_results[test_id]
        
        if not results:
            return {"status": "no_data", "message": "No results recorded yet"}
        
        # Group results by variant and metric
        variant_metrics = defaultdict(lambda: defaultdict(list))
        for result in results:
            variant_metrics[result.variant][result.metric].append(result.value)
        
        # Calculate statistical significance (simplified)
        analysis = {
            "test_id": test_id,
            "variants": {},
            "winner": None,
            "confidence": 0,
            "recommendation": ""
        }
        
        primary_metric = test.success_metrics[0] if test.success_metrics else "conversion_rate"
        
        for variant, metrics in variant_metrics.items():
            if primary_metric in metrics:
                values = metrics[primary_metric]
                analysis["variants"][variant] = {
                    "mean": statistics.mean(values),
                    "sample_size": len(values),
                    "std_dev": statistics.stdev(values) if len(values) > 1 else 0
                }
        
        # Determine winner (simplified - needs proper statistical testing)
        if len(analysis["variants"]) >= 2:
            best_variant = max(analysis["variants"].items(), 
                             key=lambda x: x[1]["mean"])
            analysis["winner"] = best_variant[0]
            analysis["confidence"] = 0.85  # Simplified
            analysis["recommendation"] = f"Variant {best_variant[0]} shows best performance"
        
        return analysis
    
    def get_recommendations(self, workflow_id: Optional[str] = None, 
                          priority_threshold: int = 5) -> List[Recommendation]:
        """Get recommendations, optionally filtered"""
        recommendations = list(self.recommendations.values())
        
        if workflow_id:
            recommendations = [r for r in recommendations 
                             if r.target_workflow == workflow_id]
        
        recommendations = [r for r in recommendations 
                         if r.priority >= priority_threshold]
        
        # Sort by priority and confidence
        recommendations.sort(key=lambda x: (x.priority, x.confidence), reverse=True)
        
        return recommendations
    
    def get_insights_summary(self) -> Dict[str, Any]:
        """Get a summary of learning insights"""
        insights = list(self.insights.values())
        
        summary = {
            "total_insights": len(insights),
            "by_type": Counter(i.insight_type for i in insights),
            "by_priority": Counter(i.priority for i in insights),
            "high_priority": len([i for i in insights if i.priority >= 8]),
            "recent_insights": len([i for i in insights 
                                  if i.created_at > datetime.now() - timedelta(days=7)])
        }
        
        return summary