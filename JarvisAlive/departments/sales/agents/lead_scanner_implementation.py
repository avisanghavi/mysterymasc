from typing import List, Dict, Optional, Literal
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging
import uuid
import asyncio
from collections import defaultdict
import re
import json
import sys
import os

# Add ai_engines to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from database.mock_data import Company, Contact, get_qualified_leads, get_all_companies, get_all_contacts
from ai_engines.base_engine import BaseAIEngine, AIEngineConfig
from ai_engines.anthropic_engine import AnthropicEngine
from ai_engines.mock_engine import MockAIEngine


class LeadScore(BaseModel):
    total_score: int  # 0-100
    industry_match: int  # 0-30
    title_relevance: int  # 0-30
    company_size_fit: int  # 0-20
    recent_activity: int  # 0-20
    explanation: str
    confidence: float  # 0.0-1.0

    @validator('total_score', 'industry_match', 'title_relevance', 'company_size_fit', 'recent_activity')
    def validate_scores(cls, v):
        return max(0, min(v, 100))

    @validator('confidence')
    def validate_confidence(cls, v):
        return max(0.0, min(v, 1.0))


class Lead(BaseModel):
    lead_id: str  # Format: "lead_[uuid]"
    contact: Contact
    company: Company
    score: LeadScore
    discovered_at: datetime
    source: str  # "mock_database", "ai_enriched", "api"
    enrichment_data: Optional[Dict] = None
    outreach_priority: Literal["high", "medium", "low"]

    @validator('lead_id')
    def validate_lead_id(cls, v):
        if not v.startswith('lead_'):
            raise ValueError('Lead ID must start with "lead_"')
        return v


class ScanCriteria(BaseModel):
    industries: Optional[List[str]] = None
    company_sizes: Optional[List[str]] = None
    titles: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    min_score: int = 60
    max_results: int = 50
    exclude_companies: Optional[List[str]] = None

    @validator('min_score')
    def validate_min_score(cls, v):
        return max(0, min(v, 100))

    @validator('max_results')
    def validate_max_results(cls, v):
        return max(1, min(v, 1000))


class LeadScannerAgent:
    def __init__(self, mode: Literal["mock", "hybrid", "ai"] = "mock", config: Optional[Dict] = None):
        self.mode = mode
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._setup_scoring_weights()
        self._setup_industry_mappings()
        self._setup_title_mappings()
        self._setup_company_size_mappings()
        
        # Initialize AI engine if needed
        self.ai_engine = None
        if mode in ["hybrid", "ai"]:
            self._initialize_ai_engine()

    def _setup_scoring_weights(self):
        """Setup configurable scoring weights"""
        self.scoring_weights = self.config.get('scoring_weights', {
            'industry_match': 30,
            'title_relevance': 30,
            'company_size_fit': 20,
            'recent_activity': 20
        })

    def _setup_industry_mappings(self):
        """Setup industry similarity mappings"""
        self.industry_mappings = {
            'SaaS': ['Software', 'Cloud Computing', 'Technology', 'Enterprise Software'],
            'FinTech': ['Financial Services', 'Banking', 'Payments', 'Investment', 'Finance'],
            'E-commerce': ['Retail', 'Commerce', 'Marketplace', 'Consumer Goods'],
            'Healthcare': ['Medical', 'Pharmaceutical', 'Biotech', 'Health Tech'],
            'Manufacturing': ['Industrial', 'Production', 'Automotive', 'Materials']
        }

    def _setup_title_mappings(self):
        """Setup title similarity mappings"""
        self.title_mappings = {
            'ceo': ['Chief Executive Officer', 'President', 'Founder'],
            'cto': ['Chief Technology Officer', 'Chief Tech Officer', 'VP Technology'],
            'vp sales': ['Vice President Sales', 'VP of Sales', 'Sales VP', 'Director of Sales'],
            'marketing': ['CMO', 'Chief Marketing Officer', 'VP Marketing', 'Marketing Director'],
            'operations': ['COO', 'Chief Operating Officer', 'VP Operations', 'Operations Director']
        }

    def _setup_company_size_mappings(self):
        """Setup company size range mappings"""
        self.size_mappings = {
            'startup': (1, 50),
            'small': (51, 200),
            'medium': (201, 1000),
            'large': (1001, 5000),
            'enterprise': (5001, float('inf'))
        }

    def _initialize_ai_engine(self):
        """Initialize AI engine based on config"""
        ai_config = AIEngineConfig(
            model=self.config.get("ai_model", "claude-3-sonnet-20240229"),
            api_key=self.config.get("api_key"),
            max_tokens=500,
            temperature=0.3,
            cache_ttl_seconds=7200  # Cache for 2 hours
        )
        
        ai_provider = self.config.get("ai_provider", "mock")
        if ai_provider == "anthropic" and ai_config.api_key:
            self.ai_engine = AnthropicEngine(ai_config)
            self.logger.info("Initialized Anthropic AI engine")
        else:
            self.ai_engine = MockAIEngine(ai_config, deterministic=True)
            self.logger.info("Initialized Mock AI engine")

    async def scan_for_leads(self, criteria: ScanCriteria) -> List[Lead]:
        """Enhanced scan with mode-specific behavior"""
        
        if self.mode == "mock":
            # Pure mock mode - no AI
            return await self._scan_mock_data(criteria)
            
        elif self.mode == "hybrid":
            # Start with mock data, enrich with AI
            mock_leads = await self._scan_mock_data(criteria)
            
            # Calculate enrichment count (20% of results, max 10)
            enrich_count = min(10, max(1, len(mock_leads) // 5))
            
            # Enrich top leads with AI
            enriched_leads = await self._enrich_with_ai(mock_leads, enrich_count)
            
            # Log enrichment stats
            enriched = sum(1 for l in enriched_leads if l.enrichment_data)
            self.logger.info(f"Hybrid mode: {enriched}/{len(enriched_leads)} leads AI-enriched")
            
            return enriched_leads
            
        elif self.mode == "ai":
            # Full AI mode - would connect to real data sources
            # For MVP, still use mock data but enrich everything
            mock_leads = await self._scan_mock_data(criteria)
            
            # Enrich all leads (with reasonable limit)
            enriched_leads = await self._enrich_with_ai(mock_leads, min(20, len(mock_leads)))
            
            return enriched_leads
            
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    async def _scan_mock_data(self, criteria: ScanCriteria) -> List[Lead]:
        """
        Main method to scan for leads based on criteria using mock data.
        
        Process:
        1. Retrieve potential leads from data source
        2. Score each lead
        3. Filter by minimum score
        4. Sort by score (descending)
        5. Apply max_results limit
        """
        try:
            self.logger.info(f"Starting mock data scan with criteria: {criteria}")
            
            # Step 1: Retrieve potential leads
            raw_leads = await self._get_raw_leads(criteria)
            
            # Step 2: Score each lead
            scored_leads = []
            for contact, company in raw_leads:
                try:
                    score = self.score_lead(contact, company, criteria)
                    
                    # Skip leads below minimum score
                    if score.total_score < criteria.min_score:
                        continue
                    
                    # Determine outreach priority
                    priority = self._determine_priority(score.total_score)
                    
                    lead = Lead(
                        lead_id=f"lead_{uuid.uuid4()}",
                        contact=contact,
                        company=company,
                        score=score,
                        discovered_at=datetime.now(),
                        source=self.mode,
                        outreach_priority=priority
                    )
                    scored_leads.append(lead)
                    
                except Exception as e:
                    self.logger.error(f"Error scoring lead {contact.email}: {e}")
                    continue
            
            # Step 3: Sort by score (descending)
            scored_leads.sort(key=lambda x: x.score.total_score, reverse=True)
            
            # Step 4: Apply max_results limit
            final_leads = scored_leads[:criteria.max_results]
            
            # Step 5: Log metrics
            self._log_scan_metrics(criteria, final_leads)
            
            return final_leads
            
        except Exception as e:
            self.logger.error(f"Error in scan_for_leads: {e}")
            raise

    def score_lead(self, contact: Contact, company: Company, criteria: ScanCriteria) -> LeadScore:
        """
        Score a lead based on multiple factors:
        
        Industry Match (0-30):
        - Exact match: 30 points
        - Related industry: 20 points
        - General B2B: 10 points
        - Other: 0 points
        
        Title Relevance (0-30):
        - Exact title match: 30 points
        - Related title: 20 points (VP Sales matches "sales executive")
        - Same department: 10 points
        - Other: 0 points
        
        Company Size Fit (0-20):
        - Exact range match: 20 points
        - Adjacent range: 10 points
        - Other: 0 points
        
        Recent Activity (0-20):
        - News in last 30 days: 20 points
        - News in last 90 days: 10 points
        - News in last 180 days: 5 points
        - No recent news: 0 points
        """
        try:
            # Calculate individual scores
            industry_score = self._calculate_industry_match(company, criteria)
            title_score = self._calculate_title_relevance(contact, criteria)
            size_score = self._calculate_company_size_fit(company, criteria)
            activity_score = self._calculate_recent_activity(company)
            
            # Calculate total score
            total = industry_score + title_score + size_score + activity_score
            
            # Calculate confidence based on data completeness
            confidence = self._calculate_confidence(contact, company, criteria)
            
            # Generate explanation
            explanation = self._generate_score_explanation(
                industry_score, title_score, size_score, activity_score, contact, company
            )
            
            return LeadScore(
                total_score=total,
                industry_match=industry_score,
                title_relevance=title_score,
                company_size_fit=size_score,
                recent_activity=activity_score,
                explanation=explanation,
                confidence=confidence
            )
            
        except Exception as e:
            self.logger.error(f"Error scoring lead: {e}")
            # Return default low score on error
            return LeadScore(
                total_score=0,
                industry_match=0,
                title_relevance=0,
                company_size_fit=0,
                recent_activity=0,
                explanation=f"Error calculating score: {e}",
                confidence=0.0
            )

    def _calculate_industry_match(self, company: Company, criteria: ScanCriteria) -> int:
        """Calculate industry match score with nuanced logic"""
        if not criteria.industries:
            return 15  # Neutral score if no industry specified
        
        company_industry = company.industry.lower()
        
        for target_industry in criteria.industries:
            target_lower = target_industry.lower()
            
            # Exact match
            if company_industry == target_lower:
                return 30
            
            # Check related industries
            for main_industry, related in self.industry_mappings.items():
                if target_lower == main_industry.lower():
                    for related_industry in related:
                        if related_industry.lower() in company_industry:
                            return 20
                
                # Check reverse mapping
                if company_industry == main_industry.lower():
                    for related_industry in related:
                        if related_industry.lower() in target_lower:
                            return 20
        
        # General B2B match
        b2b_keywords = ['technology', 'software', 'business', 'enterprise', 'professional']
        for keyword in b2b_keywords:
            if keyword in company_industry:
                return 10
        
        return 0

    def _calculate_title_relevance(self, contact: Contact, criteria: ScanCriteria) -> int:
        """Calculate title relevance with fuzzy matching"""
        if not criteria.titles:
            return 15  # Neutral score if no title specified
        
        contact_title = contact.title.lower()
        
        for target_title in criteria.titles:
            target_lower = target_title.lower()
            
            # Exact match
            if contact_title == target_lower:
                return 30
            
            # Partial match
            if target_lower in contact_title or contact_title in target_lower:
                return 25
            
            # Check title mappings
            for key, variations in self.title_mappings.items():
                if key in target_lower:
                    for variation in variations:
                        if variation.lower() in contact_title:
                            return 20
            
            # Department match
            departments = ['sales', 'marketing', 'engineering', 'operations', 'finance']
            for dept in departments:
                if dept in target_lower and dept in contact_title:
                    return 10
        
        # Seniority match
        seniority_keywords = ['vp', 'director', 'manager', 'head', 'lead', 'chief']
        for keyword in seniority_keywords:
            if keyword in contact_title:
                return 5
        
        return 0

    def _calculate_company_size_fit(self, company: Company, criteria: ScanCriteria) -> int:
        """Calculate company size fit"""
        if not criteria.company_sizes:
            return 10  # Neutral score if no size specified
        
        company_employees = company.employee_count
        
        for target_size in criteria.company_sizes:
            target_lower = target_size.lower()
            
            if target_lower in self.size_mappings:
                min_emp, max_emp = self.size_mappings[target_lower]
                
                # Exact range match
                if min_emp <= company_employees <= max_emp:
                    return 20
                
                # Adjacent range (within 50% of range)
                range_size = max_emp - min_emp if max_emp != float('inf') else 1000
                tolerance = range_size * 0.5
                
                if (min_emp - tolerance <= company_employees <= max_emp + tolerance):
                    return 10
        
        return 0

    def _calculate_recent_activity(self, company: Company) -> int:
        """Calculate recency score based on company news"""
        if not hasattr(company, 'recent_news') or not company.recent_news:
            return 0
        
        now = datetime.now()
        max_score = 0
        
        for news_item in company.recent_news:
            # Parse news date (assuming format in news_item)
            try:
                # Extract date from news item (simplified approach)
                days_ago = self._extract_days_from_news(news_item)
                
                if days_ago <= 30:
                    max_score = max(max_score, 20)
                elif days_ago <= 90:
                    max_score = max(max_score, 10)
                elif days_ago <= 180:
                    max_score = max(max_score, 5)
                
            except Exception as e:
                self.logger.warning(f"Error parsing news date: {e}")
                continue
        
        return max_score

    def _extract_days_from_news(self, news_item) -> int:
        """Extract days from news item - simplified implementation"""
        # This is a simplified approach - in reality, you'd parse actual dates
        import random
        # Use news item date if available, otherwise random
        if hasattr(news_item, 'date'):
            days_diff = (datetime.now() - news_item.date).days
            return max(1, days_diff)
        return random.randint(1, 365)  # Mock implementation

    def _calculate_confidence(self, contact: Contact, company: Company, criteria: ScanCriteria) -> float:
        """Calculate confidence based on data completeness"""
        completeness_score = 0
        total_factors = 0
        
        # Check contact data completeness
        if contact.email:
            completeness_score += 1
        total_factors += 1
        
        if contact.phone:
            completeness_score += 1
        total_factors += 1
        
        if contact.linkedin_url:
            completeness_score += 1
        total_factors += 1
        
        # Check company data completeness
        if company.website:
            completeness_score += 1
        total_factors += 1
        
        if hasattr(company, 'recent_news') and company.recent_news:
            completeness_score += 1
        total_factors += 1
        
        return completeness_score / total_factors if total_factors > 0 else 0.5

    def _generate_score_explanation(self, industry_score: int, title_score: int, 
                                  size_score: int, activity_score: int, 
                                  contact: Contact, company: Company) -> str:
        """Generate human-readable explanation of the score"""
        explanations = []
        
        if industry_score >= 20:
            explanations.append(f"Strong industry match ({company.industry})")
        elif industry_score >= 10:
            explanations.append(f"Moderate industry relevance ({company.industry})")
        
        if title_score >= 20:
            explanations.append(f"High title relevance ({contact.title})")
        elif title_score >= 10:
            explanations.append(f"Some title relevance ({contact.title})")
        
        if size_score >= 15:
            explanations.append(f"Good company size fit ({company.employee_count} employees)")
        
        if activity_score >= 15:
            explanations.append("Recent company activity detected")
        
        return "; ".join(explanations) if explanations else "Basic qualification met"

    def _determine_priority(self, score: int) -> Literal["high", "medium", "low"]:
        """Determine outreach priority based on score"""
        if score >= 80:
            return "high"
        elif score >= 60:
            return "medium"
        else:
            return "low"

    async def _get_raw_leads(self, criteria: ScanCriteria) -> List[tuple]:
        """Get raw leads from mock data source"""
        try:
            # Get all companies and contacts
            companies = get_all_companies()
            contacts = get_all_contacts()
            
            # Filter companies
            if criteria.industries:
                companies = [c for c in companies if c.industry in criteria.industries]
            
            if criteria.exclude_companies:
                companies = [c for c in companies if c.name not in criteria.exclude_companies]
            
            # Filter contacts
            if criteria.titles:
                filtered_contacts = []
                for contact in contacts:
                    for title in criteria.titles:
                        if title.lower() in contact.title.lower():
                            filtered_contacts.append(contact)
                            break
                contacts = filtered_contacts
            
            # Create lead pairs
            lead_pairs = []
            for contact in contacts:
                # Find matching company
                matching_company = None
                for company in companies:
                    if company.id == contact.company_id:
                        matching_company = company
                        break
                
                if matching_company:
                    lead_pairs.append((contact, matching_company))
            
            return lead_pairs
            
        except Exception as e:
            self.logger.error(f"Error scanning mock data: {e}")
            return []

    async def _enrich_with_ai(self, leads: List[tuple]) -> List[tuple]:
        """Enrich top leads with AI analysis (hybrid/ai mode only)"""
        # Mock AI enrichment - in reality, this would call AI services
        self.logger.info(f"AI enrichment requested for {len(leads)} leads")
        
        # Simulate AI processing time
        await asyncio.sleep(0.1)
        
        # Return leads as-is (mock implementation)
        return leads

    async def _prepare_for_ai_enrichment(self, leads: List[Lead]) -> List[Dict]:
        """Structure lead data for AI enrichment"""
        enrichment_data = []
        
        for lead in leads:
            data = {
                'lead_id': lead.lead_id,
                'company_name': lead.company.name,
                'company_industry': lead.company.industry,
                'contact_name': lead.contact.name,
                'contact_title': lead.contact.title,
                'current_score': lead.score.total_score
            }
            enrichment_data.append(data)
        
        return enrichment_data

    def _log_scan_metrics(self, criteria: ScanCriteria, results: List[Lead]):
        """Log detailed metrics for monitoring"""
        try:
            self.logger.info(f"Scan completed: {len(results)} leads found")
            
            if results:
                score_distribution = self._get_score_distribution(results)
                self.logger.info(f"Score distribution: {score_distribution}")
                
                top_industries = self._get_top_industries(results)
                self.logger.info(f"Top industries: {top_industries}")
                
                priority_distribution = self._get_priority_distribution(results)
                self.logger.info(f"Priority distribution: {priority_distribution}")
                
                avg_score = sum(lead.score.total_score for lead in results) / len(results)
                self.logger.info(f"Average score: {avg_score:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error logging scan metrics: {e}")

    def _get_score_distribution(self, results: List[Lead]) -> Dict[str, int]:
        """Get score distribution for monitoring"""
        distribution = {'90-100': 0, '80-89': 0, '70-79': 0, '60-69': 0, '50-59': 0, '<50': 0}
        
        for lead in results:
            score = lead.score.total_score
            if score >= 90:
                distribution['90-100'] += 1
            elif score >= 80:
                distribution['80-89'] += 1
            elif score >= 70:
                distribution['70-79'] += 1
            elif score >= 60:
                distribution['60-69'] += 1
            elif score >= 50:
                distribution['50-59'] += 1
            else:
                distribution['<50'] += 1
        
        return distribution

    def _get_top_industries(self, results: List[Lead]) -> Dict[str, int]:
        """Get top industries for monitoring"""
        industry_count = defaultdict(int)
        
        for lead in results:
            industry_count[lead.company.industry] += 1
        
        return dict(sorted(industry_count.items(), key=lambda x: x[1], reverse=True)[:5])

    def _get_priority_distribution(self, results: List[Lead]) -> Dict[str, int]:
        """Get priority distribution for monitoring"""
        priority_count = defaultdict(int)
        
        for lead in results:
            priority_count[lead.outreach_priority] += 1
        
        return dict(priority_count)

    async def _enrich_with_ai(self, leads: List[Lead], max_enrichment: int = 10) -> List[Lead]:
        """
        Enrich leads with AI-powered insights.
        
        Process:
        1. Select top leads for enrichment
        2. Batch similar companies for efficiency
        3. Analyze companies and contacts
        4. Add insights to lead data
        5. Recalculate scores with AI input
        """
        if not self.ai_engine:
            self.logger.warning("AI engine not initialized, skipping enrichment")
            return leads
        
        # Sort by score and take top leads
        sorted_leads = sorted(leads, key=lambda x: x.score.total_score, reverse=True)
        leads_to_enrich = sorted_leads[:max_enrichment]
        
        enriched_leads = []
        
        for lead in leads_to_enrich:
            try:
                # Enrich company insights
                company_insights = await self._analyze_company_with_ai(lead.company)
                
                # Enrich contact insights
                contact_insights = await self._analyze_contact_with_ai(lead.contact, lead.company)
                
                # Update lead with insights
                lead.enrichment_data = {
                    "company_insights": company_insights,
                    "contact_insights": contact_insights,
                    "enriched_at": datetime.now().isoformat(),
                    "ai_provider": self.ai_engine.get_engine_type()
                }
                
                # Recalculate score with AI insights
                lead.score = await self._ai_score_lead(lead, company_insights, contact_insights)
                
                enriched_leads.append(lead)
                
            except Exception as e:
                self.logger.error(f"Failed to enrich lead {lead.lead_id}: {e}")
                enriched_leads.append(lead)  # Keep original
                
        # Combine enriched and non-enriched leads
        enriched_ids = {l.lead_id for l in enriched_leads}
        remaining_leads = [l for l in leads if l.lead_id not in enriched_ids]
        
        return enriched_leads + remaining_leads
    
    async def _analyze_company_with_ai(self, company: Company) -> Dict:
        """Use AI to analyze company deeply"""
        prompt = f"""Analyze this company for sales outreach potential:

Company: {company.name}
Industry: {company.industry} ({company.sub_industry})
Size: {company.employee_count} employees
Location: {company.location}
Description: {company.description}
Recent News: {json.dumps([{"date": n.date.isoformat(), "title": n.title} for n in company.recent_news[:3]])}
Technologies: {', '.join(company.technologies[:5])}

Provide a concise analysis covering:
1. Current business priorities based on their stage and recent news
2. Likely pain points they're experiencing
3. Best timing for outreach
4. Unique angle for approach
5. Potential objections

Format as JSON with keys: priorities, pain_points, timing, approach_angle, objections"""

        response = await self.ai_engine.generate(prompt)
        
        try:
            # Parse AI response as JSON
            insights = json.loads(response.content)
            insights["raw_analysis"] = response.content
            return insights
        except json.JSONDecodeError:
            # Fallback to text analysis
            return {
                "analysis": response.content,
                "priorities": ["growth", "efficiency"],
                "pain_points": company.pain_points,
                "timing": "standard",
                "approach_angle": "value-focused",
                "objections": ["budget", "timing"]
            }
            
    async def _analyze_contact_with_ai(self, contact: Contact, company: Company) -> Dict:
        """Use AI to analyze contact in context of company"""
        prompt = f"""Analyze this contact for B2B sales outreach:

Contact: {contact.full_name}
Title: {contact.title}
Department: {contact.department}
Seniority: {contact.seniority}
Company: {company.name} ({company.industry})
Company Size: {company.employee_count} employees

Based on their role and company context, provide:
1. Their likely responsibilities and KPIs
2. Challenges they face in their role
3. What would get their attention
4. Communication style preference
5. Best outreach channel

Format as JSON with keys: responsibilities, challenges, attention_triggers, communication_style, best_channel"""

        response = await self.ai_engine.generate(prompt)
        
        try:
            insights = json.loads(response.content)
            return insights
        except:
            return {
                "responsibilities": [f"Manage {contact.department.lower()} operations"],
                "challenges": contact.pain_points,
                "attention_triggers": ["ROI", "efficiency", "innovation"],
                "communication_style": "professional",
                "best_channel": "email"
            }

    async def _ai_score_lead(self, lead: Lead, company_insights: Dict, contact_insights: Dict) -> LeadScore:
        """Enhanced scoring using AI insights"""
        
        # Base score from original algorithm
        base_score = self.score_lead(lead.contact, lead.company, ScanCriteria())
        
        # AI scoring prompt
        prompt = f"""Score this lead's quality for B2B sales (0-100):

Company: {lead.company.name}
Industry: {lead.company.industry}
Size: {lead.company.employee_count} employees
Recent Activity: {len(lead.company.recent_news)} news items in last 6 months

Contact: {lead.contact.full_name}
Title: {lead.contact.title}
Seniority: {lead.contact.seniority}

Company Insights: {json.dumps(company_insights, indent=2)}
Contact Insights: {json.dumps(contact_insights, indent=2)}

Base Score: {base_score.total_score}/100

Consider:
- Buying power and decision-making authority
- Company's likelihood to need our solution
- Timing indicators
- Budget availability

Provide a score (0-100) and brief explanation. Format as JSON with keys: score, explanation, confidence"""

        response = await self.ai_engine.generate(prompt)
        
        try:
            ai_assessment = json.loads(response.content)
            
            # Weighted average of base and AI scores
            final_score = int(0.6 * base_score.total_score + 0.4 * ai_assessment["score"])
            
            return LeadScore(
                total_score=final_score,
                industry_match=base_score.industry_match,
                title_relevance=base_score.title_relevance,
                company_size_fit=base_score.company_size_fit,
                recent_activity=base_score.recent_activity,
                explanation=f"{base_score.explanation}\n\nAI Analysis: {ai_assessment['explanation']}",
                confidence=ai_assessment.get("confidence", 0.7)
            )
        except:
            # Fallback to base score
            return base_score

    async def _batch_analyze_companies(self, companies: List[Company]) -> Dict[str, Dict]:
        """Analyze multiple similar companies in one request for cost efficiency"""
        
        # Group by industry
        industry_groups = {}
        for company in companies:
            if company.industry not in industry_groups:
                industry_groups[company.industry] = []
            industry_groups[company.industry].append(company)
            
        results = {}
        
        for industry, industry_companies in industry_groups.items():
            if len(industry_companies) > 3:
                # Batch analysis for cost efficiency
                prompt = f"""Analyze these {len(industry_companies)} {industry} companies for common patterns:

Companies:
{self._format_companies_for_batch(industry_companies)}

Identify:
1. Common challenges in this industry segment
2. Trending priorities
3. Best outreach timing patterns
4. Effective value propositions

Then provide brief individual insights for each company.
Format as JSON with keys: industry_insights, company_insights (dict with company names as keys)"""

                response = await self.ai_engine.generate(prompt, max_tokens=1500)
                
                try:
                    batch_insights = json.loads(response.content)
                    
                    # Apply insights to each company
                    for company in industry_companies:
                        company_specific = batch_insights.get("company_insights", {}).get(company.name, {})
                        results[company.id] = {
                            **batch_insights.get("industry_insights", {}),
                            **company_specific
                        }
                except:
                    # Fallback to individual analysis
                    for company in industry_companies:
                        results[company.id] = await self._analyze_company_with_ai(company)
            else:
                # Individual analysis for small groups
                for company in industry_companies:
                    results[company.id] = await self._analyze_company_with_ai(company)
                    
        return results

    def _format_companies_for_batch(self, companies: List[Company]) -> str:
        """Format companies for batch analysis"""
        formatted = []
        for company in companies:
            formatted.append(f"""
- {company.name}: {company.employee_count} employees, {company.sub_industry}
  Recent: {company.recent_news[0].title if company.recent_news else 'No recent news'}
  Tech: {', '.join(company.technologies[:3])}
""")
        return '\n'.join(formatted)