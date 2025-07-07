"""Business context layer for HeyJarvis to understand company operations."""

import json
import logging
from typing import Dict, Any, List, Optional, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class CompanyStage(str, Enum):
    """Company development stages."""
    IDEA = "idea"
    PROTOTYPE = "prototype"
    LAUNCH = "launch"
    GROWTH = "growth"
    SCALE = "scale"
    MATURE = "mature"


class Industry(str, Enum):
    """Industry categories."""
    SAAS = "saas"
    ECOMMERCE = "ecommerce"
    FINTECH = "fintech"
    HEALTHCARE = "healthcare"
    EDUCATION = "education"
    MEDIA = "media"
    REAL_ESTATE = "real_estate"
    CONSULTING = "consulting"
    MANUFACTURING = "manufacturing"
    OTHER = "other"


@dataclass
class CompanyProfile:
    """Core company information."""
    stage: CompanyStage
    industry: Industry
    team_size: int
    founded_year: Optional[int] = None
    company_name: Optional[str] = None
    description: Optional[str] = None


@dataclass
class KeyMetrics:
    """Key business metrics."""
    mrr: Optional[float] = None  # Monthly Recurring Revenue
    arr: Optional[float] = None  # Annual Recurring Revenue
    burn_rate: Optional[float] = None  # Monthly burn rate
    runway: Optional[int] = None  # Months of runway
    cac: Optional[float] = None  # Customer Acquisition Cost
    ltv: Optional[float] = None  # Lifetime Value
    churn_rate: Optional[float] = None  # Monthly churn rate
    growth_rate: Optional[float] = None  # Monthly growth rate
    cash_balance: Optional[float] = None


@dataclass
class BusinessGoal:
    """Individual business goal/OKR."""
    title: str
    description: str
    target_value: Optional[Union[float, int, str]] = None
    current_value: Optional[Union[float, int, str]] = None
    due_date: Optional[datetime] = None
    priority: str = "medium"  # high, medium, low
    category: str = "general"  # revenue, growth, product, ops, etc.
    progress: float = 0.0  # 0-1 scale


@dataclass
class ResourceConstraints:
    """Resource limitations and constraints."""
    budget: Optional[float] = None
    headcount_limit: Optional[int] = None
    tech_stack_constraints: Optional[List[str]] = None
    compliance_requirements: Optional[List[str]] = None
    time_constraints: Optional[Dict[str, Any]] = None


class BusinessContext:
    """HeyJarvis's understanding of the company context."""
    
    def __init__(self, redis_client, session_id: str):
        """Initialize business context with Redis client and session ID."""
        self.redis_client = redis_client
        self.session_id = session_id
        self.company_profile: Optional[CompanyProfile] = None
        self.key_metrics: Optional[KeyMetrics] = None
        self.active_goals: List[BusinessGoal] = []
        self.resource_constraints: Optional[ResourceConstraints] = None
        self.last_updated: Optional[datetime] = None
        
        # Redis key patterns
        self.profile_key = f"business:{session_id}:profile"
        self.metrics_key = f"business:{session_id}:metrics"
        self.goals_key = f"business:{session_id}:goals"
        self.constraints_key = f"business:{session_id}:constraints"
        self.metadata_key = f"business:{session_id}:metadata"
    
    async def load_context(self) -> bool:
        """Load business context from Redis."""
        try:
            # Load company profile
            profile_data = await self.redis_client.get(self.profile_key)
            if profile_data:
                profile_dict = json.loads(profile_data)
                self.company_profile = CompanyProfile(
                    stage=CompanyStage(profile_dict["stage"]),
                    industry=Industry(profile_dict["industry"]),
                    team_size=profile_dict["team_size"],
                    founded_year=profile_dict.get("founded_year"),
                    company_name=profile_dict.get("company_name"),
                    description=profile_dict.get("description")
                )
            
            # Load key metrics
            metrics_data = await self.redis_client.get(self.metrics_key)
            if metrics_data:
                metrics_dict = json.loads(metrics_data)
                self.key_metrics = KeyMetrics(**metrics_dict)
            
            # Load active goals
            goals_data = await self.redis_client.get(self.goals_key)
            if goals_data:
                goals_list = json.loads(goals_data)
                self.active_goals = []
                for goal_dict in goals_list:
                    # Convert datetime strings back to datetime objects
                    if goal_dict.get("due_date"):
                        goal_dict["due_date"] = datetime.fromisoformat(goal_dict["due_date"])
                    self.active_goals.append(BusinessGoal(**goal_dict))
            
            # Load resource constraints
            constraints_data = await self.redis_client.get(self.constraints_key)
            if constraints_data:
                constraints_dict = json.loads(constraints_data)
                self.resource_constraints = ResourceConstraints(**constraints_dict)
            
            # Load metadata
            metadata_data = await self.redis_client.get(self.metadata_key)
            if metadata_data:
                metadata_dict = json.loads(metadata_data)
                if metadata_dict.get("last_updated"):
                    self.last_updated = datetime.fromisoformat(metadata_dict["last_updated"])
            
            logger.info(f"Successfully loaded business context for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading business context for session {self.session_id}: {e}")
            return False
    
    async def save_context(self) -> bool:
        """Save business context to Redis."""
        try:
            # Save company profile
            if self.company_profile:
                profile_dict = {
                    "stage": self.company_profile.stage.value,
                    "industry": self.company_profile.industry.value,
                    "team_size": self.company_profile.team_size,
                    "founded_year": self.company_profile.founded_year,
                    "company_name": self.company_profile.company_name,
                    "description": self.company_profile.description
                }
                await self.redis_client.setex(
                    self.profile_key,
                    86400,  # 24 hours TTL
                    json.dumps(profile_dict)
                )
            
            # Save key metrics
            if self.key_metrics:
                metrics_dict = {
                    "mrr": self.key_metrics.mrr,
                    "arr": self.key_metrics.arr,
                    "burn_rate": self.key_metrics.burn_rate,
                    "runway": self.key_metrics.runway,
                    "cac": self.key_metrics.cac,
                    "ltv": self.key_metrics.ltv,
                    "churn_rate": self.key_metrics.churn_rate,
                    "growth_rate": self.key_metrics.growth_rate,
                    "cash_balance": self.key_metrics.cash_balance
                }
                await self.redis_client.setex(
                    self.metrics_key,
                    86400,  # 24 hours TTL
                    json.dumps(metrics_dict)
                )
            
            # Save active goals
            if self.active_goals:
                goals_list = []
                for goal in self.active_goals:
                    goal_dict = {
                        "title": goal.title,
                        "description": goal.description,
                        "target_value": goal.target_value,
                        "current_value": goal.current_value,
                        "due_date": goal.due_date.isoformat() if goal.due_date else None,
                        "priority": goal.priority,
                        "category": goal.category,
                        "progress": goal.progress
                    }
                    goals_list.append(goal_dict)
                
                await self.redis_client.setex(
                    self.goals_key,
                    86400,  # 24 hours TTL
                    json.dumps(goals_list)
                )
            
            # Save resource constraints
            if self.resource_constraints:
                constraints_dict = {
                    "budget": self.resource_constraints.budget,
                    "headcount_limit": self.resource_constraints.headcount_limit,
                    "tech_stack_constraints": self.resource_constraints.tech_stack_constraints,
                    "compliance_requirements": self.resource_constraints.compliance_requirements,
                    "time_constraints": self.resource_constraints.time_constraints
                }
                await self.redis_client.setex(
                    self.constraints_key,
                    86400,  # 24 hours TTL
                    json.dumps(constraints_dict)
                )
            
            # Save metadata
            self.last_updated = datetime.utcnow()
            metadata_dict = {
                "last_updated": self.last_updated.isoformat()
            }
            await self.redis_client.setex(
                self.metadata_key,
                86400,  # 24 hours TTL
                json.dumps(metadata_dict)
            )
            
            logger.info(f"Successfully saved business context for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving business context for session {self.session_id}: {e}")
            return False
    
    async def update_metric(self, metric_name: str, value: Union[float, int]) -> bool:
        """Update a specific business metric."""
        try:
            if not self.key_metrics:
                self.key_metrics = KeyMetrics()
            
            # Validate metric name
            if not hasattr(self.key_metrics, metric_name):
                logger.error(f"Invalid metric name: {metric_name}")
                return False
            
            # Update the metric
            setattr(self.key_metrics, metric_name, value)
            
            # Calculate derived metrics
            if metric_name in ["mrr", "arr", "burn_rate", "cash_balance"]:
                self._calculate_derived_metrics()
            
            # Save to Redis
            await self.save_context()
            
            logger.info(f"Updated metric {metric_name} to {value} for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating metric {metric_name}: {e}")
            return False
    
    def _calculate_derived_metrics(self):
        """Calculate derived metrics from base metrics."""
        if not self.key_metrics:
            return
        
        # Calculate runway if we have burn rate and cash balance
        if self.key_metrics.burn_rate and self.key_metrics.cash_balance and self.key_metrics.burn_rate > 0:
            self.key_metrics.runway = int(self.key_metrics.cash_balance / self.key_metrics.burn_rate)
        
        # Calculate ARR from MRR
        if self.key_metrics.mrr:
            self.key_metrics.arr = self.key_metrics.mrr * 12
    
    async def check_goal_progress(self) -> List[Dict[str, Any]]:
        """Check progress on all active goals."""
        progress_report = []
        
        for goal in self.active_goals:
            goal_info = {
                "title": goal.title,
                "category": goal.category,
                "priority": goal.priority,
                "progress": goal.progress,
                "target_value": goal.target_value,
                "current_value": goal.current_value,
                "status": "on_track"
            }
            
            # Determine status based on progress and due date
            if goal.due_date:
                days_until_due = (goal.due_date - datetime.now()).days
                if days_until_due < 0:
                    goal_info["status"] = "overdue"
                elif days_until_due < 7 and goal.progress < 0.8:
                    goal_info["status"] = "at_risk"
                elif goal.progress >= 1.0:
                    goal_info["status"] = "completed"
                
                goal_info["days_until_due"] = days_until_due
            
            # Check if goal is stalled
            if goal.progress < 0.1:
                goal_info["status"] = "not_started"
            elif goal.progress < 0.3:
                goal_info["status"] = "slow_progress"
            
            progress_report.append(goal_info)
        
        return progress_report
    
    def get_optimization_suggestions(self) -> List[Dict[str, Any]]:
        """Get optimization suggestions based on current context."""
        suggestions = []
        
        if not self.company_profile or not self.key_metrics:
            suggestions.append({
                "type": "data_collection",
                "priority": "high",
                "title": "Complete Business Profile",
                "description": "Set up company profile and key metrics to get personalized optimization suggestions",
                "action": "Use update_metric() and set company profile"
            })
            return suggestions
        
        # Runway-based suggestions
        if self.key_metrics.runway and self.key_metrics.runway < 6:
            suggestions.append({
                "type": "financial",
                "priority": "critical",
                "title": "Critical Runway Alert",
                "description": f"Only {self.key_metrics.runway} months runway remaining",
                "action": "Consider fundraising or reducing burn rate immediately"
            })
        elif self.key_metrics.runway and self.key_metrics.runway < 12:
            suggestions.append({
                "type": "financial",
                "priority": "high",
                "title": "Runway Warning",
                "description": f"{self.key_metrics.runway} months runway remaining",
                "action": "Start planning fundraising or cost optimization"
            })
        
        # Growth-based suggestions
        if self.key_metrics.growth_rate and self.key_metrics.growth_rate < 0.05:  # Less than 5% monthly growth
            suggestions.append({
                "type": "growth",
                "priority": "high",
                "title": "Growth Acceleration Needed",
                "description": f"Monthly growth rate is {self.key_metrics.growth_rate*100:.1f}%",
                "action": "Focus on marketing automation and customer acquisition"
            })
        
        # CAC/LTV ratio suggestions
        if self.key_metrics.cac and self.key_metrics.ltv:
            ltv_cac_ratio = self.key_metrics.ltv / self.key_metrics.cac
            if ltv_cac_ratio < 3:
                suggestions.append({
                    "type": "unit_economics",
                    "priority": "high",
                    "title": "Poor Unit Economics",
                    "description": f"LTV/CAC ratio is {ltv_cac_ratio:.1f} (should be >3)",
                    "action": "Optimize customer acquisition or increase customer lifetime value"
                })
        
        # Churn-based suggestions
        if self.key_metrics.churn_rate and self.key_metrics.churn_rate > 0.05:  # More than 5% monthly churn
            suggestions.append({
                "type": "retention",
                "priority": "high",
                "title": "High Churn Rate",
                "description": f"Monthly churn rate is {self.key_metrics.churn_rate*100:.1f}%",
                "action": "Implement customer success automation and retention campaigns"
            })
        
        # Team size vs stage suggestions
        if self.company_profile.stage == CompanyStage.GROWTH and self.company_profile.team_size < 10:
            suggestions.append({
                "type": "scaling",
                "priority": "medium",
                "title": "Team Scaling Opportunity",
                "description": "Growth stage companies typically benefit from larger teams",
                "action": "Consider hiring key roles or automating repetitive tasks"
            })
        
        # Industry-specific suggestions
        if self.company_profile.industry == Industry.SAAS:
            if not self.key_metrics.mrr:
                suggestions.append({
                    "type": "metrics",
                    "priority": "medium",
                    "title": "Track SaaS Metrics",
                    "description": "SaaS companies should track MRR, churn, and unit economics",
                    "action": "Set up MRR tracking and reporting automation"
                })
        
        return suggestions
    
    def get_context_summary(self) -> Dict[str, Any]:
        """Get a summary of the current business context."""
        summary = {
            "session_id": self.session_id,
            "has_profile": self.company_profile is not None,
            "has_metrics": self.key_metrics is not None,
            "goal_count": len(self.active_goals),
            "has_constraints": self.resource_constraints is not None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None
        }
        
        if self.company_profile:
            summary["company"] = {
                "stage": self.company_profile.stage.value,
                "industry": self.company_profile.industry.value,
                "team_size": self.company_profile.team_size,
                "name": self.company_profile.company_name
            }
        
        if self.key_metrics:
            summary["metrics"] = {
                "mrr": self.key_metrics.mrr,
                "runway": self.key_metrics.runway,
                "growth_rate": self.key_metrics.growth_rate,
                "burn_rate": self.key_metrics.burn_rate
            }
        
        if self.active_goals:
            summary["goals"] = {
                "total": len(self.active_goals),
                "by_priority": {
                    "high": len([g for g in self.active_goals if g.priority == "high"]),
                    "medium": len([g for g in self.active_goals if g.priority == "medium"]),
                    "low": len([g for g in self.active_goals if g.priority == "low"])
                },
                "avg_progress": sum([g.progress for g in self.active_goals]) / len(self.active_goals)
            }
        
        return summary
    
    async def add_goal(self, title: str, description: str, target_value: Optional[Union[float, int, str]] = None, 
                       due_date: Optional[datetime] = None, priority: str = "medium", 
                       category: str = "general") -> bool:
        """Add a new business goal."""
        try:
            goal = BusinessGoal(
                title=title,
                description=description,
                target_value=target_value,
                due_date=due_date,
                priority=priority,
                category=category
            )
            
            self.active_goals.append(goal)
            await self.save_context()
            
            logger.info(f"Added new goal '{title}' for session {self.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding goal: {e}")
            return False
    
    async def update_goal_progress(self, goal_title: str, progress: float, 
                                   current_value: Optional[Union[float, int, str]] = None) -> bool:
        """Update progress on a specific goal."""
        try:
            for goal in self.active_goals:
                if goal.title == goal_title:
                    goal.progress = max(0.0, min(1.0, progress))  # Clamp between 0 and 1
                    if current_value is not None:
                        goal.current_value = current_value
                    
                    await self.save_context()
                    logger.info(f"Updated goal '{goal_title}' progress to {progress*100:.1f}%")
                    return True
            
            logger.warning(f"Goal '{goal_title}' not found for session {self.session_id}")
            return False
            
        except Exception as e:
            logger.error(f"Error updating goal progress: {e}")
            return False
    
    def get_context_for_agent_creation(self) -> Dict[str, Any]:
        """Get relevant context for agent creation decisions."""
        context = {
            "company_stage": self.company_profile.stage.value if self.company_profile else "unknown",
            "team_size": self.company_profile.team_size if self.company_profile else 0,
            "industry": self.company_profile.industry.value if self.company_profile else "unknown",
            "critical_metrics": {},
            "urgent_goals": [],
            "constraints": {},
            "optimization_focus": []
        }
        
        # Add critical metrics
        if self.key_metrics:
            if self.key_metrics.runway and self.key_metrics.runway < 12:
                context["critical_metrics"]["runway"] = self.key_metrics.runway
            if self.key_metrics.growth_rate:
                context["critical_metrics"]["growth_rate"] = self.key_metrics.growth_rate
            if self.key_metrics.burn_rate:
                context["critical_metrics"]["burn_rate"] = self.key_metrics.burn_rate
        
        # Add urgent goals
        if self.active_goals:
            urgent_goals = [
                goal for goal in self.active_goals 
                if goal.priority == "high" or (goal.due_date and (goal.due_date - datetime.now()).days < 30)
            ]
            context["urgent_goals"] = [
                {"title": goal.title, "category": goal.category, "progress": goal.progress} 
                for goal in urgent_goals
            ]
        
        # Add constraints
        if self.resource_constraints:
            if self.resource_constraints.budget:
                context["constraints"]["budget"] = self.resource_constraints.budget
            if self.resource_constraints.headcount_limit:
                context["constraints"]["headcount_limit"] = self.resource_constraints.headcount_limit
        
        # Add optimization focus areas
        suggestions = self.get_optimization_suggestions()
        context["optimization_focus"] = [
            {"type": s["type"], "priority": s["priority"], "title": s["title"]} 
            for s in suggestions[:3]  # Top 3 suggestions
        ]
        
        return context