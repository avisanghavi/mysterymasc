"""Lead Scanner Agent for the Sales Department.

This agent monitors LinkedIn, job boards, and company databases for potential leads
that match specific criteria. It integrates with the Sales Department workflow
to provide a continuous stream of qualified prospects.
"""

import json
from typing import Dict, List, Any
from datetime import datetime

from agent_builder.agent_spec import AgentSpec, TimeTrigger, IntegrationConfig, ResourceLimits


def create_lead_scanner_spec(session_id: str, config: Dict[str, Any] = None) -> AgentSpec:
    """
    Create a Lead Scanner Agent specification for the Sales Department.
    
    This agent monitors various sources for potential leads based on configurable
    criteria and feeds them into the sales pipeline.
    
    Args:
        session_id: Session ID for the agent
        config: Optional configuration overrides
        
    Returns:
        AgentSpec: Complete agent specification
    """
    if config is None:
        config = {}
    
    # Default search criteria
    default_criteria = {
        "titles": [
            "CEO", "Chief Executive Officer",
            "CTO", "Chief Technology Officer", 
            "VP Engineering", "VP of Engineering",
            "Head of Product", "Product Manager",
            "Founder", "Co-Founder"
        ],
        "company_sizes": ["11-50", "51-200", "201-500"],
        "industries": [
            "Software Development", "SaaS", "Technology",
            "Information Technology", "Computer Software",
            "Internet", "Fintech", "Startup"
        ],
        "locations": [
            "San Francisco Bay Area", "New York", "Los Angeles",
            "Austin", "Seattle", "Boston", "Remote", "United States"
        ],
        "exclude_keywords": [
            "student", "intern", "retired", "unemployed", "seeking"
        ]
    }
    
    # Merge with provided config
    search_criteria = {**default_criteria, **config.get("search_criteria", {})}
    
    return AgentSpec(
        name="Lead Scanner Agent",
        description="Monitors LinkedIn, job boards, and company databases for potential sales leads matching specified criteria",
        capabilities=[
            "web_scraping",
            "social_media_monitoring", 
            "data_processing",
            "lead_qualification",
            "api_integration"
        ],
        triggers=[
            TimeTrigger(
                interval_minutes=config.get("scan_frequency", 60),
                description="Hourly lead scanning"
            )
        ],
        integrations={
            "linkedin": IntegrationConfig(
                service_name="linkedin",
                auth_type="oauth2",
                scopes=["r_liteprofile", "r_emailaddress", "r_network"],
                config={
                    "api_version": "v2",
                    "rate_limit": "100_requests_per_hour"
                }
            ),
            "sales_navigator": IntegrationConfig(
                service_name="sales_navigator",
                auth_type="oauth2", 
                scopes=["lead_search", "profile_access"],
                config={
                    "premium_account": True,
                    "advanced_search": True
                }
            ),
            "company_database": IntegrationConfig(
                service_name="crunchbase",
                auth_type="api_key",
                config={
                    "api_version": "v4",
                    "endpoint": "https://api.crunchbase.com/api/v4/"
                }
            ),
            "job_boards": IntegrationConfig(
                service_name="job_boards",
                auth_type="scraping",
                config={
                    "sources": ["indeed", "glassdoor", "angellist"],
                    "respect_robots_txt": True
                }
            )
        },
        created_by=session_id,
        config={
            "department_agent": True,
            "department": "sales",
            "agent_type": "lead_scanner",
            
            # Search configuration
            "search_criteria": search_criteria,
            "max_leads_per_scan": config.get("max_leads_per_scan", 25),
            "lead_scoring_enabled": True,
            "duplicate_detection": True,
            
            # Lead scoring weights
            "scoring_weights": {
                "title_relevance": 0.3,
                "company_size": 0.2,
                "industry_match": 0.2,
                "location_preference": 0.1,
                "profile_completeness": 0.1,
                "recent_activity": 0.1
            },
            
            # Quality filters
            "minimum_score": config.get("minimum_score", 6.0),
            "require_email": True,
            "require_company": True,
            
            # Data enrichment
            "enrich_profiles": True,
            "find_email_addresses": True,
            "company_research": True,
            
            # Output configuration
            "output_format": "json",
            "include_metadata": True,
            "store_in_department_db": True,
            
            # Communication settings
            "notify_on_high_value_leads": True,
            "high_value_threshold": 8.5,
            "department_broadcast": True,
            
            # Performance settings
            "batch_size": 10,
            "concurrent_requests": 3,
            "retry_attempts": 3,
            "cache_results": True,
            "cache_duration_hours": 24
        },
        resource_limits=ResourceLimits(
            memory_mb=512,
            cpu_cores=1,
            timeout=300,  # 5 minutes
            network_requests_per_minute=100
        )
    )


def create_enhanced_lead_scanner_spec(
    session_id: str,
    target_profiles: List[str] = None,
    geographic_focus: List[str] = None,
    industry_focus: List[str] = None
) -> AgentSpec:
    """
    Create an enhanced Lead Scanner Agent with specific targeting.
    
    Args:
        session_id: Session ID for the agent
        target_profiles: Specific job titles/roles to target
        geographic_focus: Specific geographic regions to focus on
        industry_focus: Specific industries to target
        
    Returns:
        AgentSpec: Enhanced agent specification
    """
    config = {}
    
    if target_profiles:
        config["search_criteria"] = {"titles": target_profiles}
    
    if geographic_focus:
        if "search_criteria" not in config:
            config["search_criteria"] = {}
        config["search_criteria"]["locations"] = geographic_focus
    
    if industry_focus:
        if "search_criteria" not in config:
            config["search_criteria"] = {}
        config["search_criteria"]["industries"] = industry_focus
    
    # Enhanced configuration for better targeting
    config.update({
        "max_leads_per_scan": 50,
        "minimum_score": 7.0,
        "scan_frequency": 30  # Every 30 minutes
    })
    
    return create_lead_scanner_spec(session_id, config)


def get_lead_scanner_prompt_template() -> str:
    """
    Get the LLM prompt template for lead scanner code generation.
    
    Returns:
        str: Prompt template for code generation
    """
    return """
Generate Python code for a Lead Scanner Agent that monitors various sources for sales leads.

The agent should:
1. Connect to LinkedIn, Sales Navigator, and other sources
2. Search for profiles matching specified criteria
3. Score leads based on relevance and quality
4. Enrich profile data with additional information
5. Store qualified leads in the department database
6. Communicate with other sales agents via message bus

Key Requirements:
- Use async/await for all I/O operations
- Implement proper error handling and retries
- Respect rate limits and API quotas
- Include data validation and sanitization
- Support configurable search criteria
- Implement lead deduplication
- Calculate lead scores based on multiple factors
- Integration with department message bus for notifications

The agent should output structured lead data including:
- Contact information (name, email, phone)
- Professional details (title, company, industry)
- Lead score and qualification notes
- Source and discovery metadata
- Enrichment data (company size, recent news, etc.)

Include proper logging and monitoring for department coordination.
"""


def get_sample_lead_data() -> Dict[str, Any]:
    """
    Get sample lead data structure for testing.
    
    Returns:
        Dict: Sample lead data
    """
    return {
        "id": "lead_12345",
        "name": "Jane Smith",
        "email": "jane.smith@techcorp.com",
        "phone": "+1-555-0123",
        "title": "VP of Engineering",
        "company": "TechCorp Inc",
        "industry": "Software Development",
        "company_size": "51-200",
        "location": "San Francisco, CA",
        "linkedin_url": "https://linkedin.com/in/janesmith",
        "score": 8.5,
        "scoring_breakdown": {
            "title_relevance": 0.9,
            "company_size": 0.8,
            "industry_match": 0.9,
            "location_preference": 0.7,
            "profile_completeness": 0.8,
            "recent_activity": 0.6
        },
        "qualification_notes": [
            "High-value target: VP level at growing tech company",
            "Company in target industry (Software Development)",
            "Located in priority geographic region",
            "Active on LinkedIn with recent posts"
        ],
        "enrichment_data": {
            "company_funding": "$25M Series B",
            "company_growth": "50% YoY",
            "recent_news": "Company announced new product line",
            "tech_stack": ["Python", "React", "AWS"],
            "hiring_indicators": "Actively hiring engineers"
        },
        "source": "linkedin_search",
        "discovered_at": datetime.utcnow().isoformat(),
        "last_updated": datetime.utcnow().isoformat(),
        "status": "new",
        "department": "sales"
    }