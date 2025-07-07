"""Sales Department implementation for autonomous sales operations.

This department coordinates multiple micro-agents to handle the complete
sales pipeline from lead generation through deal closure.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass

# Import base department infrastructure
from ..base_department import Department, DepartmentOrchestrator
from agent_builder.agent_spec import (
    create_monitor_agent, 
    create_sync_agent,
    AgentSpec as PydanticAgentSpec,
    TimeTrigger,
    ManualTrigger,
    IntegrationConfig
)

logger = logging.getLogger(__name__)


@dataclass
class Lead:
    """Represents a sales lead."""
    id: str
    name: str
    email: str
    company: str
    title: str
    source: str
    score: float
    created_at: datetime
    status: str = "new"
    contact_attempts: int = 0
    last_contacted: Optional[datetime] = None
    notes: List[str] = None
    
    def __post_init__(self):
        if self.notes is None:
            self.notes = []


@dataclass
class Prospect:
    """Represents a qualified sales prospect."""
    lead: Lead
    qualification_score: float
    pain_points: List[str]
    budget_range: Optional[str]
    timeline: Optional[str]
    decision_maker: bool
    next_action: str
    meeting_scheduled: bool = False


class SalesDepartment(Department):
    """
    Sales Department coordinating micro-agents for autonomous sales operations.
    
    This department manages the complete sales pipeline:
    1. Lead generation and scanning
    2. Outreach and nurturing
    3. Meeting scheduling
    4. Pipeline tracking and reporting
    """
    
    def __init__(
        self, 
        redis_client, 
        session_id: str,
        message_bus=None,
        sandbox_manager=None
    ):
        """
        Initialize Sales Department.
        
        Args:
            redis_client: Redis client for state management
            session_id: Session ID for this department instance
            message_bus: Message bus for agent communication
            sandbox_manager: Sandbox manager for safe agent execution
        """
        super().__init__(
            name="Sales",
            description="Autonomous sales operations and pipeline management",
            redis_client=redis_client,
            message_bus=message_bus,
            sandbox_manager=sandbox_manager
        )
        
        self.session_id = session_id
        
        # Sales-specific state
        self.leads_database: Dict[str, Lead] = {}
        self.prospects_pipeline: Dict[str, Prospect] = {}
        self.meetings_scheduled: List[Dict[str, Any]] = []
        self.sales_targets = {
            "monthly_leads": 100,
            "monthly_meetings": 20,
            "monthly_pipeline_value": 50000,
            "target_conversion_rate": 0.15
        }
        
        # Business metrics that this department affects
        self.business_metrics = [
            "leads_generated",
            "meetings_booked", 
            "pipeline_value",
            "conversion_rate",
            "cost_per_lead",
            "sales_cycle_length",
            "win_rate",
            "revenue_generated"
        ]
        
        # Lead scoring criteria
        self.lead_scoring_criteria = {
            "title_keywords": ["ceo", "cto", "vp", "director", "manager", "head"],
            "company_size_bonus": {"startup": 5, "enterprise": 10, "mid-market": 8},
            "industry_match": ["saas", "technology", "software", "fintech"],
            "engagement_bonus": 15  # Bonus for engagement activities
        }
        
        logger.info(f"Sales Department initialized for session {session_id}")
    
    async def initialize_agents(self) -> bool:
        """
        Create and configure the four specialized micro-agents for sales operations.
        
        Returns:
            bool: True if all agents initialized successfully
        """
        try:
            logger.info("Initializing Sales Department micro-agents")
            
            # 1. Lead Scanner Agent - Monitors LinkedIn and other sources for leads
            lead_scanner = create_monitor_agent(
                target="linkedin",
                frequency=60,  # Check every hour
                created_by=self.session_id,
                name="LeadScannerAgent"
            )
            
            # Enhance with sales-specific configuration
            lead_scanner_spec = {
                "name": "LeadScannerAgent",
                "description": "Monitors LinkedIn, job boards, and company databases for potential leads",
                "capabilities": [
                    "social_media_monitoring",
                    "web_scraping", 
                    "lead_qualification",
                    "data_processing"
                ],
                "integrations": ["linkedin", "sales_navigator", "company_database"],
                "code": None,
                "config": {
                    "id": lead_scanner.id,
                    "version": lead_scanner.version,
                    "pydantic_spec": lead_scanner.to_json(),
                    "search_criteria": {
                        "titles": ["CEO", "CTO", "VP Engineering", "Head of Product"],
                        "company_sizes": ["11-50", "51-200", "201-500"],
                        "industries": ["Software", "SaaS", "Technology"],
                        "locations": ["San Francisco", "New York", "Remote"]
                    },
                    "scan_frequency": 60,
                    "max_leads_per_scan": 25
                }
            }
            
            # 2. Outreach Composer Agent - Creates personalized emails and messages
            outreach_composer_spec = {
                "name": "OutreachComposerAgent", 
                "description": "Creates personalized outreach emails and LinkedIn messages",
                "capabilities": [
                    "content_creation",
                    "email_sending",
                    "personalization",
                    "template_management"
                ],
                "integrations": ["gmail", "linkedin", "outreach_platform"],
                "code": None,
                "config": {
                    "email_templates": {
                        "cold_outreach": "cold_email_template_v1",
                        "follow_up": "follow_up_template_v1", 
                        "meeting_request": "meeting_request_template_v1"
                    },
                    "personalization_fields": [
                        "name", "company", "title", "industry", "recent_news"
                    ],
                    "sending_limits": {
                        "daily_emails": 50,
                        "daily_linkedin": 20
                    },
                    "a_b_testing": True
                }
            }
            
            # 3. Meeting Scheduler Agent - Handles calendar coordination
            meeting_scheduler_spec = {
                "name": "MeetingSchedulerAgent",
                "description": "Coordinates meeting scheduling and calendar management",
                "capabilities": [
                    "calendar_management",
                    "scheduling_coordination",
                    "email_sending",
                    "notification_management"
                ],
                "integrations": ["google_calendar", "calendly", "zoom", "gmail"],
                "code": None,
                "config": {
                    "availability_windows": {
                        "monday": ["09:00-17:00"],
                        "tuesday": ["09:00-17:00"],
                        "wednesday": ["09:00-17:00"],
                        "thursday": ["09:00-17:00"],
                        "friday": ["09:00-15:00"]
                    },
                    "meeting_types": {
                        "discovery_call": {"duration": 30, "buffer": 15},
                        "demo": {"duration": 45, "buffer": 15},
                        "proposal_review": {"duration": 60, "buffer": 30}
                    },
                    "auto_confirm": True,
                    "send_reminders": True
                }
            }
            
            # 4. Pipeline Tracker Agent - Monitors CRM and tracks deal progress
            pipeline_tracker_spec = {
                "name": "PipelineTrackerAgent",
                "description": "Monitors CRM system and tracks sales pipeline progress",
                "capabilities": [
                    "data_processing",
                    "crm_integration", 
                    "report_generation",
                    "alert_sending"
                ],
                "integrations": ["salesforce", "hubspot", "pipedrive"],
                "code": None,
                "config": {
                    "tracking_frequency": 30,  # Check every 30 minutes
                    "pipeline_stages": [
                        "lead", "qualified", "meeting_scheduled", 
                        "demo_completed", "proposal_sent", "negotiation", "closed_won", "closed_lost"
                    ],
                    "alert_thresholds": {
                        "stale_lead_days": 7,
                        "pipeline_drop_percentage": 20,
                        "conversion_rate_drop": 0.05
                    },
                    "report_schedule": "daily"
                }
            }
            
            # Add all agents to the department
            agents_to_add = [
                lead_scanner_spec,
                outreach_composer_spec,
                meeting_scheduler_spec,
                pipeline_tracker_spec
            ]
            
            for agent_spec in agents_to_add:
                success = await self.add_agent(agent_spec)
                if not success:
                    logger.error(f"Failed to add agent: {agent_spec['name']}")
                    return False
            
            logger.info(f"Successfully initialized {len(agents_to_add)} Sales Department agents")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Sales Department agents: {e}")
            return False
    
    async def execute_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute sales department workflows.
        
        Args:
            task: Task specification with workflow type and parameters
            
        Returns:
            Dict containing workflow results and metrics
        """
        try:
            workflow_type = task.get("workflow_type", "full_pipeline")
            
            logger.info(f"Executing sales workflow: {workflow_type}")
            
            if workflow_type == "lead_generation":
                return await self._execute_lead_generation_workflow(task)
            elif workflow_type == "lead_nurturing":
                return await self._execute_lead_nurturing_workflow(task)
            elif workflow_type == "meeting_scheduling":
                return await self._execute_meeting_scheduling_workflow(task)
            elif workflow_type == "pipeline_reporting":
                return await self._execute_pipeline_reporting_workflow(task)
            elif workflow_type == "full_pipeline":
                return await self._execute_full_pipeline_workflow(task)
            else:
                return {
                    "success": False,
                    "error": f"Unknown workflow type: {workflow_type}",
                    "supported_workflows": [
                        "lead_generation", "lead_nurturing", "meeting_scheduling", 
                        "pipeline_reporting", "full_pipeline"
                    ]
                }
        
        except Exception as e:
            logger.error(f"Error executing sales workflow {task.get('workflow_type', 'unknown')}: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_type": task.get("workflow_type", "unknown")
            }
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive sales department status."""
        try:
            # Calculate current metrics
            current_metrics = await self._calculate_current_metrics()
            
            # Get agent statuses
            agent_statuses = {}
            for agent in self.micro_agents:
                agent_name = agent.get("name", "unknown")
                agent_statuses[agent_name] = {
                    "active": True,  # Would check actual status in real implementation
                    "last_activity": datetime.utcnow().isoformat(),
                    "tasks_completed": 0,  # Would track actual completions
                    "error_count": 0
                }
            
            # Get pipeline health
            pipeline_health = await self._assess_pipeline_health()
            
            return {
                "department": self.name,
                "health_status": self.health_status.value,
                "active_agents": len(self.micro_agents),
                "running_workflows": len(self.active_workflows),
                "current_metrics": current_metrics,
                "agent_statuses": agent_statuses,
                "pipeline_health": pipeline_health,
                "sales_targets": self.sales_targets,
                "leads_count": len(self.leads_database),
                "prospects_count": len(self.prospects_pipeline),
                "meetings_scheduled_count": len(self.meetings_scheduled),
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting sales department status: {e}")
            return {
                "department": self.name,
                "health_status": "error",
                "error": str(e)
            }
    
    async def calculate_business_impact(self) -> Dict[str, float]:
        """Calculate business impact of sales operations."""
        try:
            impact_metrics = {}
            
            # Calculate lead generation impact
            leads_generated = len(self.leads_database)
            impact_metrics["leads_generated"] = float(leads_generated)
            
            # Calculate meeting booking impact  
            meetings_booked = len(self.meetings_scheduled)
            impact_metrics["meetings_booked"] = float(meetings_booked)
            
            # Calculate pipeline value impact
            total_pipeline_value = sum(
                prospect.lead.score * 1000  # Estimate value based on lead score
                for prospect in self.prospects_pipeline.values()
            )
            impact_metrics["pipeline_value"] = total_pipeline_value
            
            # Calculate conversion rate
            qualified_leads = len(self.prospects_pipeline)
            if leads_generated > 0:
                conversion_rate = qualified_leads / leads_generated
            else:
                conversion_rate = 0.0
            impact_metrics["conversion_rate"] = conversion_rate
            
            # Calculate cost per lead (estimated)
            operational_cost = len(self.micro_agents) * 100  # $100 per agent per period
            if leads_generated > 0:
                cost_per_lead = operational_cost / leads_generated
            else:
                cost_per_lead = operational_cost
            impact_metrics["cost_per_lead"] = cost_per_lead
            
            # Calculate efficiency gains
            automation_time_saved = len(self.micro_agents) * 40  # 40 hours saved per agent
            impact_metrics["automation_time_saved_hours"] = float(automation_time_saved)
            
            logger.info(f"Calculated business impact: {impact_metrics}")
            return impact_metrics
            
        except Exception as e:
            logger.error(f"Error calculating business impact: {e}")
            return {"error": str(e)}
    
    # Sales-specific department methods
    
    async def find_new_leads(self, criteria: Dict[str, Any]) -> List[Lead]:
        """
        Find new leads based on specified criteria.
        
        Args:
            criteria: Search criteria including titles, companies, industries
            
        Returns:
            List of new leads found
        """
        try:
            logger.info(f"Finding new leads with criteria: {criteria}")
            
            # In a real implementation, this would coordinate with LeadScannerAgent
            # For now, simulate lead generation
            
            new_leads = []
            
            # Generate mock leads based on criteria
            titles = criteria.get("titles", ["CEO", "CTO", "VP"])
            industries = criteria.get("industries", ["Technology", "SaaS"])
            company_sizes = criteria.get("company_sizes", ["11-50", "51-200"])
            
            # Simulate finding leads
            for i in range(criteria.get("max_leads", 10)):
                lead_id = f"lead_{int(datetime.utcnow().timestamp())}_{i}"
                
                lead = Lead(
                    id=lead_id,
                    name=f"Contact {i+1}",
                    email=f"contact{i+1}@company{i+1}.com",
                    company=f"Company {i+1}",
                    title=titles[i % len(titles)],
                    source="linkedin_scan",
                    score=self._calculate_lead_score({
                        "title": titles[i % len(titles)],
                        "industry": industries[i % len(industries)],
                        "company_size": company_sizes[i % len(company_sizes)]
                    }),
                    created_at=datetime.utcnow()
                )
                
                new_leads.append(lead)
                self.leads_database[lead_id] = lead
            
            # Save updated state
            await self.save_state()
            
            logger.info(f"Found {len(new_leads)} new leads")
            return new_leads
            
        except Exception as e:
            logger.error(f"Error finding new leads: {e}")
            return []
    
    async def nurture_prospects(self, leads: List[Lead]) -> Dict[str, Any]:
        """
        Nurture leads through personalized outreach.
        
        Args:
            leads: List of leads to nurture
            
        Returns:
            Dict containing nurturing results
        """
        try:
            logger.info(f"Nurturing {len(leads)} prospects")
            
            nurturing_results = {
                "leads_contacted": 0,
                "emails_sent": 0,
                "responses_received": 0,
                "prospects_qualified": 0,
                "errors": []
            }
            
            for lead in leads:
                try:
                    # Simulate outreach process
                    if lead.status == "new":
                        # Send initial outreach
                        email_sent = await self._send_outreach_email(lead, "cold_outreach")
                        if email_sent:
                            nurturing_results["emails_sent"] += 1
                            lead.contact_attempts += 1
                            lead.last_contacted = datetime.utcnow()
                            lead.status = "contacted"
                        
                    elif lead.status == "contacted" and lead.contact_attempts < 3:
                        # Send follow-up
                        email_sent = await self._send_outreach_email(lead, "follow_up")
                        if email_sent:
                            nurturing_results["emails_sent"] += 1
                            lead.contact_attempts += 1
                            lead.last_contacted = datetime.utcnow()
                    
                    # Simulate response and qualification
                    if lead.score > 7 and lead.contact_attempts >= 2:
                        # Simulate positive response and qualification
                        prospect = await self._qualify_lead(lead)
                        if prospect:
                            self.prospects_pipeline[lead.id] = prospect
                            nurturing_results["prospects_qualified"] += 1
                            lead.status = "qualified"
                    
                    nurturing_results["leads_contacted"] += 1
                    
                except Exception as e:
                    nurturing_results["errors"].append(f"Error nurturing lead {lead.id}: {str(e)}")
            
            # Save updated state
            await self.save_state()
            
            logger.info(f"Nurturing completed: {nurturing_results}")
            return nurturing_results
            
        except Exception as e:
            logger.error(f"Error nurturing prospects: {e}")
            return {"success": False, "error": str(e)}
    
    async def schedule_meetings(self, prospects: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Schedule meetings with qualified prospects.
        
        Args:
            prospects: List of prospect data for meeting scheduling
            
        Returns:
            Dict containing scheduling results
        """
        try:
            logger.info(f"Scheduling meetings for {len(prospects)} prospects")
            
            scheduling_results = {
                "meetings_requested": 0,
                "meetings_confirmed": 0,
                "calendar_conflicts": 0,
                "scheduled_meetings": [],
                "errors": []
            }
            
            for prospect_data in prospects:
                try:
                    prospect_id = prospect_data.get("prospect_id")
                    meeting_type = prospect_data.get("meeting_type", "discovery_call")
                    preferred_times = prospect_data.get("preferred_times", [])
                    
                    # Find available time slot
                    available_slot = await self._find_available_slot(meeting_type, preferred_times)
                    
                    if available_slot:
                        # Create meeting
                        meeting = {
                            "id": f"meeting_{int(datetime.utcnow().timestamp())}",
                            "prospect_id": prospect_id,
                            "type": meeting_type,
                            "scheduled_time": available_slot,
                            "duration": 30,  # Default 30 minutes
                            "status": "confirmed",
                            "created_at": datetime.utcnow().isoformat()
                        }
                        
                        self.meetings_scheduled.append(meeting)
                        scheduling_results["meetings_confirmed"] += 1
                        scheduling_results["scheduled_meetings"].append(meeting)
                        
                        # Update prospect status
                        if prospect_id in self.prospects_pipeline:
                            self.prospects_pipeline[prospect_id].meeting_scheduled = True
                            self.prospects_pipeline[prospect_id].next_action = "attend_meeting"
                    else:
                        scheduling_results["calendar_conflicts"] += 1
                    
                    scheduling_results["meetings_requested"] += 1
                    
                except Exception as e:
                    scheduling_results["errors"].append(f"Error scheduling for prospect {prospect_data.get('prospect_id', 'unknown')}: {str(e)}")
            
            # Save updated state
            await self.save_state()
            
            logger.info(f"Meeting scheduling completed: {scheduling_results}")
            return scheduling_results
            
        except Exception as e:
            logger.error(f"Error scheduling meetings: {e}")
            return {"success": False, "error": str(e)}
    
    async def report_pipeline_status(self) -> Dict[str, Any]:
        """
        Generate comprehensive pipeline status report.
        
        Returns:
            Dict containing detailed pipeline metrics and status
        """
        try:
            logger.info("Generating pipeline status report")
            
            # Calculate pipeline metrics
            total_leads = len(self.leads_database)
            total_prospects = len(self.prospects_pipeline)
            total_meetings = len(self.meetings_scheduled)
            
            # Categorize leads by status
            lead_status_breakdown = {}
            for lead in self.leads_database.values():
                status = lead.status
                lead_status_breakdown[status] = lead_status_breakdown.get(status, 0) + 1
            
            # Calculate conversion metrics
            if total_leads > 0:
                lead_to_prospect_rate = total_prospects / total_leads
                lead_to_meeting_rate = total_meetings / total_leads
            else:
                lead_to_prospect_rate = 0.0
                lead_to_meeting_rate = 0.0
            
            # Calculate pipeline value
            total_pipeline_value = sum(
                prospect.lead.score * 1000
                for prospect in self.prospects_pipeline.values()
            )
            
            # Get recent activity
            recent_activity = await self._get_recent_activity()
            
            # Generate recommendations
            recommendations = await self._generate_pipeline_recommendations()
            
            report = {
                "report_timestamp": datetime.utcnow().isoformat(),
                "summary": {
                    "total_leads": total_leads,
                    "total_prospects": total_prospects,
                    "total_meetings": total_meetings,
                    "pipeline_value": total_pipeline_value,
                    "lead_to_prospect_conversion": lead_to_prospect_rate,
                    "lead_to_meeting_conversion": lead_to_meeting_rate
                },
                "lead_breakdown": lead_status_breakdown,
                "targets_vs_actual": {
                    "leads_target": self.sales_targets["monthly_leads"],
                    "leads_actual": total_leads,
                    "meetings_target": self.sales_targets["monthly_meetings"],
                    "meetings_actual": total_meetings,
                    "pipeline_value_target": self.sales_targets["monthly_pipeline_value"],
                    "pipeline_value_actual": total_pipeline_value
                },
                "recent_activity": recent_activity,
                "recommendations": recommendations,
                "health_indicators": {
                    "pipeline_health": "healthy" if total_prospects > 0 else "needs_attention",
                    "activity_level": "high" if total_leads > 10 else "low",
                    "conversion_health": "good" if lead_to_prospect_rate > 0.1 else "needs_improvement"
                }
            }
            
            logger.info("Pipeline status report generated")
            return report
            
        except Exception as e:
            logger.error(f"Error generating pipeline report: {e}")
            return {"success": False, "error": str(e)}
    
    # Private helper methods
    
    async def _execute_lead_generation_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute lead generation workflow."""
        try:
            criteria = task.get("criteria", {
                "titles": ["CEO", "CTO", "VP Engineering"],
                "max_leads": 20
            })
            
            new_leads = await self.find_new_leads(criteria)
            
            return {
                "success": True,
                "workflow_type": "lead_generation",
                "leads_found": len(new_leads),
                "leads": [{"id": lead.id, "name": lead.name, "company": lead.company, "score": lead.score} for lead in new_leads]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_lead_nurturing_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute lead nurturing workflow."""
        try:
            # Get leads to nurture
            lead_ids = task.get("lead_ids", list(self.leads_database.keys()))
            leads_to_nurture = [self.leads_database[lid] for lid in lead_ids if lid in self.leads_database]
            
            results = await self.nurture_prospects(leads_to_nurture)
            
            return {
                "success": True,
                "workflow_type": "lead_nurturing",
                "nurturing_results": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_meeting_scheduling_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute meeting scheduling workflow."""
        try:
            prospects_data = task.get("prospects", [])
            
            # If no specific prospects provided, use qualified prospects
            if not prospects_data:
                prospects_data = [
                    {"prospect_id": pid, "meeting_type": "discovery_call"}
                    for pid, prospect in self.prospects_pipeline.items()
                    if not prospect.meeting_scheduled
                ]
            
            results = await self.schedule_meetings(prospects_data)
            
            return {
                "success": True,
                "workflow_type": "meeting_scheduling",
                "scheduling_results": results
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_pipeline_reporting_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute pipeline reporting workflow."""
        try:
            report = await self.report_pipeline_status()
            
            return {
                "success": True,
                "workflow_type": "pipeline_reporting",
                "report": report
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _execute_full_pipeline_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute complete sales pipeline workflow."""
        try:
            results = {
                "success": True,
                "workflow_type": "full_pipeline",
                "stages_completed": []
            }
            
            # Stage 1: Lead Generation
            lead_gen_task = {"criteria": task.get("lead_criteria", {})}
            lead_gen_result = await self._execute_lead_generation_workflow(lead_gen_task)
            results["lead_generation"] = lead_gen_result
            results["stages_completed"].append("lead_generation")
            
            # Stage 2: Lead Nurturing
            nurture_task = {"lead_ids": []}  # Will use all leads
            nurture_result = await self._execute_lead_nurturing_workflow(nurture_task)
            results["lead_nurturing"] = nurture_result
            results["stages_completed"].append("lead_nurturing")
            
            # Stage 3: Meeting Scheduling
            meeting_task = {"prospects": []}  # Will use qualified prospects
            meeting_result = await self._execute_meeting_scheduling_workflow(meeting_task)
            results["meeting_scheduling"] = meeting_result
            results["stages_completed"].append("meeting_scheduling")
            
            # Stage 4: Pipeline Reporting
            report_result = await self._execute_pipeline_reporting_workflow({})
            results["pipeline_report"] = report_result
            results["stages_completed"].append("pipeline_reporting")
            
            return results
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _calculate_lead_score(self, lead_data: Dict[str, Any]) -> float:
        """Calculate lead score based on criteria."""
        score = 5.0  # Base score
        
        # Title scoring
        title = lead_data.get("title", "").lower()
        for keyword in self.lead_scoring_criteria["title_keywords"]:
            if keyword in title:
                score += 2.0
                break
        
        # Company size scoring
        company_size = lead_data.get("company_size", "").lower()
        for size, bonus in self.lead_scoring_criteria["company_size_bonus"].items():
            if size in company_size:
                score += bonus
                break
        
        # Industry match
        industry = lead_data.get("industry", "").lower()
        for match_industry in self.lead_scoring_criteria["industry_match"]:
            if match_industry in industry:
                score += 3.0
                break
        
        return min(score, 10.0)  # Cap at 10
    
    async def _send_outreach_email(self, lead: Lead, template_type: str) -> bool:
        """Simulate sending outreach email."""
        try:
            # In real implementation, this would coordinate with OutreachComposerAgent
            logger.info(f"Sending {template_type} email to {lead.email}")
            
            # Simulate email sending
            lead.notes.append(f"Sent {template_type} email at {datetime.utcnow().isoformat()}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email to {lead.email}: {e}")
            return False
    
    async def _qualify_lead(self, lead: Lead) -> Optional[Prospect]:
        """Qualify a lead as a prospect."""
        try:
            # Simulate qualification process
            if lead.score >= 7:
                prospect = Prospect(
                    lead=lead,
                    qualification_score=lead.score,
                    pain_points=["automation", "efficiency"],
                    budget_range="10k-50k",
                    timeline="Q1",
                    decision_maker=lead.score >= 8,
                    next_action="schedule_meeting"
                )
                return prospect
            return None
            
        except Exception as e:
            logger.error(f"Error qualifying lead {lead.id}: {e}")
            return None
    
    async def _find_available_slot(self, meeting_type: str, preferred_times: List[str]) -> Optional[str]:
        """Find available meeting slot."""
        # Simulate finding available slot
        base_time = datetime.utcnow() + timedelta(days=3)  # 3 days from now
        return base_time.isoformat()
    
    async def _calculate_current_metrics(self) -> Dict[str, float]:
        """Calculate current sales metrics."""
        return {
            "leads_generated": float(len(self.leads_database)),
            "meetings_booked": float(len(self.meetings_scheduled)),
            "pipeline_value": sum(p.lead.score * 1000 for p in self.prospects_pipeline.values()),
            "conversion_rate": len(self.prospects_pipeline) / max(len(self.leads_database), 1)
        }
    
    async def _assess_pipeline_health(self) -> Dict[str, Any]:
        """Assess overall pipeline health."""
        return {
            "status": "healthy",
            "lead_flow": "consistent",
            "conversion_trend": "improving",
            "activity_level": "high"
        }
    
    async def _get_recent_activity(self) -> List[Dict[str, Any]]:
        """Get recent sales activity."""
        return [
            {"activity": "Lead generation", "count": len(self.leads_database), "timestamp": datetime.utcnow().isoformat()},
            {"activity": "Prospect qualification", "count": len(self.prospects_pipeline), "timestamp": datetime.utcnow().isoformat()},
            {"activity": "Meeting scheduling", "count": len(self.meetings_scheduled), "timestamp": datetime.utcnow().isoformat()}
        ]
    
    async def _generate_pipeline_recommendations(self) -> List[str]:
        """Generate recommendations for pipeline improvement."""
        recommendations = []
        
        if len(self.leads_database) < 10:
            recommendations.append("Increase lead generation activity - current lead count is below optimal")
        
        if len(self.prospects_pipeline) == 0:
            recommendations.append("Focus on lead qualification - no qualified prospects in pipeline")
        
        if len(self.meetings_scheduled) == 0:
            recommendations.append("Prioritize meeting scheduling with qualified prospects")
        
        return recommendations if recommendations else ["Pipeline is performing well - continue current activities"]