"""LangGraph orchestrator for HeyJarvis AI agent automation system."""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime

import redis.asyncio as redis
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from .state import (
    OrchestratorState, 
    DeploymentStatus, 
    IntentType, 
    AgentSpec, 
    ParsedIntent,
    PydanticAgentSpec
)
from agent_builder.agent_spec import (
    create_monitor_agent, 
    create_sync_agent, 
    create_report_agent,
    TimeTrigger,
    ManualTrigger,
    IntegrationConfig
)
from agent_builder.code_generator import generate_agent_code
from agent_builder.sandbox import SandboxManager, SandboxConfig
from conversation.context_manager import ConversationContextManager
from templates.template_engine import TemplateEngine, TemplateValidationError
from templates.parameter_extractor import ParameterExtractor

logger = logging.getLogger(__name__)


class OrchestratorConfig(BaseModel):
    """Configuration for the orchestrator."""
    redis_url: str = Field(default="redis://localhost:6379")
    anthropic_api_key: str = Field(...)
    max_retries: int = Field(default=3)
    session_timeout: int = Field(default=3600)


class HeyJarvisOrchestrator:
    """Main orchestrator for the HeyJarvis system using LangGraph."""
    
    def __init__(self, config: OrchestratorConfig):
        self.config = config
        self.redis_client = None
        self.llm = ChatAnthropic(
            api_key=config.anthropic_api_key,
            model="claude-3-5-sonnet-20241022",
            temperature=0.1
        )
        self.graph = None
        self.checkpointer = None
        self.progress_callback: Optional[Callable[[str, int, str], None]] = None
        self.context_manager: Optional[ConversationContextManager] = None
        self.sandbox_manager: Optional[SandboxManager] = None
        
        # Initialize template system
        self.template_engine = TemplateEngine()
        self.parameter_extractor = ParameterExtractor()
        
        # Node progress mapping
        self.node_progress = {
            "parse_request": (20, "🔍 Understanding your request..."),
            "understand_intent": (40, "🤔 Analyzing intent..."),
            "check_existing_agents": (60, "🔎 Checking existing agents..."),
            "create_agent": (80, "🛠️ Creating your agent..."),
            "deploy_agent": (100, "🚀 Deploying agent...")
        }
        
    def set_progress_callback(self, callback: Callable[[str, int, str], None]) -> None:
        """Set callback for progress updates."""
        self.progress_callback = callback
        
    async def initialize(self) -> None:
        """Initialize Redis connection, sandbox manager, and build the graph."""
        self.redis_client = redis.from_url(self.config.redis_url)
        self.checkpointer = MemorySaver()
        
        # Initialize sandbox manager
        sandbox_config = SandboxConfig()
        self.sandbox_manager = SandboxManager(sandbox_config)
        await self.sandbox_manager.initialize()
        
        self._build_graph()
    
    def initialize_context_manager(self, session_id: str) -> None:
        """Initialize or get existing context manager for a session."""
        if not self.context_manager or self.context_manager.session_id != session_id:
            self.context_manager = ConversationContextManager(
                max_tokens=4096,
                session_id=session_id
            )
            # Try to load existing conversation state from Redis
            asyncio.create_task(self._load_conversation_context(session_id))
        
    def _build_graph(self) -> None:
        """Build the LangGraph workflow."""
        workflow = StateGraph(OrchestratorState)
        
        # Add nodes
        workflow.add_node("parse_request", self._parse_request)
        workflow.add_node("understand_intent", self._understand_intent)
        workflow.add_node("check_existing_agents", self._check_existing_agents)
        workflow.add_node("create_agent", self._create_agent)
        workflow.add_node("deploy_agent", self._deploy_agent)
        
        # Add edges
        workflow.add_edge(START, "parse_request")
        workflow.add_edge("parse_request", "understand_intent")
        workflow.add_edge("understand_intent", "check_existing_agents")
        
        # Conditional routing
        workflow.add_conditional_edges(
            "check_existing_agents",
            self._should_create_or_modify,
            {
                "create": "create_agent",
                "modify": "create_agent",  # Same node handles both
                "end": END
            }
        )
        
        workflow.add_edge("create_agent", "deploy_agent")
        workflow.add_edge("deploy_agent", END)
        
        self.graph = workflow.compile(checkpointer=self.checkpointer)
        
    async def _parse_request(self, state: OrchestratorState) -> Dict[str, Any]:
        """Parse and clean the user request."""
        session_id = state["session_id"]
        
        # Save checkpoint before processing
        await self.save_checkpoint(session_id, "parse_request", state)
        
        # Send progress update
        if self.progress_callback:
            progress, message = self.node_progress["parse_request"]
            self.progress_callback("parse_request", progress, message)
        
        try:
            user_request = state["user_request"].strip()
            if not user_request:
                raise ValueError("I couldn't understand that. Could you rephrase?")
                
            # Basic request validation and preprocessing
            cleaned_request = self._clean_text(user_request)
            
            result = {
                "user_request": cleaned_request,
                "error_message": None
            }
            
            # Save checkpoint after processing
            await self.save_checkpoint(session_id, "parse_request_complete", {**state, **result})
            
            return result
            
        except Exception as e:
            logger.error(f"Error parsing request: {e}")
            retry_count = state.get("retry_count", 0)
            
            if retry_count < self.config.max_retries:
                error_msg = "I couldn't understand that. Could you rephrase?"
            else:
                error_msg = f"Failed to parse request after {self.config.max_retries} attempts: {str(e)}"
            
            result = {
                "error_message": error_msg,
                "deployment_status": DeploymentStatus.FAILED,
                "retry_count": retry_count + 1
            }
            
            # Save error state
            await self.save_checkpoint(session_id, "parse_request_error", {**state, **result})
            
            return result
    
    async def _understand_intent(self, state: OrchestratorState) -> Dict[str, Any]:
        """Use LLM to understand user intent with enhanced parameter extraction."""
        session_id = state["session_id"]
        
        # Save checkpoint before processing
        await self.save_checkpoint(session_id, "understand_intent", state)
        
        # Send progress update
        if self.progress_callback:
            progress, message = self.node_progress["understand_intent"]
            self.progress_callback("understand_intent", progress, message)
        
        try:
            # Get conversation context if available
            context_info = ""
            if hasattr(self, 'context_manager') and self.context_manager:
                context = self.context_manager.get_context_for_intent_parsing()
                if context["recent_messages"]:
                    context_info = f"\n\nConversation context:\nRecent messages: {'; '.join(context['recent_messages'][-2:])}"
                if context["key_decisions"]:
                    context_info += f"\nPrevious decisions: {json.dumps(context['key_decisions'], indent=2)}"
            
            system_prompt = """
            You are an advanced AI intent classifier for an agent orchestration system.
            
            IMPORTANT: Make reasonable assumptions and avoid asking for clarification unless the request is truly ambiguous. 
            Use smart defaults when possible.
            
            Analyze the user request and extract detailed information:
            
            INTENT TYPES:
            - CREATE_AGENT: User wants to create a new automation agent
            - MODIFY_AGENT: User wants to modify an existing agent  
            - DELETE_AGENT: User wants to delete an agent
            - LIST_AGENTS: User wants to see existing agents
            - EXECUTE_TASK: User wants to run a specific task
            - CLARIFICATION_NEEDED: Only when request is truly incomprehensible
            
            SMART DEFAULTS:
            - frequency: If not specified, assume "real-time" for monitoring, "daily" for reports
            - notification_preferences: If mentioned "notify" but no method, assume "email"  
            - platforms: If email mentioned, assume "gmail" unless specified
            - conditions: Be specific based on context (e.g., "urgent emails" = subject contains urgent/important)
            
            PARAMETER EXTRACTION:
            Extract these parameters when present:
            - primary_action: main action (monitor, create, send, backup, etc.)
            - targets: what to act on (email, files, social_media, etc.)
            - conditions: specific conditions or triggers
            - frequency: how often (real-time, hourly, daily, weekly)
            - notification_preferences: how to notify (email, slack, sms)
            - platforms: specific platforms (gmail, twitter, instagram, etc.)
            - compound_request: true if multiple agents needed
            - integration_requirements: external services needed
            
            CONFIDENCE RULES:
            - High confidence (0.8-1.0): Clear, specific requests with smart defaults applied
            - Medium confidence (0.6-0.7): Somewhat clear, can proceed with assumptions
            - Low confidence (0.0-0.5): Truly vague or incomprehensible
            
            Return a JSON object with:
            {
                "intent_type": "one of the above types",
                "parameters": {
                    "primary_action": "extracted action",
                    "targets": ["list", "of", "targets"],
                    "conditions": {
                        "target1": ["condition1", "condition2"],
                        "target2": ["condition3"]
                    },
                    "frequency": "extracted frequency",
                    "notification_preferences": ["list", "of", "preferences"],
                    "platforms": ["specific", "platforms"],
                    "compound_request": false,
                    "integration_requirements": ["required", "services"],
                    "complexity_level": "simple|moderate|complex",
                    "estimated_setup_time": "quick|moderate|extended"
                },
                "confidence": 0.85,
                "alternate_intents": [
                    {
                        "intent_type": "alternate possibility",
                        "confidence": 0.3,
                        "reasoning": "why this might be an alternative"
                    }
                ],
                "clarification_needed": {
                    "questions": ["What specific emails?", "How often?"],
                    "missing_info": ["frequency", "conditions"],
                    "suggestions": ["monitor urgent emails", "daily backup"]
                }
            }
            
            VALIDATION:
            - Check if the request is technically feasible
            - Identify missing critical information
            - Flag impossible requests clearly
            """
            
            user_context = f"User request: {state['user_request']}{context_info}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_context)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Clean and parse response more robustly
            content = response.content.strip()
            
            # Remove markdown code blocks
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            
            content = content.strip()
            
            # Extract JSON object more robustly
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx + 1]
            else:
                json_content = content
            
            intent_data = json.loads(json_content)
            
            # Enhanced parsed intent structure
            parsed_intent: ParsedIntent = {
                "intent_type": IntentType(intent_data["intent_type"]),
                "parameters": intent_data.get("parameters", {}),
                "confidence": intent_data.get("confidence", 0.0),
                "alternate_intents": intent_data.get("alternate_intents", []),
                "clarification_needed": intent_data.get("clarification_needed", {})
            }
            
            # Determine if clarification is needed - be more lenient
            needs_clarification = (
                parsed_intent["confidence"] < 0.5 or
                intent_data["intent_type"] == "CLARIFICATION_NEEDED"
            )
            
            result = {
                "parsed_intent": parsed_intent,
                "needs_clarification": needs_clarification,
                "error_message": None
            }
            
            # Add clarification questions to result if needed
            if needs_clarification:
                clarification_info = parsed_intent.get("clarification_needed", {})
                result["clarification_questions"] = clarification_info.get("questions", [])
                result["missing_info"] = clarification_info.get("missing_info", [])
                result["suggestions"] = clarification_info.get("suggestions", [])
            
            # Store context if available
            if hasattr(self, 'context_manager') and self.context_manager:
                self.context_manager.add_assistant_message(
                    f"Analyzed intent: {intent_data['intent_type']} (confidence: {parsed_intent['confidence']})",
                    metadata={
                        "type": "intent_analysis",
                        "intent": intent_data["intent_type"],
                        "confidence": parsed_intent["confidence"],
                        "needs_clarification": needs_clarification
                    }
                )
            
            # Save checkpoint after processing
            await self.save_checkpoint(session_id, "understand_intent_complete", {**state, **result})
            
            return result
            
        except Exception as e:
            logger.error(f"Error understanding intent: {e}")
            retry_count = state.get("retry_count", 0)
            
            if retry_count < self.config.max_retries:
                error_msg = "I had trouble understanding your request. Could you be more specific?"
            else:
                error_msg = f"Failed to understand intent after {self.config.max_retries} attempts: {str(e)}"
            
            result = {
                "error_message": error_msg,
                "deployment_status": DeploymentStatus.FAILED,
                "retry_count": retry_count + 1,
                "needs_clarification": True,
                "clarification_questions": ["Could you rephrase your request with more details?"]
            }
            
            # Save error state
            await self.save_checkpoint(session_id, "understand_intent_error", {**state, **result})
            
            return result
    
    async def _check_existing_agents(self, state: OrchestratorState) -> Dict[str, Any]:
        """Check for existing agents that match the request."""
        session_id = state["session_id"]
        
        # Save checkpoint before processing
        await self.save_checkpoint(session_id, "check_existing_agents", state)
        
        # Send progress update
        if self.progress_callback:
            progress, message = self.node_progress["check_existing_agents"]
            self.progress_callback("check_existing_agents", progress, message)
        
        try:
            agents_key = f"agents:{session_id}"
            
            # Retrieve existing agents from Redis
            agents_data = await self.redis_client.get(agents_key)
            existing_agents = []
            
            if agents_data:
                agents_list = json.loads(agents_data)
                existing_agents = [AgentSpec(**agent) for agent in agents_list]
            
            result = {
                "existing_agents": existing_agents,
                "error_message": None
            }
            
            # Save checkpoint after processing
            await self.save_checkpoint(session_id, "check_existing_agents_complete", {**state, **result})
            
            return result
            
        except Exception as e:
            logger.error(f"Error checking existing agents: {e}")
            retry_count = state.get("retry_count", 0)
            
            result = {
                "error_message": f"Failed to check existing agents: {str(e)}",
                "deployment_status": DeploymentStatus.FAILED,
                "retry_count": retry_count + 1,
                "existing_agents": []
            }
            
            # Save error state
            await self.save_checkpoint(session_id, "check_existing_agents_error", {**state, **result})
            
            return result
    
    async def _request_clarification(self, state: OrchestratorState) -> Dict[str, Any]:
        """Generate and handle clarification questions for ambiguous requests."""
        session_id = state["session_id"]
        
        # Save checkpoint before processing
        await self.save_checkpoint(session_id, "request_clarification", state)
        
        try:
            parsed_intent = state.get("parsed_intent", {})
            clarification_info = parsed_intent.get("clarification_needed", {})
            
            # Generate contextual clarification questions
            questions = clarification_info.get("questions", [])
            missing_info = clarification_info.get("missing_info", [])
            suggestions = clarification_info.get("suggestions", [])
            
            # If no specific questions were generated, create generic ones
            if not questions:
                questions = self._generate_default_clarification_questions(state)
            
            # Store clarification request in context
            if hasattr(self, 'context_manager') and self.context_manager:
                self.context_manager.add_system_message(
                    f"Requested clarification for: {state['user_request']}",
                    metadata={
                        "type": "clarification_request",
                        "questions": questions,
                        "missing_info": missing_info,
                        "suggestions": suggestions
                    }
                )
            
            result = {
                "needs_clarification": True,
                "clarification_questions": questions,
                "missing_info": missing_info,
                "suggestions": suggestions,
                "error_message": None,
                "deployment_status": DeploymentStatus.PENDING
            }
            
            # Save checkpoint after processing
            await self.save_checkpoint(session_id, "request_clarification_complete", {**state, **result})
            
            return result
            
        except Exception as e:
            logger.error(f"Error requesting clarification: {e}")
            
            result = {
                "error_message": f"Failed to generate clarification questions: {str(e)}",
                "deployment_status": DeploymentStatus.FAILED,
                "needs_clarification": True,
                "clarification_questions": ["Could you provide more details about what you'd like to automate?"]
            }
            
            # Save error state
            await self.save_checkpoint(session_id, "request_clarification_error", {**state, **result})
            
            return result
    
    def _generate_default_clarification_questions(self, state: OrchestratorState) -> List[str]:
        """Generate default clarification questions when specific ones aren't available."""
        user_request = state.get("user_request", "").lower()
        questions = []
        
        # Analyze the request to generate relevant questions
        if "monitor" in user_request:
            questions.extend([
                "What specifically would you like to monitor?",
                "How often should the monitoring happen?",
                "How would you like to be notified?"
            ])
        elif "backup" in user_request:
            questions.extend([
                "Which files or folders should be backed up?",
                "Where should the backups be stored?",
                "How frequently should backups occur?"
            ])
        elif "social media" in user_request:
            questions.extend([
                "Which social media platforms?",
                "What type of content or activity?",
                "What actions should be taken?"
            ])
        elif "email" in user_request:
            questions.extend([
                "Which email account or service?",
                "What types of emails are you interested in?",
                "What should happen when conditions are met?"
            ])
        else:
            # Generic questions for unclear requests
            questions.extend([
                "What specific task would you like to automate?",
                "What triggers should start this automation?",
                "What outcome are you looking for?"
            ])
        
        return questions[:3]  # Limit to 3 questions to avoid overwhelming
    
    async def _process_clarification_response(self, state: OrchestratorState, responses: Dict[str, str]) -> Dict[str, Any]:
        """Process user's responses to clarification questions."""
        session_id = state["session_id"]
        
        try:
            # Store clarification responses in context
            if hasattr(self, 'context_manager') and self.context_manager:
                for question, answer in responses.items():
                    self.context_manager.add_user_message(
                        answer,
                        metadata={
                            "type": "clarification",
                            "question": question,
                            "answer": answer
                        },
                        priority=3  # High priority for clarifications
                    )
            
            # Combine original request with clarifications
            clarifications_text = " ".join([f"{q}: {a}" for q, a in responses.items()])
            enhanced_request = f"{state['user_request']}. Additional details: {clarifications_text}"
            
            # Update state with enhanced request and reset workflow
            updated_state = state.copy()
            updated_state["user_request"] = enhanced_request
            updated_state["needs_clarification"] = False
            updated_state["parsed_intent"] = None  # Reset to re-parse with new context
            updated_state["deployment_status"] = DeploymentStatus.PENDING
            
            # Run the complete workflow with enhanced request
            config = {"configurable": {"thread_id": session_id}}
            
            async for step in self.graph.astream(updated_state, config=config):
                logger.info(f"Clarification workflow step: {step}")
            
            # Get final state
            final_state = await self.graph.aget_state(config)
            return final_state.values
            
        except Exception as e:
            logger.error(f"Error processing clarification response: {e}")
            
            return {
                "error_message": f"Failed to process clarification: {str(e)}",
                "deployment_status": DeploymentStatus.FAILED
            }
    
    def _should_create_or_modify(self, state: OrchestratorState) -> str:
        """Conditional routing logic."""
        if state.get("error_message"):
            return "end"
            
        parsed_intent = state.get("parsed_intent")
        if not parsed_intent:
            return "end"
            
        intent_type = parsed_intent["intent_type"]
        
        if intent_type in [IntentType.CREATE_AGENT, IntentType.MODIFY_AGENT]:
            return "create" if intent_type == IntentType.CREATE_AGENT else "modify"
        
        return "end"
    
    async def _try_template_creation(self, user_request: str, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Try to create an agent using templates first.
        
        Returns:
            Dict with agent spec and generated code if successful, None if fallback needed
        """
        try:
            # Extract parameters from user request
            extraction_result = self.parameter_extractor.extract_parameters(user_request)
            
            logger.info(f"Template extraction: {extraction_result.template_match}, "
                       f"confidence: {extraction_result.confidence:.3f}")
            
            # Check if confidence is high enough
            if extraction_result.confidence < 0.7:
                logger.info(f"Template confidence too low ({extraction_result.confidence:.3f}), "
                           f"falling back to LLM generation")
                return None
            
            # Check if we have all required parameters
            if extraction_result.missing_required:
                logger.info(f"Missing required parameters: {extraction_result.missing_required}, "
                           f"falling back to LLM generation")
                return None
            
            template_name = extraction_result.template_match
            parameters = extraction_result.extracted_parameters
            
            # Add agent name if not provided
            if "agent_name" not in parameters:
                template_info = self.template_engine.get_template_info(template_name)
                parameters["agent_name"] = template_info.description.split(" - ")[0] if template_info else "Template Agent"
            
            # Render the template
            try:
                generated_code = self.template_engine.render_template(
                    template_name, 
                    parameters, 
                    validate=True
                )
                
                logger.info(f"Successfully generated {len(generated_code)} characters from template {template_name}")
                
                # Create agent spec from template
                template_info = self.template_engine.get_template_info(template_name)
                agent_spec = {
                    "name": parameters["agent_name"],
                    "description": template_info.description,
                    "capabilities": template_info.capabilities,
                    "integrations": template_info.integrations,
                    "code": generated_code,
                    "template_used": template_name,
                    "template_parameters": parameters,
                    "config": {
                        "created_from_template": True,
                        "template_name": template_name,
                        "template_confidence": extraction_result.confidence
                    }
                }
                
                return {
                    "agent_spec": agent_spec,
                    "deployment_status": DeploymentStatus.PENDING,
                    "generated_code": generated_code,
                    "template_name": template_name,
                    "template_confidence": extraction_result.confidence
                }
                
            except TemplateValidationError as e:
                logger.error(f"Template validation failed: {e}, falling back to LLM generation")
                return None
            
        except Exception as e:
            logger.error(f"Template creation failed: {e}, falling back to LLM generation")
            return None
    
    async def _create_agent(self, state: OrchestratorState) -> Dict[str, Any]:
        """Create or modify an agent specification."""
        session_id = state["session_id"]
        
        # Save checkpoint before processing
        await self.save_checkpoint(session_id, "create_agent", state)
        
        # Send progress update
        if self.progress_callback:
            progress, message = self.node_progress["create_agent"]
            self.progress_callback("create_agent", progress, message)
        
        try:
            parsed_intent = state["parsed_intent"]
            is_modification = parsed_intent["intent_type"] == IntentType.MODIFY_AGENT
            
            # Try template-based creation first (only for new agents)
            if not is_modification:
                user_request = state.get("user_request", "")
                template_result = await self._try_template_creation(user_request, session_id)
                
                if template_result:
                    logger.info(f"Successfully created agent using template: {template_result.get('template_name')}")
                    
                    # Save checkpoint with template result
                    await self.save_checkpoint(session_id, "create_agent_complete", {**state, **template_result})
                    
                    return template_result
                
                logger.info("Template creation not suitable, falling back to LLM generation")
            
            action_text = "Modify the existing agent" if is_modification else "Create a new agent"
            system_prompt = ("You are an advanced AI agent builder. " + action_text + 
                           " based on the user request using sophisticated agent specifications.\n\n"
                           "Analyze the request and determine:\n"
                           "1. Agent type: monitor, sync, report, or custom\n"
                           "2. Primary action: what the agent does\n"
                           "3. Targets: what it acts on (email, files, social media, etc.)\n"
                           "4. Frequency: how often it runs\n"
                           "5. Integrations needed: which services to connect\n"
                           "6. Capabilities required: from the allowed list\n\n"
                           "ALLOWED CAPABILITIES:\n"
                           "email_monitoring, email_sending, calendar_management, file_backup, file_sync, "
                           "file_monitoring, social_media_posting, social_media_monitoring, web_scraping, "
                           "api_integration, data_processing, report_generation, alert_sending, "
                           "workflow_automation, database_operations, cloud_storage, notification_management, "
                           "task_scheduling, content_creation, data_analysis\n\n"
                           "COMMON PATTERNS:\n"
                           "- Monitor agents: use \"monitor\" pattern with targets and frequency\n"
                           "- Sync agents: use \"sync\" pattern with source and destination\n"
                           "- Report agents: use \"report\" pattern with data source and schedule\n\n"
                           "Return a VALID JSON object with:\n"
                           "- pattern: \"monitor\", \"sync\", \"report\", or \"custom\"\n"
                           "- name: agent name (2-50 chars, alphanumeric + spaces)\n"
                           "- description: what the agent does (10-500 chars)\n"
                           "- capabilities: list from allowed capabilities (at least 1)\n"
                           "- primary_action: main action (monitor, backup, send, etc.)\n"
                           "- targets: array of what to act on\n"
                           "- frequency_minutes: how often to run (for monitor/sync)\n"
                           "- schedule: cron expression (for reports)\n"
                           "- integrations: object with service configs\n"
                           "- trigger_type: \"time\", \"event\", or \"manual\"\n"
                           "- estimated_complexity: \"simple\", \"moderate\", or \"complex\"\n\n"
                           "Example for \"monitor my email\":\n"
                           "{\n"
                           "    \"pattern\": \"monitor\",\n"
                           "    \"name\": \"Email Monitor Agent\",\n"
                           "    \"description\": \"Monitors Gmail inbox for new messages and important emails\",\n"
                           "    \"capabilities\": [\"email_monitoring\", \"alert_sending\"],\n"
                           "    \"primary_action\": \"monitor\",\n"
                           "    \"targets\": [\"email\", \"gmail\"],\n"
                           "    \"frequency_minutes\": 5,\n"
                           "    \"integrations\": {\n"
                           "        \"gmail\": {\n"
                           "            \"service_name\": \"gmail\",\n"
                           "            \"auth_type\": \"oauth2\",\n"
                           "            \"scopes\": [\"gmail.readonly\"]\n"
                           "        }\n"
                           "    },\n"
                           "    \"trigger_type\": \"time\",\n"
                           "    \"estimated_complexity\": \"simple\"\n"
                           "}")
            
            context = f"User request: {state['user_request']}"
            if is_modification and state.get("existing_agents"):
                existing_agents_json = json.dumps([agent for agent in state['existing_agents']], indent=2)
                context += f"\nExisting agents: {existing_agents_json}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=context)
            ]
            
            response = await self.llm.ainvoke(messages)
            
            # Clean response content to handle potential formatting issues
            content = response.content.strip()
            
            # Remove markdown code blocks
            if content.startswith('```json'):
                content = content[7:]
            elif content.startswith('```'):
                content = content[3:]
            if content.endswith('```'):
                content = content[:-3]
            
            # Extract JSON object more robustly
            content = content.strip()
            
            # Find the first { and last } to extract just the JSON
            start_idx = content.find('{')
            end_idx = content.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                json_content = content[start_idx:end_idx + 1]
            else:
                json_content = content
            
            agent_data = json.loads(json_content)
            
            # Create Pydantic agent spec using factory methods or custom creation
            pattern = agent_data.get("pattern", "custom")
            session_id = state["session_id"]
            
            try:
                if pattern == "monitor":
                    # Use monitor agent factory
                    target = agent_data.get("targets", ["unknown"])[0]
                    frequency = agent_data.get("frequency_minutes", 5)
                    pydantic_agent_spec = create_monitor_agent(
                        target=target,
                        frequency=frequency,
                        created_by=session_id,
                        name=agent_data["name"]
                    )
                    
                elif pattern == "sync":
                    # Use sync agent factory  
                    targets = agent_data.get("targets", [])
                    source = targets[0] if len(targets) > 0 else "unknown"
                    destination = targets[1] if len(targets) > 1 else "unknown"
                    schedule = agent_data.get("schedule", "0 2 * * *")
                    
                    pydantic_agent_spec = create_sync_agent(
                        source=source,
                        destination=destination,
                        created_by=session_id,
                        schedule=schedule,
                        name=agent_data["name"]
                    )
                    
                elif pattern == "report":
                    # Use report agent factory
                    targets = agent_data.get("targets", [])
                    data_source = targets[0] if targets else "unknown"
                    schedule = agent_data.get("schedule", "0 9 * * 1")  # Weekly Monday 9 AM
                    
                    pydantic_agent_spec = create_report_agent(
                        data_source=data_source,
                        schedule=schedule,
                        created_by=session_id,
                        name=agent_data["name"]
                    )
                    
                else:
                    # Custom agent creation
                    from agent_builder.agent_spec import AgentSpec as PydanticAgentSpecClass
                    
                    # Build integrations
                    integrations = {}
                    for service_name, config in agent_data.get("integrations", {}).items():
                        integrations[service_name] = IntegrationConfig(**config)
                    
                    # Build triggers based on type
                    triggers = []
                    trigger_type = agent_data.get("trigger_type", "manual")
                    
                    if trigger_type == "time":
                        frequency = agent_data.get("frequency_minutes")
                        schedule = agent_data.get("schedule")
                        
                        if frequency:
                            triggers.append(TimeTrigger(interval_minutes=frequency))
                        elif schedule:
                            triggers.append(TimeTrigger(cron_expression=schedule))
                        else:
                            triggers.append(TimeTrigger(interval_minutes=60))  # Default hourly
                    else:
                        triggers.append(ManualTrigger(description="Manually triggered agent"))
                    
                    pydantic_agent_spec = PydanticAgentSpecClass(
                        name=agent_data["name"],
                        description=agent_data["description"],
                        capabilities=agent_data.get("capabilities", []),
                        triggers=triggers,
                        integrations=integrations,
                        created_by=session_id
                    )
                
                # Validate the agent spec
                pydantic_agent_spec.validate_capabilities()
                pydantic_agent_spec.validate_integrations()
                
                # Convert to legacy format for compatibility
                agent_spec: AgentSpec = {
                    "name": pydantic_agent_spec.name,
                    "description": pydantic_agent_spec.description,
                    "capabilities": pydantic_agent_spec.capabilities,
                    "integrations": list(pydantic_agent_spec.integrations.keys()),
                    "code": None,
                    "config": {
                        "id": pydantic_agent_spec.id,
                        "version": pydantic_agent_spec.version,
                        "status": pydantic_agent_spec.status,
                        "resource_limits": pydantic_agent_spec.resource_limits.model_dump(),
                        "triggers": [trigger.model_dump() for trigger in pydantic_agent_spec.triggers],
                        "integrations": {k: v.model_dump() for k, v in pydantic_agent_spec.integrations.items()},
                        "pydantic_spec": pydantic_agent_spec.to_json()  # Store full spec
                    }
                }
                
            except Exception as validation_error:
                logger.error(f"Agent validation failed: {validation_error}")
                # Fallback to simple agent creation
                agent_spec: AgentSpec = {
                    "name": agent_data["name"],
                    "description": agent_data["description"],
                    "capabilities": agent_data.get("capabilities", []),
                    "integrations": [integration for integration in agent_data.get("integrations", {}).keys()],
                    "code": None,
                    "config": agent_data.get("config", {})
                }
            
            result = {
                "agent_spec": agent_spec,
                "deployment_status": DeploymentStatus.PENDING,
                "error_message": None
            }
            
            # Save checkpoint after processing
            await self.save_checkpoint(session_id, "create_agent_complete", {**state, **result})
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating agent: {e}")
            retry_count = state.get("retry_count", 0)
            
            if retry_count < self.config.max_retries:
                error_msg = "There was an issue creating your agent. Would you like to try again?"
            else:
                error_msg = f"Failed to create agent after {self.config.max_retries} attempts: {str(e)}"
            
            result = {
                "error_message": error_msg,
                "deployment_status": DeploymentStatus.FAILED,
                "retry_count": retry_count + 1
            }
            
            # Save error state
            await self.save_checkpoint(session_id, "create_agent_error", {**state, **result})
            
            return result
    
    async def _deploy_agent(self, state: OrchestratorState) -> Dict[str, Any]:
        """Deploy the agent (placeholder for actual deployment logic)."""
        session_id = state["session_id"]
        
        # Save checkpoint before processing
        await self.save_checkpoint(session_id, "deploy_agent", state)
        
        # Send progress update
        if self.progress_callback:
            progress, message = self.node_progress["deploy_agent"]
            self.progress_callback("deploy_agent", progress, message)
        
        try:
            agent_spec = state["agent_spec"]
            
            if not agent_spec:
                raise ValueError("No agent specification to deploy")
            
            # Save agent to Redis
            agents_key = f"agents:{session_id}"
            existing_agents = state.get("existing_agents", [])
            
            # Generate executable code for the agent first
            if agent_spec.get("config", {}).get("pydantic_spec"):
                try:
                    # Get the full Pydantic spec from config
                    from agent_builder.agent_spec import AgentSpec as PydanticAgentSpecClass
                    pydantic_spec_json = agent_spec["config"]["pydantic_spec"]
                    pydantic_spec = PydanticAgentSpecClass.from_json(pydantic_spec_json)
                    
                    # Generate the Python code
                    generated_code = await generate_agent_code(pydantic_spec, self.config.anthropic_api_key)
                    
                    # Store the generated code
                    agent_spec["code"] = generated_code
                    
                    logger.info(f"Generated {len(generated_code)} characters of code for {agent_spec['name']}")
                    
                    # Create and execute agent in sandbox
                    if self.sandbox_manager:
                        try:
                            logger.info(f"Creating sandbox for {agent_spec['name']}")
                            
                            # Prepare secrets from integrations
                            secrets = {}
                            for integration_name, integration_config in pydantic_spec.integrations.items():
                                # In production, get actual OAuth tokens from secure storage
                                # For now, use placeholder
                                secrets[f"{integration_name}_token"] = f"placeholder_token_for_{integration_name}"
                            
                            # Create sandbox
                            container_id = await self.sandbox_manager.create_sandbox(
                                agent_id=agent_spec["name"].replace(" ", "_").lower(),
                                agent_code=generated_code,
                                agent_spec=pydantic_spec,
                                secrets=secrets
                            )
                            
                            # Execute agent in sandbox
                            logger.info(f"Executing agent in sandbox: {container_id}")
                            execution_result = await self.sandbox_manager.execute_agent(
                                container_id, 
                                timeout=pydantic_spec.resource_limits.timeout
                            )
                            
                            # Store execution results
                            agent_spec["sandbox_results"] = execution_result
                            agent_spec["container_id"] = container_id
                            
                            logger.info(f"Sandbox execution completed: {execution_result.get('status', 'unknown')}")
                            
                            # Get logs for debugging
                            logs = await self.sandbox_manager.get_agent_logs(container_id)
                            agent_spec["execution_logs"] = logs[-50:]  # Keep last 50 lines
                            
                        except Exception as sandbox_error:
                            logger.error(f"Sandbox execution failed for {agent_spec['name']}: {sandbox_error}")
                            agent_spec["sandbox_results"] = {
                                "status": "sandbox_error",
                                "error": str(sandbox_error)
                            }
                    
                except Exception as code_gen_error:
                    logger.warning(f"Code generation failed for {agent_spec['name']}: {code_gen_error}")
                    # Continue deployment without generated code
                    agent_spec["code"] = f"# Code generation failed: {code_gen_error}\n# Manual implementation required"
            
            # Add or update agent (after code generation)
            agent_found = False
            for i, existing_agent in enumerate(existing_agents):
                if existing_agent["name"] == agent_spec["name"]:
                    existing_agents[i] = agent_spec
                    agent_found = True
                    break
            
            if not agent_found:
                existing_agents.append(agent_spec)
            
            # Save to Redis (now includes the generated code)
            await self.redis_client.setex(
                agents_key,
                self.config.session_timeout,
                json.dumps(existing_agents)
            )
            
            # Update execution context with sandbox information
            execution_context = {
                "agent_id": f"{session_id}:{agent_spec['name']}",
                "deployed_at": datetime.utcnow().isoformat(),
                "endpoint": f"/agents/{session_id}/{agent_spec['name']}"
            }
            
            # Add sandbox information if available
            if agent_spec.get("container_id"):
                execution_context["container_id"] = agent_spec["container_id"]
                execution_context["sandbox_status"] = agent_spec.get("sandbox_results", {}).get("status", "unknown")
            
            result = {
                "deployment_status": DeploymentStatus.COMPLETED,
                "error_message": None,
                "execution_context": execution_context
            }
            
            # Save final checkpoint
            await self.save_checkpoint(session_id, "deploy_agent_complete", {**state, **result})
            
            return result
            
        except Exception as e:
            logger.error(f"Error deploying agent: {e}")
            retry_count = state.get("retry_count", 0)
            
            result = {
                "error_message": f"Failed to deploy agent: {str(e)}",
                "deployment_status": DeploymentStatus.FAILED,
                "retry_count": retry_count + 1
            }
            
            # Save error state
            await self.save_checkpoint(session_id, "deploy_agent_error", {**state, **result})
            
            return result
    
    async def save_checkpoint(self, session_id: str, node_name: str, state: Dict[str, Any]) -> None:
        """Save checkpoint to Redis."""
        try:
            checkpoint_key = f"checkpoint:{session_id}:{node_name}"
            checkpoint_data = {
                "state": state,
                "timestamp": datetime.utcnow().isoformat(),
                "node_name": node_name
            }
            
            # Save with 24-hour TTL
            await self.redis_client.setex(
                checkpoint_key,
                86400,  # 24 hours
                json.dumps(checkpoint_data)
            )
            
            # Also save latest checkpoint reference
            latest_key = f"checkpoint:{session_id}:latest"
            await self.redis_client.setex(
                latest_key,
                86400,
                json.dumps({
                    "node_name": node_name,
                    "timestamp": datetime.utcnow().isoformat()
                })
            )
            
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
    
    async def load_checkpoint(self, session_id: str, node_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Load checkpoint from Redis."""
        try:
            if not node_name:
                # Load latest checkpoint
                latest_key = f"checkpoint:{session_id}:latest"
                latest_data = await self.redis_client.get(latest_key)
                if not latest_data:
                    return None
                    
                latest_info = json.loads(latest_data)
                node_name = latest_info["node_name"]
            
            checkpoint_key = f"checkpoint:{session_id}:{node_name}"
            checkpoint_data = await self.redis_client.get(checkpoint_key)
            
            if not checkpoint_data:
                return None
                
            checkpoint = json.loads(checkpoint_data)
            return checkpoint["state"]
            
        except Exception as e:
            logger.error(f"Error loading checkpoint: {e}")
            return None
    
    async def list_active_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions that can be resumed."""
        try:
            # Scan for all checkpoint keys
            pattern = "checkpoint:*:latest"
            sessions = []
            
            async for key in self.redis_client.scan_iter(match=pattern):
                key_str = key.decode() if isinstance(key, bytes) else key
                session_id = key_str.split(':')[1]
                
                # Get session info
                session_data = await self.redis_client.get(key)
                if session_data:
                    session_info = json.loads(session_data)
                    
                    # Load the actual state to get more details
                    state = await self.load_checkpoint(session_id)
                    
                    sessions.append({
                        "session_id": session_id,
                        "timestamp": session_info["timestamp"],
                        "status": state.get("deployment_status", "unknown") if state else "unknown",
                        "request": state.get("user_request", "Unknown") if state else "Unknown"
                    })
            
            # Sort by timestamp (newest first)
            sessions.sort(key=lambda x: x["timestamp"], reverse=True)
            return sessions
            
        except Exception as e:
            logger.error(f"Error listing active sessions: {e}")
            return []
    
    
    async def recover_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover a session from Redis checkpoint."""
        try:
            # First try to get from Redis checkpoint
            state = await self.load_checkpoint(session_id)
            if state:
                return state
                
            # Fallback to LangGraph checkpointer
            config = {"configurable": {"thread_id": session_id}}
            langgraph_state = await self.graph.aget_state(config)
            return langgraph_state.values if langgraph_state else None
            
        except Exception as e:
            logger.error(f"Error recovering session {session_id}: {e}")
            return None
    
    def _clean_text(self, text: str) -> str:
        """Clean and normalize text input."""
        return text.strip().replace("\\n", " ").replace("\\t", " ")
    
    async def _load_conversation_context(self, session_id: str) -> None:
        """Load conversation context from Redis."""
        try:
            context_key = f"conversation_context:{session_id}"
            context_data = await self.redis_client.get(context_key)
            
            if context_data and self.context_manager:
                context_state = json.loads(context_data)
                self.context_manager.load_conversation_state(context_state)
                logger.info(f"Loaded conversation context for session {session_id}")
                
        except Exception as e:
            logger.warning(f"Failed to load conversation context for {session_id}: {e}")
    
    async def _save_conversation_context(self, session_id: str) -> None:
        """Save conversation context to Redis."""
        try:
            if not self.context_manager:
                return
                
            context_key = f"conversation_context:{session_id}"
            context_state = self.context_manager.get_conversation_state()
            
            # Save with 24-hour TTL
            await self.redis_client.setex(
                context_key,
                86400,  # 24 hours
                json.dumps(context_state)
            )
            
            logger.debug(f"Saved conversation context for session {session_id}")
            
        except Exception as e:
            logger.warning(f"Failed to save conversation context for {session_id}: {e}")
    
    async def process_request(self, user_request: str, session_id: str, clarification_responses: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Process a user request through the orchestration workflow."""
        try:
            # Initialize context manager for this session
            self.initialize_context_manager(session_id)
            
            # Store user message in context
            if self.context_manager:
                if clarification_responses:
                    # This is a clarification response
                    for question, answer in clarification_responses.items():
                        self.context_manager.add_user_message(
                            answer,
                            metadata={
                                "type": "clarification",
                                "question": question,
                                "answer": answer
                            },
                            priority=3
                        )
                else:
                    # Regular user request
                    self.context_manager.add_user_message(
                        user_request,
                        metadata={"type": "user_request"},
                        priority=2
                    )
            
            # Check if there's an existing session to resume
            existing_state = await self.load_checkpoint(session_id)
            
            # Handle clarification responses
            if clarification_responses and existing_state:
                result = await self._process_clarification_response(existing_state, clarification_responses)
                await self._save_conversation_context(session_id)
                return result
            
            if existing_state and existing_state.get("deployment_status") != DeploymentStatus.COMPLETED:
                # Resume from existing state
                initial_state = existing_state
                initial_state["user_request"] = user_request  # Update with new request if different
            else:
                # Create new state
                initial_state: OrchestratorState = {
                    "user_request": user_request,
                    "session_id": session_id,
                    "parsed_intent": None,
                    "existing_agents": [],
                    "agent_spec": None,
                    "deployment_status": DeploymentStatus.PENDING,
                    "error_message": None,
                    "execution_context": {},
                    "retry_count": 0,
                    "needs_clarification": None,
                    "clarification_questions": None,
                    "missing_info": None,
                    "suggestions": None,
                    # Initialize new department fields
                    "active_departments": [],
                    "department_coordination": {},
                    "current_department": None,
                    "department_states": {}
                }
            
            # Execute the workflow with checkpointing
            config = {"configurable": {"thread_id": session_id}}
            
            async for step in self.graph.astream(initial_state, config=config):
                logger.info(f"Workflow step: {step}")
                
                # Check if clarification is needed
                if step and isinstance(step, dict):
                    for key, value in step.items():
                        if isinstance(value, dict) and value.get("needs_clarification"):
                            # Save context and return clarification request
                            await self._save_conversation_context(session_id)
                            return value
            
            # Get final state
            final_state = await self.graph.aget_state(config)
            result = final_state.values
            
            # Save conversation context
            await self._save_conversation_context(session_id)
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing request: {e}")
            error_result = {
                "error_message": f"Failed to process request: {str(e)}",
                "deployment_status": DeploymentStatus.FAILED
            }
            
            # Save error state and context
            await self.save_checkpoint(session_id, "process_request_error", error_result)
            if session_id:
                await self._save_conversation_context(session_id)
            
            return error_result
    
    async def close(self) -> None:
        """Clean up resources."""
        if self.sandbox_manager:
            await self.sandbox_manager.cleanup_all()
        if self.redis_client:
            await self.redis_client.aclose()
    
    async def stop_agent(self, session_id: str, agent_name: str) -> bool:
        """Stop a running agent in sandbox."""
        try:
            # Get agent from Redis
            agents_key = f"agents:{session_id}"
            agents_data = await self.redis_client.get(agents_key)
            
            if not agents_data:
                return False
            
            agents = json.loads(agents_data)
            for agent in agents:
                if agent["name"] == agent_name and agent.get("container_id"):
                    container_id = agent["container_id"]
                    
                    if self.sandbox_manager:
                        success = await self.sandbox_manager.stop_agent(container_id)
                        if success:
                            # Update agent status
                            agent["status"] = "stopped"
                            await self.redis_client.setex(
                                agents_key,
                                self.config.session_timeout,
                                json.dumps(agents)
                            )
                        return success
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to stop agent {agent_name}: {e}")
            return False
    
    async def get_agent_logs(self, session_id: str, agent_name: str) -> List[str]:
        """Get logs for a specific agent."""
        try:
            # Get agent from Redis
            agents_key = f"agents:{session_id}"
            agents_data = await self.redis_client.get(agents_key)
            
            if not agents_data:
                return []
            
            agents = json.loads(agents_data)
            for agent in agents:
                if agent["name"] == agent_name:
                    # Return stored logs if available
                    if agent.get("execution_logs"):
                        return agent["execution_logs"]
                    
                    # Get real-time logs from sandbox
                    if agent.get("container_id") and self.sandbox_manager:
                        return await self.sandbox_manager.get_agent_logs(agent["container_id"])
            
            return []
            
        except Exception as e:
            logger.error(f"Failed to get logs for agent {agent_name}: {e}")
            return [f"Error getting logs: {e}"]
    
    async def get_agent_status(self, session_id: str, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get real-time status of an agent."""
        try:
            # Get agent from Redis
            agents_key = f"agents:{session_id}"
            agents_data = await self.redis_client.get(agents_key)
            
            if not agents_data:
                return None
            
            agents = json.loads(agents_data)
            for agent in agents:
                if agent["name"] == agent_name:
                    status = {
                        "name": agent["name"],
                        "status": agent.get("status", "unknown"),
                        "deployment_status": agent.get("deployment_status", "unknown"),
                        "container_id": agent.get("container_id"),
                        "sandbox_results": agent.get("sandbox_results", {})
                    }
                    
                    # Get real-time container stats if available
                    if agent.get("container_id") and self.sandbox_manager:
                        stats = await self.sandbox_manager.get_container_stats(agent["container_id"])
                        if stats:
                            status["container_stats"] = stats
                    
                    return status
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get status for agent {agent_name}: {e}")
            return None
    
    async def cleanup_agent(self, session_id: str, agent_name: str) -> bool:
        """Cleanup a specific agent's sandbox."""
        try:
            # Get agent from Redis
            agents_key = f"agents:{session_id}"
            agents_data = await self.redis_client.get(agents_key)
            
            if not agents_data:
                return False
            
            agents = json.loads(agents_data)
            for i, agent in enumerate(agents):
                if agent["name"] == agent_name and agent.get("container_id"):
                    container_id = agent["container_id"]
                    
                    if self.sandbox_manager:
                        success = await self.sandbox_manager.cleanup_sandbox(container_id)
                        if success:
                            # Remove agent from list or mark as cleaned
                            agents.pop(i)
                            await self.redis_client.setex(
                                agents_key,
                                self.config.session_timeout,
                                json.dumps(agents)
                            )
                        return success
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to cleanup agent {agent_name}: {e}")
            return False