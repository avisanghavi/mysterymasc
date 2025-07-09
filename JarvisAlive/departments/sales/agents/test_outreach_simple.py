#!/usr/bin/env python3
"""
Simple test for Outreach Composer without dependencies
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from outreach_composer_implementation import OutreachComposerAgent, OutreachConfig, ToneStyle
from email_templates import EmailTemplateLibrary

# Create mock classes for testing
class MockCompany:
    def __init__(self):
        self.name = "TestTech Inc"
        self.industry = "SaaS"
        self.employee_count = 150
        self.location = "San Francisco, CA"
        self.founded_year = 2018
        self.recent_news = []
        self.pain_points = ["customer churn", "scaling infrastructure"]

class MockContact:
    def __init__(self):
        self.first_name = "John"
        self.last_name = "Doe"
        self.full_name = "John Doe"
        self.title = "Chief Technology Officer"
        self.department = "Engineering"
        self.seniority = "C-Level"
        self.email = "john.doe@testtech.com"

class MockScore:
    def __init__(self):
        self.total_score = 85
        self.industry_match = 30
        self.title_relevance = 25
        self.company_size_fit = 20
        self.recent_activity = 10

class MockLead:
    def __init__(self):
        self.lead_id = "lead_test_123"
        self.contact = MockContact()
        self.company = MockCompany()
        self.score = MockScore()
        self.outreach_priority = "high"


async def test_outreach_simple():
    """Test basic outreach composition functionality"""
    
    print("📧 Testing Outreach Composer - Simple Test")
    print("=" * 50)
    
    # Test 1: Template Library
    print("\n📚 Test 1: Template Library")
    library = EmailTemplateLibrary()
    
    print(f"✅ Loaded {len(library.templates)} templates")
    
    # Test templates by category
    cold_templates = library.get_templates_by_category("cold_outreach")
    follow_up_templates = library.get_templates_by_category("follow_up")
    meeting_templates = library.get_templates_by_category("meeting_request")
    
    print(f"   - Cold Outreach: {len(cold_templates)} templates")
    print(f"   - Follow-up: {len(follow_up_templates)} templates")
    print(f"   - Meeting Request: {len(meeting_templates)} templates")
    
    # Test 2: Basic Composition
    print("\n📝 Test 2: Basic Composition")
    
    composer = OutreachComposerAgent(mode="template")
    lead = MockLead()
    
    config = OutreachConfig(
        category="cold_outreach",
        tone=ToneStyle.FORMAL,
        sender_info={
            "sender_name": "Jane Smith",
            "sender_title": "Account Executive",
            "sender_company": "SalesBoost Inc"
        }
    )
    
    try:
        message = await composer.compose_outreach(lead, config)
        print(f"✅ Generated message successfully")
        print(f"   Message ID: {message.message_id}")
        print(f"   Subject: {message.subject}")
        print(f"   Body length: {len(message.body.split())} words")
        print(f"   Template: {message.template_id}")
        print(f"   Tone: {message.tone}")
        print(f"   Category: {message.category}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Template Selection
    print("\n🎯 Test 3: Template Selection")
    
    for category in ["cold_outreach", "follow_up", "meeting_request"]:
        config = OutreachConfig(category=category)
        selected_template = composer.select_template(lead, config)
        print(f"✅ {category} → {selected_template}")
    
    # Test 4: Personalization Variables
    print("\n🎨 Test 4: Personalization Variables")
    
    variables = composer._extract_personalization_variables(lead)
    print(f"✅ Extracted {len(variables)} variables")
    
    key_variables = ["first_name", "company", "industry", "title", "pain_point"]
    for var in key_variables:
        if var in variables:
            print(f"   - {var}: {variables[var]}")
        else:
            print(f"   - {var}: [MISSING]")
    
    # Test 5: Different Tones
    print("\n🎭 Test 5: Different Tones")
    
    tones = [ToneStyle.CASUAL, ToneStyle.TECHNICAL, ToneStyle.EXECUTIVE]
    for tone in tones:
        config = OutreachConfig(
            category="cold_outreach",
            tone=tone,
            sender_info={
                "sender_name": "Test User",
                "sender_title": "Tester",
                "sender_company": "TestCorp"
            }
        )
        
        try:
            message = await composer.compose_outreach(lead, config)
            print(f"✅ {tone.value.upper()} - Template: {message.template_id}")
            print(f"   Subject: {message.subject}")
            
        except Exception as e:
            print(f"❌ {tone.value} error: {e}")
    
    # Test 6: Quality Scoring
    print("\n📊 Test 6: Quality Scoring")
    
    config = OutreachConfig(
        category="cold_outreach",
        sender_info={
            "sender_name": "Quality Tester",
            "sender_title": "QA Engineer",
            "sender_company": "QualityCheck"
        }
    )
    
    try:
        message = await composer.compose_outreach(lead, config)
        
        print(f"✅ Quality Metrics:")
        print(f"   Personalization Score: {message.personalization_score:.2f}")
        print(f"   Predicted Response Rate: {message.predicted_response_rate:.2f}")
        print(f"   Message Length: {len(message.body.split())} words")
        print(f"   Subject Length: {len(message.subject.split())} words")
        
    except Exception as e:
        print(f"❌ Quality scoring error: {e}")
    
    # Test 7: A/B Variants
    print("\n🔬 Test 7: A/B Variants")
    
    try:
        message = await composer.compose_outreach(lead, config)
        variants = message.metadata.get("ab_variants", [])
        
        print(f"✅ Generated {len(variants)} A/B variants")
        for variant in variants[:3]:
            print(f"   Variant {variant['variant']}: {variant['subject']}")
        
    except Exception as e:
        print(f"❌ A/B testing error: {e}")
    
    # Test 8: Show Complete Message
    print("\n📧 Test 8: Complete Message Example")
    
    config = OutreachConfig(
        category="cold_outreach",
        tone=ToneStyle.FORMAL,
        personalization_depth="deep",
        sender_info={
            "sender_name": "Sarah Johnson",
            "sender_title": "Senior Account Executive",
            "sender_company": "SolutionsCorp",
            "calendar_link": "https://calendly.com/sarah-johnson"
        }
    )
    
    try:
        message = await composer.compose_outreach(lead, config)
        
        print("=" * 60)
        print(f"Subject: {message.subject}")
        print("=" * 60)
        print(message.body)
        print("=" * 60)
        print(f"Personalization: {message.personalization_score:.2f} | Response Rate: {message.predicted_response_rate:.2f}")
        
    except Exception as e:
        print(f"❌ Complete message error: {e}")
    
    print("\n🎉 Outreach Composer simple test completed!")


if __name__ == "__main__":
    asyncio.run(test_outreach_simple())