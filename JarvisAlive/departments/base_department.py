"""Base department architecture for micro-agent coordination.

This module provides the foundational classes for department-level coordination,
allowing multiple micro-agents to work together on complex business workflows.
"""

import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta
from enum import Enum

import redis.asyncio as redis

# Import existing agent infrastructure
from agent_builder.agent_spec import AgentSpec
from agent_builder.sandbox import SandboxManager
from orchestration.agent_communication import AgentMessageBus, MessageType

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Status of department workflows."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class DepartmentHealth(str, Enum):
    """Department health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    OFFLINE = "offline"


class Department(ABC):
    """
    Abstract base class for all department implementations.
    
    Departments coordinate multiple micro-agents to achieve complex business
    objectives. Each department specializes in a specific business function
    (e.g., Sales, Marketing, Operations) and manages its own workflows.
    """
    
    def __init__(
        self, 
        name: str, 
        description: str, 
        redis_client: redis.Redis,
        message_bus: Optional[AgentMessageBus] = None,
        sandbox_manager: Optional[SandboxManager] = None
    ):
        """
        Initialize department with core infrastructure.
        
        Args:
            name: Department name (e.g., "Sales", "Marketing")
            description: Description of department purpose
            redis_client: Redis client for state management
            message_bus: Message bus for agent communication
            sandbox_manager: Sandbox manager for safe agent execution
        """
        self.name = name
        self.description = description
        self.redis_client = redis_client
        self.message_bus = message_bus
        self.sandbox_manager = sandbox_manager
        
        # Department state
        self.micro_agents: List[AgentSpec] = []
        self.shared_state: Dict[str, Any] = {}
        self.business_metrics: List[str] = []  # KPIs this department affects
        self.active_workflows: Dict[str, Dict[str, Any]] = {}
        
        # Redis keys for state management
        self.state_key = f"dept:{name.lower()}:state"
        self.metrics_key = f"dept:{name.lower()}:metrics"
        self.workflows_key = f"dept:{name.lower()}:workflows"
        self.agents_key = f"dept:{name.lower()}:agents"
        
        # Department health tracking
        self.health_status = DepartmentHealth.OFFLINE
        self.last_health_check = None
        self.error_count = 0
        self.max_errors = 5
        
        # Performance metrics
        self.workflows_completed = 0
        self.workflows_failed = 0
        self.average_completion_time = 0.0
        
        logger.info(f"Department {name} initialized")
    
    @abstractmethod
    async def initialize_agents(self) -> bool:
        """
        Create and configure micro-agents for this department.
        
        This method should:
        1. Define the micro-agents needed for department operations
        2. Configure agent specifications and capabilities
        3. Set up agent coordination rules
        4. Initialize agent sandbox environments
        
        Returns:
            bool: True if initialization successful, False otherwise
        """
        pass
    
    @abstractmethod
    async def execute_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a department-specific workflow.
        
        This method should:
        1. Analyze the task requirements
        2. Coordinate appropriate micro-agents
        3. Monitor workflow progress
        4. Handle errors and retries
        5. Return results and metrics
        
        Args:
            task: Task specification with requirements and context
            
        Returns:
            Dict containing workflow results, status, and metrics
        """
        pass
    
    @abstractmethod
    async def get_status(self) -> Dict[str, Any]:
        """
        Get comprehensive department status and health metrics.
        
        Returns:
            Dict containing:
            - health_status: Current health (healthy/degraded/critical/offline)
            - active_agents: Number of active micro-agents
            - running_workflows: Number of active workflows
            - recent_performance: Recent performance metrics
            - resource_usage: Current resource consumption
            - error_summary: Recent errors and issues
        """
        pass
    
    @abstractmethod
    async def calculate_business_impact(self) -> Dict[str, float]:
        """
        Calculate the business impact of this department's operations.
        
        This method should:
        1. Analyze workflow outcomes
        2. Measure KPI improvements
        3. Calculate ROI and efficiency gains
        4. Track goal progress
        
        Returns:
            Dict mapping KPI names to impact values
            Example: {"conversion_rate": 0.15, "cost_savings": 5000.0}
        """
        pass
    
    # Concrete methods for common department operations
    
    async def start(self) -> bool:
        """Start the department and initialize all components."""
        try:
            logger.info(f"Starting department: {self.name}")
            
            # Load existing state
            await self.load_state()
            
            # Initialize agents
            if not await self.initialize_agents():
                logger.error(f"Failed to initialize agents for department {self.name}")
                return False
            
            # Start message bus if available
            if self.message_bus:
                # Subscribe to department-wide topics
                await self.message_bus.subscribe_to_topics(
                    f"dept_{self.name.lower()}", 
                    [f"dept_{self.name.lower()}_broadcast", "global_announcements"]
                )
            
            # Set health status
            self.health_status = DepartmentHealth.HEALTHY
            self.last_health_check = datetime.utcnow()
            
            # Save initial state
            await self.save_state()
            
            logger.info(f"Department {self.name} started successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error starting department {self.name}: {e}")
            self.health_status = DepartmentHealth.CRITICAL
            await self.save_state()
            return False
    
    async def stop(self) -> bool:
        """Stop the department and clean up resources."""
        try:
            logger.info(f"Stopping department: {self.name}")
            
            # Stop all active workflows
            for workflow_id in list(self.active_workflows.keys()):
                await self.stop_workflow(workflow_id)
            
            # Clean up agent resources
            if self.sandbox_manager:
                for agent in self.micro_agents:
                    try:
                        container_id = agent.get("container_id")
                        if container_id:
                            await self.sandbox_manager.cleanup_sandbox(container_id)
                    except Exception as e:
                        logger.error(f"Error cleaning up agent {agent.get('name', 'unknown')}: {e}")
            
            # Update health status
            self.health_status = DepartmentHealth.OFFLINE
            await self.save_state()
            
            logger.info(f"Department {self.name} stopped successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping department {self.name}: {e}")
            return False
    
    async def add_agent(self, agent_spec: AgentSpec) -> bool:
        """Add a micro-agent to the department."""
        try:
            # Validate agent specification
            if not agent_spec.get("name") or not agent_spec.get("capabilities"):
                logger.error("Invalid agent specification")
                return False
            
            # Add to department agents
            self.micro_agents.append(agent_spec)
            
            # Register with message bus if available
            if self.message_bus:
                agent_id = agent_spec["name"]
                await self.message_bus.subscribe_to_topics(
                    agent_id,
                    [f"dept_{self.name.lower()}_broadcast", f"agent_{agent_id}_direct"]
                )
            
            # Save state
            await self.save_state()
            
            logger.info(f"Added agent {agent_spec['name']} to department {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error adding agent to department {self.name}: {e}")
            return False
    
    async def remove_agent(self, agent_name: str) -> bool:
        """Remove a micro-agent from the department."""
        try:
            # Find and remove agent
            for i, agent in enumerate(self.micro_agents):
                if agent.get("name") == agent_name:
                    removed_agent = self.micro_agents.pop(i)
                    
                    # Clean up agent resources
                    if self.sandbox_manager and removed_agent.get("container_id"):
                        await self.sandbox_manager.cleanup_sandbox(removed_agent["container_id"])
                    
                    # Save state
                    await self.save_state()
                    
                    logger.info(f"Removed agent {agent_name} from department {self.name}")
                    return True
            
            logger.warning(f"Agent {agent_name} not found in department {self.name}")
            return False
            
        except Exception as e:
            logger.error(f"Error removing agent {agent_name} from department {self.name}: {e}")
            return False
    
    async def start_workflow(self, workflow_id: str, task: Dict[str, Any]) -> bool:
        """Start a new workflow."""
        try:
            if workflow_id in self.active_workflows:
                logger.warning(f"Workflow {workflow_id} already active in department {self.name}")
                return False
            
            # Create workflow record
            workflow = {
                "id": workflow_id,
                "task": task,
                "status": WorkflowStatus.IN_PROGRESS,
                "started_at": datetime.utcnow().isoformat(),
                "progress": 0.0,
                "assigned_agents": [],
                "results": {},
                "errors": []
            }
            
            self.active_workflows[workflow_id] = workflow
            
            # Execute the workflow
            asyncio.create_task(self._execute_workflow_async(workflow_id, task))
            
            # Save state
            await self.save_state()
            
            logger.info(f"Started workflow {workflow_id} in department {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting workflow {workflow_id} in department {self.name}: {e}")
            return False
    
    async def stop_workflow(self, workflow_id: str) -> bool:
        """Stop an active workflow."""
        try:
            if workflow_id not in self.active_workflows:
                logger.warning(f"Workflow {workflow_id} not found in department {self.name}")
                return False
            
            workflow = self.active_workflows[workflow_id]
            workflow["status"] = WorkflowStatus.PAUSED
            workflow["stopped_at"] = datetime.utcnow().isoformat()
            
            # Save state
            await self.save_state()
            
            logger.info(f"Stopped workflow {workflow_id} in department {self.name}")
            return True
            
        except Exception as e:
            logger.error(f"Error stopping workflow {workflow_id} in department {self.name}: {e}")
            return False
    
    async def _execute_workflow_async(self, workflow_id: str, task: Dict[str, Any]) -> None:
        """Execute workflow asynchronously."""
        try:
            workflow = self.active_workflows.get(workflow_id)
            if not workflow:
                return
            
            # Execute the workflow
            result = await self.execute_workflow(task)
            
            # Update workflow record
            workflow["status"] = WorkflowStatus.COMPLETED if result.get("success") else WorkflowStatus.FAILED
            workflow["completed_at"] = datetime.utcnow().isoformat()
            workflow["results"] = result
            workflow["progress"] = 100.0
            
            # Update performance metrics
            if result.get("success"):
                self.workflows_completed += 1
            else:
                self.workflows_failed += 1
                self.error_count += 1
            
            # Calculate completion time
            if workflow.get("started_at"):
                start_time = datetime.fromisoformat(workflow["started_at"])
                completion_time = (datetime.utcnow() - start_time).total_seconds()
                
                # Update average completion time
                total_workflows = self.workflows_completed + self.workflows_failed
                if total_workflows > 1:
                    self.average_completion_time = (
                        (self.average_completion_time * (total_workflows - 1) + completion_time) / total_workflows
                    )
                else:
                    self.average_completion_time = completion_time
            
            # Check health status
            await self._update_health_status()
            
            # Save state
            await self.save_state()
            
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_id}: {e}")
            if workflow_id in self.active_workflows:
                self.active_workflows[workflow_id]["status"] = WorkflowStatus.FAILED
                self.active_workflows[workflow_id]["errors"].append(str(e))
                self.workflows_failed += 1
                self.error_count += 1
                await self.save_state()
    
    async def _update_health_status(self) -> None:
        """Update department health status based on recent performance."""
        try:
            self.last_health_check = datetime.utcnow()
            
            # Calculate success rate
            total_workflows = self.workflows_completed + self.workflows_failed
            if total_workflows == 0:
                success_rate = 1.0
            else:
                success_rate = self.workflows_completed / total_workflows
            
            # Determine health status
            if self.error_count >= self.max_errors:
                self.health_status = DepartmentHealth.CRITICAL
            elif success_rate < 0.5:
                self.health_status = DepartmentHealth.DEGRADED
            elif success_rate < 0.8:
                self.health_status = DepartmentHealth.DEGRADED
            else:
                self.health_status = DepartmentHealth.HEALTHY
            
            # Reset error count if health is good
            if self.health_status == DepartmentHealth.HEALTHY:
                self.error_count = max(0, self.error_count - 1)
            
        except Exception as e:
            logger.error(f"Error updating health status for department {self.name}: {e}")
            self.health_status = DepartmentHealth.CRITICAL
    
    # State management methods
    
    async def save_state(self) -> bool:
        """Save department state to Redis."""
        try:
            # Prepare state data
            state_data = {
                "name": self.name,
                "description": self.description,
                "shared_state": self.shared_state,
                "business_metrics": self.business_metrics,
                "health_status": self.health_status.value,
                "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
                "error_count": self.error_count,
                "workflows_completed": self.workflows_completed,
                "workflows_failed": self.workflows_failed,
                "average_completion_time": self.average_completion_time,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            # Save main state
            await self.redis_client.setex(
                self.state_key,
                86400,  # 24 hours TTL
                json.dumps(state_data)
            )
            
            # Save workflows separately
            workflows_data = {
                "active_workflows": self.active_workflows,
                "updated_at": datetime.utcnow().isoformat()
            }
            await self.redis_client.setex(
                self.workflows_key,
                86400,
                json.dumps(workflows_data)
            )
            
            # Save agents separately
            agents_data = {
                "micro_agents": self.micro_agents,
                "updated_at": datetime.utcnow().isoformat()
            }
            await self.redis_client.setex(
                self.agents_key,
                86400,
                json.dumps(agents_data)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving state for department {self.name}: {e}")
            return False
    
    async def load_state(self) -> bool:
        """Load department state from Redis."""
        try:
            # Load main state
            state_data = await self.redis_client.get(self.state_key)
            if state_data:
                state = json.loads(state_data)
                self.shared_state = state.get("shared_state", {})
                self.business_metrics = state.get("business_metrics", [])
                self.health_status = DepartmentHealth(state.get("health_status", "offline"))
                self.error_count = state.get("error_count", 0)
                self.workflows_completed = state.get("workflows_completed", 0)
                self.workflows_failed = state.get("workflows_failed", 0)
                self.average_completion_time = state.get("average_completion_time", 0.0)
                
                if state.get("last_health_check"):
                    self.last_health_check = datetime.fromisoformat(state["last_health_check"])
            
            # Load workflows
            workflows_data = await self.redis_client.get(self.workflows_key)
            if workflows_data:
                workflows = json.loads(workflows_data)
                self.active_workflows = workflows.get("active_workflows", {})
            
            # Load agents
            agents_data = await self.redis_client.get(self.agents_key)
            if agents_data:
                agents = json.loads(agents_data)
                self.micro_agents = agents.get("micro_agents", [])
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading state for department {self.name}: {e}")
            return False


class DepartmentOrchestrator:
    """
    Orchestrator for coordinating micro-agents within a department.
    
    Similar to the main orchestrator but specialized for department-level
    coordination and workflow management.
    """
    
    def __init__(
        self, 
        department: Department,
        message_bus: Optional[AgentMessageBus] = None,
        sandbox_manager: Optional[SandboxManager] = None
    ):
        """
        Initialize department orchestrator.
        
        Args:
            department: Department to orchestrate
            message_bus: Message bus for agent communication
            sandbox_manager: Sandbox manager for safe execution
        """
        self.department = department
        self.message_bus = message_bus or department.message_bus
        self.sandbox_manager = sandbox_manager or department.sandbox_manager
        
        # Coordination state
        self.active_coordinations: Dict[str, Dict[str, Any]] = {}
        self.coordination_history: List[Dict[str, Any]] = []
        
        logger.info(f"DepartmentOrchestrator initialized for {department.name}")
    
    async def coordinate_agents(self, workflow_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Coordinate micro-agents for a specific workflow.
        
        Args:
            workflow_name: Name of the workflow to execute
            context: Workflow context and parameters
            
        Returns:
            Dict containing coordination results and metrics
        """
        try:
            coordination_id = f"{workflow_name}_{int(datetime.utcnow().timestamp())}"
            
            logger.info(f"Starting agent coordination: {coordination_id}")
            
            # Create coordination record
            coordination = {
                "id": coordination_id,
                "workflow_name": workflow_name,
                "context": context,
                "started_at": datetime.utcnow().isoformat(),
                "participating_agents": [],
                "status": "in_progress",
                "results": {},
                "messages_sent": 0
            }
            
            self.active_coordinations[coordination_id] = coordination
            
            # Analyze context to determine required agents
            required_agents = await self._analyze_agent_requirements(workflow_name, context)
            coordination["participating_agents"] = [agent["name"] for agent in required_agents]
            
            # Coordinate agents based on workflow type
            if workflow_name == "parallel_execution":
                results = await self._coordinate_parallel_execution(required_agents, context)
            elif workflow_name == "sequential_execution":
                results = await self._coordinate_sequential_execution(required_agents, context)
            elif workflow_name == "collaborative_execution":
                results = await self._coordinate_collaborative_execution(required_agents, context)
            else:
                # Default to collaborative execution
                results = await self._coordinate_collaborative_execution(required_agents, context)
            
            # Update coordination record
            coordination["status"] = "completed" if results.get("success") else "failed"
            coordination["completed_at"] = datetime.utcnow().isoformat()
            coordination["results"] = results
            
            # Add to history
            self.coordination_history.append(coordination.copy())
            
            # Clean up active coordination
            del self.active_coordinations[coordination_id]
            
            logger.info(f"Agent coordination completed: {coordination_id}")
            return results
            
        except Exception as e:
            logger.error(f"Error coordinating agents for workflow {workflow_name}: {e}")
            return {
                "success": False,
                "error": str(e),
                "coordination_id": coordination_id if 'coordination_id' in locals() else None
            }
    
    async def broadcast_to_agents(self, message: Dict[str, Any]) -> List[str]:
        """
        Broadcast a message to all agents in the department.
        
        Args:
            message: Message to broadcast
            
        Returns:
            List of message IDs for each agent
        """
        try:
            if not self.message_bus:
                logger.error("Message bus not available for broadcasting")
                return []
            
            message_ids = []
            
            # Add department context to message
            enhanced_message = {
                **message,
                "department": self.department.name,
                "broadcast_time": datetime.utcnow().isoformat(),
                "message_type": "department_broadcast"
            }
            
            # Send to each agent
            for agent in self.department.micro_agents:
                try:
                    agent_id = agent.get("name")
                    if agent_id:
                        message_id = await self.message_bus.publish_message(
                            f"dept_{self.department.name.lower()}",
                            agent_id,
                            "CoordinationMessage",
                            enhanced_message
                        )
                        message_ids.append(message_id)
                        
                except Exception as e:
                    logger.error(f"Error sending message to agent {agent.get('name', 'unknown')}: {e}")
            
            # Also use department broadcast channel
            dept_message_ids = await self.message_bus.broadcast_to_department(
                self.department.name.lower(),
                enhanced_message,
                f"dept_{self.department.name.lower()}"
            )
            message_ids.extend(dept_message_ids)
            
            logger.info(f"Broadcast message sent to {len(message_ids)} recipients in department {self.department.name}")
            return message_ids
            
        except Exception as e:
            logger.error(f"Error broadcasting message in department {self.department.name}: {e}")
            return []
    
    async def _analyze_agent_requirements(
        self, 
        workflow_name: str, 
        context: Dict[str, Any]
    ) -> List[AgentSpec]:
        """Analyze workflow requirements and select appropriate agents."""
        try:
            required_agents = []
            
            # Extract required capabilities from context
            required_capabilities = context.get("required_capabilities", [])
            task_complexity = context.get("complexity", "moderate")
            
            # Select agents based on capabilities and availability
            for agent in self.department.micro_agents:
                agent_capabilities = agent.get("capabilities", [])
                
                # Check if agent has required capabilities
                if any(cap in agent_capabilities for cap in required_capabilities):
                    required_agents.append(agent)
                    
                # For complex tasks, include more agents
                elif task_complexity == "complex" and len(required_agents) < 3:
                    required_agents.append(agent)
            
            # Ensure we have at least one agent
            if not required_agents and self.department.micro_agents:
                required_agents = [self.department.micro_agents[0]]
            
            logger.info(f"Selected {len(required_agents)} agents for workflow {workflow_name}")
            return required_agents
            
        except Exception as e:
            logger.error(f"Error analyzing agent requirements: {e}")
            return self.department.micro_agents[:1]  # Fallback to first agent
    
    async def _coordinate_parallel_execution(
        self, 
        agents: List[AgentSpec], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate parallel execution among agents."""
        try:
            tasks = []
            results = {}
            
            # Divide work among agents
            work_items = context.get("work_items", [context])
            agents_count = len(agents)
            
            for i, agent in enumerate(agents):
                # Assign work items to each agent
                agent_work = work_items[i::agents_count]  # Round-robin assignment
                
                if agent_work:
                    task_context = {
                        "agent_id": agent["name"],
                        "work_items": agent_work,
                        "execution_mode": "parallel"
                    }
                    tasks.append(self._execute_agent_task(agent, task_context))
            
            # Execute all tasks in parallel
            if tasks:
                agent_results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Compile results
                for i, result in enumerate(agent_results):
                    agent_name = agents[i]["name"]
                    if isinstance(result, Exception):
                        results[agent_name] = {"success": False, "error": str(result)}
                    else:
                        results[agent_name] = result
            
            # Determine overall success
            success = all(r.get("success", False) for r in results.values())
            
            return {
                "success": success,
                "execution_mode": "parallel",
                "agent_results": results,
                "agents_used": len(agents)
            }
            
        except Exception as e:
            logger.error(f"Error in parallel execution coordination: {e}")
            return {"success": False, "error": str(e)}
    
    async def _coordinate_sequential_execution(
        self, 
        agents: List[AgentSpec], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate sequential execution among agents."""
        try:
            results = {}
            workflow_context = context.copy()
            
            # Execute agents sequentially, passing results forward
            for i, agent in enumerate(agents):
                task_context = {
                    "agent_id": agent["name"],
                    "step_number": i + 1,
                    "previous_results": results,
                    "workflow_context": workflow_context,
                    "execution_mode": "sequential"
                }
                
                # Execute agent task
                agent_result = await self._execute_agent_task(agent, task_context)
                results[agent["name"]] = agent_result
                
                # Stop if agent failed and it's a critical step
                if not agent_result.get("success") and task_context.get("critical", True):
                    break
                
                # Update workflow context with results
                workflow_context.update(agent_result.get("output", {}))
            
            # Determine overall success
            success = all(r.get("success", False) for r in results.values())
            
            return {
                "success": success,
                "execution_mode": "sequential",
                "agent_results": results,
                "final_context": workflow_context
            }
            
        except Exception as e:
            logger.error(f"Error in sequential execution coordination: {e}")
            return {"success": False, "error": str(e)}
    
    async def _coordinate_collaborative_execution(
        self, 
        agents: List[AgentSpec], 
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Coordinate collaborative execution with agent communication."""
        try:
            results = {}
            collaboration_context = context.copy()
            
            # Start collaborative session
            session_id = f"collab_{int(datetime.utcnow().timestamp())}"
            
            # Notify all agents about collaboration
            if self.message_bus:
                collaboration_message = {
                    "session_id": session_id,
                    "participants": [agent["name"] for agent in agents],
                    "context": collaboration_context,
                    "coordination_type": "collaborative"
                }
                
                await self.broadcast_to_agents(collaboration_message)
            
            # Execute agents with communication enabled
            tasks = []
            for agent in agents:
                task_context = {
                    "agent_id": agent["name"],
                    "session_id": session_id,
                    "collaboration_context": collaboration_context,
                    "execution_mode": "collaborative",
                    "other_agents": [a["name"] for a in agents if a["name"] != agent["name"]]
                }
                tasks.append(self._execute_agent_task(agent, task_context))
            
            # Execute with timeout for collaboration
            timeout = context.get("collaboration_timeout", 300)  # 5 minutes default
            
            try:
                agent_results = await asyncio.wait_for(
                    asyncio.gather(*tasks, return_exceptions=True),
                    timeout=timeout
                )
                
                # Compile results
                for i, result in enumerate(agent_results):
                    agent_name = agents[i]["name"]
                    if isinstance(result, Exception):
                        results[agent_name] = {"success": False, "error": str(result)}
                    else:
                        results[agent_name] = result
                        
            except asyncio.TimeoutError:
                logger.warning(f"Collaborative execution timed out after {timeout} seconds")
                return {"success": False, "error": "Collaboration timeout"}
            
            # Aggregate collaborative results
            combined_output = {}
            for result in results.values():
                if result.get("success") and result.get("output"):
                    combined_output.update(result["output"])
            
            success = any(r.get("success", False) for r in results.values())
            
            return {
                "success": success,
                "execution_mode": "collaborative",
                "agent_results": results,
                "combined_output": combined_output,
                "session_id": session_id
            }
            
        except Exception as e:
            logger.error(f"Error in collaborative execution coordination: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_agent_task(self, agent: AgentSpec, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a task for a specific agent."""
        try:
            # Simulate agent execution (in a real implementation, this would
            # interact with the sandbox manager and execute the agent code)
            
            agent_name = agent["name"]
            logger.info(f"Executing task for agent {agent_name}")
            
            # Simulate processing time
            await asyncio.sleep(0.1)
            
            # Mock successful execution
            return {
                "success": True,
                "agent_id": agent_name,
                "execution_time": 0.1,
                "output": {
                    "processed": True,
                    "result": f"Task completed by {agent_name}",
                    "context_received": bool(context)
                }
            }
            
        except Exception as e:
            logger.error(f"Error executing task for agent {agent.get('name', 'unknown')}: {e}")
            return {
                "success": False,
                "agent_id": agent.get("name", "unknown"),
                "error": str(e)
            }
    
    def get_coordination_status(self) -> Dict[str, Any]:
        """Get current coordination status."""
        return {
            "active_coordinations": len(self.active_coordinations),
            "coordination_history_count": len(self.coordination_history),
            "department": self.department.name,
            "active_agents": len(self.department.micro_agents),
            "recent_coordinations": self.coordination_history[-5:] if self.coordination_history else []
        }