"""
Jarvis Meta-Orchestrator: Business-level orchestration layer for HeyJarvis.

This module implements Jarvis, a meta-orchestrator that sits above the existing
HeyJarvisOrchestrator to provide business-level intelligence and coordination.
Jarvis understands company context, manages departments, and coordinates 
multiple agents while preserving all existing functionality.

Key Responsibilities:
- Business context awareness and decision making
- Department-level coordination and management
- Multi-agent workflow orchestration
- Strategic task planning and resource allocation
- Integration with existing single-agent workflows

Jarvis wraps the existing orchestrator rather than replacing it, ensuring
full backward compatibility with current agent building capabilities.
"""

import logging
import asyncio
import json
import re
import uuid
from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

import redis.asyncio as redis
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

# Import existing orchestration components
from .orchestrator import HeyJarvisOrchestrator, OrchestratorConfig
from .business_context import BusinessContext, CompanyStage, Industry
from .agent_communication import AgentMessageBus
from .state import (
    DeploymentStatus, 
    DepartmentStatus, 
    IntentType,
    DepartmentSpec,
    DepartmentState,
    OrchestratorState
)

logger = logging.getLogger(__name__)


class BusinessIntent(BaseModel):
    """Business-level intent analysis result."""
    category: Literal[
        "GROW_REVENUE", 
        "REDUCE_COSTS", 
        "IMPROVE_EFFICIENCY", 
        "LAUNCH_PRODUCT", 
        "CUSTOM_AUTOMATION"
    ] = Field(..., description="Business intent category")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    suggested_departments: List[str] = Field(
        default_factory=list, 
        description="Suggested departments for this intent"
    )
    key_metrics_to_track: List[str] = Field(
        default_factory=list,
        description="Key business metrics to track for this intent"
    )
    reasoning: str = Field(..., description="Explanation of the categorization")
    complexity_level: Literal["simple", "moderate", "complex"] = Field(
        default="moderate",
        description="Complexity level of the business intent"
    )
    estimated_timeline: Optional[str] = Field(
        None,
        description="Estimated timeline for implementation"
    )
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Prerequisites needed before implementation"
    )
    success_criteria: List[str] = Field(
        default_factory=list,
        description="Success criteria for measuring achievement"
    )


# TASK 13: Sales-focused enhancements
class SalesIntentType(Enum):
    """Sales-specific intent types for enhanced processing"""
    LEAD_GENERATION = "lead_generation"
    QUICK_WINS = "quick_wins"
    OUTREACH_CAMPAIGN = "outreach_campaign"
    BUSINESS_SUMMARY = "business_summary"
    WORKFLOW_STATUS = "workflow_status"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class SalesIntent:
    """Sales-specific intent with parameters"""
    intent_type: SalesIntentType
    confidence: float
    parameters: Dict[str, Any]
    raw_text: str
    session_id: str
    timestamp: datetime


@dataclass
class SalesResponse:
    """Enhanced response for sales requests"""
    response_text: str
    data: Optional[Dict[str, Any]] = None
    actions: Optional[List[str]] = None
    next_suggestions: Optional[List[str]] = None
    workflow_id: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class JarvisConfig:
    """Configuration for Jarvis meta-orchestrator."""
    # Inherit from existing orchestrator config
    orchestrator_config: OrchestratorConfig
    
    # Jarvis-specific settings
    max_concurrent_departments: int = 5
    business_context_refresh_interval: int = 300  # 5 minutes
    department_coordination_timeout: int = 30  # 30 seconds
    enable_autonomous_department_creation: bool = True
    enable_cross_department_coordination: bool = True
    
    # AI model settings for business-level decisions
    business_model: str = "claude-3-5-sonnet-20241022"
    business_temperature: float = 0.2  # More conservative for business decisions


class JarvisDepartment:
    """Represents a managed department within Jarvis."""
    
    def __init__(self, spec: DepartmentSpec, message_bus: AgentMessageBus):
        self.spec = spec
        self.message_bus = message_bus
        self.state = DepartmentState(
            department_id=spec["department_id"] or f"dept_{int(datetime.utcnow().timestamp())}",
            active_agents=[],
            shared_memory={},
            status=DepartmentStatus.INACTIVE,
            last_coordination=None,
            coordination_history=[],
            resource_usage={},
            error_log=[]
        )
        self.created_at = datetime.utcnow()
        self.last_activity = datetime.utcnow()
    
    async def activate(self) -> bool:
        """Activate the department and its agents."""
        try:
            self.state["status"] = DepartmentStatus.INITIALIZING
            logger.info(f"Activating department: {self.spec['name']}")
            
            # Activate agents in the department
            for agent_spec in self.spec["micro_agents"]:
                agent_id = agent_spec.get("name", "unknown_agent")
                self.state["active_agents"].append(agent_id)
            
            self.state["status"] = DepartmentStatus.ACTIVE
            self.last_activity = datetime.utcnow()
            
            logger.info(f"Department {self.spec['name']} activated with {len(self.state['active_agents'])} agents")
            return True
            
        except Exception as e:
            logger.error(f"Error activating department {self.spec['name']}: {e}")
            self.state["status"] = DepartmentStatus.ERROR
            self.state["error_log"].append({
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "context": "department_activation"
            })
            return False
    
    async def coordinate_agents(self) -> Dict[str, Any]:
        """Coordinate agents within the department based on coordination rules."""
        try:
            self.state["status"] = DepartmentStatus.COORDINATING
            coordination_results = {}
            
            # Apply coordination rules
            for rule in self.spec["coordination_rules"]:
                if not rule["enabled"]:
                    continue
                
                try:
                    # Evaluate trigger condition (simplified for now)
                    if await self._evaluate_coordination_rule(rule):
                        result = await self._execute_coordination_actions(rule["actions"])
                        coordination_results[rule["rule_id"]] = result
                        
                        # Log coordination event
                        self.state["coordination_history"].append({
                            "timestamp": datetime.utcnow().isoformat(),
                            "rule_id": rule["rule_id"],
                            "rule_name": rule["name"],
                            "actions_executed": len(rule["actions"]),
                            "result": result
                        })
                        
                except Exception as e:
                    logger.error(f"Error executing coordination rule {rule['rule_id']}: {e}")
                    coordination_results[rule["rule_id"]] = {"error": str(e)}
            
            self.state["status"] = DepartmentStatus.ACTIVE
            self.state["last_coordination"] = datetime.utcnow().isoformat()
            self.last_activity = datetime.utcnow()
            
            return coordination_results
            
        except Exception as e:
            logger.error(f"Error coordinating department {self.spec['name']}: {e}")
            self.state["status"] = DepartmentStatus.ERROR
            return {"error": str(e)}
    
    async def _evaluate_coordination_rule(self, rule: Dict[str, Any]) -> bool:
        """Evaluate if a coordination rule should be triggered."""
        # Simplified rule evaluation - in a full implementation,
        # this would parse and evaluate the trigger_condition
        trigger = rule.get("trigger_condition", "")
        
        # For now, always return True to execute all enabled rules
        # In practice, this would evaluate conditions like:
        # - "agent_status == 'idle'"
        # - "message_queue_length > 10"
        # - "time_since_last_activity > 300"
        return True
    
    async def _execute_coordination_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute coordination actions."""
        results = []
        
        for action in actions:
            try:
                action_type = action.get("type", "unknown")
                action_params = action.get("parameters", {})
                
                if action_type == "send_message":
                    # Send coordination message between agents
                    result = await self._send_coordination_message(action_params)
                elif action_type == "redistribute_tasks":
                    # Redistribute tasks among agents
                    result = await self._redistribute_tasks(action_params)
                elif action_type == "update_shared_memory":
                    # Update shared department memory
                    result = await self._update_shared_memory(action_params)
                else:
                    result = {"error": f"Unknown action type: {action_type}"}
                
                results.append({"action": action_type, "result": result})
                
            except Exception as e:
                results.append({"action": action.get("type", "unknown"), "error": str(e)})
        
        return {"actions_executed": len(results), "results": results}
    
    async def _send_coordination_message(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a coordination message between agents."""
        try:
            from_agent = params.get("from_agent")
            to_agent = params.get("to_agent")
            message_content = params.get("message", {})
            
            if from_agent and to_agent:
                message_id = await self.message_bus.publish_message(
                    from_agent, to_agent, "CoordinationMessage", message_content
                )
                return {"success": True, "message_id": message_id}
            else:
                return {"error": "Missing from_agent or to_agent"}
                
        except Exception as e:
            return {"error": str(e)}
    
    async def _redistribute_tasks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Redistribute tasks among department agents."""
        # Placeholder for task redistribution logic
        return {"success": True, "redistributed_tasks": 0}
    
    async def _update_shared_memory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Update shared department memory."""
        try:
            updates = params.get("updates", {})
            self.state["shared_memory"].update(updates)
            return {"success": True, "updated_keys": list(updates.keys())}
        except Exception as e:
            return {"error": str(e)}


class Jarvis:
    """
    Jarvis Meta-Orchestrator: Business-level orchestration for HeyJarvis.
    
    Jarvis is a meta-orchestrator that provides business intelligence and 
    department-level coordination while preserving all existing agent 
    building functionality. It wraps the existing HeyJarvisOrchestrator
    and adds:
    
    - Business context awareness
    - Department management and coordination
    - Multi-agent workflow orchestration
    - Strategic decision making
    - Resource optimization
    
    All existing single-agent workflows continue to work unchanged.
    """
    
    def __init__(self, config: JarvisConfig):
        """
        Initialize Jarvis meta-orchestrator.
        
        Args:
            config: Jarvis configuration including orchestrator config
        """
        self.config = config
        
        # Initialize existing orchestrator (DO NOT MODIFY)
        self.agent_orchestrator = HeyJarvisOrchestrator(config.orchestrator_config)
        
        # Initialize Redis client (reuse from orchestrator)
        self.redis_client = None
        
        # Initialize business context (will be set per session)
        self.business_context: Optional[BusinessContext] = None
        
        # Initialize message bus (will be set after Redis client)
        self.message_bus: Optional[AgentMessageBus] = None
        
        # Department management
        self.active_departments: Dict[str, JarvisDepartment] = {}
        
        # Business-level LLM for strategic decisions
        self.business_llm = ChatAnthropic(
            api_key=config.orchestrator_config.anthropic_api_key,
            model=config.business_model,
            temperature=config.business_temperature
        )
        
        # State tracking
        self.last_business_context_refresh = None
        self.session_contexts: Dict[str, BusinessContext] = {}
        
        logger.info("Jarvis meta-orchestrator initialized")
    
    async def initialize(self) -> None:
        """Initialize Jarvis and all underlying components."""
        try:
            # Initialize the existing orchestrator first
            await self.agent_orchestrator.initialize()
            
            # Get Redis client from orchestrator
            self.redis_client = self.agent_orchestrator.redis_client
            
            # Initialize message bus
            self.message_bus = AgentMessageBus(self.redis_client)
            
            logger.info("Jarvis initialization completed successfully")
            
        except Exception as e:
            logger.error(f"Error initializing Jarvis: {e}")
            raise
    
    async def analyze_business_intent(self, request: str, session_id: str) -> BusinessIntent:
        """
        Analyze a business request to determine the underlying business intent.
        
        This method uses the existing LLM to categorize business requests into
        strategic categories and provides guidance on implementation approach.
        
        Args:
            request: User's business request
            session_id: Session identifier for context
            
        Returns:
            BusinessIntent: Analyzed business intent with category and guidance
        """
        try:
            # Get business context for enhanced analysis
            await self._ensure_business_context(session_id)
            context_info = ""
            
            if self.business_context:
                context_summary = self.business_context.get_context_summary()
                if context_summary.get("company"):
                    company = context_summary["company"]
                    context_info = f"""
Company Context:
- Stage: {company.get('stage', 'unknown')}
- Industry: {company.get('industry', 'unknown')}
- Team Size: {company.get('team_size', 'unknown')}
"""
                
                # Add optimization focus areas
                optimization_suggestions = self.business_context.get_optimization_suggestions()
                if optimization_suggestions:
                    focus_areas = [s.get("type", "unknown") for s in optimization_suggestions[:3]]
                    context_info += f"- Current Focus: {', '.join(focus_areas)}\n"
            
            system_prompt = """You are an expert business analyst specializing in translating business requests into strategic categories.

Analyze business requests and categorize them into these strategic categories:

BUSINESS INTENT CATEGORIES:
1. GROW_REVENUE: Sales growth, marketing expansion, customer acquisition, revenue optimization
   Examples: "increase sales", "get more customers", "improve conversion rates", "expand market reach"

2. REDUCE_COSTS: Cost reduction, operational efficiency, resource optimization, automation for savings
   Examples: "cut costs", "reduce burn rate", "optimize spending", "automate manual processes"

3. IMPROVE_EFFICIENCY: Process improvement, productivity enhancement, workflow optimization
   Examples: "streamline operations", "improve productivity", "optimize workflows", "reduce manual work"

4. LAUNCH_PRODUCT: Product development, feature releases, market launch activities
   Examples: "launch new feature", "product rollout", "go-to-market", "release management"

5. CUSTOM_AUTOMATION: Technical automation, specific tools, agent creation for operational tasks
   Examples: "create email agent", "automate backups", "monitor system", "integrate APIs"

DEPARTMENT MAPPING:
- GROW_REVENUE → Sales, Marketing, Customer Success, Business Development
- REDUCE_COSTS → Operations, Finance, IT, Procurement
- IMPROVE_EFFICIENCY → Operations, HR, IT, Process Engineering
- LAUNCH_PRODUCT → Product, Marketing, Engineering, Sales
- CUSTOM_AUTOMATION → IT, Engineering, Operations

KEY METRICS BY CATEGORY:
- GROW_REVENUE → MRR, ARR, CAC, LTV, conversion rates, pipeline value
- REDUCE_COSTS → burn rate, cost per acquisition, operational costs, efficiency ratios
- IMPROVE_EFFICIENCY → cycle time, throughput, error rates, productivity metrics
- LAUNCH_PRODUCT → time to market, adoption rates, feature usage, customer feedback
- CUSTOM_AUTOMATION → automation coverage, error reduction, time savings, system uptime

COMPLEXITY ASSESSMENT:
- simple: Single process, clear requirements, minimal dependencies
- moderate: Multiple processes, some integration needed, clear business case
- complex: Cross-functional, significant change management, high business impact

TIMELINE ESTIMATES:
- simple: 1-4 weeks
- moderate: 1-3 months  
- complex: 3-12 months

Return a JSON object with the exact structure:
{
    "category": "one of the 5 categories above",
    "confidence": 0.85,
    "suggested_departments": ["list", "of", "departments"],
    "key_metrics_to_track": ["list", "of", "metrics"],
    "reasoning": "explanation of why this category was chosen",
    "complexity_level": "simple|moderate|complex",
    "estimated_timeline": "timeline estimate",
    "prerequisites": ["list", "of", "requirements"],
    "success_criteria": ["list", "of", "success", "measures"]
}

Be specific and actionable in your analysis. Consider the business context provided."""

            user_context = f"""Business Request: {request}

{context_info.strip() if context_info.strip() else "No company context available yet."}

Analyze this request and categorize it strategically."""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_context)
            ]

            response = await self.business_llm.ainvoke(messages)
            
            # Clean and parse response
            content = response.content.strip()
            
            # Remove markdown code blocks
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            
            content = content.strip()
            
            # Extract JSON object
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx + 1]
            else:
                json_content = content
            
            intent_data = json.loads(json_content)
            
            # Create BusinessIntent object
            business_intent = BusinessIntent(**intent_data)
            
            logger.info(f"Business intent analyzed: {business_intent.category} (confidence: {business_intent.confidence:.2f})")
            
            return business_intent
            
        except Exception as e:
            logger.error(f"Error analyzing business intent: {e}")
            
            # Fallback: assume custom automation with low confidence
            return BusinessIntent(
                category="CUSTOM_AUTOMATION",
                confidence=0.3,
                suggested_departments=["IT", "Engineering"],
                key_metrics_to_track=["automation_coverage", "time_savings"],
                reasoning=f"Failed to analyze intent due to error: {str(e)}. Defaulting to custom automation.",
                complexity_level="moderate",
                estimated_timeline="2-6 weeks",
                prerequisites=["Technical requirements analysis"],
                success_criteria=["Agent successfully deployed", "User requirements met"]
            )

    async def process_business_request(
        self, 
        request: str, 
        session_id: str,
        clarification_responses: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Process a business request with full context awareness.
        
        This is the main entry point for Jarvis. It analyzes the request
        in business context and decides whether to:
        1. Forward to existing single-agent orchestrator
        2. Create/coordinate departments
        3. Handle as a business-level decision
        
        Args:
            request: User's business request
            session_id: Session identifier
            clarification_responses: Optional clarification responses
            
        Returns:
            Result dictionary with processing outcome
        """
        try:
            logger.info(f"Jarvis processing business request: {request[:100]}...")
            
            # Initialize or get business context for this session
            await self._ensure_business_context(session_id)
            
            # Log request in business context
            start_time = datetime.utcnow()
            
            try:
                # Step 1: Analyze business intent
                business_intent = await self.analyze_business_intent(request, session_id)
                
                # Step 2: Route based on intent category
                if business_intent.category == "CUSTOM_AUTOMATION":
                    # Route to existing agent builder for technical automation
                    logger.info(f"Routing to agent builder for custom automation request")
                    result = await self.agent_orchestrator.process_request(
                        request, session_id, clarification_responses
                    )
                else:
                    # Handle business-level intents
                    logger.info(f"Processing business intent: {business_intent.category}")
                    result = await self._handle_business_intent(
                        request, session_id, business_intent, clarification_responses
                    )
                
                # Add Jarvis metadata to the result
                result["jarvis_metadata"] = {
                    "processed_by": "jarvis_meta_orchestrator",
                    "business_context_available": self.business_context is not None,
                    "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000),
                    "active_departments": list(self.active_departments.keys()),
                    "session_id": session_id,
                    "business_intent": {
                        "category": business_intent.category,
                        "confidence": business_intent.confidence,
                        "complexity": business_intent.complexity_level,
                        "estimated_timeline": business_intent.estimated_timeline
                    }
                }
                
                # Store business intent in context for tracking
                if self.business_context:
                    await self._store_business_intent(business_intent, request, session_id)
                
                # Update business context if agent was created successfully
                if result.get("deployment_status") == DeploymentStatus.COMPLETED:
                    await self._update_business_context_from_result(result, request)
                
                logger.info(f"Jarvis successfully processed {business_intent.category} request for session {session_id}")
                return result
                
            except Exception as orchestrator_error:
                logger.error(f"Orchestrator error: {orchestrator_error}")
                
                # Fallback error handling
                return {
                    "error_message": f"Jarvis encountered an error: {str(orchestrator_error)}",
                    "deployment_status": DeploymentStatus.FAILED,
                    "jarvis_metadata": {
                        "processed_by": "jarvis_meta_orchestrator",
                        "error_handled_by_jarvis": True,
                        "fallback_attempted": True,
                        "processing_time_ms": int((datetime.utcnow() - start_time).total_seconds() * 1000)
                    }
                }
                
        except Exception as e:
            logger.error(f"Critical error in Jarvis processing: {e}")
            
            # Ultimate fallback - return error but preserve system stability
            return {
                "error_message": f"Critical Jarvis error: {str(e)}",
                "deployment_status": DeploymentStatus.FAILED,
                "jarvis_metadata": {
                    "processed_by": "jarvis_meta_orchestrator",
                    "critical_error": True,
                    "error_type": type(e).__name__
                }
            }
    
    async def get_business_insights(self, session_id: str) -> Dict[str, Any]:
        """Get business insights and optimization suggestions."""
        try:
            await self._ensure_business_context(session_id)
            
            if not self.business_context:
                return {"error": "Business context not available"}
            
            # Get optimization suggestions
            suggestions = self.business_context.get_optimization_suggestions()
            
            # Get goal progress
            goal_progress = await self.business_context.check_goal_progress()
            
            # Get context summary
            context_summary = self.business_context.get_context_summary()
            
            return {
                "business_insights": {
                    "optimization_suggestions": suggestions,
                    "goal_progress": goal_progress,
                    "context_summary": context_summary,
                    "active_departments": {
                        dept_id: {
                            "name": dept.spec["name"],
                            "status": dept.state["status"],
                            "active_agents": len(dept.state["active_agents"]),
                            "last_activity": dept.last_activity.isoformat()
                        }
                        for dept_id, dept in self.active_departments.items()
                    }
                },
                "generated_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting business insights: {e}")
            return {"error": str(e)}
    
    async def create_department(
        self, 
        name: str, 
        description: str, 
        agent_specs: List[Dict[str, Any]],
        coordination_rules: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Create a new department with specified agents."""
        try:
            department_id = f"dept_{name.lower().replace(' ', '_')}_{int(datetime.utcnow().timestamp())}"
            
            # Create department specification
            dept_spec: DepartmentSpec = {
                "name": name,
                "description": description,
                "micro_agents": agent_specs,
                "coordination_rules": coordination_rules or [],
                "department_id": department_id,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
                "config": {}
            }
            
            # Create department instance
            department = JarvisDepartment(dept_spec, self.message_bus)
            
            # Activate department
            if await department.activate():
                self.active_departments[department_id] = department
                logger.info(f"Created and activated department: {name} ({department_id})")
                return department_id
            else:
                raise Exception("Failed to activate department")
                
        except Exception as e:
            logger.error(f"Error creating department {name}: {e}")
            raise
    
    async def get_department_status(self, department_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific department."""
        department = self.active_departments.get(department_id)
        if not department:
            return None
        
        return {
            "department_id": department_id,
            "name": department.spec["name"],
            "description": department.spec["description"],
            "status": department.state["status"],
            "active_agents": department.state["active_agents"],
            "agent_count": len(department.state["active_agents"]),
            "coordination_rules": len(department.spec["coordination_rules"]),
            "last_coordination": department.state["last_coordination"],
            "created_at": department.created_at.isoformat(),
            "last_activity": department.last_activity.isoformat(),
            "resource_usage": department.state["resource_usage"],
            "recent_coordination_history": department.state["coordination_history"][-5:]  # Last 5 events
        }
    
    async def list_departments(self) -> List[Dict[str, Any]]:
        """List all active departments."""
        departments = []
        for dept_id, dept in self.active_departments.items():
            dept_info = await self.get_department_status(dept_id)
            if dept_info:
                departments.append(dept_info)
        return departments
    
    async def coordinate_department(self, department_id: str) -> Dict[str, Any]:
        """Manually trigger coordination for a department."""
        department = self.active_departments.get(department_id)
        if not department:
            return {"error": f"Department {department_id} not found"}
        
        return await department.coordinate_agents()
    
    async def _handle_business_intent(
        self, 
        request: str, 
        session_id: str, 
        business_intent: BusinessIntent,
        clarification_responses: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Handle business-level intents that may require department coordination.
        
        For now, this routes business intents to the existing orchestrator but
        provides enhanced context and prepares for future department activation.
        """
        try:
            logger.info(f"Handling business intent: {business_intent.category}")
            
            # For Phase 2, route business intents to existing orchestrator with enhanced context
            # Future phases will create departments and coordinate multiple agents
            
            # Enhance the request with business context
            enhanced_request = await self._enhance_request_with_business_context(
                request, business_intent
            )
            
            # Process through existing orchestrator
            result = await self.agent_orchestrator.process_request(
                enhanced_request, session_id, clarification_responses
            )
            
            # Add business intent guidance to the result
            result["business_guidance"] = {
                "intent_category": business_intent.category,
                "suggested_departments": business_intent.suggested_departments,
                "key_metrics": business_intent.key_metrics_to_track,
                "complexity": business_intent.complexity_level,
                "timeline": business_intent.estimated_timeline,
                "prerequisites": business_intent.prerequisites,
                "success_criteria": business_intent.success_criteria,
                "reasoning": business_intent.reasoning
            }
            
            logger.info(f"Business intent {business_intent.category} processed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Error handling business intent {business_intent.category}: {e}")
            
            # Fallback to regular processing
            result = await self.agent_orchestrator.process_request(
                request, session_id, clarification_responses
            )
            
            result["business_guidance"] = {
                "intent_category": business_intent.category,
                "note": f"Business intent detected but processed as regular automation due to error: {str(e)}"
            }
            
            return result
    
    async def _enhance_request_with_business_context(
        self, 
        request: str, 
        business_intent: BusinessIntent
    ) -> str:
        """Enhance the user request with business context for better agent creation."""
        
        # Add business context to help the agent builder understand the strategic purpose
        enhancement = f"""
Business Context: This request is part of a {business_intent.category} initiative.
Strategic Purpose: {business_intent.reasoning}
Target Departments: {', '.join(business_intent.suggested_departments)}
Key Success Metrics: {', '.join(business_intent.key_metrics_to_track)}

Original Request: {request}
"""
        
        return enhancement.strip()
    
    async def _store_business_intent(
        self, 
        business_intent: BusinessIntent, 
        original_request: str, 
        session_id: str
    ) -> None:
        """Store business intent in Redis for tracking and analytics."""
        try:
            intent_key = f"business_intent:{session_id}:{int(datetime.utcnow().timestamp())}"
            
            intent_data = {
                "request": original_request,
                "category": business_intent.category,
                "confidence": business_intent.confidence,
                "suggested_departments": business_intent.suggested_departments,
                "key_metrics": business_intent.key_metrics_to_track,
                "reasoning": business_intent.reasoning,
                "complexity": business_intent.complexity_level,
                "timeline": business_intent.estimated_timeline,
                "prerequisites": business_intent.prerequisites,
                "success_criteria": business_intent.success_criteria,
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": session_id
            }
            
            # Store intent data
            await self.redis_client.setex(
                intent_key,
                86400,  # 24 hours TTL
                json.dumps(intent_data)
            )
            
            # Add to session's intent history
            intent_history_key = f"business_intents:{session_id}"
            await self.redis_client.lpush(intent_history_key, intent_key)
            await self.redis_client.expire(intent_history_key, 86400)
            
            logger.info(f"Business intent stored: {business_intent.category} for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error storing business intent: {e}")
    
    async def get_business_intent_history(self, session_id: str) -> List[Dict[str, Any]]:
        """Get historical business intents for a session."""
        try:
            intent_history_key = f"business_intents:{session_id}"
            intent_keys = await self.redis_client.lrange(intent_history_key, 0, -1)
            
            intents = []
            for intent_key in intent_keys:
                intent_data = await self.redis_client.get(intent_key.decode())
                if intent_data:
                    intents.append(json.loads(intent_data))
            
            return intents
            
        except Exception as e:
            logger.error(f"Error getting business intent history: {e}")
            return []
    
    async def _ensure_business_context(self, session_id: str) -> None:
        """Ensure business context is loaded for the session."""
        try:
            # Check if we need to refresh or create business context
            if (session_id not in self.session_contexts or 
                self._should_refresh_business_context()):
                
                # Create new business context
                business_context = BusinessContext(self.redis_client, session_id)
                
                # Try to load existing context
                await business_context.load_context()
                
                # Store in session contexts
                self.session_contexts[session_id] = business_context
                self.business_context = business_context
                self.last_business_context_refresh = datetime.utcnow()
                
                logger.info(f"Business context loaded/refreshed for session {session_id}")
            else:
                # Use existing context
                self.business_context = self.session_contexts[session_id]
                
        except Exception as e:
            logger.error(f"Error ensuring business context for session {session_id}: {e}")
            # Create empty context as fallback
            self.business_context = BusinessContext(self.redis_client, session_id)
    
    def _should_refresh_business_context(self) -> bool:
        """Check if business context should be refreshed."""
        if not self.last_business_context_refresh:
            return True
        
        refresh_interval = timedelta(seconds=self.config.business_context_refresh_interval)
        return datetime.utcnow() - self.last_business_context_refresh > refresh_interval
    
    async def _update_business_context_from_result(
        self, 
        result: Dict[str, Any], 
        original_request: str
    ) -> None:
        """Update business context based on successful agent creation."""
        try:
            if not self.business_context:
                return
            
            # Extract insights from the created agent
            agent_spec = result.get("agent_spec", {})
            agent_name = agent_spec.get("name", "Unknown Agent")
            capabilities = agent_spec.get("capabilities", [])
            
            # This could trigger business metric updates
            # For example, if an agent was created for lead generation,
            # we might want to track that as part of growth initiatives
            
            logger.info(f"Business context updated after creating agent: {agent_name}")
            
        except Exception as e:
            logger.error(f"Error updating business context from result: {e}")
    
    # TASK 13: Sales-focused enhancements
    async def process_sales_request(self, user_input: str, session_id: str = None) -> SalesResponse:
        """Enhanced sales request processing with specialized intent analysis"""
        if not session_id:
            session_id = f"sales_session_{uuid.uuid4()}"
        
        try:
            # Analyze sales intent
            sales_intent = await self._analyze_sales_intent(user_input, session_id)
            
            # Store in session context
            await self._store_sales_intent(sales_intent)
            
            # Process based on intent type
            if sales_intent.intent_type == SalesIntentType.LEAD_GENERATION:
                return await self._handle_lead_generation_intent(sales_intent)
            elif sales_intent.intent_type == SalesIntentType.QUICK_WINS:
                return await self._handle_quick_wins_intent(sales_intent)
            elif sales_intent.intent_type == SalesIntentType.OUTREACH_CAMPAIGN:
                return await self._handle_outreach_campaign_intent(sales_intent)
            elif sales_intent.intent_type == SalesIntentType.BUSINESS_SUMMARY:
                return await self._handle_business_summary_intent(sales_intent)
            elif sales_intent.intent_type == SalesIntentType.WORKFLOW_STATUS:
                return await self._handle_workflow_status_intent(sales_intent)
            elif sales_intent.intent_type == SalesIntentType.HELP:
                return await self._handle_sales_help_intent(sales_intent)
            else:
                return await self._handle_unknown_sales_intent(sales_intent)
        
        except Exception as e:
            logger.error(f"Error processing sales request: {e}")
            return SalesResponse(
                response_text=f"I encountered an error processing your request: {str(e)}",
                session_id=session_id
            )
    
    async def _analyze_sales_intent(self, user_input: str, session_id: str) -> SalesIntent:
        """Analyze user input for sales-specific intents"""
        user_input_lower = user_input.lower()
        
        # Sales intent patterns
        sales_patterns = {
            SalesIntentType.LEAD_GENERATION: [
                r"find.*leads?", r"scan.*prospects?", r"search.*companies?",
                r"generate.*leads?", r"look for.*contacts?", r"i need.*leads?",
                r"find.*\b(cto|ceo|vp|director|manager)\b",
                r"target.*\b(saas|fintech|healthcare|manufacturing)\b",
                r"get.*\d+.*leads?", r"identify.*potential.*customers?"
            ],
            SalesIntentType.QUICK_WINS: [
                r"quick.*wins?", r"immediate.*opportunities?", r"high.*priority.*leads?",
                r"urgent.*prospects?", r"fast.*results?", r"top.*leads?",
                r"hottest.*prospects?", r"best.*opportunities?"
            ],
            SalesIntentType.OUTREACH_CAMPAIGN: [
                r"create.*campaign", r"send.*outreach", r"compose.*messages?",
                r"write.*emails?", r"start.*campaign", r"launch.*outreach",
                r"personalize.*messages?", r"generate.*outreach"
            ],
            SalesIntentType.BUSINESS_SUMMARY: [
                r"summarize.*business", r"business.*summary", r"pipeline.*status",
                r"sales.*report", r"performance.*summary", r"analytics.*report",
                r"dashboard.*summary", r"metrics.*overview"
            ],
            SalesIntentType.WORKFLOW_STATUS: [
                r"workflow.*status", r"check.*progress", r"execution.*status",
                r"task.*progress", r"what.*running", r"current.*workflows?",
                r"active.*processes?", r"job.*status"
            ],
            SalesIntentType.HELP: [
                r"help", r"what.*can.*do", r"how.*work", r"commands?",
                r"capabilities?", r"functions?", r"features?", r"usage"
            ]
        }
        
        # Check patterns
        for intent_type, patterns in sales_patterns.items():
            for pattern in patterns:
                if re.search(pattern, user_input_lower):
                    parameters = await self._extract_sales_parameters(user_input, intent_type)
                    return SalesIntent(
                        intent_type=intent_type,
                        confidence=0.8,
                        parameters=parameters,
                        raw_text=user_input,
                        session_id=session_id,
                        timestamp=datetime.utcnow()
                    )
        
        # Fallback to AI analysis
        return await self._ai_analyze_sales_intent(user_input, session_id)
    
    async def _extract_sales_parameters(self, user_input: str, intent_type: SalesIntentType) -> Dict[str, Any]:
        """Extract parameters from user input for sales intents"""
        parameters = {}
        
        if intent_type == SalesIntentType.LEAD_GENERATION:
            # Extract industries
            industries = []
            industry_patterns = {
                r"\bsaas\b": "SaaS", r"\bfintech\b": "FinTech",
                r"\be-commerce\b": "E-commerce", r"\bhealthcare\b": "Healthcare",
                r"\bmanufacturing\b": "Manufacturing"
            }
            
            for pattern, industry in industry_patterns.items():
                if re.search(pattern, user_input.lower()):
                    industries.append(industry)
            
            if industries:
                parameters["industries"] = industries
            
            # Extract titles
            titles = []
            title_patterns = {
                r"\bcto\b": "CTO", r"\bceo\b": "CEO", r"\bvp\b": "VP",
                r"\bdirector\b": "Director", r"\bmanager\b": "Manager"
            }
            
            for pattern, title in title_patterns.items():
                if re.search(pattern, user_input.lower()):
                    titles.append(title)
            
            if titles:
                parameters["titles"] = titles
            
            # Extract numbers
            numbers = re.findall(r'\b(\d+)\b', user_input)
            if numbers:
                parameters["max_results"] = int(numbers[0])
        
        elif intent_type == SalesIntentType.QUICK_WINS:
            # Extract count
            numbers = re.findall(r'\b(\d+)\b', user_input)
            if numbers:
                parameters["count"] = int(numbers[0])
            else:
                parameters["count"] = 5  # Default
        
        elif intent_type == SalesIntentType.OUTREACH_CAMPAIGN:
            # Extract campaign parameters
            if "formal" in user_input.lower():
                parameters["tone"] = "formal"
            elif "casual" in user_input.lower():
                parameters["tone"] = "casual"
            elif "friendly" in user_input.lower():
                parameters["tone"] = "friendly"
        
        return parameters
    
    async def _ai_analyze_sales_intent(self, user_input: str, session_id: str) -> SalesIntent:
        """Use AI to analyze complex sales intents"""
        system_prompt = """Analyze this sales request for intent and parameters:

Available intents:
- lead_generation: Finding new prospects
- quick_wins: Immediate high-value opportunities  
- outreach_campaign: Creating and sending messages
- business_summary: Reporting and analytics
- workflow_status: Checking process status
- help: Getting assistance
- unknown: Unclear intent

Extract parameters like:
- industries: SaaS, FinTech, E-commerce, Healthcare, Manufacturing
- titles: CTO, CEO, VP, Director, Manager
- max_results: number of results wanted
- tone: formal, casual, friendly

Respond with JSON containing: intent, confidence (0-1), parameters"""
        
        try:
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"User Input: {user_input}")
            ]
            
            response = await self.business_llm.ainvoke(messages)
            analysis = json.loads(response.content)
            
            return SalesIntent(
                intent_type=SalesIntentType(analysis.get("intent", "unknown")),
                confidence=analysis.get("confidence", 0.5),
                parameters=analysis.get("parameters", {}),
                raw_text=user_input,
                session_id=session_id,
                timestamp=datetime.utcnow()
            )
        except:
            return SalesIntent(
                intent_type=SalesIntentType.UNKNOWN,
                confidence=0.3,
                parameters={},
                raw_text=user_input,
                session_id=session_id,
                timestamp=datetime.utcnow()
            )
    
    async def _handle_lead_generation_intent(self, intent: SalesIntent) -> SalesResponse:
        """Handle lead generation requests"""
        # Extract parameters
        industries = intent.parameters.get("industries", ["SaaS"])
        titles = intent.parameters.get("titles", ["CTO", "VP"])
        max_results = intent.parameters.get("max_results", 20)
        
        # Start progress tracking
        await self._publish_progress_update(intent.session_id, {
            "status": "scanning",
            "progress": 10,
            "message": "Scanning for leads..."
        })
        
        # Simulate lead generation process
        await asyncio.sleep(0.1)  # Brief processing delay
        
        await self._publish_progress_update(intent.session_id, {
            "status": "processing",
            "progress": 50,
            "message": "Processing lead data..."
        })
        
        # Generate mock results
        leads_found = min(max_results, 25)  # Simulate realistic results
        high_quality = int(leads_found * 0.3)  # 30% high quality
        
        await self._publish_progress_update(intent.session_id, {
            "status": "completed",
            "progress": 100,
            "message": f"Found {leads_found} qualified leads!"
        })
        
        response_text = f"""🎯 Lead Generation Complete!

Found {leads_found} qualified leads:
• {high_quality} high-quality prospects (80+ score)
• {leads_found - high_quality} medium-quality prospects (60-79 score)

Target Profile:
• Industries: {', '.join(industries)}
• Titles: {', '.join(titles)}
• Results: {leads_found} leads"""
        
        data = {
            "leads_found": leads_found,
            "high_quality_count": high_quality,
            "medium_quality_count": leads_found - high_quality,
            "target_industries": industries,
            "target_titles": titles,
            "search_parameters": intent.parameters
        }
        
        next_suggestions = [
            "Create outreach campaign for top leads",
            "Get quick wins from high-priority prospects",
            "Analyze lead quality patterns",
            "Export leads to CRM"
        ]
        
        return SalesResponse(
            response_text=response_text,
            data=data,
            next_suggestions=next_suggestions,
            session_id=intent.session_id
        )
    
    async def _handle_quick_wins_intent(self, intent: SalesIntent) -> SalesResponse:
        """Handle quick wins requests"""
        count = intent.parameters.get("count", 5)
        
        response_text = f"""⚡ Quick Wins Analysis Complete!

Identified {count} high-impact opportunities:

Top prospects ready for immediate outreach:
1. Sarah Chen - VP Engineering at TechCorp (Score: 92/100)
2. Mike Johnson - CTO at DataFlow Inc (Score: 89/100)
3. Lisa Wang - Director of IT at CloudSys (Score: 85/100)"""
        
        data = {
            "quick_wins_count": count,
            "avg_score": 88.7,
            "total_revenue_potential": f"${count * 25000:,}",
            "estimated_close_time": "2-4 weeks"
        }
        
        next_suggestions = [
            "Review and send personalized messages",
            "Schedule follow-up sequences",
            "Add to high-priority pipeline",
            "Set up response tracking"
        ]
        
        return SalesResponse(
            response_text=response_text,
            data=data,
            next_suggestions=next_suggestions,
            session_id=intent.session_id
        )
    
    async def _handle_outreach_campaign_intent(self, intent: SalesIntent) -> SalesResponse:
        """Handle outreach campaign creation"""
        tone = intent.parameters.get("tone", "professional")
        
        # Simulate campaign creation
        campaign_id = f"campaign_{uuid.uuid4()}"
        
        response_text = f"""📧 Outreach Campaign Created Successfully!

Campaign ID: {campaign_id}
Tone: {tone.title()}
Status: Ready for Launch

Campaign Details:
• Target Audience: Decision makers in tech companies
• Message Templates: 3 variations created
• Follow-up Sequence: 5-touch sequence
• Estimated Reach: 500+ prospects"""
        
        data = {
            "campaign_id": campaign_id,
            "tone": tone,
            "status": "ready",
            "templates_created": 3,
            "follow_up_sequence": 5,
            "estimated_reach": 500
        }
        
        next_suggestions = [
            "Review and approve campaign messages",
            "Schedule campaign launch",
            "Set up tracking and analytics",
            "Configure A/B testing"
        ]
        
        return SalesResponse(
            response_text=response_text,
            data=data,
            workflow_id=campaign_id,
            next_suggestions=next_suggestions,
            session_id=intent.session_id
        )
    
    async def _handle_business_summary_intent(self, intent: SalesIntent) -> SalesResponse:
        """Handle business summary requests"""
        response_text = """📊 Business Summary Report

Sales Pipeline Overview:
• Total Leads Scanned: 1,250
• Qualified Leads: 387
• Messages Sent: 156
• Response Rate: 23.4%
• Conversion Rate: 12.1%

Performance Metrics:
• Average Lead Score: 72.5/100
• Top Industries: SaaS, FinTech, Healthcare
• Active Campaigns: 3
• Completed Workflows: 18

AI Insights:
• 5 performance patterns detected
• 3 optimization recommendations available
• Best performing: Tuesday morning outreach
• Improvement opportunity: Follow-up timing"""
        
        data = {
            "metrics": {
                "total_leads_scanned": 1250,
                "qualified_leads": 387,
                "messages_sent": 156,
                "response_rate": 0.234,
                "conversion_rate": 0.121,
                "avg_lead_score": 72.5
            },
            "top_industries": ["SaaS", "FinTech", "Healthcare"],
            "active_campaigns": 3,
            "completed_workflows": 18,
            "patterns_detected": 5,
            "recommendations_available": 3
        }
        
        next_suggestions = [
            "View detailed analytics dashboard",
            "Export performance report",
            "Apply optimization recommendations",
            "Schedule automated reports"
        ]
        
        return SalesResponse(
            response_text=response_text,
            data=data,
            next_suggestions=next_suggestions,
            session_id=intent.session_id
        )
    
    async def _handle_workflow_status_intent(self, intent: SalesIntent) -> SalesResponse:
        """Handle workflow status requests"""
        response_text = """🔄 Workflow Status Overview

Active Workflows:
🟢 Lead Generation Campaign
   Status: Running
   Progress: 65%
   ETA: 3 minutes

🟡 Outreach Sequence
   Status: Queued
   Progress: 0%
   ETA: 10 minutes

📊 Recent Activity:
• 3 workflows completed today
• 2 workflows currently active
• Average execution time: 4.2 minutes"""
        
        data = {
            "active_workflows": 2,
            "completed_today": 3,
            "average_execution_time": 4.2,
            "workflows": [
                {
                    "id": "wf_001",
                    "name": "Lead Generation Campaign",
                    "status": "running",
                    "progress": 65
                },
                {
                    "id": "wf_002", 
                    "name": "Outreach Sequence",
                    "status": "queued",
                    "progress": 0
                }
            ]
        }
        
        next_suggestions = [
            "View detailed workflow logs",
            "Start new workflow",
            "Cancel running workflows",
            "Schedule workflow execution"
        ]
        
        return SalesResponse(
            response_text=response_text,
            data=data,
            next_suggestions=next_suggestions,
            session_id=intent.session_id
        )
    
    async def _handle_sales_help_intent(self, intent: SalesIntent) -> SalesResponse:
        """Handle help requests for sales functionality"""
        response_text = """🤖 Enhanced Jarvis Sales Assistant

I can help you with:

🎯 Lead Generation:
• "Find 50 SaaS CTOs" - Scan for specific prospects
• "Target fintech companies" - Industry-focused search
• "Generate qualified leads" - Comprehensive lead discovery

⚡ Quick Wins:
• "Show me 5 quick wins" - High-impact opportunities
• "Find urgent prospects" - Time-sensitive leads
• "Top priority targets" - Ready-to-close prospects

📧 Outreach Campaigns:
• "Create outreach campaign" - Automated sequences
• "Compose formal messages" - Professional outreach
• "Launch email campaign" - Multi-touch sequences

📊 Business Intelligence:
• "Business summary" - Performance overview
• "Sales analytics" - Detailed metrics
• "Pipeline status" - Current opportunities

🔄 Workflow Management:
• "Workflow status" - Check running processes
• "Active workflows" - Current executions

💡 Examples:
• "Find 20 SaaS CTOs for quick wins"
• "Create formal outreach campaign"
• "Show me business summary"
• "What workflows are running?"

Just ask me naturally - I understand context and can help optimize your sales process!"""
        
        data = {
            "capabilities": [
                "lead_generation",
                "quick_wins", 
                "outreach_campaigns",
                "business_intelligence",
                "workflow_management"
            ],
            "example_queries": [
                "Find SaaS CTOs",
                "Show me quick wins",
                "Create outreach campaign",
                "Business summary",
                "Workflow status"
            ]
        }
        
        return SalesResponse(
            response_text=response_text,
            data=data,
            session_id=intent.session_id
        )
    
    async def _handle_unknown_sales_intent(self, intent: SalesIntent) -> SalesResponse:
        """Handle unknown or unclear sales requests"""
        response_text = f"""🤔 I'm not sure how to help with: "{intent.raw_text}"

Let me suggest some things I can help with:

🎯 Lead Generation:
• "Find leads in [industry]"
• "Target [title] at companies"

⚡ Quick Opportunities:
• "Show me quick wins"
• "Find urgent prospects"

📧 Outreach:
• "Create outreach campaign"
• "Compose messages"

📊 Analytics:
• "Business summary"
• "Sales performance"

🔄 Workflows:
• "Workflow status"
• "Active processes"

Type "help" for more detailed examples, or try rephrasing your request!"""
        
        data = {
            "original_request": intent.raw_text,
            "confidence": intent.confidence,
            "suggestions": [
                "Try asking about lead generation",
                "Request quick wins analysis",
                "Ask for help with commands",
                "Check workflow status"
            ]
        }
        
        return SalesResponse(
            response_text=response_text,
            data=data,
            session_id=intent.session_id
        )
    
    async def _store_sales_intent(self, intent: SalesIntent) -> None:
        """Store sales intent for session tracking"""
        try:
            intent_key = f"sales_intent:{intent.session_id}:{int(datetime.utcnow().timestamp())}"
            
            intent_data = {
                "intent_type": intent.intent_type.value,
                "confidence": intent.confidence,
                "parameters": intent.parameters,
                "raw_text": intent.raw_text,
                "timestamp": intent.timestamp.isoformat(),
                "session_id": intent.session_id
            }
            
            await self.redis_client.setex(intent_key, 3600, json.dumps(intent_data))  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Error storing sales intent: {e}")
    
    async def _publish_progress_update(self, session_id: str, update: Dict[str, Any]) -> None:
        """Publish progress updates for WebSocket clients"""
        try:
            channel = f"progress:{session_id}"
            await self.redis_client.publish(channel, json.dumps(update))
        except Exception as e:
            logger.error(f"Error publishing progress update: {e}")
    
    async def get_sales_session_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get sales session context for continuity"""
        try:
            # Get recent sales intents for this session
            keys = await self.redis_client.keys(f"sales_intent:{session_id}:*")
            intents = []
            
            for key in keys:
                intent_data = await self.redis_client.get(key)
                if intent_data:
                    intents.append(json.loads(intent_data))
            
            return {
                "session_id": session_id,
                "recent_intents": sorted(intents, key=lambda x: x["timestamp"], reverse=True)[:10],
                "intent_count": len(intents)
            }
        except Exception as e:
            logger.error(f"Error getting sales session context: {e}")
            return None
    
    async def close(self) -> None:
        """Clean up Jarvis resources."""
        try:
            # Close existing orchestrator
            if self.agent_orchestrator:
                await self.agent_orchestrator.close()
            
            # Clean up departments
            for dept_id, dept in self.active_departments.items():
                try:
                    dept.state["status"] = DepartmentStatus.INACTIVE
                except Exception as e:
                    logger.error(f"Error deactivating department {dept_id}: {e}")
            
            # Clear session contexts
            self.session_contexts.clear()
            
            logger.info("Jarvis meta-orchestrator closed successfully")
            
        except Exception as e:
            logger.error(f"Error closing Jarvis: {e}")
    
    # Convenience methods for backward compatibility
    async def process_request(self, request: str, session_id: str) -> Dict[str, Any]:
        """Alias for process_business_request for backward compatibility."""
        return await self.process_business_request(request, session_id)
    
    def set_progress_callback(self, callback) -> None:
        """Set progress callback on underlying orchestrator."""
        if self.agent_orchestrator:
            self.agent_orchestrator.set_progress_callback(callback)
    
    async def recover_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover a session using underlying orchestrator."""
        if self.agent_orchestrator:
            return await self.agent_orchestrator.recover_session(session_id)
        return None
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List active sessions using underlying orchestrator."""
        if self.agent_orchestrator:
            return await self.agent_orchestrator.list_active_sessions()
        return []