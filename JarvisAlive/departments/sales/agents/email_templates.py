from typing import Dict, List, Optional
from pydantic import BaseModel
from enum import Enum


class ToneStyle(str, Enum):
    FORMAL = "formal"
    CASUAL = "casual"
    TECHNICAL = "technical"
    EXECUTIVE = "executive"


class EmailTemplate(BaseModel):
    id: str
    name: str
    category: str  # "cold_outreach", "follow_up", "meeting_request", "revival"
    tone: ToneStyle
    subject_lines: List[str]  # A/B test variations
    body_template: str
    variables: List[str]  # Required variables
    industry_variants: Dict[str, str]  # Industry-specific versions


class EmailTemplateLibrary:
    def __init__(self):
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, EmailTemplate]:
        """Load all email templates"""
        return {
            # ========== COLD OUTREACH TEMPLATES ==========
            
            "cold_outreach_formal_1": EmailTemplate(
                id="cold_outreach_formal_1",
                name="Formal Introduction - Pain Point Focus",
                category="cold_outreach",
                tone=ToneStyle.FORMAL,
                subject_lines=[
                    "Quick question about {{company}}'s {{pain_point}}",
                    "{{first_name}}, solving {{pain_point}} at {{company}}",
                    "Idea for {{company}}'s {{department}} team"
                ],
                body_template="""Hi {{first_name}},

I noticed that {{company}} {{recent_achievement}}. Congratulations on that milestone!

Many {{industry}} companies at your stage struggle with {{pain_point}}. We've helped similar companies like {{similar_company}} achieve {{specific_result}}.

I'm curious - is {{pain_point}} a priority for {{company}} this quarter?

Would you be open to a brief 15-minute call to discuss how we've helped companies in {{industry}} {{value_proposition}}?

Best regards,
{{sender_name}}
{{sender_title}}
{{sender_company}}""",
                variables=["first_name", "company", "recent_achievement", "industry", 
                          "pain_point", "similar_company", "specific_result", "department",
                          "value_proposition", "sender_name", "sender_title", "sender_company"],
                industry_variants={
                    "SaaS": "We've helped similar SaaS companies reduce churn by 30%",
                    "FinTech": "We've helped FinTech companies achieve SOC2 compliance 50% faster",
                    "E-commerce": "We've helped e-commerce brands increase conversion rates by 25%",
                    "Healthcare": "We've helped healthcare companies reduce patient onboarding time by 40%",
                    "Manufacturing": "We've helped manufacturers reduce downtime by 35%"
                }
            ),
            
            "cold_outreach_casual_2": EmailTemplate(
                id="cold_outreach_casual_2",
                name="Casual Introduction - Value Proposition Focus",
                category="cold_outreach",
                tone=ToneStyle.CASUAL,
                subject_lines=[
                    "{{first_name}} - quick thought on {{company}}'s growth",
                    "Noticed {{company}} is hiring - scaling challenge?",
                    "Fellow {{industry}} enthusiast reaching out"
                ],
                body_template="""Hey {{first_name}}!

Saw that {{company}} is {{recent_achievement}} - that's awesome! 🎉

I work with {{industry}} companies and noticed you might be dealing with {{pain_point}}. We just helped {{similar_company}} {{specific_result}}, and I think we could do something similar for {{company}}.

Worth a quick chat? I promise to keep it under 15 minutes.

Here's my calendar if you want to grab time: {{calendar_link}}

Cheers,
{{sender_name}}

P.S. {{ps_line}}""",
                variables=["first_name", "company", "recent_achievement", "industry",
                          "pain_point", "similar_company", "specific_result",
                          "calendar_link", "sender_name", "ps_line"],
                industry_variants={
                    "SaaS": "P.S. Love what you're building - the {{product_feature}} feature is brilliant!",
                    "FinTech": "P.S. Your approach to {{fintech_area}} is really innovative",
                    "E-commerce": "P.S. Your product selection is impressive - especially the {{product_category}}",
                    "Healthcare": "P.S. Your focus on patient experience really stands out",
                    "Manufacturing": "P.S. Your commitment to innovation in {{manufacturing_area}} is admirable"
                }
            ),
            
            "cold_outreach_technical_3": EmailTemplate(
                id="cold_outreach_technical_3",
                name="Technical Introduction - Question/Curiosity Focus",
                category="cold_outreach",
                tone=ToneStyle.TECHNICAL,
                subject_lines=[
                    "Technical question about {{company}}'s {{technical_area}}",
                    "{{first_name}} - how are you handling {{technical_challenge}}?",
                    "Thoughts on {{company}}'s approach to {{technical_area}}"
                ],
                body_template="""Hi {{first_name}},

I've been following {{company}}'s technical blog and your approach to {{technical_area}} caught my attention.

Quick question: How are you currently handling {{technical_challenge}}? 

We've developed a solution that helps {{industry}} companies:
• {{benefit_1}}
• {{benefit_2}}
• {{benefit_3}}

{{similar_company}} saw {{technical_metric}} after implementing our approach.

Would you be interested in a technical deep-dive? Happy to share our architecture and benchmarks.

Best,
{{sender_name}}
{{sender_title}} | {{sender_company}}
{{technical_credentials}}""",
                variables=["first_name", "company", "technical_area", "technical_challenge",
                          "industry", "benefit_1", "benefit_2", "benefit_3", "similar_company",
                          "technical_metric", "sender_name", "sender_title", "sender_company",
                          "technical_credentials"],
                industry_variants={
                    "SaaS": "reduce infrastructure costs by 40% while scaling 10x",
                    "FinTech": "achieve 99.99% uptime for critical payment systems",
                    "E-commerce": "handle 100k+ concurrent users during peak sales",
                    "Healthcare": "ensure HIPAA compliance while maintaining performance",
                    "Manufacturing": "reduce sensor data processing time by 70%"
                }
            ),
            
            # ========== FOLLOW-UP TEMPLATES ==========
            
            "follow_up_no_response_1": EmailTemplate(
                id="follow_up_no_response_1",
                name="No Response Follow-up - Friendly Check-in",
                category="follow_up",
                tone=ToneStyle.CASUAL,
                subject_lines=[
                    "Re: {{original_subject}}",
                    "{{first_name}} - did my email get buried?",
                    "Following up - {{company}} + {{value_prop_short}}"
                ],
                body_template="""Hi {{first_name}},

I know your inbox is probably overwhelming - mine certainly is!

Just wanted to float my previous email back to the top. To recap, I reached out because {{recap_reason}}.

If this isn't a priority right now, no worries at all. Would you prefer I check back in {{timeframe}}?

{{sender_name}}

---Original Message---
{{original_message_snippet}}""",
                variables=["first_name", "company", "original_subject", "value_prop_short",
                          "recap_reason", "timeframe", "sender_name", "original_message_snippet"],
                industry_variants={
                    "SaaS": "in Q2 when you're planning next quarter's roadmap",
                    "FinTech": "after your compliance audit wraps up",
                    "E-commerce": "after the holiday season rush",
                    "Healthcare": "when you're evaluating new vendors next quarter",
                    "Manufacturing": "during your next technology review cycle"
                }
            ),
            
            "follow_up_value_add_2": EmailTemplate(
                id="follow_up_value_add_2",
                name="Value-Add Follow-up - Sharing Resource",
                category="follow_up",
                tone=ToneStyle.FORMAL,
                subject_lines=[
                    "{{first_name}} - resource on {{topic}} for {{company}}",
                    "Thought this might help with {{pain_point}}",
                    "Case study: How {{similar_company}} solved {{challenge}}"
                ],
                body_template="""Hi {{first_name}},

Following up on my previous email, I wanted to share something that might be valuable for {{company}}.

We just published a case study on how {{similar_company}} addressed {{challenge}} and achieved {{result}}. Given {{company}}'s focus on {{focus_area}}, I thought you might find their approach interesting.

Here's the link: {{resource_link}}

Key takeaways:
• {{takeaway_1}}
• {{takeaway_2}}
• {{takeaway_3}}

Happy to discuss how this might apply to {{company}}'s specific situation if you're interested.

Best regards,
{{sender_name}}
{{sender_title}}""",
                variables=["first_name", "company", "topic", "pain_point", "similar_company",
                          "challenge", "result", "focus_area", "resource_link",
                          "takeaway_1", "takeaway_2", "takeaway_3", "sender_name", "sender_title"],
                industry_variants={
                    "SaaS": "reduced customer churn from 15% to 8% annually",
                    "FinTech": "decreased fraud detection time by 85%",
                    "E-commerce": "improved checkout conversion by 32%",
                    "Healthcare": "reduced patient wait times by 45%",
                    "Manufacturing": "increased OEE by 23% in 6 months"
                }
            ),
            
            "follow_up_post_conversation": EmailTemplate(
                id="follow_up_post_conversation",
                name="Post-Conversation Follow-up",
                category="follow_up",
                tone=ToneStyle.FORMAL,
                subject_lines=[
                    "Great speaking with you, {{first_name}} - next steps",
                    "Following up on our {{day}} conversation",
                    "{{company}} + {{sender_company}} partnership discussion"
                ],
                body_template="""Hi {{first_name}},

Thank you for taking the time to speak with me {{day}}. I really enjoyed learning about {{specific_topic_discussed}} at {{company}}.

As discussed, here are the next steps:

1. {{next_step_1}}
2. {{next_step_2}}
3. {{next_step_3}}

I've attached {{attachment_description}} for your review.

As mentioned, we can help {{company}} {{key_value_prop}} within {{timeline}}.

Looking forward to {{next_meeting_action}}.

Best regards,
{{sender_name}}
{{sender_title}}
{{sender_company}}""",
                variables=["first_name", "company", "day", "specific_topic_discussed",
                          "next_step_1", "next_step_2", "next_step_3", "attachment_description",
                          "key_value_prop", "timeline", "next_meeting_action",
                          "sender_name", "sender_title", "sender_company"],
                industry_variants={
                    "SaaS": "reduce your customer support tickets by 40%",
                    "FinTech": "strengthen your security posture significantly",
                    "E-commerce": "optimize your conversion funnel for 20%+ improvement",
                    "Healthcare": "streamline patient data management",
                    "Manufacturing": "improve production efficiency by 30%"
                }
            ),
            
            # ========== MEETING REQUEST TEMPLATES ==========
            
            "meeting_request_direct": EmailTemplate(
                id="meeting_request_direct",
                name="Direct Meeting Request",
                category="meeting_request",
                tone=ToneStyle.EXECUTIVE,
                subject_lines=[
                    "15 min chat about {{company}}'s {{objective}}?",
                    "{{first_name}} - partnership opportunity for {{company}}",
                    "Quick call to discuss {{value_proposition}}"
                ],
                body_template="""{{first_name}},

I'll keep this brief. {{sender_company}} helps {{industry}} companies {{core_value_prop}}.

Recent results:
• {{client_1}}: {{result_1}}
• {{client_2}}: {{result_2}}
• {{client_3}}: {{result_3}}

I believe we can deliver similar results for {{company}}.

Are you available for a 15-minute call {{day_options}}?

{{calendar_link}}

{{sender_name}}
{{sender_title}}""",
                variables=["first_name", "company", "objective", "value_proposition",
                          "industry", "core_value_prop", "client_1", "result_1",
                          "client_2", "result_2", "client_3", "result_3",
                          "day_options", "calendar_link", "sender_name", "sender_title", "sender_company"],
                industry_variants={
                    "SaaS": "increase ARR by 25-40% through churn reduction",
                    "FinTech": "reduce compliance costs by 50% while improving security",
                    "E-commerce": "boost revenue by 30% through conversion optimization",
                    "Healthcare": "improve patient satisfaction scores by 35%",
                    "Manufacturing": "reduce operational costs by 20-30%"
                }
            ),
            
            "meeting_request_soft": EmailTemplate(
                id="meeting_request_soft",
                name="Soft Meeting Suggestion",
                category="meeting_request",
                tone=ToneStyle.CASUAL,
                subject_lines=[
                    "{{first_name}} - coffee chat about {{topic}}?",
                    "Comparing notes on {{industry}} trends",
                    "Quick sync on {{mutual_interest}}?"
                ],
                body_template="""Hey {{first_name}},

I've been following {{company}}'s journey in the {{industry}} space - really impressive what you've built!

I'm particularly intrigued by {{specific_company_initiative}}. We work with similar companies and I'd love to compare notes on {{mutual_interest}}.

No sales pitch - just a genuine conversation about {{topic}}. Maybe we could grab a virtual coffee sometime next week?

If you're open to it, here are a few times that work for me:
• {{time_option_1}}
• {{time_option_2}}
• {{time_option_3}}

Or feel free to suggest what works for you!

{{sender_name}}""",
                variables=["first_name", "company", "topic", "industry", "specific_company_initiative",
                          "mutual_interest", "time_option_1", "time_option_2", "time_option_3",
                          "sender_name"],
                industry_variants={
                    "SaaS": "scaling challenges and growth strategies",
                    "FinTech": "regulatory changes and innovation",
                    "E-commerce": "customer experience and retention",
                    "Healthcare": "digital transformation in patient care",
                    "Manufacturing": "Industry 4.0 and automation trends"
                }
            ),
            
            # ========== REVIVAL TEMPLATES ==========
            
            "revival_cold_lead": EmailTemplate(
                id="revival_cold_lead",
                name="Re-engage Cold Lead",
                category="revival",
                tone=ToneStyle.CASUAL,
                subject_lines=[
                    "{{first_name}} - still interested in {{solution_area}}?",
                    "Checking in - {{company}} update",
                    "New approach to {{pain_point}} for {{company}}"
                ],
                body_template="""Hi {{first_name}},

It's been a while since we last connected about {{previous_topic}}. Hope {{company}} has been thriving!

I noticed {{recent_company_news}}, which made me think of you.

Since we last spoke, we've {{new_development}} which specifically addresses {{pain_point}}. {{similar_company}} recently used this to {{achievement}}.

Would it make sense to revisit this conversation? Things have changed quite a bit on our end, and I think the timing might be better now.

No pressure - just thought I'd reach out given {{trigger_reason}}.

All the best,
{{sender_name}}""",
                variables=["first_name", "company", "solution_area", "pain_point",
                          "previous_topic", "recent_company_news", "new_development",
                          "similar_company", "achievement", "trigger_reason", "sender_name"],
                industry_variants={
                    "SaaS": "launched our AI-powered analytics that automates reporting",
                    "FinTech": "achieved SOC2 Type II certification and enhanced our security features",
                    "E-commerce": "developed a new personalization engine",
                    "Healthcare": "received HIPAA certification and expanded our healthcare features",
                    "Manufacturing": "introduced predictive maintenance capabilities"
                }
            ),
            
            "revival_win_back": EmailTemplate(
                id="revival_win_back",
                name="Win-back Past Conversation",
                category="revival",
                tone=ToneStyle.FORMAL,
                subject_lines=[
                    "{{first_name}} - update on what we discussed in {{previous_month}}",
                    "Circling back with better timing for {{company}}",
                    "Re: {{original_subject}} - new developments"
                ],
                body_template="""Hi {{first_name}},

I hope this email finds you well. When we spoke in {{previous_month}}, you mentioned that {{previous_objection}}.

I wanted to reach out because:

1. {{change_1}}
2. {{change_2}}
3. {{change_3}}

Given these changes, I believe we're now in a much better position to help {{company}} {{value_proposition}}.

Would you be open to a brief call to explore if the timing is better now? I can share how {{similar_company}} overcame similar challenges and achieved {{specific_outcome}}.

Available for a quick chat {{availability}}?

Best regards,
{{sender_name}}
{{sender_title}}
{{sender_company}}""",
                variables=["first_name", "company", "previous_month", "original_subject",
                          "previous_objection", "change_1", "change_2", "change_3",
                          "value_proposition", "similar_company", "specific_outcome",
                          "availability", "sender_name", "sender_title", "sender_company"],
                industry_variants={
                    "SaaS": "the timing wasn't right due to your product roadmap",
                    "FinTech": "you were focused on compliance and security audits",
                    "E-commerce": "you were in the middle of platform migration",
                    "Healthcare": "you were dealing with regulatory changes",
                    "Manufacturing": "you were implementing your ERP system"
                }
            )
        }
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a specific template by ID"""
        return self.templates.get(template_id)
    
    def get_templates_by_category(self, category: str) -> List[EmailTemplate]:
        """Get all templates in a specific category"""
        return [t for t in self.templates.values() if t.category == category]
    
    def get_templates_by_tone(self, tone: ToneStyle) -> List[EmailTemplate]:
        """Get all templates with a specific tone"""
        return [t for t in self.templates.values() if t.tone == tone]
    
    def search_templates(self, category: Optional[str] = None, 
                        tone: Optional[ToneStyle] = None) -> List[EmailTemplate]:
        """Search templates by multiple criteria"""
        results = list(self.templates.values())
        
        if category:
            results = [t for t in results if t.category == category]
        
        if tone:
            results = [t for t in results if t.tone == tone]
        
        return results