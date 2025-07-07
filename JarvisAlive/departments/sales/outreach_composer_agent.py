"""Outreach Composer Agent for the Sales Department.

This agent creates personalized outreach emails and LinkedIn messages using LLM
capabilities. It integrates with lead data from the Scanner Agent and coordinates
with the Sales Department workflow.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from agent_builder.agent_spec import AgentSpec, TimeTrigger, ManualTrigger, IntegrationConfig, ResourceLimits


def create_outreach_composer_spec(session_id: str, config: Dict[str, Any] = None) -> AgentSpec:
    """
    Create an Outreach Composer Agent specification for the Sales Department.
    
    This agent generates personalized outreach content using LLM capabilities
    and sends emails/messages through various channels.
    
    Args:
        session_id: Session ID for the agent
        config: Optional configuration overrides
        
    Returns:
        AgentSpec: Complete agent specification
    """
    if config is None:
        config = {}
    
    # Default email templates
    default_templates = {
        "cold_outreach": {
            "subject_templates": [
                "Quick question about {company}'s {pain_point}",
                "Helping {company} with {solution_area}",
                "{name}, thoughts on {industry_trend}?",
                "5-minute conversation about {company}'s growth?"
            ],
            "message_templates": [
                "personalized_value_proposition",
                "industry_insight_opener", 
                "mutual_connection_reference",
                "company_news_reference"
            ]
        },
        "follow_up": {
            "subject_templates": [
                "Following up on my message to {name}",
                "Quick follow-up: {original_topic}",
                "Still interested in {solution_area}?"
            ],
            "message_templates": [
                "soft_follow_up",
                "value_add_follow_up",
                "breakup_email"
            ]
        },
        "meeting_request": {
            "subject_templates": [
                "15-minute call to discuss {topic}?",
                "Coffee chat about {company}'s {challenge}?",
                "Quick call next week?"
            ],
            "message_templates": [
                "direct_meeting_request",
                "calendar_link_share",
                "value_driven_meeting_ask"
            ]
        }
    }
    
    return AgentSpec(
        name="Outreach Composer Agent",
        description="Creates personalized outreach emails and LinkedIn messages using AI-powered content generation",
        capabilities=[
            "content_creation",
            "email_sending",
            "social_media_posting",
            "personalization",
            "template_management",
            "a_b_testing"
        ],
        triggers=[
            ManualTrigger(
                description="Triggered when new leads need outreach"
            ),
            TimeTrigger(
                interval_minutes=config.get("batch_processing_interval", 120),
                description="Process outreach queue every 2 hours"
            )
        ],
        integrations={
            "gmail": IntegrationConfig(
                service_name="gmail",
                auth_type="oauth2",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.readonly"
                ],
                config={
                    "api_version": "v1",
                    "batch_send": True
                }
            ),
            "linkedin": IntegrationConfig(
                service_name="linkedin",
                auth_type="oauth2",
                scopes=["w_member_social", "r_liteprofile"],
                config={
                    "message_limits": {
                        "daily": 20,
                        "weekly": 100
                    }
                }
            ),
            "anthropic": IntegrationConfig(
                service_name="anthropic",
                auth_type="api_key",
                config={
                    "model": "claude-3-5-sonnet-20241022",
                    "max_tokens": 1000,
                    "temperature": 0.3
                }
            ),
            "outreach_platform": IntegrationConfig(
                service_name="outreach_io",
                auth_type="api_key",
                config={
                    "sequences_enabled": True,
                    "analytics_tracking": True
                }
            )
        },
        created_by=session_id,
        config={
            "department_agent": True,
            "department": "sales",
            "agent_type": "outreach_composer",
            
            # Email configuration
            "email_templates": {**default_templates, **config.get("email_templates", {})},
            "sender_info": {
                "name": config.get("sender_name", "Sales Team"),
                "email": config.get("sender_email", "sales@company.com"),
                "signature": config.get("signature", "Best regards,\nSales Team"),
                "company": config.get("company_name", "Your Company")
            },
            
            # Personalization settings
            "personalization_fields": [
                "name", "company", "title", "industry", 
                "location", "mutual_connections", "recent_news",
                "pain_points", "company_size", "tech_stack"
            ],
            "research_depth": config.get("research_depth", "standard"),  # light, standard, deep
            "include_company_news": True,
            "include_mutual_connections": True,
            "include_social_proof": True,
            
            # Content generation
            "llm_config": {
                "model": "claude-3-5-sonnet-20241022",
                "temperature": 0.3,
                "max_tokens": 1000,
                "system_prompt": get_outreach_system_prompt()
            },
            "content_guidelines": {
                "tone": "professional_friendly",
                "length": "concise",  # concise, medium, detailed
                "include_value_prop": True,
                "include_call_to_action": True,
                "avoid_buzzwords": True
            },
            
            # A/B Testing
            "ab_testing": {
                "enabled": config.get("enable_ab_testing", True),
                "test_elements": ["subject_line", "opening", "call_to_action"],
                "min_sample_size": 20,
                "confidence_threshold": 0.95
            },
            
            # Sending limits and scheduling
            "sending_limits": {
                "daily_emails": config.get("daily_email_limit", 50),
                "daily_linkedin": config.get("daily_linkedin_limit", 20),
                "hourly_limit": config.get("hourly_limit", 10)
            },
            "sending_schedule": {
                "business_hours_only": True,
                "timezone": "America/Los_Angeles",
                "preferred_hours": ["09:00", "11:00", "14:00", "16:00"],
                "avoid_fridays": False,
                "avoid_mondays": False
            },
            
            # Quality control
            "quality_checks": {
                "spell_check": True,
                "grammar_check": True,
                "personalization_validation": True,
                "spam_score_check": True,
                "max_spam_score": 3.0
            },
            
            # Analytics and tracking
            "tracking": {
                "open_tracking": True,
                "click_tracking": True,
                "reply_tracking": True,
                "unsubscribe_tracking": True
            },
            
            # Department integration
            "lead_source": "lead_scanner_agent",
            "coordinate_with": ["meeting_scheduler_agent", "pipeline_tracker_agent"],
            "department_notifications": True,
            
            # Performance settings
            "batch_size": config.get("batch_size", 5),
            "processing_delay": 2,  # seconds between emails
            "retry_attempts": 3,
            "timeout_per_email": 30
        },
        resource_limits=ResourceLimits(
            memory_mb=1024,  # Higher for LLM processing
            cpu_cores=2,
            timeout=600,  # 10 minutes for batch processing
            network_requests_per_minute=60
        )
    )


def create_high_volume_outreach_spec(session_id: str) -> AgentSpec:
    """
    Create a high-volume Outreach Composer Agent for large-scale campaigns.
    
    Args:
        session_id: Session ID for the agent
        
    Returns:
        AgentSpec: High-volume agent specification
    """
    config = {
        "daily_email_limit": 200,
        "daily_linkedin_limit": 50,
        "batch_size": 20,
        "batch_processing_interval": 60,  # Every hour
        "enable_ab_testing": True,
        "research_depth": "light"  # Faster processing
    }
    
    return create_outreach_composer_spec(session_id, config)


def get_outreach_system_prompt() -> str:
    """
    Get the system prompt for LLM-powered outreach generation.
    
    Returns:
        str: System prompt for content generation
    """
    return """You are an expert sales outreach specialist creating personalized emails and LinkedIn messages.

Your role:
- Generate highly personalized, engaging outreach content
- Focus on value proposition and genuine interest in the prospect
- Avoid pushy sales language and generic templates
- Include specific references to the prospect's company and role
- Create compelling subject lines and clear calls-to-action

Guidelines:
1. Always personalize using available prospect data
2. Keep emails concise (under 150 words)
3. Lead with value, not with your product
4. Include one clear, specific call-to-action
5. Use a professional but friendly tone
6. Reference mutual connections or company news when available
7. Avoid superlatives and buzzwords
8. Make it feel like a human wrote it

Structure for cold outreach:
1. Personalized opening line
2. Brief value proposition or insight
3. Specific call-to-action
4. Professional closing

Structure for follow-ups:
1. Reference previous message
2. Add new value or insight
3. Simplified call-to-action
4. Graceful closing

Always maintain authenticity and focus on building genuine business relationships."""


def get_outreach_prompt_template() -> str:
    """
    Get the LLM prompt template for outreach composer code generation.
    
    Returns:
        str: Prompt template for code generation
    """
    return """
Generate Python code for an Outreach Composer Agent that creates personalized sales emails and LinkedIn messages.

The agent should:
1. Receive lead data from the Lead Scanner Agent
2. Research prospects using available data sources
3. Generate personalized outreach content using LLM
4. Send emails via Gmail and messages via LinkedIn
5. Track engagement and responses
6. Coordinate with other sales agents via message bus
7. Implement A/B testing for optimization

Key Requirements:
- Use async/await for all I/O operations
- Integrate with Claude/Anthropic API for content generation
- Implement proper rate limiting and sending schedules
- Include spam score checking and quality validation
- Support multiple templates and personalization levels
- Track opens, clicks, and replies
- Coordinate with department message bus
- Handle bounces and unsubscribes properly

The agent should generate:
- Personalized subject lines
- Email content with proper formatting
- LinkedIn message content
- Follow-up sequences
- A/B test variations

Include comprehensive error handling, logging, and integration with the Sales Department workflow.
"""


def get_sample_outreach_data() -> Dict[str, Any]:
    """
    Get sample outreach data structure for testing.
    
    Returns:
        Dict: Sample outreach data
    """
    return {
        "outreach_id": "outreach_12345",
        "lead_id": "lead_12345",
        "campaign_type": "cold_outreach",
        "channel": "email",
        "generated_content": {
            "subject": "Quick question about TechCorp's engineering growth",
            "body": """Hi Jane,

I noticed TechCorp recently announced your Series B funding - congratulations! 

With your engineering team likely growing rapidly, I wanted to share how we've helped similar VP Engineering leaders at companies like yours streamline their development workflows while scaling from 50 to 200+ engineers.

Would you be open to a 15-minute call next week to discuss some specific strategies that might be relevant to TechCorp's growth phase?

Best regards,
Sales Team""",
            "call_to_action": "15-minute call next week"
        },
        "personalization_data": {
            "name": "Jane",
            "company": "TechCorp",
            "title": "VP of Engineering",
            "recent_news": "Series B funding announcement",
            "company_size": "51-200",
            "pain_points": ["scaling engineering team", "development workflows"]
        },
        "ab_test_variant": "A",
        "quality_scores": {
            "personalization_score": 0.9,
            "spam_score": 1.2,
            "readability_score": 0.85,
            "call_to_action_clarity": 0.9
        },
        "scheduled_send_time": "2024-01-15T10:00:00Z",
        "tracking": {
            "opens": 0,
            "clicks": 0,
            "replies": 0,
            "bounced": False,
            "unsubscribed": False
        },
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat(),
        "department": "sales"
    }