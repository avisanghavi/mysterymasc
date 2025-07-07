"""Comprehensive Pydantic schema system for agent specifications."""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Union, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from semantic_version import Version


class ResourceLimits(BaseModel):
    """Resource limits for agent execution."""
    cpu: float = Field(default=1.0, ge=0.1, le=4.0, description="CPU allocation in cores")
    memory: int = Field(default=512, ge=128, le=2048, description="Memory allocation in MB")
    timeout: int = Field(default=300, ge=30, le=3600, description="Execution timeout in seconds")
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")


class IntegrationConfig(BaseModel):
    """Configuration for external service integrations."""
    service_name: str = Field(..., description="Name of the external service")
    auth_type: Literal["oauth2", "api_key", "webhook", "internal", "scraping"] = Field(..., description="Authentication method")
    scopes: List[str] = Field(default_factory=list, description="Required permissions/scopes")
    rate_limit: Optional[int] = Field(None, ge=1, le=10000, description="Requests per minute limit")
    validated: bool = Field(default=False, description="Whether integration is validated")
    
    @field_validator('service_name')
    @classmethod
    def validate_service_name(cls, v):
        allowed_services = {
            'gmail', 'outlook', 'slack', 'discord', 'twitter', 'linkedin', 
            'github', 'gitlab', 'jira', 'trello', 'notion', 'airtable',
            'dropbox', 'google_drive', 'aws_s3', 'azure_blob', 'webhook',
            'http_api', 'database', 'file_system', 'sales_navigator', 'anthropic',
            'google_calendar', 'calendly', 'zoom', 'salesforce', 'hubspot', 
            'pipedrive', 'crunchbase', 'job_boards', 'outreach_io', 'custom_analytics'
        }
        if v.lower() not in allowed_services:
            raise ValueError(f"Service '{v}' not in allowed services: {allowed_services}")
        return v.lower()


class TriggerConfig(BaseModel):
    """Base class for trigger configurations."""
    trigger_type: str = Field(..., description="Type of trigger")
    description: Optional[str] = Field(None, description="Human-readable description")
    enabled: bool = Field(default=True, description="Whether trigger is active")


class TimeTrigger(TriggerConfig):
    """Time-based trigger configuration."""
    trigger_type: Literal["time"] = "time"
    cron_expression: Optional[str] = Field(None, description="Cron expression for scheduling")
    interval_minutes: Optional[int] = Field(None, ge=1, le=43200, description="Interval in minutes")
    
    @model_validator(mode='after')
    def validate_time_config(self):
        cron = self.cron_expression
        interval = self.interval_minutes
        
        if not cron and not interval:
            raise ValueError("Either cron_expression or interval_minutes must be provided")
        if cron and interval:
            raise ValueError("Cannot specify both cron_expression and interval_minutes")
        
        return self
    
    @field_validator('cron_expression')
    @classmethod
    def validate_cron(cls, v):
        if v is not None:
            # Basic cron validation (5 fields)
            parts = v.split()
            if len(parts) != 5:
                raise ValueError("Cron expression must have 5 fields: minute hour day month weekday")
        return v


class EventTrigger(TriggerConfig):
    """Event-based trigger configuration."""
    trigger_type: Literal["event"] = "event"
    webhook_url: Optional[str] = Field(None, description="Webhook URL for receiving events")
    event_types: List[str] = Field(default_factory=list, description="Types of events to listen for")
    source_service: Optional[str] = Field(None, description="Service generating events")
    
    @field_validator('webhook_url')
    @classmethod
    def validate_webhook_url(cls, v):
        if v is not None and not v.startswith(('http://', 'https://')):
            raise ValueError("Webhook URL must start with http:// or https://")
        return v


class ManualTrigger(TriggerConfig):
    """Manual trigger configuration."""
    trigger_type: Literal["manual"] = "manual"
    description: str = Field(..., min_length=5, max_length=200, description="Description of manual trigger")


class FieldSchema(BaseModel):
    """Schema for input/output fields."""
    field_name: str = Field(..., min_length=1, max_length=50, description="Name of the field")
    field_type: Literal["string", "number", "boolean", "object", "array"] = Field(..., description="Data type")
    required: bool = Field(default=False, description="Whether field is required")
    description: str = Field(..., min_length=5, max_length=200, description="Field description")
    validation_rules: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Validation rules")
    default_value: Optional[Any] = Field(None, description="Default value if not provided")
    
    @field_validator('field_name')
    @classmethod
    def validate_field_name(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError("Field name must be alphanumeric with underscores only")
        return v.lower()


class AgentSpec(BaseModel):
    """Comprehensive agent specification model."""
    
    # Core identity
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique agent identifier")
    name: str = Field(..., min_length=2, max_length=50, description="Agent name")
    description: str = Field(..., min_length=10, max_length=500, description="Agent description")
    version: str = Field(default="1.0.0", description="Semantic version")
    
    # Functional specification
    capabilities: List[str] = Field(..., min_items=1, description="Agent capabilities")
    triggers: List[Union[TimeTrigger, EventTrigger, ManualTrigger]] = Field(
        ..., min_items=1, description="Trigger configurations"
    )
    integrations: Dict[str, IntegrationConfig] = Field(
        default_factory=dict, description="External service integrations"
    )
    inputs: Dict[str, FieldSchema] = Field(
        default_factory=dict, description="Input field specifications"
    )
    outputs: Dict[str, FieldSchema] = Field(
        default_factory=dict, description="Output field specifications"
    )
    
    # Resource and execution configuration
    resource_limits: ResourceLimits = Field(default_factory=ResourceLimits)
    llm_config: Optional[Dict[str, Any]] = Field(
        None, description="LLM configuration (model, temperature, max_tokens)"
    )
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Additional agent configuration"
    )
    
    # Metadata
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    created_by: str = Field(..., description="User/session ID that created the agent")
    status: Literal["draft", "active", "paused", "archived"] = Field(default="draft")
    
    # Configuration
    class Config:
        use_enum_values = True
        validate_assignment = True
        arbitrary_types_allowed = True
    
    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not all(c.isalnum() or c.isspace() for c in v):
            raise ValueError("Name must contain only alphanumeric characters and spaces")
        return v.strip()
    
    @field_validator('version')
    @classmethod
    def validate_version(cls, v):
        try:
            Version(v)
        except ValueError:
            raise ValueError("Version must follow semantic versioning (e.g., 1.0.0)")
        return v
    
    @field_validator('capabilities')
    @classmethod
    def validate_capabilities_list(cls, v):
        allowed_capabilities = {
            'email_monitoring', 'email_sending', 'calendar_management',
            'file_backup', 'file_sync', 'file_monitoring',
            'social_media_posting', 'social_media_monitoring',
            'web_scraping', 'api_integration', 'data_processing',
            'report_generation', 'alert_sending', 'workflow_automation',
            'database_operations', 'cloud_storage', 'notification_management',
            'task_scheduling', 'content_creation', 'data_analysis',
            'lead_qualification', 'personalization', 'template_management',
            'a_b_testing', 'timezone_handling', 'scheduling_coordination',
            'analytics_computation', 'crm_integration', 'trend_analysis'
        }
        
        invalid_caps = set(v) - allowed_capabilities
        if invalid_caps:
            raise ValueError(f"Invalid capabilities: {invalid_caps}. Allowed: {allowed_capabilities}")
        
        return list(set(v))  # Remove duplicates
    
    def validate_capabilities(self) -> bool:
        """Validate that capabilities are properly configured."""
        required_integrations = {
            'email_monitoring': ['gmail', 'outlook'],
            'email_sending': ['gmail', 'outlook'],
            'social_media_posting': ['twitter', 'linkedin'],
            'social_media_monitoring': ['twitter', 'linkedin'],
            'file_backup': ['dropbox', 'google_drive', 'aws_s3'],
            'file_sync': ['dropbox', 'google_drive'],
            'cloud_storage': ['aws_s3', 'azure_blob', 'google_drive']
        }
        
        for capability in self.capabilities:
            if capability in required_integrations:
                required_services = required_integrations[capability]
                if not any(service in self.integrations for service in required_services):
                    raise ValueError(
                        f"Capability '{capability}' requires one of these integrations: {required_services}"
                    )
        
        return True
    
    def validate_integrations(self) -> bool:
        """Validate that all integrations are properly configured."""
        for service_name, config in self.integrations.items():
            if config.service_name != service_name:
                raise ValueError(f"Integration key '{service_name}' doesn't match service_name '{config.service_name}'")
            
            # Check required scopes for known services
            required_scopes = {
                'gmail': ['gmail.readonly'] if 'email_monitoring' in self.capabilities else ['gmail.send'],
                'slack': ['chat:write'] if any(cap in self.capabilities for cap in ['alert_sending', 'notification_management']) else [],
                'twitter': ['tweet.read', 'tweet.write'] if 'social_media_posting' in self.capabilities else ['tweet.read']
            }
            
            if service_name in required_scopes and not config.scopes:
                raise ValueError(f"Integration '{service_name}' requires scopes: {required_scopes[service_name]}")
        
        return True
    
    def to_json(self) -> str:
        """Serialize agent spec to JSON."""
        return json.dumps(self.model_dump(mode='json'), indent=2, default=str)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'AgentSpec':
        """Deserialize agent spec from JSON with validation."""
        data = json.loads(json_str)
        return cls.model_validate(data)
    
    def get_version(self) -> Version:
        """Get semantic version object."""
        return Version(self.version)
    
    def increment_version(self, version_type: Literal["major", "minor", "patch"]) -> str:
        """Increment version and update timestamp."""
        current_version = self.get_version()
        
        if version_type == "major":
            new_version = current_version.next_major()
        elif version_type == "minor":
            new_version = current_version.next_minor()
        else:  # patch
            new_version = current_version.next_patch()
        
        self.version = str(new_version)
        self.updated_at = datetime.now(timezone.utc)
        
        return self.version
    
    def estimate_resource_usage(self) -> Dict[str, float]:
        """Estimate resource usage based on capabilities and configuration."""
        base_cpu = 0.5
        base_memory = 256
        
        # Capability-based scaling
        capability_weights = {
            'data_processing': (0.5, 128),
            'web_scraping': (0.3, 64),
            'file_backup': (0.2, 128),
            'email_monitoring': (0.1, 32),
            'social_media_posting': (0.1, 32),
            'report_generation': (0.4, 96),
            'data_analysis': (0.6, 256)
        }
        
        cpu_usage = base_cpu
        memory_usage = base_memory
        
        for capability in self.capabilities:
            if capability in capability_weights:
                cpu_add, memory_add = capability_weights[capability]
                cpu_usage += cpu_add
                memory_usage += memory_add
        
        # Integration overhead
        cpu_usage += len(self.integrations) * 0.1
        memory_usage += len(self.integrations) * 16
        
        # Trigger overhead
        trigger_overhead = {
            'time': (0.05, 8),
            'event': (0.1, 16),
            'manual': (0.02, 4)
        }
        
        for trigger in self.triggers:
            cpu_add, memory_add = trigger_overhead.get(trigger.trigger_type, (0, 0))
            cpu_usage += cpu_add
            memory_usage += memory_add
        
        return {
            'estimated_cpu': min(cpu_usage, self.resource_limits.cpu),
            'estimated_memory': min(memory_usage, self.resource_limits.memory),
            'efficiency_score': (cpu_usage + memory_usage/512) / len(self.capabilities) if self.capabilities else 1.0
        }
    
    def get_required_permissions(self) -> List[str]:
        """Get all required permissions/scopes across integrations."""
        all_scopes = []
        for integration in self.integrations.values():
            all_scopes.extend(integration.scopes)
        return list(set(all_scopes))
    
    def update_timestamp(self):
        """Update the updated_at timestamp."""
        self.updated_at = datetime.now(timezone.utc)


# Factory methods for common agent patterns

def create_monitor_agent(
    target: str, 
    frequency: int, 
    created_by: str,
    name: Optional[str] = None,
    notification_channels: Optional[List[str]] = None
) -> AgentSpec:
    """Create a monitoring agent for a specific target."""
    
    if not name:
        name = f"{target.title()} Monitor Agent"
    
    description = f"Monitors {target} every {frequency} minutes and sends alerts when conditions are met."
    
    capabilities = []
    integrations = {}
    
    # Determine capabilities and integrations based on target
    if target.lower() in ['email', 'gmail', 'inbox']:
        capabilities.extend(['email_monitoring', 'alert_sending'])
        integrations['gmail'] = IntegrationConfig(
            service_name='gmail',
            auth_type='oauth2',
            scopes=['gmail.readonly']
        )
    elif target.lower() in ['files', 'folder', 'directory']:
        capabilities.extend(['file_monitoring', 'alert_sending'])
        integrations['file_system'] = IntegrationConfig(
            service_name='file_system',
            auth_type='api_key',
            scopes=['read']
        )
    elif target.lower() in ['website', 'web', 'url']:
        capabilities.extend(['web_scraping', 'alert_sending'])
        integrations['http_api'] = IntegrationConfig(
            service_name='http_api',
            auth_type='api_key',
            scopes=['read']
        )
    
    # Add notification integrations
    if notification_channels:
        for channel in notification_channels:
            if channel.lower() == 'slack':
                integrations['slack'] = IntegrationConfig(
                    service_name='slack',
                    auth_type='oauth2',
                    scopes=['chat:write']
                )
            elif channel.lower() == 'email':
                capabilities.append('email_sending')
    
    return AgentSpec(
        name=name,
        description=description,
        capabilities=capabilities,
        triggers=[TimeTrigger(interval_minutes=frequency)],
        integrations=integrations,
        created_by=created_by,
        resource_limits=ResourceLimits(cpu=0.5, memory=256)
    )


def create_sync_agent(
    source: str, 
    destination: str, 
    created_by: str,
    schedule: str = "0 2 * * *",  # Daily at 2 AM
    name: Optional[str] = None
) -> AgentSpec:
    """Create a synchronization agent between two services."""
    
    if not name:
        source_clean = source.replace('_', ' ').title()
        dest_clean = destination.replace('_', ' ').title()
        name = f"{source_clean} to {dest_clean} Sync Agent"
    
    description = f"Automatically synchronizes data from {source} to {destination} on schedule."
    
    capabilities = ['file_sync', 'data_processing']
    integrations = {}
    
    # Configure source integration
    if source.lower() in ['google_drive', 'gdrive']:
        integrations['google_drive'] = IntegrationConfig(
            service_name='google_drive',
            auth_type='oauth2',
            scopes=['drive.readonly']
        )
    elif source.lower() in ['dropbox']:
        integrations['dropbox'] = IntegrationConfig(
            service_name='dropbox',
            auth_type='oauth2',
            scopes=['files.content.read']
        )
    
    # Configure destination integration
    if destination.lower() in ['aws_s3', 's3']:
        integrations['aws_s3'] = IntegrationConfig(
            service_name='aws_s3',
            auth_type='api_key',
            scopes=['s3:PutObject', 's3:PutObjectAcl']
        )
    elif destination.lower() in ['azure_blob']:
        integrations['azure_blob'] = IntegrationConfig(
            service_name='azure_blob',
            auth_type='api_key',
            scopes=['blob.write']
        )
    
    return AgentSpec(
        name=name,
        description=description,
        capabilities=capabilities,
        triggers=[TimeTrigger(cron_expression=schedule)],
        integrations=integrations,
        created_by=created_by,
        resource_limits=ResourceLimits(cpu=1.0, memory=512)
    )


def create_report_agent(
    data_source: str, 
    schedule: str,
    created_by: str,
    report_format: str = "pdf",
    name: Optional[str] = None
) -> AgentSpec:
    """Create a report generation agent."""
    
    if not name:
        source_clean = data_source.replace('_', ' ').title()
        name = f"{source_clean} Report Agent"
    
    description = f"Generates {report_format.upper()} reports from {data_source} data on schedule."
    
    capabilities = ['data_analysis', 'report_generation', 'email_sending']
    integrations = {}
    
    # Configure data source integration
    if data_source.lower() in ['database', 'db']:
        integrations['database'] = IntegrationConfig(
            service_name='database',
            auth_type='api_key',
            scopes=['read']
        )
    elif data_source.lower() in ['google_sheets', 'sheets']:
        integrations['google_drive'] = IntegrationConfig(
            service_name='google_drive',
            auth_type='oauth2',
            scopes=['spreadsheets.readonly']
        )
    elif data_source.lower() in ['airtable']:
        integrations['airtable'] = IntegrationConfig(
            service_name='airtable',
            auth_type='api_key',
            scopes=['base.read']
        )
    
    # Add email for report delivery
    integrations['gmail'] = IntegrationConfig(
        service_name='gmail',
        auth_type='oauth2',
        scopes=['gmail.send']
    )
    
    return AgentSpec(
        name=name,
        description=description,
        capabilities=capabilities,
        triggers=[TimeTrigger(cron_expression=schedule)],
        integrations=integrations,
        created_by=created_by,
        resource_limits=ResourceLimits(cpu=1.5, memory=768),
        outputs={
            'report_file': FieldSchema(
                field_name='report_file',
                field_type='string',
                required=True,
                description=f'Generated {report_format.upper()} report file path'
            ),
            'summary': FieldSchema(
                field_name='summary',
                field_type='string',
                required=True,
                description='Report summary and key metrics'
            )
        }
    )