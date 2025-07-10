from typing import Dict, List, Optional, Literal, Tuple, Any
from datetime import datetime, timedelta
from pydantic import BaseModel, validator
import logging
import uuid
import re
import random
import json
import sys
import os
import asyncio
from collections import defaultdict

# Add ai_engines to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from .email_templates import EmailTemplateLibrary, ToneStyle, EmailTemplate
from ai_engines.base_engine import BaseAIEngine, AIEngineConfig
from ai_engines.anthropic_engine import AnthropicEngine
from ai_engines.mock_engine import MockAIEngine

# Import Lead from lead scanner
try:
    from lead_scanner_implementation import Lead
except ImportError:
    # Fallback for testing - create a mock Lead class
    from typing import Any
    class Lead:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

# Import Gmail integration
try:
    from integrations.gmail_integration import GmailIntegration, EmailMessage, EmailRecipient
    from integrations.supabase_auth_manager import SupabaseAuthManager
    import redis.asyncio as redis
except ImportError:
    # Fallback for testing
    GmailIntegration = None
    EmailMessage = None
    EmailRecipient = None
    SupabaseAuthManager = None
    redis = None


class OutreachMessage(BaseModel):
    message_id: str  # Format: "msg_[uuid]"
    lead_id: str
    subject: str
    body: str
    tone: ToneStyle
    category: str
    template_id: Optional[str]
    personalization_score: float  # 0.0-1.0
    predicted_response_rate: float  # 0.0-1.0
    generation_mode: Literal["template", "ai", "hybrid"]
    ab_variant: str  # "A", "B", "C"
    created_at: datetime
    metadata: Dict

    @validator('message_id')
    def validate_message_id(cls, v):
        if not v.startswith('msg_'):
            raise ValueError('Message ID must start with "msg_"')
        return v

    @validator('personalization_score', 'predicted_response_rate')
    def validate_scores(cls, v):
        return max(0.0, min(v, 1.0))


class OutreachConfig(BaseModel):
    tone: Optional[ToneStyle] = None
    category: str = "cold_outreach"
    max_length: int = 300  # words
    personalization_depth: Literal["basic", "moderate", "deep"] = "moderate"
    include_calendar_link: bool = False
    sender_info: Dict[str, str] = {}

    @validator('max_length')
    def validate_max_length(cls, v):
        return max(50, min(v, 1000))


class OutreachComposerAgent:
    def __init__(self, mode: Literal["template", "ai", "hybrid"] = "template", config: Optional[Dict] = None):
        self.mode = mode
        self.config = config or {}
        self.template_library = EmailTemplateLibrary()
        self.logger = logging.getLogger(__name__)
        self._setup_personalization_data()
        self._setup_industry_insights()
        self._setup_response_rate_model()
        
        # Initialize AI engine for ai/hybrid modes
        self.ai_engine = None
        if mode in ["ai", "hybrid"]:
            self._initialize_ai_engine()
        
        # Initialize Gmail integration
        self.gmail_client = None
        self.auth_manager = None
        self.redis_client = None
        self.user_id = config.get('user_id') if config else None
        self.gmail_enabled = config.get('gmail_enabled', False) if config else False
        
        if self.gmail_enabled and GmailIntegration:
            asyncio.create_task(self._initialize_gmail())
            
    def _initialize_ai_engine(self):
        """Initialize AI engine"""
        ai_config = AIEngineConfig(
            model=self.config.get("ai_model", "claude-3-sonnet-20240229"),
            api_key=self.config.get("api_key"),
            max_tokens=800,
            temperature=0.7,  # More creative for messaging
            cache_ttl_seconds=3600
        )
        
        ai_provider = self.config.get("ai_provider", "mock")
        if ai_provider == "anthropic" and ai_config.api_key:
            self.ai_engine = AnthropicEngine(ai_config)
            self.logger.info("Initialized Anthropic AI engine for outreach")
        else:
            self.ai_engine = MockAIEngine(ai_config, deterministic=False)
            self.logger.info("Initialized Mock AI engine for outreach")
    
    async def _initialize_gmail(self):
        """Initialize Gmail integration with credentials from Supabase"""
        try:
            # Initialize Redis for queue management
            redis_url = self.config.get('redis_url', 'redis://localhost:6379')
            self.redis_client = await redis.from_url(redis_url)
            
            # Initialize auth manager
            self.auth_manager = SupabaseAuthManager(
                supabase_url=self.config.get('supabase_url', os.getenv('SUPABASE_URL')),
                supabase_key=self.config.get('supabase_key', os.getenv('SUPABASE_KEY')),
                encryption_key=self.config.get('encryption_key', os.getenv('ENCRYPTION_KEY'))
            )
            await self.auth_manager.initialize()
            
            # Get Gmail credentials
            if self.user_id:
                credential = await self.auth_manager.get_credentials(
                    user_id=self.user_id,
                    service="google",
                    auto_refresh=True
                )
                
                if credential and credential.access_token:
                    # Initialize Gmail client
                    from google.oauth2.credentials import Credentials
                    
                    google_creds = Credentials(
                        token=credential.access_token,
                        refresh_token=credential.refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=self.config.get('gmail_client_id', os.getenv('GMAIL_CLIENT_ID')),
                        client_secret=self.config.get('gmail_client_secret', os.getenv('GMAIL_CLIENT_SECRET'))
                    )
                    
                    self.gmail_client = GmailIntegration(
                        credentials=google_creds,
                        redis_client=self.redis_client,
                        test_mode=self.config.get('gmail_test_mode', True),
                        daily_limit=self.config.get('daily_email_limit', 50),
                        tracking_domain=self.config.get('tracking_domain', 'localhost:8000')
                    )
                    self.logger.info("Gmail integration initialized successfully")
                else:
                    self.logger.warning("No Gmail credentials found, email sending disabled")
                    self.gmail_enabled = False
            else:
                self.logger.warning("No user_id provided, email sending disabled")
                self.gmail_enabled = False
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Gmail: {e}")
            self.gmail_enabled = False

    def _setup_personalization_data(self):
        """Setup data for personalization"""
        self.company_achievements = {
            "SaaS": ["raised Series A", "launched new product", "expanded internationally", "acquired competitor"],
            "FinTech": ["achieved SOC2 compliance", "raised funding", "launched mobile app", "expanded to new markets"],
            "E-commerce": ["increased sales by 50%", "launched new product line", "expanded to new regions", "improved customer satisfaction"],
            "Healthcare": ["received FDA approval", "expanded services", "improved patient outcomes", "adopted new technology"],
            "Manufacturing": ["automated production line", "increased efficiency", "expanded capacity", "reduced waste"]
        }
        
        self.pain_points_mapping = {
            "SaaS": ["customer churn", "scaling infrastructure", "product adoption", "user onboarding"],
            "FinTech": ["regulatory compliance", "fraud prevention", "security", "transaction processing"],
            "E-commerce": ["cart abandonment", "customer retention", "inventory management", "shipping costs"],
            "Healthcare": ["patient engagement", "data security", "regulatory compliance", "operational efficiency"],
            "Manufacturing": ["production efficiency", "quality control", "supply chain", "predictive maintenance"]
        }

    def _setup_industry_insights(self):
        """Setup industry-specific insights"""
        self.industry_insights = {
            "SaaS": {
                "trends": ["AI integration", "customer success automation", "product-led growth"],
                "challenges": ["customer acquisition cost", "retention rates", "feature adoption"],
                "success_metrics": ["ARR growth", "churn reduction", "NPS improvement"]
            },
            "FinTech": {
                "trends": ["open banking", "blockchain adoption", "regulatory technology"],
                "challenges": ["compliance costs", "security threats", "customer trust"],
                "success_metrics": ["transaction volume", "fraud reduction", "compliance score"]
            },
            "E-commerce": {
                "trends": ["mobile commerce", "personalization", "social commerce"],
                "challenges": ["competition", "customer acquisition", "logistics"],
                "success_metrics": ["conversion rate", "average order value", "customer lifetime value"]
            },
            "Healthcare": {
                "trends": ["telemedicine", "AI diagnostics", "patient portals"],
                "challenges": ["regulatory compliance", "data privacy", "patient engagement"],
                "success_metrics": ["patient satisfaction", "clinical outcomes", "operational efficiency"]
            },
            "Manufacturing": {
                "trends": ["Industry 4.0", "predictive maintenance", "supply chain visibility"],
                "challenges": ["digital transformation", "skilled workforce", "sustainability"],
                "success_metrics": ["OEE improvement", "cost reduction", "quality metrics"]
            }
        }

    def _setup_response_rate_model(self):
        """Setup response rate prediction model"""
        self.response_rate_factors = {
            "personalization_score": 0.35,
            "subject_line_quality": 0.25,
            "message_length": 0.15,
            "lead_score": 0.15,
            "timing": 0.10
        }

    async def compose_outreach(self, lead: Lead, config: OutreachConfig) -> OutreachMessage:
        """Compose message with mode-specific logic"""
        
        if self.mode == "template":
            # Pure template mode
            template_id = self.select_template(lead, config)
            return self._compose_with_template(lead, template_id, config)
            
        elif self.mode == "hybrid":
            # Use AI for high-value leads, templates for others
            if lead.score.total_score >= 80 or lead.enrichment_data:
                # High-value or AI-enriched lead - use AI
                try:
                    # Check if AI engine is functional first
                    if self.ai_engine and hasattr(self.ai_engine, 'failure_rate') and self.ai_engine.failure_rate >= 1.0:
                        raise Exception("AI engine failure rate is 100%")
                    
                    message = await self._compose_with_ai(lead, {}, config)
                    # Ensure generation_mode is set correctly
                    message.generation_mode = "ai"
                    return message
                except Exception as e:
                    self.logger.warning(f"AI generation failed, falling back to template: {e}")
                    template_id = self.select_template(lead, config)
                    message = self._compose_with_template(lead, template_id, config)
                    # Ensure generation_mode is set correctly for fallback
                    message.generation_mode = "template"
                    return message
            else:
                # Standard lead - use template
                template_id = self.select_template(lead, config)
                message = self._compose_with_template(lead, template_id, config)
                message.generation_mode = "template"
                return message
                
        elif self.mode == "ai":
            # Full AI mode
            return await self._compose_with_ai(lead, {}, config)
            
        else:
            raise ValueError(f"Unknown mode: {self.mode}")

    async def _compose_with_ai(self, lead: Lead, style_guide: Dict, config: OutreachConfig) -> OutreachMessage:
        """Generate message using AI with deep personalization"""
        
        if not self.ai_engine:
            # Fallback to template
            return self._compose_with_template(lead, "cold_outreach_formal_1", config)
        
        # Build comprehensive context
        context = self._build_ai_context(lead, config)
        
        # Generate message
        prompt = f"""Write a personalized B2B sales email based on this context:

RECIPIENT:
Name: {lead.contact.full_name}
Title: {lead.contact.title}
Company: {lead.company.name}
Industry: {lead.company.industry}
Company Size: {lead.company.employee_count} employees

INSIGHTS:
Recent News: {context['recent_news']}
Pain Points: {context['pain_points']}
AI Analysis: {context['ai_insights']}

SENDER:
Name: {config.sender_info.get('name', 'Sales Representative')}
Title: {config.sender_info.get('title', 'Account Executive')}
Company: {config.sender_info.get('company', 'Our Company')}
Value Proposition: {config.sender_info.get('value_proposition', 'Help companies grow efficiently')}

REQUIREMENTS:
- Tone: {config.tone or 'professional but friendly'}
- Length: {config.max_length} words maximum
- Reference specific recent news or pain point
- Include clear value proposition
- End with soft call-to-action
- Make it feel personal, not templated

Generate both subject line and email body. Format as:
SUBJECT: [subject line]
BODY: [email body]"""

        response = await self.ai_engine.generate(prompt)
        
        # Parse response
        subject, body = self._parse_ai_email(response.content)
        
        # Generate A/B variations
        variations = await self._generate_ai_variations(lead, subject, body, config)
        
        # Select best variation
        selected = variations[0]  # Could use more sophisticated selection
        
        # Create message object
        message = OutreachMessage(
            message_id=f"msg_{uuid.uuid4()}",
            lead_id=lead.lead_id,
            subject=selected["subject"],
            body=selected["body"],
            tone=config.tone or ToneStyle.CASUAL,
            category=config.category,
            template_id=None,
            personalization_score=self.calculate_personalization_score(selected["body"], lead),
            predicted_response_rate=await self._predict_response_rate_ai(selected, lead),
            generation_mode="ai",
            ab_variant="A",
            created_at=datetime.now(),
            metadata={
                "ai_provider": self.ai_engine.get_engine_type(),
                "ai_tokens": response.usage.get('total_tokens', 0),
                "variations_generated": len(variations)
            }
        )
        
        # Quality check
        quality_result = await self._quality_check_ai_message(message.body, lead)
        if not quality_result["passed"]:
            self.logger.warning(f"AI message failed quality checks: {quality_result['issues']}")
            # Could implement retry or fallback logic here
        
        return message
    
    def _build_ai_context(self, lead: Lead, config: OutreachConfig) -> Dict:
        """Build comprehensive context for AI"""
        context = {
            "recent_news": "No recent news",
            "pain_points": ", ".join(lead.company.pain_points[:3]) if hasattr(lead.company, 'pain_points') else "General business challenges",
            "ai_insights": {}
        }
        
        # Add recent news
        if hasattr(lead.company, 'recent_news') and lead.company.recent_news:
            recent = lead.company.recent_news[0]
            context["recent_news"] = f"{recent.title}"
            
        # Add AI insights if available
        if hasattr(lead, 'enrichment_data') and lead.enrichment_data:
            context["ai_insights"] = lead.enrichment_data.get("company_insights", {})
            
        return context
    
    def _parse_ai_email(self, ai_response: str) -> Tuple[str, str]:
        """Parse AI response into subject and body"""
        lines = ai_response.strip().split('\n')
        subject = ""
        body_lines = []
        in_body = False
        
        for line in lines:
            if line.startswith("SUBJECT:"):
                subject = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                in_body = True
                body_content = line.replace("BODY:", "").strip()
                if body_content:
                    body_lines.append(body_content)
            elif in_body and line.strip():
                body_lines.append(line)
                
        body = '\n'.join(body_lines).strip()
        
        # Validation
        if not subject:
            subject = "Quick question about your business goals"
        if not body:
            raise ValueError("AI failed to generate email body")
            
        return subject, body

    async def _generate_ai_variations(self, lead: Lead, base_subject: str, base_body: str, config: OutreachConfig) -> List[Dict]:
        """Generate A/B test variations using AI"""
        
        variations = [{"subject": base_subject, "body": base_body, "variant": "A"}]
        
        # Generate 2 more variations
        variation_prompt = f"""Generate 2 alternative versions of this email with different angles:

ORIGINAL SUBJECT: {base_subject}
ORIGINAL BODY: {base_body}

CONTEXT:
- Recipient: {lead.contact.title} at {lead.company.name}
- Industry: {lead.company.industry}

Create variations that:
1. First variation: Focus more on ROI and business impact
2. Second variation: Focus more on innovation and competitive advantage

Keep the same general length and tone. Format each as:
VARIATION 1:
SUBJECT: [subject]
BODY: [body]

VARIATION 2:
SUBJECT: [subject]
BODY: [body]"""

        try:
            response = await self.ai_engine.generate(variation_prompt, temperature=0.8)
            
            # Parse variations
            parsed_variations = self._parse_variations(response.content)
            
            for i, var in enumerate(parsed_variations):
                if "subject" in var and "body" in var:
                    variations.append({
                        "subject": var["subject"],
                        "body": var["body"],
                        "variant": chr(66 + i)  # B, C, etc.
                    })
            
            # If parsing failed, create synthetic variations as fallback
            if len(variations) == 1:  # Only original
                variations.extend(self._create_synthetic_variations(base_subject, base_body, lead))
                
        except Exception as e:
            self.logger.warning(f"Failed to generate variations: {e}")
            # Create synthetic variations as fallback
            variations.extend(self._create_synthetic_variations(base_subject, base_body, lead))
            
        return variations
    
    def _parse_variations(self, ai_response: str) -> List[Dict]:
        """Parse multiple variations from AI response"""
        variations = []
        current_variation = {}
        
        lines = ai_response.strip().split('\n')
        
        for line in lines:
            if line.startswith("VARIATION"):
                if current_variation and "subject" in current_variation:
                    if isinstance(current_variation.get("body"), list):
                        current_variation["body"] = '\n'.join(current_variation["body"]).strip()
                    variations.append(current_variation)
                current_variation = {}
            elif line.startswith("SUBJECT:"):
                current_variation["subject"] = line.replace("SUBJECT:", "").strip()
            elif line.startswith("BODY:"):
                current_variation["body"] = []
                body_content = line.replace("BODY:", "").strip()
                if body_content:
                    current_variation["body"].append(body_content)
            elif current_variation.get("body") is not None and line.strip():
                current_variation["body"].append(line)
                
        # Finalize last variation
        if current_variation and "subject" in current_variation:
            if isinstance(current_variation.get("body"), list):
                current_variation["body"] = '\n'.join(current_variation["body"]).strip()
            variations.append(current_variation)
            
        return variations

    def _create_synthetic_variations(self, base_subject: str, base_body: str, lead: Lead) -> List[Dict]:
        """Create synthetic A/B variations when AI generation fails"""
        variations = []
        
        # Variation B: ROI-focused
        roi_subject = base_subject.replace("Quick question", "ROI opportunity").replace("Partnership", "Revenue growth")
        roi_body = base_body.replace("I noticed", "I saw that").replace("growth", "increase revenue by 25%").replace("discuss", "explore the ROI potential")
        
        variations.append({
            "subject": roi_subject,
            "body": roi_body,
            "variant": "B"
        })
        
        # Variation C: Innovation-focused  
        innovation_subject = base_subject.replace("Quick question", "Innovation opportunity").replace("Partnership", "Competitive advantage")
        innovation_body = base_body.replace("I noticed", "I came across").replace("growth", "stay ahead of competitors").replace("discuss", "explore innovative solutions")
        
        variations.append({
            "subject": innovation_subject,
            "body": innovation_body,
            "variant": "C"
        })
        
        return variations

    async def _predict_response_rate_ai(self, message: Dict, lead: Lead) -> float:
        """Use AI to predict response likelihood"""
        
        prompt = f"""Analyze this sales email and predict the likelihood of a response (0.0-1.0):

RECIPIENT:
Title: {lead.contact.title}
Seniority: {lead.contact.seniority if hasattr(lead.contact, 'seniority') else 'Unknown'}
Industry: {lead.company.industry}
Company Size: {lead.company.employee_count}
Lead Score: {lead.score.total_score}/100

EMAIL:
Subject: {message['subject']}
Body: {message['body']}

Consider these factors:
1. Subject line effectiveness (compelling, relevant, not spammy)
2. Opening line quality (personalized, relevant)
3. Value proposition clarity
4. Call-to-action strength (clear but not pushy)
5. Overall length and readability
6. Personalization depth

Provide:
- Response probability (0.0-1.0)
- Key strengths (2-3 points)
- Key weaknesses (2-3 points)
- One improvement suggestion

Format as JSON with keys: probability, strengths, weaknesses, improvement"""

        try:
            response = await self.ai_engine.generate(prompt, temperature=0.2)
            
            prediction = json.loads(response.content)
            
            # Store feedback for learning
            if not hasattr(self, 'prediction_feedback'):
                self.prediction_feedback = []
                
            self.prediction_feedback.append({
                "message_id": message.get("message_id"),
                "prediction": prediction,
                "lead_score": lead.score.total_score
            })
                
            return float(prediction.get("probability", 0.5))
        except:
            # Fallback calculation based on heuristics
            return self._calculate_response_probability_heuristic(message, lead)
            
    def _calculate_response_probability_heuristic(self, message: Dict, lead: Lead) -> float:
        """Enhanced heuristic-based response prediction with quality correlation"""
        score = 0.3  # Lower base score
        
        # Lead quality bonus (reduced impact)
        score += (lead.score.total_score / 100) * 0.2
        
        # Message quality factors (more discriminating)
        subject = message.get("subject", "")
        body = message.get("body", "")
        body_words = body.split()
        
        # Subject line quality
        if 30 < len(subject) < 60:  # Optimal length
            score += 0.1
        if any(word in subject.lower() for word in ["question", "opportunity", "partnership"]):
            score += 0.05
        if any(spam in subject.lower() for spam in ["free", "guarantee", "urgent", "!!!"]):
            score -= 0.2
            
        # Body quality
        if 50 < len(body_words) < 150:  # Optimal length
            score += 0.15
        elif len(body_words) > 200:  # Too long
            score -= 0.1
        elif len(body_words) < 30:  # Too short
            score -= 0.1
            
        # Personalization (higher weight)
        if lead.contact.first_name in body:
            score += 0.15
        if lead.company.name in body:
            score += 0.1
            
        # Professional quality indicators
        if any(word in body.lower() for word in ["noticed", "congratulations", "brief call", "discuss"]):
            score += 0.1
        if "would you be" in body.lower() or "are you interested" in body.lower():
            score += 0.05
            
        # Negative quality indicators
        spam_phrases = ["guarantee", "100%", "free", "limited time", "act now", "click here"]
        spam_count = sum(1 for phrase in spam_phrases if phrase in body.lower())
        score -= spam_count * 0.1
        
        # Excessive punctuation or caps
        if body.count("!") > 2:
            score -= 0.1
        caps_ratio = sum(1 for c in body if c.isupper()) / max(1, len(body))
        if caps_ratio > 0.1:
            score -= 0.15
            
        return min(0.9, max(0.05, score))

    async def _quality_check_ai_message(self, message: str, lead: Lead) -> Dict[str, Any]:
        """Ensure AI-generated message meets quality standards"""
        
        checks = {
            "length_appropriate": 50 < len(message.split()) < 300,
            "no_hallucinations": self._check_no_hallucinations(message, lead),
            "professional_tone": await self._check_professional_tone(message),
            "no_spam_triggers": self._check_spam_score(message) < 3.0,
            "has_personalization": lead.contact.first_name in message or lead.company.name in message,
            "has_clear_cta": any(phrase in message.lower() for phrase in ["call", "meeting", "discuss", "chat", "connect", "schedule"]),
            "no_sensitive_topics": self._check_no_sensitive_topics(message)
        }
        
        passed = all(checks.values())
        
        return {
            "passed": passed,
            "checks": checks,
            "issues": [k for k, v in checks.items() if not v]
        }
    
    def _check_no_hallucinations(self, message: str, lead: Lead) -> bool:
        """Verify message doesn't contain false information"""
        # Check that any mentioned facts match lead data
        
        # Must contain actual company name
        if lead.company.name not in message:
            return False
        
        # Don't mention specific people unless we know them
        import re
        names_mentioned = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', message)
        known_names = [lead.contact.full_name]
        if hasattr(lead.contact, 'first_name') and hasattr(lead.contact, 'last_name'):
            known_names.append(f"{lead.contact.first_name} {lead.contact.last_name}")
            
        for name in names_mentioned:
            if name not in known_names and name not in ["Sales Representative", "Account Executive"]:
                return False  # Mentioned unknown person
                
        return True
    
    async def _check_professional_tone(self, message: str) -> bool:
        """Check if message maintains professional tone"""
        unprofessional_phrases = [
            "guarantee success", "100% guaranteed", "no risk", "act now",
            "limited time", "once in a lifetime", "don't miss out", "urgent"
        ]
        
        message_lower = message.lower()
        return not any(phrase in message_lower for phrase in unprofessional_phrases)
    
    def _check_spam_score(self, message: str) -> float:
        """Simple spam score calculation"""
        spam_triggers = [
            "free", "guarantee", "no obligation", "act now", "limited time",
            "click here", "buy now", "special offer", "!!!!", "$$",
            "100% guaranteed", "risk-free", "urgent", "winner"
        ]
        
        message_lower = message.lower()
        score = 0.0
        
        for trigger in spam_triggers:
            if trigger in message_lower:
                score += 0.5
                
        # Excessive caps
        caps_ratio = sum(1 for c in message if c.isupper()) / max(1, len(message))
        if caps_ratio > 0.3:
            score += 2.0
            
        return score

    def _check_no_sensitive_topics(self, message: str) -> bool:
        """Ensure message avoids sensitive topics"""
        sensitive_terms = [
            "layoff", "fired", "bankruptcy", "lawsuit", "scandal",
            "controversy", "failure", "crisis", "problem"
        ]
        
        message_lower = message.lower()
        return not any(term in message_lower for term in sensitive_terms)

    def _compose_with_template(self, lead: Lead, template_id: str, config: OutreachConfig) -> OutreachMessage:
        """
        Generate message using template system.
        
        Steps:
        1. Load template
        2. Extract variables from lead data
        3. Fill in missing variables with smart defaults
        4. Apply industry-specific variants
        5. Personalize based on depth setting
        """
        try:
            template = self.template_library.get_template(template_id)
            if not template:
                raise ValueError(f"Template {template_id} not found")
            
            # Extract personalization variables
            variables = self._extract_personalization_variables(lead)
            
            # Add sender information
            variables.update(config.sender_info)
            
            # Fill in missing variables with smart defaults
            variables = self._smart_defaults(variables, template.variables)
            
            # Apply industry-specific variants
            if lead.company.industry in template.industry_variants:
                industry_variant = template.industry_variants[lead.company.industry]
                variables["industry_specific"] = industry_variant
            
            # Select and personalize subject line
            subject = self.optimize_subject_line(template.subject_lines, lead)
            subject = self._fill_template_variables(subject, variables)
            
            # Fill template body
            body = self._fill_template_variables(template.body_template, variables)
            
            # Apply personalization depth
            if config.personalization_depth == "deep":
                body = self._enhance_personalization(body, lead, variables)
            
            # Add calendar link if requested
            if config.include_calendar_link and "calendar_link" not in variables:
                variables["calendar_link"] = config.sender_info.get("calendar_link", "[Calendar Link]")
            
            # Ensure message length
            body = self._ensure_message_length(body, config.max_length)
            
            return OutreachMessage(
                message_id=f"msg_{uuid.uuid4()}",
                lead_id=lead.lead_id,
                subject=subject,
                body=body,
                tone=template.tone,
                category=template.category,
                template_id=template_id,
                personalization_score=0.0,  # Will be calculated later
                predicted_response_rate=0.0,  # Will be calculated later
                generation_mode=self.mode,
                ab_variant="A",
                created_at=datetime.now(),
                metadata={
                    "template_name": template.name,
                    "variables_used": list(variables.keys()),
                    "personalization_depth": config.personalization_depth
                }
            )
            
        except Exception as e:
            self.logger.error(f"Error composing with template: {e}")
            raise

    async def _compose_with_ai(self, lead: Lead, style_guide: Dict, config: OutreachConfig) -> OutreachMessage:
        """
        Generate message using AI (placeholder for future).
        
        For now, returns enhanced template version.
        """
        self.logger.info("AI composition requested - using enhanced template approach")
        
        # For now, use the best template and enhance it
        template_id = self.select_template(lead, config)
        base_message = self._compose_with_template(lead, template_id, config)
        
        # Simulate AI enhancement
        enhanced_body = self._ai_enhance_message(base_message.body, lead, style_guide)
        enhanced_subject = self._ai_enhance_subject(base_message.subject, lead)
        
        base_message.body = enhanced_body
        base_message.subject = enhanced_subject
        base_message.generation_mode = "ai"
        base_message.metadata["ai_enhanced"] = True
        
        return base_message

    async def _enhance_with_ai(self, base_message: OutreachMessage, lead: Lead, config: OutreachConfig) -> OutreachMessage:
        """Enhance template message with AI (hybrid mode)"""
        self.logger.info("Enhancing template with AI")
        
        # Simulate AI enhancement
        enhanced_body = self._ai_enhance_message(base_message.body, lead, {})
        base_message.body = enhanced_body
        base_message.generation_mode = "hybrid"
        base_message.metadata["ai_enhanced"] = True
        
        return base_message

    def _extract_personalization_variables(self, lead: Lead) -> Dict[str, str]:
        """
        Extract all available personalization data from lead.
        
        Returns:
        - first_name, last_name, company
        - recent_achievement (from company news)
        - pain_point (highest priority from company pain points)
        - industry, department, title
        - similar_company (from same industry in database)
        - specific_result (based on pain point)
        """
        variables = {}
        
        # Basic contact info
        variables["first_name"] = lead.contact.first_name
        variables["last_name"] = lead.contact.last_name
        variables["full_name"] = lead.contact.full_name
        variables["company"] = lead.company.name
        variables["title"] = lead.contact.title
        variables["department"] = lead.contact.department
        variables["industry"] = lead.company.industry
        
        # Company details
        variables["company_size"] = str(lead.company.employee_count)
        variables["company_location"] = lead.company.location
        variables["company_founded"] = str(lead.company.founded_year)
        
        # Recent achievement from company news
        if hasattr(lead.company, 'recent_news') and lead.company.recent_news:
            latest_news = lead.company.recent_news[0]
            variables["recent_achievement"] = latest_news.title.lower()
        else:
            # Use industry-specific default
            achievements = self.company_achievements.get(lead.company.industry, ["has been growing rapidly"])
            variables["recent_achievement"] = random.choice(achievements)
        
        # Pain points
        if hasattr(lead.company, 'pain_points') and lead.company.pain_points:
            variables["pain_point"] = lead.company.pain_points[0]
        else:
            # Use industry-specific default
            pain_points = self.pain_points_mapping.get(lead.company.industry, ["operational efficiency"])
            variables["pain_point"] = random.choice(pain_points)
        
        # Similar company (simplified - would use actual database lookup)
        industry_companies = {
            "SaaS": ["Salesforce", "HubSpot", "Zendesk"],
            "FinTech": ["Stripe", "Square", "Plaid"],
            "E-commerce": ["Shopify", "BigCommerce", "Magento"],
            "Healthcare": ["Epic", "Cerner", "Veracyte"],
            "Manufacturing": ["GE", "Siemens", "Honeywell"]
        }
        similar_companies = industry_companies.get(lead.company.industry, ["companies like yours"])
        variables["similar_company"] = random.choice(similar_companies)
        
        # Specific result based on pain point
        results_mapping = {
            "customer churn": "reduce churn by 30%",
            "scaling infrastructure": "scale 10x without downtime",
            "regulatory compliance": "achieve compliance 50% faster",
            "cart abandonment": "recover 25% of abandoned carts",
            "production efficiency": "increase efficiency by 35%"
        }
        variables["specific_result"] = results_mapping.get(variables["pain_point"], "achieve significant improvements")
        
        # Value proposition
        value_props = {
            "SaaS": "increase customer retention and reduce churn",
            "FinTech": "streamline compliance and enhance security",
            "E-commerce": "boost conversions and customer lifetime value",
            "Healthcare": "improve patient outcomes and operational efficiency",
            "Manufacturing": "optimize production and reduce costs"
        }
        variables["value_proposition"] = value_props.get(lead.company.industry, "drive growth and efficiency")
        
        return variables

    def _smart_defaults(self, variables: Dict[str, str], required: List[str]) -> Dict[str, str]:
        """
        Fill in missing variables with intelligent defaults.
        
        Examples:
        - Missing recent_achievement → "has been growing rapidly"
        - Missing pain_point → industry-specific default
        - Missing similar_company → "companies like yours"
        """
        defaults = {
            "recent_achievement": "has been growing rapidly",
            "pain_point": "operational efficiency",
            "similar_company": "companies like yours",
            "specific_result": "achieve significant improvements",
            "value_proposition": "drive growth and efficiency",
            "sender_name": "Sales Team",
            "sender_title": "Account Executive",
            "sender_company": "Our Company",
            "calendar_link": "[Calendar Link]",
            "ps_line": "Looking forward to connecting!",
            "timeframe": "next quarter",
            "technical_area": "system architecture",
            "technical_challenge": "scalability",
            "benefit_1": "improved performance",
            "benefit_2": "reduced costs",
            "benefit_3": "enhanced security",
            "technical_metric": "40% performance improvement",
            "technical_credentials": "10+ years in system architecture"
        }
        
        for var in required:
            if var not in variables:
                variables[var] = defaults.get(var, f"[{var}]")
        
        return variables

    def _fill_template_variables(self, template: str, variables: Dict[str, str]) -> str:
        """Fill template variables with actual values"""
        result = template
        for var, value in variables.items():
            placeholder = f"{{{{{var}}}}}"
            result = result.replace(placeholder, str(value))
        return result

    def _enhance_personalization(self, body: str, lead: Lead, variables: Dict[str, str]) -> str:
        """Add deep personalization touches"""
        # Add industry-specific insights
        if lead.company.industry in self.industry_insights:
            insights = self.industry_insights[lead.company.industry]
            trend = random.choice(insights["trends"])
            body += f"\n\nP.S. I see {lead.company.industry} is embracing {trend} - exciting times ahead!"
        
        return body

    def _ensure_message_length(self, body: str, max_length: int) -> str:
        """Ensure message doesn't exceed max length"""
        words = body.split()
        if len(words) > max_length:
            body = " ".join(words[:max_length]) + "..."
        return body

    def _ai_enhance_message(self, body: str, lead: Lead, style_guide: Dict) -> str:
        """Simulate AI enhancement of message"""
        # For now, just add some AI-like touches
        enhancements = [
            f"Based on {lead.company.name}'s recent growth trajectory, ",
            f"Given your role as {lead.contact.title}, ",
            f"Considering {lead.company.industry} market dynamics, "
        ]
        
        enhancement = random.choice(enhancements)
        sentences = body.split('. ')
        if len(sentences) > 1:
            sentences[1] = enhancement + sentences[1].lower()
            body = '. '.join(sentences)
        
        return body

    def _ai_enhance_subject(self, subject: str, lead: Lead) -> str:
        """Simulate AI enhancement of subject line"""
        # Add urgency or curiosity elements
        enhancements = [
            f"Re: {lead.company.name}'s growth opportunity",
            f"Quick question for {lead.contact.first_name}",
            f"{lead.company.name} + efficiency gains"
        ]
        
        return random.choice(enhancements)

    def _create_style_guide(self, lead: Lead, config: OutreachConfig) -> Dict:
        """Create style guide for AI composition"""
        return {
            "tone": config.tone or ToneStyle.FORMAL,
            "industry": lead.company.industry,
            "seniority": lead.contact.seniority,
            "company_size": lead.company.employee_count,
            "personalization_depth": config.personalization_depth
        }

    def _analyze_lead_context(self, lead: Lead) -> Dict:
        """Analyze lead context for better composition"""
        return {
            "lead_score": lead.score.total_score,
            "industry": lead.company.industry,
            "title": lead.contact.title,
            "company_size": lead.company.employee_count,
            "priority": lead.outreach_priority
        }

    def _generate_ab_variants(self, base_message: OutreachMessage, lead: Lead) -> List[Dict]:
        """
        Generate A/B test variants of the message.
        
        Variations:
        - Different subject lines
        - Different CTAs
        - Different value propositions emphasis
        """
        variants = []
        
        # Get template for more subject lines
        if base_message.template_id:
            template = self.template_library.get_template(base_message.template_id)
            if template and len(template.subject_lines) > 1:
                for i, subject in enumerate(template.subject_lines[:3]):
                    variant_letter = chr(65 + i)  # A, B, C
                    variables = self._extract_personalization_variables(lead)
                    filled_subject = self._fill_template_variables(subject, variables)
                    
                    variants.append({
                        "variant": variant_letter,
                        "subject": filled_subject,
                        "body": base_message.body,
                        "changes": f"Subject line variation {variant_letter}"
                    })
        
        # CTA variations
        cta_variations = [
            "Would you be open to a brief 15-minute call?",
            "Worth a quick chat to explore this?",
            "Available for a brief conversation this week?"
        ]
        
        for i, cta in enumerate(cta_variations):
            variant_letter = chr(65 + i + 3)  # D, E, F
            modified_body = base_message.body.replace(
                "Would you be open to a brief 15-minute call",
                cta
            )
            variants.append({
                "variant": variant_letter,
                "subject": base_message.subject,
                "body": modified_body,
                "changes": f"CTA variation {variant_letter}"
            })
        
        return variants[:3]  # Return max 3 variants

    def optimize_subject_line(self, subject_lines: List[str], lead: Lead) -> str:
        """
        Select best subject line based on lead characteristics.
        
        Factors:
        - Industry preferences
        - Title/seniority level
        - Company size
        - Previous engagement patterns
        """
        if not subject_lines:
            return "Quick question about your business"
        
        # Score each subject line
        scores = []
        for subject in subject_lines:
            score = 0
            
            # Industry preferences
            if lead.company.industry == "SaaS" and "question" in subject.lower():
                score += 10
            elif lead.company.industry == "FinTech" and "partnership" in subject.lower():
                score += 10
            elif lead.company.industry == "E-commerce" and "idea" in subject.lower():
                score += 10
            
            # Title/seniority preferences
            if "C-Level" in lead.contact.seniority and len(subject.split()) <= 6:
                score += 15  # Executives prefer shorter subjects
            elif "VP" in lead.contact.title and "quick" in subject.lower():
                score += 10
            
            # Company size preferences
            if lead.company.employee_count > 1000 and "partnership" in subject.lower():
                score += 5
            elif lead.company.employee_count < 100 and "idea" in subject.lower():
                score += 5
            
            scores.append(score)
        
        # Return subject line with highest score
        best_index = scores.index(max(scores))
        return subject_lines[best_index]

    def calculate_personalization_score(self, message: str, lead: Lead) -> float:
        """
        Calculate how personalized the message is.
        
        Factors:
        - Number of personalized elements used
        - Specificity of references
        - Relevance of pain points mentioned
        - Quality of company research shown
        
        Returns: 0.0 (generic) to 1.0 (highly personalized)
        """
        score = 0.0
        message_lower = message.lower()
        
        # Check for personalized elements
        if lead.contact.first_name.lower() in message_lower:
            score += 0.15
        
        if lead.company.name.lower() in message_lower:
            score += 0.20
        
        if lead.company.industry.lower() in message_lower:
            score += 0.15
        
        if lead.contact.title.lower() in message_lower:
            score += 0.10
        
        # Check for specific company references
        if hasattr(lead.company, 'recent_news') and lead.company.recent_news:
            for news in lead.company.recent_news:
                if any(word in message_lower for word in news.title.lower().split()[:3]):
                    score += 0.15
                    break
        
        # Check for pain point relevance
        if hasattr(lead.company, 'pain_points') and lead.company.pain_points:
            for pain_point in lead.company.pain_points:
                if pain_point.lower() in message_lower:
                    score += 0.15
                    break
        
        # Check for industry-specific terminology
        industry_terms = {
            "SaaS": ["churn", "ARR", "MRR", "onboarding", "activation"],
            "FinTech": ["compliance", "security", "fraud", "transaction", "regulatory"],
            "E-commerce": ["conversion", "cart", "checkout", "fulfillment", "retention"],
            "Healthcare": ["patient", "HIPAA", "clinical", "outcomes", "care"],
            "Manufacturing": ["production", "efficiency", "quality", "automation", "supply chain"]
        }
        
        terms = industry_terms.get(lead.company.industry, [])
        for term in terms:
            if term in message_lower:
                score += 0.05
                break
        
        return min(score, 1.0)

    def predict_response_rate(self, message: OutreachMessage, lead: Lead) -> float:
        """
        Predict likelihood of response.
        
        Based on:
        - Message length (optimal: 150-200 words)
        - Personalization score
        - Subject line quality
        - Lead score
        - Time of week/day
        
        Returns: 0.0 (unlikely) to 1.0 (very likely)
        """
        base_rate = 0.15  # Base response rate
        
        # Factor 1: Message length (optimal: 150-200 words)
        word_count = len(message.body.split())
        if 150 <= word_count <= 200:
            length_factor = 1.0
        elif 100 <= word_count < 150 or 200 < word_count <= 250:
            length_factor = 0.8
        else:
            length_factor = 0.6
        
        # Factor 2: Personalization score
        personalization_factor = message.personalization_score
        
        # Factor 3: Subject line quality (simplified)
        subject_quality = 0.8  # Default
        if len(message.subject.split()) <= 8:
            subject_quality = 0.9
        if message.subject.endswith('?'):
            subject_quality += 0.1
        
        # Factor 4: Lead score influence
        lead_score_factor = min(lead.score.total_score / 100, 1.0)
        
        # Factor 5: Industry response rates
        industry_rates = {
            "SaaS": 0.18,
            "FinTech": 0.12,
            "E-commerce": 0.15,
            "Healthcare": 0.10,
            "Manufacturing": 0.08
        }
        industry_factor = industry_rates.get(lead.company.industry, 0.12)
        
        # Combine factors
        predicted_rate = (
            base_rate * 0.2 +
            length_factor * self.response_rate_factors["message_length"] +
            personalization_factor * self.response_rate_factors["personalization_score"] +
            subject_quality * self.response_rate_factors["subject_line_quality"] +
            lead_score_factor * self.response_rate_factors["lead_score"] +
            industry_factor * self.response_rate_factors["timing"]
        )
        
        return min(predicted_rate, 1.0)

    def select_template(self, lead: Lead, config: OutreachConfig) -> str:
        """
        Intelligently select best template for lead.
        
        Consider:
        - Lead score (high score → more direct approach)
        - Industry (technical vs non-technical)
        - Title/seniority (executive vs manager)
        - Company stage (startup vs enterprise)
        - Previous interactions
        """
        # Get templates for the specified category
        templates = self.template_library.get_templates_by_category(config.category)
        
        if not templates:
            # Default to cold outreach if category not found
            templates = self.template_library.get_templates_by_category("cold_outreach")
        
        # Score each template
        template_scores = []
        for template in templates:
            score = 0
            
            # Lead score influence
            if lead.score.total_score >= 80:
                # High score leads → more direct approach
                if template.tone == ToneStyle.EXECUTIVE:
                    score += 20
                elif template.tone == ToneStyle.FORMAL:
                    score += 15
            elif lead.score.total_score >= 60:
                # Medium score leads → balanced approach
                if template.tone == ToneStyle.FORMAL:
                    score += 20
                elif template.tone == ToneStyle.CASUAL:
                    score += 15
            else:
                # Lower score leads → more casual approach
                if template.tone == ToneStyle.CASUAL:
                    score += 20
                elif template.tone == ToneStyle.FORMAL:
                    score += 10
            
            # Industry preferences
            if lead.company.industry in ["SaaS", "FinTech"]:
                if template.tone == ToneStyle.TECHNICAL:
                    score += 15
                elif template.tone == ToneStyle.FORMAL:
                    score += 10
            elif lead.company.industry in ["Healthcare", "Manufacturing"]:
                if template.tone == ToneStyle.FORMAL:
                    score += 15
                elif template.tone == ToneStyle.EXECUTIVE:
                    score += 10
            
            # Title/seniority preferences
            if "C-Level" in lead.contact.seniority:
                if template.tone == ToneStyle.EXECUTIVE:
                    score += 25
                elif template.tone == ToneStyle.FORMAL:
                    score += 15
            elif "VP" in lead.contact.title:
                if template.tone == ToneStyle.FORMAL:
                    score += 20
                elif template.tone == ToneStyle.EXECUTIVE:
                    score += 15
            elif "Director" in lead.contact.title:
                if template.tone == ToneStyle.FORMAL:
                    score += 20
                elif template.tone == ToneStyle.CASUAL:
                    score += 10
            
            # Company size preferences
            if lead.company.employee_count > 1000:
                if template.tone == ToneStyle.EXECUTIVE:
                    score += 10
                elif template.tone == ToneStyle.FORMAL:
                    score += 5
            elif lead.company.employee_count < 100:
                if template.tone == ToneStyle.CASUAL:
                    score += 10
                elif template.tone == ToneStyle.FORMAL:
                    score += 5
            
            # Tone preference from config
            if config.tone and template.tone == config.tone:
                score += 30
            
            template_scores.append((template.id, score))
        
        # Return template with highest score
        if template_scores:
            best_template = max(template_scores, key=lambda x: x[1])
            return best_template[0]
        
        # Fallback to first template
        return templates[0].id if templates else "cold_outreach_formal_1"
    
    async def send_real_email(
        self,
        message: OutreachMessage,
        lead: Lead,
        send_immediately: bool = False,
        queue_priority: int = 5
    ) -> Dict[str, Any]:
        """
        Send real email via Gmail API with tracking and safety features
        
        Args:
            message: Outreach message to send
            lead: Lead information for personalization
            send_immediately: If True, send now; if False, add to queue
            queue_priority: Queue priority (1-10, lower = higher priority)
            
        Returns:
            Dictionary with send status and tracking information
        """
        if not self.gmail_enabled or not self.gmail_client:
            return {
                "success": False,
                "error": "Gmail integration not available",
                "fallback": "email_sending_disabled"
            }
        
        try:
            # Create email recipients
            recipients = []
            for contact in [lead.contact]:  # Can extend to multiple contacts
                recipient = EmailRecipient(
                    email=contact.email,
                    name=contact.full_name,
                    lead_id=lead.lead_id
                )
                recipients.append(recipient)
            
            # Convert text body to HTML if needed
            html_body = self._convert_to_html(message.body, lead)
            
            # Create unsubscribe URL
            unsubscribe_url = self._generate_unsubscribe_url(lead, message.message_id)
            
            # Create Gmail message
            gmail_message = EmailMessage(
                id=message.message_id,
                to=recipients,
                subject=message.subject,
                text_body=message.body,
                html_body=html_body,
                tracking_enabled=True,
                unsubscribe_url=unsubscribe_url,
                thread_id=None  # For now, not handling threads
            )
            
            if send_immediately:
                # Send immediately
                result = await self.gmail_client.send_email(
                    gmail_message,
                    self.user_id,
                    bypass_limits=False
                )
                
                if result["success"]:
                    # Update lead with tracking information
                    await self._update_lead_tracking(lead, message, result)
                    
                    return {
                        "success": True,
                        "method": "immediate_send",
                        "gmail_id": result.get("gmail_id"),
                        "thread_id": result.get("thread_id"),
                        "tracking_ids": [r.tracking_id for r in recipients],
                        "test_mode": result.get("test_mode", False)
                    }
                else:
                    return {
                        "success": False,
                        "error": result.get("error"),
                        "queued_for_retry": result.get("queued_for_retry", False)
                    }
            else:
                # Add to queue
                queued = await self.gmail_client.add_to_queue(
                    gmail_message,
                    self.user_id,
                    priority=queue_priority,
                    delay_minutes=0
                )
                
                if queued:
                    return {
                        "success": True,
                        "method": "queued",
                        "message_id": message.message_id,
                        "queue_priority": queue_priority,
                        "tracking_ids": [r.tracking_id for r in recipients]
                    }
                else:
                    return {
                        "success": False,
                        "error": "Failed to add to queue"
                    }
        
        except Exception as e:
            self.logger.error(f"Failed to send email {message.message_id}: {e}")
            return {
                "success": False,
                "error": str(e),
                "message_id": message.message_id
            }
    
    def _convert_to_html(self, text_body: str, lead: Lead) -> str:
        """Convert text email to HTML with proper formatting"""
        
        # Escape HTML characters
        import html
        escaped_text = html.escape(text_body)
        
        # Convert line breaks to <br> tags
        html_body = escaped_text.replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        # Wrap in paragraphs
        html_body = f'<p>{html_body}</p>'
        
        # Create full HTML email template
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>{lead.company.name} - Outreach</title>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    margin: 0;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .email-container {{
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .email-header {{
                    border-bottom: 2px solid #f0f0f0;
                    padding-bottom: 20px;
                    margin-bottom: 30px;
                }}
                .email-content {{
                    font-size: 16px;
                    line-height: 1.7;
                }}
                .email-content p {{
                    margin: 0 0 20px 0;
                }}
                .email-footer {{
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #eee;
                    font-size: 14px;
                    color: #666;
                    text-align: center;
                }}
                .signature {{
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #f0f0f0;
                    font-size: 14px;
                    color: #666;
                }}
                a {{
                    color: #0066cc;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="email-header">
                    <h2 style="margin: 0; color: #333;">Personal Message for {lead.contact.first_name}</h2>
                </div>
                
                <div class="email-content">
                    {html_body}
                </div>
                
                <div class="signature">
                    <p><strong>{self.config.get('sender_name', 'Sales Team')}</strong><br>
                    {self.config.get('sender_title', 'Account Executive')}<br>
                    {self.config.get('sender_company', 'Our Company')}<br>
                    {self.config.get('sender_phone', '')}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def _generate_unsubscribe_url(self, lead: Lead, message_id: str) -> str:
        """Generate unique unsubscribe URL for the lead"""
        
        # Create unique token for unsubscribe
        import hashlib
        token_data = f"{lead.lead_id}:{message_id}:{lead.contact.email}"
        token = hashlib.sha256(token_data.encode()).hexdigest()[:16]
        
        base_url = self.config.get('base_url', 'https://localhost:8000')
        return f"{base_url}/api/unsubscribe/{token}"
    
    async def _update_lead_tracking(self, lead: Lead, message: OutreachMessage, send_result: Dict):
        """Update lead with email tracking information"""
        
        if not self.redis_client:
            return
        
        try:
            # Store lead-message mapping for tracking
            tracking_data = {
                "lead_id": lead.lead_id,
                "message_id": message.message_id,
                "gmail_id": send_result.get("gmail_id"),
                "thread_id": send_result.get("thread_id"),
                "sent_at": datetime.now().isoformat(),
                "subject": message.subject,
                "recipient": lead.contact.email,
                "contact_name": lead.contact.full_name,
                "company_name": lead.company.name,
                "lead_score": lead.score.total_score
            }
            
            # Store in Redis for 30 days
            tracking_key = f"outreach_tracking:{message.message_id}"
            await self.redis_client.setex(
                tracking_key,
                timedelta(days=30),
                json.dumps(tracking_data)
            )
            
            # Update lead's email history
            lead_history_key = f"lead_emails:{lead.lead_id}"
            email_entry = {
                "message_id": message.message_id,
                "sent_at": datetime.now().isoformat(),
                "subject": message.subject,
                "gmail_id": send_result.get("gmail_id")
            }
            
            # Add to lead's email history (keep last 50 emails)
            await self.redis_client.lpush(lead_history_key, json.dumps(email_entry))
            await self.redis_client.ltrim(lead_history_key, 0, 49)
            await self.redis_client.expire(lead_history_key, timedelta(days=90))
            
        except Exception as e:
            self.logger.error(f"Failed to update lead tracking: {e}")
    
    async def get_email_status(self, message_id: str) -> Optional[Dict[str, Any]]:
        """Get email sending and tracking status"""
        
        if not self.gmail_client or not self.redis_client:
            return None
        
        try:
            # Get tracking data
            tracking_key = f"outreach_tracking:{message_id}"
            tracking_data = await self.redis_client.get(tracking_key)
            
            if not tracking_data:
                return None
            
            tracking_info = json.loads(tracking_data)
            
            # Get Gmail tracking summary (if available)
            gmail_summary = None
            if "tracking_ids" in tracking_info:
                for tracking_id in tracking_info["tracking_ids"]:
                    summary = await self.gmail_client.get_tracking_summary(tracking_id)
                    if summary:
                        gmail_summary = summary
                        break
            
            return {
                "message_id": message_id,
                "tracking_info": tracking_info,
                "gmail_tracking": gmail_summary,
                "status": "sent" if tracking_info.get("gmail_id") else "queued"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get email status: {e}")
            return None
    
    async def get_user_email_stats(self, days: int = 30) -> Dict[str, Any]:
        """Get email sending statistics for the user"""
        
        if not self.gmail_client:
            return {"error": "Gmail integration not available"}
        
        try:
            return await self.gmail_client.get_user_stats(self.user_id, days)
        except Exception as e:
            self.logger.error(f"Failed to get email stats: {e}")
            return {"error": str(e)}