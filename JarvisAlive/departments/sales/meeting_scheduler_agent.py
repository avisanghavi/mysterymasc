"""Meeting Scheduler Agent for the Sales Department.

This agent handles calendar coordination and meeting scheduling with prospects.
It integrates with calendar systems and coordinates with other sales agents.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from agent_builder.agent_spec import AgentSpec, TimeTrigger, ManualTrigger, IntegrationConfig, ResourceLimits


def create_meeting_scheduler_spec(session_id: str, config: Dict[str, Any] = None) -> AgentSpec:
    """
    Create a Meeting Scheduler Agent specification for the Sales Department.
    
    This agent coordinates meeting scheduling and calendar management for sales activities.
    
    Args:
        session_id: Session ID for the agent
        config: Optional configuration overrides
        
    Returns:
        AgentSpec: Complete agent specification
    """
    if config is None:
        config = {}
    
    # Default availability windows
    default_availability = {
        "monday": ["09:00-17:00"],
        "tuesday": ["09:00-17:00"], 
        "wednesday": ["09:00-17:00"],
        "thursday": ["09:00-17:00"],
        "friday": ["09:00-15:00"],
        "saturday": [],
        "sunday": []
    }
    
    # Default meeting types
    default_meeting_types = {
        "discovery_call": {
            "duration": 30,
            "buffer_before": 15,
            "buffer_after": 15,
            "description": "Initial discovery and qualification call"
        },
        "demo": {
            "duration": 45,
            "buffer_before": 15,
            "buffer_after": 15,
            "description": "Product demonstration"
        },
        "proposal_review": {
            "duration": 60,
            "buffer_before": 30,
            "buffer_after": 30,
            "description": "Proposal discussion and review"
        },
        "follow_up": {
            "duration": 25,
            "buffer_before": 10,
            "buffer_after": 10,
            "description": "Follow-up discussion"
        }
    }
    
    return AgentSpec(
        name="Meeting Scheduler Agent",
        description="Coordinates meeting scheduling and calendar management for sales activities",
        capabilities=[
            "calendar_management",
            "scheduling_coordination",
            "email_sending",
            "notification_management",
            "timezone_handling"
        ],
        triggers=[
            ManualTrigger(
                description="Triggered when meeting scheduling is requested"
            ),
            TimeTrigger(
                interval_minutes=config.get("reminder_check_interval", 30),
                description="Check for upcoming meetings and send reminders"
            )
        ],
        integrations={
            "google_calendar": IntegrationConfig(
                service_name="google_calendar",
                auth_type="oauth2",
                scopes=[
                    "https://www.googleapis.com/auth/calendar",
                    "https://www.googleapis.com/auth/calendar.events"
                ],
                config={
                    "api_version": "v3",
                    "calendar_id": config.get("primary_calendar_id", "primary")
                }
            ),
            "calendly": IntegrationConfig(
                service_name="calendly",
                auth_type="oauth2",
                scopes=["read", "write"],
                config={
                    "webhook_enabled": True,
                    "auto_confirm": True
                }
            ),
            "zoom": IntegrationConfig(
                service_name="zoom",
                auth_type="oauth2",
                scopes=["meeting:write", "meeting:read"],
                config={
                    "auto_generate_links": True,
                    "waiting_room": False,
                    "record_meetings": config.get("record_meetings", False)
                }
            ),
            "gmail": IntegrationConfig(
                service_name="gmail",
                auth_type="oauth2",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.send",
                    "https://www.googleapis.com/auth/gmail.readonly"
                ],
                config={
                    "send_confirmations": True,
                    "send_reminders": True
                }
            ),
            "outlook": IntegrationConfig(
                service_name="outlook",
                auth_type="oauth2",
                scopes=["Calendar.ReadWrite", "Mail.Send"],
                config={
                    "graph_api_version": "v1.0"
                }
            )
        },
        created_by=session_id,
        config={
            "department_agent": True,
            "department": "sales",
            "agent_type": "meeting_scheduler",
            
            # Calendar configuration
            "availability_windows": {**default_availability, **config.get("availability_windows", {})},
            "timezone": config.get("timezone", "America/Los_Angeles"),
            "business_hours_only": config.get("business_hours_only", True),
            "minimum_advance_booking": config.get("minimum_advance_hours", 24),  # hours
            "maximum_advance_booking": config.get("maximum_advance_days", 60),  # days
            
            # Meeting types and durations
            "meeting_types": {**default_meeting_types, **config.get("meeting_types", {})},
            "default_meeting_type": "discovery_call",
            "auto_confirm_meetings": config.get("auto_confirm", True),
            
            # Scheduling preferences
            "preferred_meeting_times": [
                "10:00", "11:00", "14:00", "15:00", "16:00"
            ],
            "avoid_back_to_back": True,
            "lunch_break": {"start": "12:00", "end": "13:00"},
            "end_of_day_buffer": 60,  # minutes before end of day
            
            # Reminder settings
            "reminders": {
                "email_24h": True,
                "email_2h": True,
                "email_15m": False,
                "sms_1h": config.get("sms_reminders", False)
            },
            "reminder_templates": {
                "24h": "Meeting reminder: {meeting_type} tomorrow at {time}",
                "2h": "Meeting reminder: {meeting_type} in 2 hours",
                "15m": "Meeting starting in 15 minutes"
            },
            
            # Meeting link generation
            "video_conferencing": {
                "default_provider": config.get("video_provider", "zoom"),
                "auto_generate_links": True,
                "include_dial_in": True,
                "waiting_room_enabled": False
            },
            
            # Conflict resolution
            "conflict_resolution": {
                "suggest_alternatives": True,
                "alternative_count": 3,
                "reschedule_automatically": False,
                "notify_on_conflicts": True
            },
            
            # Integration with other agents
            "coordinate_with": [
                "outreach_composer_agent",
                "pipeline_tracker_agent"
            ],
            "notify_on_scheduling": True,
            "update_crm": True,
            
            # Attendee management
            "attendee_limits": {
                "discovery_call": 3,
                "demo": 5,
                "proposal_review": 4
            },
            "require_attendee_confirmation": True,
            "track_no_shows": True,
            
            # Quality settings
            "validate_email_addresses": True,
            "prevent_double_booking": True,
            "timezone_detection": True,
            "calendar_sync_interval": 15,  # minutes
            
            # Analytics and reporting
            "track_metrics": {
                "scheduling_success_rate": True,
                "no_show_rate": True,
                "reschedule_rate": True,
                "average_booking_time": True
            },
            
            # Department integration
            "department_notifications": True,
            "broadcast_scheduled_meetings": True,
            "pipeline_integration": True
        },
        resource_limits=ResourceLimits(
            memory_mb=512,
            cpu_cores=1,
            timeout=180,  # 3 minutes
            network_requests_per_minute=120
        )
    )


def create_high_volume_scheduler_spec(session_id: str) -> AgentSpec:
    """
    Create a high-volume Meeting Scheduler Agent for busy sales teams.
    
    Args:
        session_id: Session ID for the agent
        
    Returns:
        AgentSpec: High-volume scheduler specification
    """
    config = {
        "auto_confirm": True,
        "reminder_check_interval": 15,  # Check every 15 minutes
        "business_hours_only": False,  # More flexibility
        "minimum_advance_hours": 4,  # Shorter advance booking
        "video_provider": "zoom",
        "record_meetings": True
    }
    
    return create_meeting_scheduler_spec(session_id, config)


def get_scheduler_prompt_template() -> str:
    """
    Get the LLM prompt template for meeting scheduler code generation.
    
    Returns:
        str: Prompt template for code generation
    """
    return """
Generate Python code for a Meeting Scheduler Agent that coordinates calendar management and meeting scheduling.

The agent should:
1. Integrate with Google Calendar, Calendly, and other calendar systems
2. Handle meeting requests from outreach responses
3. Find available time slots based on preferences
4. Generate and send meeting invitations
5. Create video conference links automatically
6. Send reminders before meetings
7. Handle rescheduling and cancellations
8. Track no-shows and meeting outcomes
9. Coordinate with other sales agents via message bus

Key Requirements:
- Use async/await for all calendar operations
- Handle multiple timezone calculations
- Implement proper conflict detection
- Support various meeting types with different durations
- Generate professional meeting invitations
- Include video conferencing links
- Send automated reminders
- Track scheduling metrics
- Integrate with CRM for pipeline updates

The agent should handle:
- Availability checking across multiple calendars
- Meeting invitation generation with proper formatting
- Automatic video link creation (Zoom, Google Meet, etc.)
- Reminder scheduling and delivery
- Reschedule request processing
- No-show tracking and follow-up
- Calendar synchronization

Include comprehensive error handling, timezone management, and integration with the Sales Department workflow.
"""


def get_sample_meeting_data() -> Dict[str, Any]:
    """
    Get sample meeting data structure for testing.
    
    Returns:
        Dict: Sample meeting data
    """
    return {
        "meeting_id": "meeting_12345",
        "prospect_id": "lead_12345",
        "meeting_type": "discovery_call",
        "scheduled_time": "2024-01-20T10:00:00-08:00",
        "duration": 30,
        "timezone": "America/Los_Angeles",
        "attendees": [
            {
                "name": "Jane Smith",
                "email": "jane.smith@techcorp.com",
                "role": "prospect",
                "confirmed": True
            },
            {
                "name": "Sales Rep",
                "email": "sales@company.com", 
                "role": "host",
                "confirmed": True
            }
        ],
        "meeting_details": {
            "title": "Discovery Call - TechCorp",
            "description": "Initial discovery call to understand TechCorp's engineering challenges and explore potential solutions.",
            "location": "Video Conference",
            "video_link": "https://zoom.us/j/123456789",
            "calendar_link": "https://calendar.google.com/event?eid=abc123"
        },
        "reminders": {
            "24h_sent": False,
            "2h_sent": False,
            "15m_sent": False
        },
        "status": "scheduled",
        "created_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
        "notes": "Prospect interested in engineering workflow solutions",
        "follow_up_required": True,
        "department": "sales"
    }