"""
Workflow Intelligence System - Core Orchestration
Provides intelligent workflow orchestration, parallel execution, and adaptive optimization
"""
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
from enum import Enum
import uuid
import asyncio
import logging
import json
from collections import defaultdict, deque
import time


class WorkflowStepType(str, Enum):
    SCAN_LEADS = "scan_leads"
    ENRICH_LEADS = "enrich_leads"
    COMPOSE_OUTREACH = "compose_outreach"
    SEND_EMAIL = "send_email"
    TRACK_RESPONSE = "track_response"
    FOLLOW_UP = "follow_up"
    SCHEDULE_MEETING = "schedule_meeting"
    UPDATE_CRM = "update_crm"
    GENERATE_REPORT = "generate_report"
    CUSTOM = "custom"


class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowStep(BaseModel):
    step_id: str
    name: str
    step_type: WorkflowStepType
    agent_class: Optional[str] = None
    function_name: Optional[str] = None
    parameters: Dict[str, Any] = {}
    dependencies: List[str] = []  # step_ids this step depends on
    timeout_seconds: int = 300
    retry_count: int = 3
    retry_delay: int = 5
    condition: Optional[str] = None  # Python expression to evaluate
    parallel_group: Optional[str] = None  # Steps in same group can run in parallel
    priority: WorkflowPriority = WorkflowPriority.MEDIUM
    estimated_duration: int = 60  # seconds
    cost_estimate: float = 0.0  # USD
    
    @validator('step_id')
    def validate_step_id(cls, v):
        if not v:
            return f"step_{uuid.uuid4().hex[:8]}"
        return v


class WorkflowStepResult(BaseModel):
    step_id: str
    status: WorkflowStepStatus
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    result_data: Dict[str, Any] = {}
    error_message: Optional[str] = None
    retry_attempts: int = 0
    performance_metrics: Dict[str, Any] = {}
    cost_actual: float = 0.0


class WorkflowTemplate(BaseModel):
    template_id: str
    name: str
    description: str
    version: str = "1.0"
    category: str  # "lead_generation", "outreach", "follow_up", "meeting", "reporting"
    steps: List[WorkflowStep]
    default_parameters: Dict[str, Any] = {}
    tags: List[str] = []
    estimated_total_duration: int = 0  # Auto-calculated
    estimated_total_cost: float = 0.0  # Auto-calculated
    success_rate: float = 0.95  # Historical success rate
    last_optimized: Optional[datetime] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self._calculate_estimates()
    
    def _calculate_estimates(self):
        """Calculate total duration and cost estimates"""
        # Find critical path for duration (accounting for parallelization)
        dependency_graph = self._build_dependency_graph()
        self.estimated_total_duration = self._calculate_critical_path(dependency_graph)
        self.estimated_total_cost = sum(step.cost_estimate for step in self.steps)
    
    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """Build dependency graph for steps"""
        graph = defaultdict(list)
        for step in self.steps:
            graph[step.step_id] = step.dependencies
        return dict(graph)
    
    def _calculate_critical_path(self, dependency_graph: Dict[str, List[str]]) -> int:
        """Calculate critical path duration considering parallelization"""
        step_map = {step.step_id: step for step in self.steps}
        
        def calculate_path_duration(step_id: str, memo: Dict[str, int] = None) -> int:
            if memo is None:
                memo = {}
            
            if step_id in memo:
                return memo[step_id]
            
            step = step_map[step_id]
            dependencies = dependency_graph.get(step_id, [])
            
            if not dependencies:
                duration = step.estimated_duration
            else:
                # Max duration of dependencies (they can run in parallel)
                max_dep_duration = max(calculate_path_duration(dep_id, memo) for dep_id in dependencies)
                duration = max_dep_duration + step.estimated_duration
            
            memo[step_id] = duration
            return duration
        
        # Calculate for all steps and return maximum
        return max(calculate_path_duration(step.step_id) for step in self.steps)


class WorkflowExecution(BaseModel):
    execution_id: str
    template_id: str
    template_name: str
    status: WorkflowStepStatus
    parameters: Dict[str, Any] = {}
    step_results: Dict[str, WorkflowStepResult] = {}
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_duration: Optional[float] = None
    total_cost: float = 0.0
    context_data: Dict[str, Any] = {}  # Shared data between steps
    priority: WorkflowPriority = WorkflowPriority.MEDIUM
    created_by: str = "system"
    tags: List[str] = []
    
    @validator('execution_id')
    def validate_execution_id(cls, v):
        if not v:
            return f"exec_{uuid.uuid4().hex[:8]}"
        return v


class WorkflowMetrics(BaseModel):
    total_executions: int = 0
    successful_executions: int = 0
    failed_executions: int = 0
    average_duration: float = 0.0
    average_cost: float = 0.0
    bottleneck_steps: List[str] = []
    optimization_suggestions: List[str] = []
    last_calculated: datetime = datetime.now()


class WorkflowOrchestrator:
    """Core workflow orchestration and execution engine"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Template and execution storage
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.executions: Dict[str, WorkflowExecution] = {}
        self.active_executions: Dict[str, asyncio.Task] = {}
        
        # Performance tracking
        self.metrics: Dict[str, WorkflowMetrics] = {}
        self.step_performance: Dict[str, List[float]] = defaultdict(list)
        
        # Agent registry
        self.agent_registry: Dict[str, Any] = {}
        
        # Load default templates
        self._load_default_templates()
    
    def register_agent(self, agent_class_name: str, agent_instance: Any):
        """Register an agent for workflow steps"""
        self.agent_registry[agent_class_name] = agent_instance
        self.logger.info(f"Registered agent: {agent_class_name}")
    
    def create_template(self, template: WorkflowTemplate) -> str:
        """Create a new workflow template"""
        self.templates[template.template_id] = template
        self.metrics[template.template_id] = WorkflowMetrics()
        self.logger.info(f"Created workflow template: {template.name}")
        return template.template_id
    
    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """Get a workflow template by ID"""
        return self.templates.get(template_id)
    
    def list_templates(self, category: Optional[str] = None) -> List[WorkflowTemplate]:
        """List all templates, optionally filtered by category"""
        templates = list(self.templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates
    
    async def execute_workflow(self, template_id: str, parameters: Dict[str, Any] = None,
                              priority: WorkflowPriority = WorkflowPriority.MEDIUM) -> str:
        """Start workflow execution"""
        template = self.templates.get(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        execution = WorkflowExecution(
            execution_id=execution_id,
            template_id=template_id,
            template_name=template.name,
            status=WorkflowStepStatus.PENDING,
            parameters=parameters or {},
            priority=priority,
            start_time=datetime.now()
        )
        
        self.executions[execution_id] = execution
        
        # Start execution task
        task = asyncio.create_task(self._execute_workflow_internal(execution_id))
        self.active_executions[execution_id] = task
        
        self.logger.info(f"Started workflow execution: {execution_id}")
        return execution_id
    
    async def _execute_workflow_internal(self, execution_id: str):
        """Internal workflow execution logic"""
        execution = self.executions[execution_id]
        template = self.templates[execution.template_id]
        
        try:
            execution.status = WorkflowStepStatus.RUNNING
            
            # Build execution graph
            dependency_graph = self._build_execution_graph(template.steps)
            
            # Execute steps in dependency order with parallelization
            completed_steps = set()
            
            while len(completed_steps) < len(template.steps):
                # Find ready steps (dependencies completed)
                ready_steps = []
                for step in template.steps:
                    if (step.step_id not in completed_steps and
                        all(dep in completed_steps for dep in step.dependencies)):
                        ready_steps.append(step)
                
                if not ready_steps:
                    break  # No more steps can be executed
                
                # Group steps by parallel_group for concurrent execution
                parallel_groups = defaultdict(list)
                for step in ready_steps:
                    group_key = step.parallel_group or step.step_id
                    parallel_groups[group_key].append(step)
                
                # Execute parallel groups
                tasks = []
                for group_steps in parallel_groups.values():
                    if len(group_steps) == 1:
                        task = self._execute_step(execution_id, group_steps[0])
                        tasks.append(task)
                    else:
                        # Execute steps in parallel group concurrently
                        for step in group_steps:
                            task = self._execute_step(execution_id, step)
                            tasks.append(task)
                
                # Wait for all parallel groups to complete
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for i, result in enumerate(results):
                    if isinstance(result, Exception):
                        self.logger.error(f"Parallel group failed: {result}")
                        execution.status = WorkflowStepStatus.FAILED
                        return
                    else:
                        completed_steps.update(result)
            
            # Mark execution as completed
            execution.status = WorkflowStepStatus.COMPLETED
            execution.end_time = datetime.now()
            execution.total_duration = (execution.end_time - execution.start_time).total_seconds()
            
            # Update metrics
            self._update_execution_metrics(execution_id)
            
        except Exception as e:
            self.logger.error(f"Workflow execution failed: {e}")
            execution.status = WorkflowStepStatus.FAILED
            execution.end_time = datetime.now()
            
        finally:
            # Clean up active execution
            if execution_id in self.active_executions:
                del self.active_executions[execution_id]
    
    async def _execute_step(self, execution_id: str, step: WorkflowStep) -> set:
        """Execute a single workflow step"""
        execution = self.executions[execution_id]
        
        # Check condition if specified
        if step.condition:
            condition_met = self._evaluate_condition(step.condition, execution.context_data)
            self.logger.debug(f"Step {step.step_id} condition '{step.condition}' evaluated to {condition_met}")
            
            if not condition_met:
                result = WorkflowStepResult(
                    step_id=step.step_id,
                    status=WorkflowStepStatus.SKIPPED,
                    start_time=datetime.now(),
                    end_time=datetime.now()
                )
                execution.step_results[step.step_id] = result
                self.logger.info(f"Step {step.step_id} skipped due to condition")
                return {step.step_id}
        
        result = WorkflowStepResult(
            step_id=step.step_id,
            status=WorkflowStepStatus.RUNNING,
            start_time=datetime.now()
        )
        execution.step_results[step.step_id] = result
        
        # Execute with retries
        for attempt in range(step.retry_count + 1):
            try:
                result.retry_attempts = attempt
                
                # Execute the step
                step_result = await self._call_step_function(step, execution)
                
                # Update context with results
                if isinstance(step_result, dict):
                    execution.context_data.update(step_result)
                    result.result_data = step_result
                
                result.status = WorkflowStepStatus.COMPLETED
                result.end_time = datetime.now()
                result.duration_seconds = (result.end_time - result.start_time).total_seconds()
                
                break
                
            except Exception as e:
                self.logger.error(f"Step {step.step_id} failed (attempt {attempt + 1}): {e}")
                
                if attempt == step.retry_count:
                    result.status = WorkflowStepStatus.FAILED
                    result.error_message = str(e)
                    result.end_time = datetime.now()
                    break
                else:
                    await asyncio.sleep(step.retry_delay)
        
        return {step.step_id}
    
    async def _execute_parallel_steps(self, execution_id: str, steps: List[WorkflowStep]) -> set:
        """Execute multiple steps in parallel"""
        tasks = [self._execute_step(execution_id, step) for step in steps]
        results = await asyncio.gather(*tasks)
        
        completed = set()
        for result_set in results:
            completed.update(result_set)
        
        return completed
    
    async def _call_step_function(self, step: WorkflowStep, execution: WorkflowExecution) -> Any:
        """Call the actual function for a workflow step"""
        # Get agent instance
        if step.agent_class and step.agent_class in self.agent_registry:
            agent = self.agent_registry[step.agent_class]
            
            if step.function_name and hasattr(agent, step.function_name):
                func = getattr(agent, step.function_name)
                
                # Prepare parameters - resolve template variables
                params = {}
                for key, value in step.parameters.items():
                    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
                        # Template variable like {{scan_limit}}
                        var_name = value[2:-2].strip()
                        params[key] = execution.parameters.get(var_name, value)
                    else:
                        params[key] = value
                
                # Add execution parameters
                params.update(execution.parameters)
                params['context'] = execution.context_data
                
                # Call function
                if asyncio.iscoroutinefunction(func):
                    return await func(**params)
                else:
                    return func(**params)
        
        # Handle built-in step types
        return await self._handle_builtin_step(step, execution)
    
    async def _handle_builtin_step(self, step: WorkflowStep, execution: WorkflowExecution) -> Dict[str, Any]:
        """Handle built-in workflow steps"""
        if step.step_type == WorkflowStepType.CUSTOM:
            # Custom step - just return parameters
            return step.parameters
        
        # Simulate step execution for demo
        await asyncio.sleep(0.1)
        return {
            "step_type": step.step_type.value,
            "executed_at": datetime.now().isoformat(),
            "parameters": step.parameters
        }
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Evaluate a condition expression safely"""
        try:
            # Simple and safe evaluation of conditions
            # In production, use a proper expression evaluator
            
            # Handle common condition patterns
            if ">" in condition:
                # Handle "context.get('score', 0) > 80" type conditions
                parts = condition.split(">")
                if len(parts) == 2:
                    left_expr = parts[0].strip()
                    right_value = float(parts[1].strip())
                    
                    # Extract value from context
                    if "context.get(" in left_expr:
                        # Extract key from context.get('key', default)
                        start = left_expr.find("'") + 1
                        end = left_expr.find("'", start)
                        key = left_expr[start:end]
                        
                        # Get default value
                        default_start = left_expr.find(",") + 1
                        default_end = left_expr.find(")")
                        default_val = float(left_expr[default_start:default_end].strip())
                        
                        actual_value = context.get(key, default_val)
                        return float(actual_value) > right_value
            
            elif "<=" in condition:
                # Handle "<=" conditions
                parts = condition.split("<=")
                if len(parts) == 2:
                    left_expr = parts[0].strip()
                    right_value = float(parts[1].strip())
                    
                    if "context.get(" in left_expr:
                        start = left_expr.find("'") + 1
                        end = left_expr.find("'", start)
                        key = left_expr[start:end]
                        
                        default_start = left_expr.find(",") + 1
                        default_end = left_expr.find(")")
                        default_val = float(left_expr[default_start:default_end].strip())
                        
                        actual_value = context.get(key, default_val)
                        return float(actual_value) <= right_value
            
            # Fallback to eval for other expressions
            return eval(condition, {"__builtins__": {}}, context)
        except Exception as e:
            self.logger.debug(f"Condition evaluation failed: {condition} - {e}")
            return True  # Default to true if evaluation fails
    
    def _build_execution_graph(self, steps: List[WorkflowStep]) -> Dict[str, List[str]]:
        """Build dependency graph for execution planning"""
        graph = {}
        for step in steps:
            graph[step.step_id] = step.dependencies
        return graph
    
    def _update_execution_metrics(self, execution_id: str):
        """Update performance metrics after execution"""
        execution = self.executions[execution_id]
        template_metrics = self.metrics[execution.template_id]
        
        template_metrics.total_executions += 1
        
        if execution.status == WorkflowStepStatus.COMPLETED:
            template_metrics.successful_executions += 1
        else:
            template_metrics.failed_executions += 1
        
        if execution.total_duration:
            # Update average duration
            total_duration_sum = (template_metrics.average_duration * 
                                (template_metrics.total_executions - 1) + 
                                execution.total_duration)
            template_metrics.average_duration = total_duration_sum / template_metrics.total_executions
        
        # Update step performance tracking
        for step_id, result in execution.step_results.items():
            if result.duration_seconds:
                self.step_performance[step_id].append(result.duration_seconds)
                # Keep only last 100 measurements
                if len(self.step_performance[step_id]) > 100:
                    self.step_performance[step_id] = self.step_performance[step_id][-100:]
        
        template_metrics.last_calculated = datetime.now()
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get current execution status"""
        execution = self.executions.get(execution_id)
        if not execution:
            return None
        
        return {
            "execution_id": execution_id,
            "status": execution.status,
            "progress": self._calculate_progress(execution),
            "start_time": execution.start_time,
            "duration": self._calculate_current_duration(execution),
            "step_results": {k: v.dict() for k, v in execution.step_results.items()}
        }
    
    def _calculate_progress(self, execution: WorkflowExecution) -> float:
        """Calculate execution progress percentage"""
        template = self.templates[execution.template_id]
        total_steps = len(template.steps)
        completed_steps = sum(1 for result in execution.step_results.values() 
                            if result.status in [WorkflowStepStatus.COMPLETED, WorkflowStepStatus.SKIPPED])
        return (completed_steps / total_steps) * 100 if total_steps > 0 else 0
    
    def _calculate_current_duration(self, execution: WorkflowExecution) -> Optional[float]:
        """Calculate current execution duration"""
        if execution.start_time:
            end_time = execution.end_time or datetime.now()
            return (end_time - execution.start_time).total_seconds()
        return None
    
    def analyze_performance(self, template_id: str) -> Dict[str, Any]:
        """Analyze workflow performance and identify bottlenecks"""
        template = self.templates.get(template_id)
        metrics = self.metrics.get(template_id)
        
        if not template or not metrics:
            return {"error": "Template or metrics not found"}
        
        # Identify bottleneck steps
        step_avg_durations = {}
        for step in template.steps:
            durations = self.step_performance.get(step.step_id, [])
            if durations:
                step_avg_durations[step.step_id] = sum(durations) / len(durations)
        
        # Sort by duration to find bottlenecks
        bottlenecks = sorted(step_avg_durations.items(), key=lambda x: x[1], reverse=True)[:3]
        metrics.bottleneck_steps = [step_id for step_id, _ in bottlenecks]
        
        # Generate optimization suggestions
        suggestions = []
        for step_id, avg_duration in bottlenecks:
            step = next(s for s in template.steps if s.step_id == step_id)
            if avg_duration > step.estimated_duration * 1.5:
                suggestions.append(f"Step '{step.name}' taking longer than expected - consider optimization")
        
        if metrics.failed_executions > metrics.successful_executions * 0.1:
            suggestions.append("High failure rate - review error handling and retry logic")
        
        metrics.optimization_suggestions = suggestions
        
        return {
            "template_id": template_id,
            "metrics": metrics.dict(),
            "bottlenecks": bottlenecks,
            "suggestions": suggestions,
            "step_performance": step_avg_durations
        }
    
    def _load_default_templates(self):
        """Load default workflow templates"""
        
        # Lead Generation Workflow
        lead_gen_template = WorkflowTemplate(
            template_id="lead_generation_basic",
            name="Basic Lead Generation",
            description="Scan for leads, enrich data, and prepare for outreach",
            category="lead_generation",
            steps=[
                WorkflowStep(
                    step_id="scan_leads",
                    name="Scan for Leads",
                    step_type=WorkflowStepType.SCAN_LEADS,
                    agent_class="LeadScannerAgent",
                    function_name="scan_leads",
                    parameters={"limit": 50},
                    estimated_duration=120,
                    cost_estimate=0.10
                ),
                WorkflowStep(
                    step_id="enrich_high_value",
                    name="Enrich High-Value Leads",
                    step_type=WorkflowStepType.ENRICH_LEADS,
                    agent_class="LeadScannerAgent", 
                    function_name="enrich_leads",
                    dependencies=["scan_leads"],
                    condition="len(context.get('leads', [])) > 0",
                    estimated_duration=180,
                    cost_estimate=0.50
                )
            ]
        )
        
        # Outreach Campaign Workflow
        outreach_template = WorkflowTemplate(
            template_id="outreach_campaign_ai",
            name="AI-Powered Outreach Campaign",
            description="Generate personalized outreach messages and send emails",
            category="outreach",
            steps=[
                WorkflowStep(
                    step_id="compose_messages",
                    name="Compose Personalized Messages",
                    step_type=WorkflowStepType.COMPOSE_OUTREACH,
                    agent_class="OutreachComposerAgent",
                    function_name="compose_outreach",
                    parameters={"mode": "ai"},
                    parallel_group="compose",
                    estimated_duration=60,
                    cost_estimate=0.25
                ),
                WorkflowStep(
                    step_id="send_emails",
                    name="Send Outreach Emails",
                    step_type=WorkflowStepType.SEND_EMAIL,
                    dependencies=["compose_messages"],
                    estimated_duration=30,
                    cost_estimate=0.05
                ),
                WorkflowStep(
                    step_id="schedule_followup",
                    name="Schedule Follow-up",
                    step_type=WorkflowStepType.FOLLOW_UP,
                    dependencies=["send_emails"],
                    parameters={"delay_days": 3},
                    estimated_duration=15,
                    cost_estimate=0.01
                )
            ]
        )
        
        # Meeting Pipeline Workflow
        meeting_template = WorkflowTemplate(
            template_id="meeting_pipeline",
            name="Meeting Pipeline Management",
            description="Track responses and schedule meetings",
            category="meeting",
            steps=[
                WorkflowStep(
                    step_id="track_responses",
                    name="Track Email Responses",
                    step_type=WorkflowStepType.TRACK_RESPONSE,
                    estimated_duration=45,
                    cost_estimate=0.02
                ),
                WorkflowStep(
                    step_id="schedule_meetings",
                    name="Schedule Meetings",
                    step_type=WorkflowStepType.SCHEDULE_MEETING,
                    dependencies=["track_responses"],
                    condition="context.get('responses', 0) > 0",
                    estimated_duration=90,
                    cost_estimate=0.10
                ),
                WorkflowStep(
                    step_id="update_crm",
                    name="Update CRM Records",
                    step_type=WorkflowStepType.UPDATE_CRM,
                    dependencies=["schedule_meetings"],
                    parallel_group="update",
                    estimated_duration=30,
                    cost_estimate=0.03
                )
            ]
        )
        
        # Store templates
        self.create_template(lead_gen_template)
        self.create_template(outreach_template)
        self.create_template(meeting_template)