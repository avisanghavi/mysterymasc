"""LLM-powered code generator for HeyJarvis agents."""

import ast
import asyncio
import logging
import re
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage

from .agent_spec import AgentSpec, TimeTrigger, EventTrigger, ManualTrigger

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Result of code validation."""
    is_valid: bool
    error: Optional[str] = None
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class CodeGenerationError(Exception):
    """Raised when code generation fails after all attempts."""
    pass


class AgentCodeGenerator:
    """LLM-powered generator for agent Python code."""
    
    def __init__(self, openai_api_key: str):
        self.llm = ChatOpenAI(
            api_key=openai_api_key,
            model="gpt-4o-mini",
            temperature=0.1
        )
        
        # Approved libraries for security
        self.approved_libraries = {
            'asyncio', 'logging', 'datetime', 'typing', 'json', 'os', 're',
            'time', 'uuid', 'hashlib', 'base64', 'urllib', 'http',
            'email', 'mimetypes', 'pathlib', 'shutil', 'tempfile',
            'google.oauth2', 'googleapiclient', 'slack_sdk', 'requests',
            'aiohttp', 'pandas', 'numpy', 'tenacity', 'schedule',
            'pydantic', 'sqlalchemy', 'redis', 'boto3', 'azure.storage',
            'dropbox', 'notion_client', 'jira', 'github', 'tweepy'
        }
        
        # Forbidden operations for security (more specific patterns)
        self.forbidden_patterns = [
            r'\bexec\s*\(', r'\beval\s*\(', r'__import__\s*\(',
            r'subprocess\s*\.', r'os\.system\s*\(', 
            r'\bopen\s*\([^)]*["\'][rwa]["\']', # Only forbid open() with write/append modes
            r'\binput\s*\(', r'raw_input\s*\(',
            r'globals\s*\(\)', r'locals\s*\(\)', r'vars\s*\('
        ]

    async def generate_agent_code(self, spec: AgentSpec) -> str:
        """
        Generate executable Python code for an AgentSpec.
        
        Args:
            spec: Validated AgentSpec instance
            
        Returns:
            Executable Python code as string
            
        Raises:
            CodeGenerationError: If generation fails after 3 attempts
        """
        previous_error = None
        
        for attempt in range(3):
            logger.info(f"Code generation attempt {attempt + 1}/3 for agent: {spec.name}")
            
            try:
                code = await self._generate_code_attempt(spec, previous_error)
                validation_result = await self._validate_code(code)
                
                if validation_result.is_valid:
                    logger.info(f"Code generation successful for {spec.name}")
                    return code
                
                previous_error = validation_result.error
                logger.warning(f"Attempt {attempt + 1} failed: {previous_error}")
                
            except Exception as e:
                previous_error = str(e)
                logger.error(f"Attempt {attempt + 1} exception: {previous_error}")
        
        raise CodeGenerationError(f"Failed to generate code after 3 attempts: {previous_error}")

    async def _generate_code_attempt(self, spec: AgentSpec, previous_error: Optional[str]) -> str:
        """Generate a single attempt at creating agent code."""
        
        # Determine template based on capabilities
        template_type = self._determine_template_type(spec)
        
        # Build the system prompt
        system_prompt = self._build_system_prompt(spec)
        
        # Build the user prompt
        user_prompt = self._build_user_prompt(spec, template_type, previous_error)
        
        # Generate code using LLM
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = await self.llm.ainvoke(messages)
        
        # Extract code from response
        code = self._extract_code_from_response(response.content)
        
        return code

    def _determine_template_type(self, spec: AgentSpec) -> str:
        """Determine the appropriate template type based on capabilities."""
        capabilities = set(spec.capabilities)
        
        if any(cap in capabilities for cap in ['email_monitoring', 'file_monitoring', 'web_scraping']):
            return 'monitor'
        elif any(cap in capabilities for cap in ['file_sync', 'data_processing']):
            return 'sync'
        elif any(cap in capabilities for cap in ['report_generation', 'data_analysis']):
            return 'report'
        elif any(cap in capabilities for cap in ['webhook']):
            return 'webhook'
        elif any(cap in capabilities for cap in ['task_scheduling']):
            return 'scheduled'
        else:
            return 'custom'

    def _build_system_prompt(self, spec: AgentSpec) -> str:
        """Build the system prompt for code generation."""
        approved_libs = ', '.join(sorted(self.approved_libraries))
        
        return f"""You are an expert Python developer creating production-ready agent code.

Generate clean, efficient, async Python code that:
- Uses type hints everywhere
- Includes comprehensive error handling with try/except blocks
- Follows PEP 8 style guidelines
- Is optimized for resource limits: CPU={spec.resource_limits.cpu}, Memory={spec.resource_limits.memory}MB
- Uses only these approved libraries: {approved_libs}
- Includes proper logging statements
- Uses exponential backoff for retries (tenacity library)
- Has timeout protection using asyncio.wait_for()
- Cleans up resources properly in finally blocks

CRITICAL SECURITY RULES:
- Never use exec(), eval(), __import__(), subprocess, os.system(), globals(), locals()
- Never use open() with write/append modes - use tempfile for temporary files
- Use logging.getLogger() instead of creating files directly
- Always validate inputs and sanitize data
- Use parameterized queries for databases
- Implement proper rate limiting
- For file operations, use pathlib and tempfile modules only

CODE STRUCTURE REQUIREMENTS:
1. Import statements at top
2. Import SandboxAgent: from base_agent import SandboxAgent
3. Class definition inheriting from SandboxAgent
4. __init__ method with configuration (call super().__init__())
5. async initialize() method for setup
6. async execute() method for main logic
7. async cleanup() method for teardown
8. Helper methods as needed

INTEGRATION PATTERNS:
- Gmail: Use google-auth + googleapiclient
- Slack: Use slack_sdk.WebClient
- AWS: Use boto3 with proper credentials
- Database: Use sqlalchemy with async support
- HTTP APIs: Use aiohttp for async requests

Generate ONLY the Python code, no explanations or markdown formatting."""

    def _build_user_prompt(self, spec: AgentSpec, template_type: str, previous_error: Optional[str]) -> str:
        """Build the user prompt with agent specifications."""
        
        # Convert triggers to readable format
        trigger_info = []
        for trigger in spec.triggers:
            if isinstance(trigger, TimeTrigger):
                if trigger.interval_minutes:
                    trigger_info.append(f"Timer: every {trigger.interval_minutes} minutes")
                elif trigger.cron_expression:
                    trigger_info.append(f"Cron: {trigger.cron_expression}")
            elif isinstance(trigger, EventTrigger):
                trigger_info.append(f"Event: {trigger.event_types}")
            elif isinstance(trigger, ManualTrigger):
                trigger_info.append("Manual trigger")
        
        # Convert integrations to readable format
        integration_info = []
        for name, config in spec.integrations.items():
            integration_info.append(f"{name} ({config.auth_type}, scopes: {config.scopes})")
        
        base_prompt = f"""Generate Python code for an agent with these specifications:

AGENT DETAILS:
- Name: {spec.name}
- Description: {spec.description}
- Version: {spec.version}
- Template Type: {template_type}

FUNCTIONAL REQUIREMENTS:
- Capabilities: {spec.capabilities}
- Triggers: {trigger_info}
- Integrations: {integration_info}

RESOURCE CONSTRAINTS:
- CPU Limit: {spec.resource_limits.cpu} cores
- Memory Limit: {spec.resource_limits.memory} MB
- Timeout: {spec.resource_limits.timeout} seconds
- Max Retries: {spec.resource_limits.max_retries}

CLASS NAME: {self._generate_class_name(spec.name)}

BASE TEMPLATE STRUCTURE:
```python
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
# Additional imports based on integrations
from base_agent import SandboxAgent

class {self._generate_class_name(spec.name)}(SandboxAgent):
    \"\"\"Generated agent: {spec.description}\"\"\"
    
    def __init__(self):
        super().__init__()
        self.name = "{spec.name}"
        self.version = "{spec.version}"
        self.capabilities = {spec.capabilities}
        self.config = {self._generate_config_dict(spec)}
        self.logger = logging.getLogger(self.name)
        # Initialize instance variables
        
    async def initialize(self):
        \"\"\"Initialize agent resources and connections\"\"\"
        # Setup code based on integrations
        
    async def execute(self):
        \"\"\"Main execution logic\"\"\"
        # Main agent logic based on capabilities and triggers
        
    async def cleanup(self):
        \"\"\"Cleanup resources\"\"\"
        # Cleanup code
```

SPECIFIC REQUIREMENTS FOR {template_type.upper()} TEMPLATE:
{self._get_template_specific_requirements(template_type, spec)}"""

        if previous_error:
            base_prompt += f"""

PREVIOUS ATTEMPT FAILED WITH ERROR:
{previous_error}

Please fix this error in your generated code."""

        return base_prompt

    def _generate_class_name(self, agent_name: str) -> str:
        """Generate a valid Python class name from agent name."""
        # Remove special characters and convert to CamelCase
        clean_name = re.sub(r'[^a-zA-Z0-9\s]', '', agent_name)
        words = clean_name.split()
        class_name = ''.join(word.capitalize() for word in words) + 'Agent'
        return class_name

    def _generate_config_dict(self, spec: AgentSpec) -> Dict[str, Any]:
        """Generate configuration dictionary for the agent."""
        config = {
            'id': spec.id,
            'resource_limits': {
                'cpu': spec.resource_limits.cpu,
                'memory': spec.resource_limits.memory,
                'timeout': spec.resource_limits.timeout,
                'max_retries': spec.resource_limits.max_retries
            },
            'integrations': {}
        }
        
        for name, integration in spec.integrations.items():
            config['integrations'][name] = {
                'service_name': integration.service_name,
                'auth_type': integration.auth_type,
                'scopes': integration.scopes,
                'rate_limit': integration.rate_limit
            }
        
        return config

    def _get_template_specific_requirements(self, template_type: str, spec: AgentSpec) -> str:
        """Get specific requirements based on template type."""
        
        if template_type == 'monitor':
            interval = 300  # Default 5 minutes
            for trigger in spec.triggers:
                if isinstance(trigger, TimeTrigger) and trigger.interval_minutes:
                    interval = trigger.interval_minutes * 60
            
            return f"""
- Implement continuous monitoring loop
- Check conditions every {interval} seconds
- Include rate limiting to respect API limits
- Log all monitoring activities
- Handle connection failures gracefully
- Implement exponential backoff for retries"""

        elif template_type == 'sync':
            return """
- Implement source data retrieval
- Implement destination data upload
- Include data transformation logic
- Add conflict resolution for existing data
- Implement incremental sync where possible
- Include progress tracking and logging"""

        elif template_type == 'report':
            return """
- Implement data collection from specified sources
- Include data aggregation and analysis
- Generate report in specified format (HTML/PDF/JSON)
- Implement delivery mechanism (email/file/API)
- Include error reporting for failed data collection
- Cache intermediate results for efficiency"""

        elif template_type == 'webhook':
            return """
- Implement webhook endpoint handling
- Include request validation and authentication
- Process incoming webhook data
- Implement response formatting
- Include security measures (rate limiting, input validation)
- Log all webhook activities"""

        elif template_type == 'scheduled':
            return """
- Implement cron-based scheduling
- Include task queue management
- Handle overlapping execution prevention
- Implement job persistence and recovery
- Include comprehensive job logging
- Handle timezone considerations"""

        else:  # custom
            return """
- Implement custom logic based on specified capabilities
- Include error handling for all external operations
- Implement proper resource management
- Include comprehensive logging
- Handle edge cases and failures gracefully"""

    def _extract_code_from_response(self, response_content: str) -> str:
        """Extract Python code from LLM response."""
        # Remove markdown code blocks if present
        content = response_content.strip()
        
        # Handle code blocks
        if content.startswith('```python'):
            content = content[9:]
        elif content.startswith('```'):
            content = content[3:]
        
        if content.endswith('```'):
            content = content[:-3]
        
        return content.strip()

    async def _validate_code(self, code: str) -> ValidationResult:
        """Validate generated code for syntax and security."""
        warnings = []
        
        try:
            # Check syntax by parsing
            ast.parse(code)
            
        except SyntaxError as e:
            return ValidationResult(
                is_valid=False,
                error=f"Syntax error: {e}"
            )
        
        # Check for forbidden patterns
        for pattern in self.forbidden_patterns:
            if re.search(pattern, code):
                return ValidationResult(
                    is_valid=False,
                    error=f"Forbidden operation detected: {pattern}"
                )
        
        # Check imports
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if not self._is_approved_import(alias.name):
                            return ValidationResult(
                                is_valid=False,
                                error=f"Unapproved import: {alias.name}"
                            )
                elif isinstance(node, ast.ImportFrom):
                    if node.module and not self._is_approved_import(node.module):
                        return ValidationResult(
                            is_valid=False,
                            error=f"Unapproved import: {node.module}"
                        )
        except Exception as e:
            warnings.append(f"Import validation warning: {e}")
        
        # Check for required methods
        required_methods = ['__init__', 'initialize', 'execute', 'cleanup']
        for method in required_methods:
            if f"def {method}" not in code and f"async def {method}" not in code:
                return ValidationResult(
                    is_valid=False,
                    error=f"Missing required method: {method}"
                )
        
        # Check for class definition
        if "class " not in code or ("BaseAgent" not in code and "SandboxAgent" not in code):
            return ValidationResult(
                is_valid=False,
                error="Missing class definition or BaseAgent/SandboxAgent inheritance"
            )
        
        return ValidationResult(
            is_valid=True,
            warnings=warnings
        )

    def _is_approved_import(self, module_name: str) -> bool:
        """Check if an import is in the approved list."""
        # Check exact match first
        if module_name in self.approved_libraries:
            return True
        
        # Check if it's a submodule of an approved library
        for approved in self.approved_libraries:
            if module_name.startswith(approved + '.'):
                return True
        
        return False

    def generate_test_code(self, spec: AgentSpec) -> str:
        """Generate pytest test cases for the agent."""
        class_name = self._generate_class_name(spec.name)
        
        test_code = f'''"""Test cases for {spec.name}."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from {class_name.lower()} import {class_name}


class Test{class_name}:
    """Test suite for {class_name}."""
    
    @pytest.fixture
    async def agent(self):
        """Create agent instance for testing."""
        agent = {class_name}()
        await agent.initialize()
        yield agent
        await agent.cleanup()
    
    @pytest.mark.asyncio
    async def test_initialization(self):
        """Test agent initialization."""
        agent = {class_name}()
        await agent.initialize()
        
        assert agent.name == "{spec.name}"
        assert agent.version == "{spec.version}"
        assert agent.capabilities == {spec.capabilities}
        
        await agent.cleanup()
    
    @pytest.mark.asyncio
    async def test_execute_success(self, agent):
        """Test successful execution."""
        # Mock external dependencies
        with patch.object(agent, '_external_call', new_callable=AsyncMock) as mock_call:
            mock_call.return_value = {{"success": True}}
            
            result = await agent.execute()
            
            # Add specific assertions based on agent type
            assert result is not None
    
    @pytest.mark.asyncio
    async def test_execute_with_errors(self, agent):
        """Test execution with error handling."""
        with patch.object(agent, '_external_call', new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = Exception("Test error")
            
            # Should handle errors gracefully
            result = await agent.execute()
            
            # Verify error handling
            assert agent.logger.error.called if hasattr(agent.logger, 'error') else True
    
    @pytest.mark.asyncio
    async def test_resource_limits(self, agent):
        """Test resource limit enforcement."""
        # Test timeout handling
        with patch.object(agent, 'execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = asyncio.TimeoutError()
            
            with pytest.raises(asyncio.TimeoutError):
                await asyncio.wait_for(agent.execute(), timeout=0.1)
    
    @pytest.mark.asyncio
    async def test_cleanup(self, agent):
        """Test cleanup functionality."""
        await agent.cleanup()
        
        # Verify resources are cleaned up
        # Add specific cleanup assertions based on agent type
        assert True  # Placeholder - add specific checks
'''

        return test_code

    def generate_base_agent_class(self) -> str:
        """Generate the base agent class that all agents inherit from."""
        return '''"""Base agent class for all generated agents."""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime


class BaseAgent(ABC):
    """Base class for all HeyJarvis agents."""
    
    def __init__(self):
        self.name: str = "BaseAgent"
        self.version: str = "1.0.0"
        self.capabilities: List[str] = []
        self.config: Dict[str, Any] = {}
        self.logger: logging.Logger = logging.getLogger(self.name)
        self.is_running: bool = False
        self.start_time: Optional[datetime] = None
        
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize agent resources and connections."""
        pass
    
    @abstractmethod
    async def execute(self) -> Any:
        """Main execution logic."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
    
    async def start(self) -> None:
        """Start the agent."""
        if self.is_running:
            self.logger.warning("Agent is already running")
            return
        
        try:
            self.logger.info(f"Starting agent: {self.name}")
            self.start_time = datetime.utcnow()
            self.is_running = True
            
            await self.initialize()
            result = await self.execute()
            
            self.logger.info(f"Agent {self.name} completed successfully")
            return result
            
        except Exception as e:
            self.logger.error(f"Agent {self.name} failed: {e}")
            raise
        finally:
            self.is_running = False
            await self.cleanup()
    
    async def stop(self) -> None:
        """Stop the agent."""
        if not self.is_running:
            return
        
        self.logger.info(f"Stopping agent: {self.name}")
        self.is_running = False
        await self.cleanup()
    
    def get_status(self) -> Dict[str, Any]:
        """Get agent status information."""
        uptime = None
        if self.start_time:
            uptime = (datetime.utcnow() - self.start_time).total_seconds()
        
        return {
            "name": self.name,
            "version": self.version,
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime,
            "capabilities": self.capabilities
        }
'''


# Main function for external use
async def generate_agent_code(spec: AgentSpec, openai_api_key: str) -> str:
    """
    Generate executable Python code for an AgentSpec.
    
    Args:
        spec: Validated AgentSpec instance
        openai_api_key: OpenAI API key for LLM
        
    Returns:
        Executable Python code as string
    """
    generator = AgentCodeGenerator(openai_api_key)
    return await generator.generate_agent_code(spec)