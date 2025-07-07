"""State definitions for the HeyJarvis orchestration system."""

from typing import Dict, Any, List, Optional, TypedDict
from enum import Enum

# Import the new Pydantic model
from agent_builder.agent_spec import AgentSpec as PydanticAgentSpec


class DeploymentStatus(str, Enum):
    """Status of agent deployment."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class DepartmentStatus(str, Enum):
    """Status of department operations."""
    INACTIVE = "inactive"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    COORDINATING = "coordinating"
    PAUSED = "paused"
    ERROR = "error"


class IntentType(str, Enum):
    """Types of user intents."""
    CREATE_AGENT = "CREATE_AGENT"
    MODIFY_AGENT = "MODIFY_AGENT"
    DELETE_AGENT = "DELETE_AGENT"
    LIST_AGENTS = "LIST_AGENTS"
    EXECUTE_TASK = "EXECUTE_TASK"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"
    # Department-level intents
    CREATE_DEPARTMENT = "CREATE_DEPARTMENT"
    MODIFY_DEPARTMENT = "MODIFY_DEPARTMENT"
    DELETE_DEPARTMENT = "DELETE_DEPARTMENT"
    LIST_DEPARTMENTS = "LIST_DEPARTMENTS"


# Keep the old TypedDict for backward compatibility, but use Pydantic model in practice
class AgentSpec(TypedDict):
    """Legacy specification for an agent (use PydanticAgentSpec for new code)."""
    name: str
    description: str
    capabilities: List[str]
    integrations: List[str]
    code: Optional[str]
    config: Dict[str, Any]


class CoordinationRule(TypedDict):
    """Rule for coordinating agents within a department."""
    rule_id: str
    name: str
    description: str
    trigger_condition: str  # Condition that triggers this rule
    actions: List[Dict[str, Any]]  # Actions to take when triggered
    priority: int  # Rule priority (higher = more important)
    enabled: bool


class DepartmentSpec(TypedDict):
    """Specification for a department containing multiple agents."""
    name: str
    description: str
    micro_agents: List[AgentSpec]  # List of agents in this department
    coordination_rules: List[CoordinationRule]  # Rules for agent coordination
    department_id: Optional[str]  # Unique identifier
    created_at: Optional[str]  # Creation timestamp
    updated_at: Optional[str]  # Last update timestamp
    config: Dict[str, Any]  # Additional configuration


class DepartmentState(TypedDict):
    """Runtime state of a department."""
    department_id: str
    active_agents: List[str]  # IDs of currently active agents
    shared_memory: Dict[str, Any]  # Shared data between agents
    status: DepartmentStatus
    last_coordination: Optional[str]  # Timestamp of last coordination event
    coordination_history: List[Dict[str, Any]]  # History of coordination events
    resource_usage: Dict[str, Any]  # Resource usage metrics
    error_log: List[Dict[str, Any]]  # Error history


class ParsedIntent(TypedDict):
    """Parsed user intent."""
    intent_type: IntentType
    parameters: Dict[str, Any]
    confidence: float
    alternate_intents: Optional[List[Dict[str, Any]]]
    clarification_needed: Optional[Dict[str, Any]]


class OrchestratorState(TypedDict):
    """State for the orchestration workflow."""
    # Existing fields (maintained for backward compatibility)
    user_request: str
    session_id: str
    parsed_intent: Optional[ParsedIntent]
    existing_agents: List[AgentSpec]
    agent_spec: Optional[AgentSpec]
    deployment_status: DeploymentStatus
    error_message: Optional[str]
    execution_context: Dict[str, Any]
    retry_count: int
    needs_clarification: Optional[bool]
    clarification_questions: Optional[List[str]]
    missing_info: Optional[List[str]]
    suggestions: Optional[List[str]]
    # New department-level fields
    active_departments: List[DepartmentSpec]
    department_coordination: Dict[str, Any]  # Cross-department coordination state
    current_department: Optional[str]  # Currently active department ID
    department_states: Dict[str, DepartmentState]  # Runtime states by department ID