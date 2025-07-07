#!/usr/bin/env python3
"""Template engine for HeyJarvis agent code generation."""

import os
import re
import ast
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import jinja2
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TemplateInfo:
    """Information about a template."""
    name: str
    description: str
    required_params: List[str]
    optional_params: List[str]
    capabilities: List[str]
    integrations: List[str]


@dataclass
class TemplateMatch:
    """Result of template matching."""
    template_name: str
    confidence: float
    extracted_params: Dict[str, Any]
    missing_required: List[str]
    template_info: TemplateInfo


class TemplateValidationError(Exception):
    """Raised when template validation fails."""
    pass


class TemplateEngine:
    """Jinja2-based template engine for agent code generation."""
    
    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or Path(__file__).parent / "library"
        self.templates_dir.mkdir(exist_ok=True)
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(self.templates_dir)),
            autoescape=False,  # We're generating Python code
            trim_blocks=True,
            lstrip_blocks=True,
            undefined=jinja2.StrictUndefined  # Fail on undefined variables
        )
        
        # Add custom filters
        self.jinja_env.filters['snake_case'] = self._snake_case
        self.jinja_env.filters['camel_case'] = self._camel_case
        self.jinja_env.filters['class_name'] = self._class_name
        
        # Template registry
        self.templates: Dict[str, TemplateInfo] = {}
        self._load_template_metadata()
        
    def _snake_case(self, text: str) -> str:
        """Convert text to snake_case."""
        # Replace spaces and special chars with underscores
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', '_', text)
        # Insert underscores before capitals and convert to lowercase
        text = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', text)
        return text.lower().strip('_')
    
    def _camel_case(self, text: str) -> str:
        """Convert text to camelCase."""
        words = re.sub(r'[^\w\s]', '', text).split()
        if not words:
            return text
        return words[0].lower() + ''.join(word.capitalize() for word in words[1:])
    
    def _class_name(self, text: str) -> str:
        """Convert text to ClassName."""
        words = re.sub(r'[^\w\s]', '', text).split()
        return ''.join(word.capitalize() for word in words)
    
    def _load_template_metadata(self) -> None:
        """Load metadata for available templates."""
        self.templates = {
            "gmail_monitor": TemplateInfo(
                name="gmail_monitor",
                description="Monitor Gmail inbox for specific emails and send alerts",
                required_params=["email_filter", "check_interval"],
                optional_params=["sender_filter", "subject_filter", "alert_webhook"],
                capabilities=["email_monitoring", "alert_sending"],
                integrations=["gmail"]
            ),
            "slack_notifier": TemplateInfo(
                name="slack_notifier",
                description="Send notifications to Slack channels or users",
                required_params=["channel"],
                optional_params=["slack_token", "username", "icon_emoji", "webhook_url"],
                capabilities=["messaging", "notifications"],
                integrations=["slack"]
            ),
            "web_scraper": TemplateInfo(
                name="web_scraper",
                description="Scrape websites and extract data",
                required_params=["target_url", "scrape_interval"],
                optional_params=["css_selectors", "xpath_selectors", "headers", "cookies"],
                capabilities=["web_scraping", "data_extraction"],
                integrations=["http"]
            ),
            "file_processor": TemplateInfo(
                name="file_processor",
                description="Process and transform files",
                required_params=["input_path", "operation"],
                optional_params=["output_path", "file_pattern", "transformation_rules"],
                capabilities=["file_processing", "data_transformation"],
                integrations=["filesystem"]
            ),
            "data_analyzer": TemplateInfo(
                name="data_analyzer",
                description="Analyze data and generate insights",
                required_params=["data_source", "analysis_type"],
                optional_params=["metrics", "chart_types", "export_format"],
                capabilities=["data_analysis", "reporting"],
                integrations=["pandas", "matplotlib"]
            )
        }
    
    def list_templates(self) -> Dict[str, TemplateInfo]:
        """Get all available templates."""
        return self.templates.copy()
    
    def get_template_info(self, template_name: str) -> Optional[TemplateInfo]:
        """Get information about a specific template."""
        return self.templates.get(template_name)
    
    def render_template(
        self,
        template_name: str,
        parameters: Dict[str, Any],
        validate: bool = True
    ) -> str:
        """
        Render a template with given parameters.
        
        Args:
            template_name: Name of the template to render
            parameters: Parameters to pass to the template
            validate: Whether to validate the rendered code
            
        Returns:
            Rendered Python code
            
        Raises:
            TemplateValidationError: If template or parameters are invalid
        """
        if template_name not in self.templates:
            raise TemplateValidationError(f"Template '{template_name}' not found")
        
        template_info = self.templates[template_name]
        
        # Check required parameters
        missing_required = [
            param for param in template_info.required_params
            if param not in parameters
        ]
        if missing_required:
            raise TemplateValidationError(
                f"Missing required parameters: {missing_required}"
            )
        
        try:
            # Load and render template
            template_file = f"{template_name}_template.j2"
            template = self.jinja_env.get_template(template_file)
            
            # Add template metadata to parameters
            render_params = parameters.copy()
            render_params.update({
                'template_name': template_name,
                'template_info': template_info,
                'agent_name': parameters.get('agent_name', 
                    f"{template_name.replace('_', ' ').title()} Agent")
            })
            
            # Add default values for all optional parameters to prevent undefined variable errors
            for param in template_info.optional_params:
                if param not in render_params:
                    render_params[param] = None
            
            rendered_code = template.render(**render_params)
            
            if validate:
                self._validate_code(rendered_code)
            
            logger.info(f"Successfully rendered template: {template_name}")
            return rendered_code
            
        except jinja2.TemplateNotFound:
            raise TemplateValidationError(
                f"Template file '{template_file}' not found in {self.templates_dir}"
            )
        except jinja2.TemplateError as e:
            raise TemplateValidationError(f"Template rendering failed: {e}")
    
    def _validate_code(self, code: str) -> None:
        """
        Validate that the rendered code is syntactically correct Python.
        
        Args:
            code: Python code to validate
            
        Raises:
            TemplateValidationError: If code is invalid
        """
        try:
            # Parse the code to check syntax
            ast.parse(code)
            
            # Additional validation checks
            self._validate_agent_class(code)
            
        except SyntaxError as e:
            raise TemplateValidationError(f"Invalid Python syntax: {e}")
        except Exception as e:
            raise TemplateValidationError(f"Code validation failed: {e}")
    
    def _validate_agent_class(self, code: str) -> None:
        """
        Validate that the code contains a proper SandboxAgent subclass.
        
        Args:
            code: Python code to validate
            
        Raises:
            TemplateValidationError: If agent class is invalid
        """
        # Check for required imports
        required_imports = [
            "from base_agent import SandboxAgent",
            "import asyncio",
            "import logging"
        ]
        
        for import_stmt in required_imports:
            if import_stmt not in code:
                raise TemplateValidationError(
                    f"Missing required import: {import_stmt}"
                )
        
        # Check for SandboxAgent subclass
        if "class " not in code or "SandboxAgent" not in code:
            raise TemplateValidationError(
                "Code must contain a class that inherits from SandboxAgent"
            )
        
        # Check for required methods
        required_methods = ["async def initialize", "async def execute", "async def cleanup"]
        for method in required_methods:
            if method not in code:
                raise TemplateValidationError(
                    f"Agent class must implement: {method.replace('async def ', '')}"
                )
    
    def create_custom_template(
        self,
        template_name: str,
        template_content: str,
        template_info: TemplateInfo
    ) -> None:
        """
        Create a new custom template.
        
        Args:
            template_name: Name for the new template
            template_content: Jinja2 template content
            template_info: Template metadata
        """
        template_file = self.templates_dir / f"{template_name}_template.j2"
        
        try:
            # Validate template syntax
            self.jinja_env.from_string(template_content)
            
            # Save template file
            with open(template_file, 'w') as f:
                f.write(template_content)
            
            # Register template
            self.templates[template_name] = template_info
            
            logger.info(f"Created custom template: {template_name}")
            
        except jinja2.TemplateError as e:
            raise TemplateValidationError(f"Invalid template syntax: {e}")
        except Exception as e:
            raise TemplateValidationError(f"Failed to create template: {e}")
    
    def test_template(
        self,
        template_name: str,
        test_parameters: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Test a template with sample parameters.
        
        Args:
            template_name: Name of template to test
            test_parameters: Parameters for testing
            
        Returns:
            Tuple of (success, result_or_error)
        """
        try:
            rendered_code = self.render_template(
                template_name, 
                test_parameters, 
                validate=True
            )
            return True, rendered_code
        except Exception as e:
            return False, str(e)