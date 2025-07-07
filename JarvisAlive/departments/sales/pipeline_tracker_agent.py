"""Pipeline Tracker Agent for the Sales Department.

This agent monitors CRM systems and tracks sales pipeline progress, providing
insights and alerts for deal progression and potential pipeline risks.
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from agent_builder.agent_spec import AgentSpec, TimeTrigger, ManualTrigger, IntegrationConfig, ResourceLimits


def create_pipeline_tracker_spec(session_id: str, config: Dict[str, Any] = None) -> AgentSpec:
    """
    Create a Pipeline Tracker Agent specification for the Sales Department.
    
    This agent monitors CRM systems and tracks deal progression through the sales pipeline.
    
    Args:
        session_id: Session ID for the agent
        config: Optional configuration overrides
        
    Returns:
        AgentSpec: Complete agent specification
    """
    if config is None:
        config = {}
    
    # Default pipeline stages
    default_pipeline_stages = [
        "lead",
        "qualified", 
        "meeting_scheduled",
        "demo_completed",
        "proposal_sent",
        "negotiation",
        "closed_won",
        "closed_lost"
    ]
    
    # Default alert thresholds
    default_alert_thresholds = {
        "stale_lead_days": 7,
        "stale_prospect_days": 14,
        "stale_negotiation_days": 30,
        "pipeline_drop_percentage": 20,
        "conversion_rate_drop": 0.05,
        "deal_value_change": 0.25,
        "activity_gap_days": 5
    }
    
    return AgentSpec(
        name="Pipeline Tracker Agent",
        description="Monitors CRM systems and tracks sales pipeline progress with real-time insights and alerts",
        capabilities=[
            "data_processing",
            "crm_integration",
            "report_generation", 
            "alert_sending",
            "analytics_computation",
            "trend_analysis"
        ],
        triggers=[
            TimeTrigger(
                interval_minutes=config.get("tracking_frequency", 30),
                description="Monitor pipeline changes every 30 minutes"
            ),
            TimeTrigger(
                interval_minutes=config.get("report_frequency", 1440),  # Daily
                description="Generate daily pipeline reports"
            ),
            ManualTrigger(
                description="Triggered for on-demand pipeline analysis"
            )
        ],
        integrations={
            "salesforce": IntegrationConfig(
                service_name="salesforce",
                auth_type="oauth2",
                scopes=["full", "refresh_token"],
                config={
                    "api_version": "v57.0",
                    "sandbox": config.get("use_sandbox", False),
                    "bulk_api_enabled": True
                }
            ),
            "hubspot": IntegrationConfig(
                service_name="hubspot",
                auth_type="oauth2",
                scopes=["contacts", "deals", "timeline"],
                config={
                    "api_version": "v3",
                    "properties_to_fetch": [
                        "dealname", "amount", "dealstage", "closedate",
                        "createdate", "hs_lastmodifieddate", "pipeline"
                    ]
                }
            ),
            "pipedrive": IntegrationConfig(
                service_name="pipedrive",
                auth_type="api_key",
                config={
                    "api_version": "v1",
                    "company_domain": config.get("pipedrive_domain", "company")
                }
            ),
            "slack": IntegrationConfig(
                service_name="slack",
                auth_type="oauth2",
                scopes=["chat:write", "channels:read"],
                config={
                    "notification_channel": config.get("slack_channel", "#sales-alerts"),
                    "mention_on_critical": True
                }
            ),
            "email": IntegrationConfig(
                service_name="gmail",
                auth_type="oauth2",
                scopes=[
                    "https://www.googleapis.com/auth/gmail.send"
                ],
                config={
                    "send_reports": True,
                    "report_recipients": config.get("report_recipients", [])
                }
            ),
            "analytics": IntegrationConfig(
                service_name="custom_analytics",
                auth_type="internal",
                config={
                    "enable_forecasting": True,
                    "trend_analysis_window": 30,  # days
                    "predictive_modeling": config.get("enable_predictions", True)
                }
            )
        },
        created_by=session_id,
        config={
            "department_agent": True,
            "department": "sales",
            "agent_type": "pipeline_tracker",
            
            # Pipeline configuration
            "pipeline_stages": {**dict(enumerate(default_pipeline_stages)), **config.get("pipeline_stages", {})},
            "stage_progression_rules": {
                "lead": ["qualified", "closed_lost"],
                "qualified": ["meeting_scheduled", "closed_lost"],
                "meeting_scheduled": ["demo_completed", "closed_lost"],
                "demo_completed": ["proposal_sent", "closed_lost"],
                "proposal_sent": ["negotiation", "closed_lost"],
                "negotiation": ["closed_won", "closed_lost"]
            },
            "required_fields_by_stage": {
                "qualified": ["contact_info", "budget_range", "timeline"],
                "proposal_sent": ["proposal_value", "decision_maker"],
                "negotiation": ["close_date", "final_value"]
            },
            
            # Tracking and monitoring
            "tracking_frequency": config.get("tracking_frequency", 30),  # minutes
            "alert_thresholds": {**default_alert_thresholds, **config.get("alert_thresholds", {})},
            "data_retention_days": config.get("data_retention_days", 365),
            
            # Metrics and KPIs
            "key_metrics": [
                "pipeline_value",
                "pipeline_velocity",
                "conversion_rate_by_stage",
                "average_deal_size",
                "sales_cycle_length",
                "win_rate",
                "activity_volume",
                "pipeline_coverage"
            ],
            "benchmark_targets": {
                "win_rate": config.get("target_win_rate", 0.20),
                "average_cycle_days": config.get("target_cycle_days", 45),
                "pipeline_coverage": config.get("target_coverage", 3.0),
                "stage_conversion_rates": {
                    "lead_to_qualified": 0.30,
                    "qualified_to_meeting": 0.50,
                    "meeting_to_demo": 0.70,
                    "demo_to_proposal": 0.60,
                    "proposal_to_negotiation": 0.40,
                    "negotiation_to_close": 0.50
                }
            },
            
            # Reporting configuration
            "report_schedule": config.get("report_schedule", "daily"),
            "report_types": {
                "daily_summary": True,
                "weekly_trends": True,
                "monthly_forecast": True,
                "quarterly_review": True
            },
            "report_distribution": {
                "sales_team": True,
                "management": True,
                "individual_reps": config.get("individual_reports", True)
            },
            
            # Alert configuration
            "alert_channels": ["slack", "email"],
            "alert_types": {
                "stale_deals": True,
                "pipeline_drops": True,
                "conversion_anomalies": True,
                "high_value_opportunities": True,
                "at_risk_deals": True
            },
            "alert_priorities": {
                "critical": ["pipeline_drops", "high_value_at_risk"],
                "high": ["stale_deals", "conversion_anomalies"],
                "medium": ["activity_gaps", "forecast_changes"],
                "low": ["general_updates", "milestone_achievements"]
            },
            
            # Data analysis
            "analysis_features": {
                "trend_detection": True,
                "anomaly_detection": True,
                "forecasting": True,
                "cohort_analysis": True,
                "attribution_modeling": True
            },
            "forecasting_models": {
                "linear_regression": True,
                "moving_average": True,
                "exponential_smoothing": True,
                "confidence_intervals": True
            },
            
            # Integration settings
            "crm_sync_frequency": config.get("crm_sync_minutes", 15),
            "data_validation": {
                "required_fields_check": True,
                "data_quality_scoring": True,
                "duplicate_detection": True,
                "consistency_validation": True
            },
            
            # Performance optimization
            "caching_enabled": True,
            "cache_duration_minutes": 30,
            "batch_processing": True,
            "parallel_processing": True,
            "incremental_sync": True,
            
            # Department integration
            "coordinate_with": [
                "lead_scanner_agent",
                "outreach_composer_agent", 
                "meeting_scheduler_agent"
            ],
            "department_notifications": True,
            "pipeline_broadcast": True,
            "metric_sharing": True,
            
            # Quality assurance
            "data_validation_rules": {
                "deal_value_range": {"min": 1000, "max": 1000000},
                "probability_range": {"min": 0, "max": 100},
                "date_consistency": True,
                "stage_progression_validation": True
            },
            "audit_logging": True,
            "change_tracking": True,
            
            # Customization options
            "custom_fields": config.get("custom_fields", []),
            "custom_stages": config.get("custom_stages", []),
            "custom_metrics": config.get("custom_metrics", []),
            "dashboard_widgets": [
                "pipeline_overview",
                "conversion_funnel",
                "trending_metrics",
                "forecast_accuracy",
                "individual_performance"
            ]
        },
        resource_limits=ResourceLimits(
            memory_mb=1024,  # Higher for data processing
            cpu_cores=2,
            timeout=600,  # 10 minutes for complex analysis
            network_requests_per_minute=180
        )
    )


def create_enterprise_pipeline_tracker_spec(session_id: str) -> AgentSpec:
    """
    Create an enterprise-grade Pipeline Tracker Agent for large sales organizations.
    
    Args:
        session_id: Session ID for the agent
        
    Returns:
        AgentSpec: Enterprise pipeline tracker specification
    """
    config = {
        "tracking_frequency": 15,  # Every 15 minutes
        "report_frequency": 720,  # Every 12 hours
        "crm_sync_minutes": 10,
        "data_retention_days": 1095,  # 3 years
        "use_sandbox": False,
        "enable_predictions": True,
        "individual_reports": True,
        "alert_thresholds": {
            "stale_lead_days": 3,
            "stale_prospect_days": 7,
            "stale_negotiation_days": 14,
            "pipeline_drop_percentage": 10,
            "conversion_rate_drop": 0.03
        },
        "target_win_rate": 0.25,
        "target_cycle_days": 35,
        "target_coverage": 4.0
    }
    
    return create_pipeline_tracker_spec(session_id, config)


def get_pipeline_tracker_prompt_template() -> str:
    """
    Get the LLM prompt template for pipeline tracker code generation.
    
    Returns:
        str: Prompt template for code generation
    """
    return """
Generate Python code for a Pipeline Tracker Agent that monitors and analyzes sales pipeline data.

The agent should:
1. Connect to CRM systems (Salesforce, HubSpot, Pipedrive)
2. Monitor deal progression through pipeline stages
3. Calculate key sales metrics and KPIs
4. Detect anomalies and potential issues
5. Generate automated reports and alerts
6. Provide forecasting and trend analysis
7. Coordinate with other sales agents via message bus

Key Requirements:
- Use async/await for all I/O operations
- Implement robust error handling and retries
- Support multiple CRM platforms with unified data model
- Calculate pipeline velocity and conversion rates
- Detect stale deals and pipeline risks
- Generate actionable insights and recommendations
- Send alerts via Slack and email
- Maintain data quality and validation
- Support real-time and batch processing

The agent should track:
- Deal progression through stages
- Pipeline value and velocity
- Conversion rates at each stage
- Sales cycle length and trends
- Win/loss ratios and analysis
- Activity levels and engagement
- Forecast accuracy and adjustments
- Individual and team performance

Analytics capabilities:
- Trend detection and forecasting
- Anomaly detection for pipeline health
- Cohort analysis for deal progression
- Attribution modeling for lead sources
- Predictive modeling for deal outcomes

Include comprehensive logging, monitoring, and integration with the Sales Department workflow.
"""


def get_sample_pipeline_data() -> Dict[str, Any]:
    """
    Get sample pipeline data structure for testing.
    
    Returns:
        Dict: Sample pipeline data
    """
    return {
        "pipeline_snapshot": {
            "snapshot_id": "pipeline_snapshot_12345",
            "timestamp": datetime.utcnow().isoformat(),
            "total_deals": 45,
            "total_pipeline_value": 1250000,
            "weighted_pipeline_value": 375000,
            "deals_by_stage": {
                "lead": {"count": 12, "value": 180000},
                "qualified": {"count": 8, "value": 240000},
                "meeting_scheduled": {"count": 6, "value": 180000},
                "demo_completed": {"count": 5, "value": 200000},
                "proposal_sent": {"count": 4, "value": 160000},
                "negotiation": {"count": 3, "value": 150000},
                "closed_won": {"count": 2, "value": 80000},
                "closed_lost": {"count": 5, "value": 60000}
            },
            "conversion_rates": {
                "lead_to_qualified": 0.35,
                "qualified_to_meeting": 0.60,
                "meeting_to_demo": 0.75,
                "demo_to_proposal": 0.65,
                "proposal_to_negotiation": 0.50,
                "negotiation_to_close": 0.55
            },
            "pipeline_velocity": {
                "average_days_by_stage": {
                    "lead": 5.2,
                    "qualified": 8.5,
                    "meeting_scheduled": 3.1,
                    "demo_completed": 7.8,
                    "proposal_sent": 12.3,
                    "negotiation": 18.7
                },
                "overall_cycle_length": 55.6
            }
        },
        "alerts": [
            {
                "alert_id": "alert_001",
                "type": "stale_deal",
                "priority": "high",
                "deal_id": "deal_12345",
                "deal_name": "TechCorp Enterprise Solution",
                "days_stale": 21,
                "stage": "negotiation",
                "value": 50000,
                "owner": "sales_rep_1",
                "message": "Deal has been in negotiation stage for 21 days without activity"
            },
            {
                "alert_id": "alert_002", 
                "type": "pipeline_drop",
                "priority": "critical",
                "metric": "qualified_leads",
                "change_percentage": -25,
                "timeframe": "last_7_days",
                "message": "Qualified leads dropped 25% in the last 7 days"
            }
        ],
        "metrics": {
            "win_rate": 0.22,
            "average_deal_size": 27777,
            "sales_cycle_length": 55.6,
            "pipeline_coverage": 3.2,
            "forecast_accuracy": 0.85,
            "activity_volume": {
                "calls": 45,
                "emails": 89,
                "meetings": 12,
                "demos": 8
            }
        },
        "forecast": {
            "current_quarter": {
                "target": 500000,
                "forecast": 425000,
                "confidence": 0.78,
                "likely_closes": [
                    {"deal_id": "deal_001", "value": 75000, "probability": 0.85},
                    {"deal_id": "deal_002", "value": 50000, "probability": 0.70}
                ]
            },
            "next_quarter": {
                "target": 600000,
                "forecast": 380000,
                "confidence": 0.62
            }
        },
        "recommendations": [
            "Focus on moving 3 deals out of negotiation stage - they represent $150K in pipeline value",
            "Increase qualified lead generation - current rate is 25% below target",
            "Schedule follow-up activities for 8 stale deals in qualified stage",
            "Review pricing strategy for deals in proposal stage - conversion rate is below benchmark"
        ],
        "department": "sales",
        "generated_at": datetime.utcnow().isoformat()
    }


def get_pipeline_stage_definitions() -> Dict[str, Dict[str, Any]]:
    """
    Get standard pipeline stage definitions and requirements.
    
    Returns:
        Dict: Pipeline stage definitions
    """
    return {
        "lead": {
            "description": "Initial contact or inquiry",
            "required_fields": ["contact_info", "company"],
            "typical_duration_days": 3,
            "next_stages": ["qualified", "closed_lost"],
            "activities": ["research", "initial_contact"]
        },
        "qualified": {
            "description": "Lead has been qualified based on BANT criteria",
            "required_fields": ["budget_range", "authority", "need", "timeline"],
            "typical_duration_days": 7,
            "next_stages": ["meeting_scheduled", "closed_lost"],
            "activities": ["discovery_call", "needs_assessment"]
        },
        "meeting_scheduled": {
            "description": "Initial meeting or demo scheduled",
            "required_fields": ["meeting_date", "attendees"],
            "typical_duration_days": 2,
            "next_stages": ["demo_completed", "closed_lost"],
            "activities": ["calendar_coordination", "meeting_preparation"]
        },
        "demo_completed": {
            "description": "Product demonstration completed",
            "required_fields": ["demo_outcome", "next_steps"],
            "typical_duration_days": 5,
            "next_stages": ["proposal_sent", "closed_lost"],
            "activities": ["demo_delivery", "follow_up"]
        },
        "proposal_sent": {
            "description": "Formal proposal or quote sent",
            "required_fields": ["proposal_value", "proposal_date"],
            "typical_duration_days": 10,
            "next_stages": ["negotiation", "closed_lost"],
            "activities": ["proposal_creation", "proposal_review"]
        },
        "negotiation": {
            "description": "Terms and pricing negotiation",
            "required_fields": ["negotiation_points", "decision_timeline"],
            "typical_duration_days": 15,
            "next_stages": ["closed_won", "closed_lost"],
            "activities": ["terms_negotiation", "stakeholder_alignment"]
        },
        "closed_won": {
            "description": "Deal successfully closed",
            "required_fields": ["close_date", "final_value", "contract_details"],
            "typical_duration_days": 0,
            "next_stages": [],
            "activities": ["contract_signing", "onboarding_handoff"]
        },
        "closed_lost": {
            "description": "Deal lost or abandoned",
            "required_fields": ["loss_reason", "close_date"],
            "typical_duration_days": 0,
            "next_stages": [],
            "activities": ["loss_analysis", "relationship_maintenance"]
        }
    }