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


class IntentType(str, Enum):
    """Types of user intents."""
    CREATE_AGENT = "CREATE_AGENT"
    MODIFY_AGENT = "MODIFY_AGENT"
    DELETE_AGENT = "DELETE_AGENT"
    LIST_AGENTS = "LIST_AGENTS"
    EXECUTE_TASK = "EXECUTE_TASK"
    CLARIFICATION_NEEDED = "CLARIFICATION_NEEDED"


# Keep the old TypedDict for backward compatibility, but use Pydantic model in practice
class AgentSpec(TypedDict):
    """Legacy specification for an agent (use PydanticAgentSpec for new code)."""
    name: str
    description: str
    capabilities: List[str]
    integrations: List[str]
    code: Optional[str]
    config: Dict[str, Any]


class ParsedIntent(TypedDict):
    """Parsed user intent."""
    intent_type: IntentType
    parameters: Dict[str, Any]
    confidence: float
    alternate_intents: Optional[List[Dict[str, Any]]]
    clarification_needed: Optional[Dict[str, Any]]


class OrchestratorState(TypedDict):
    """State for the orchestration workflow."""
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