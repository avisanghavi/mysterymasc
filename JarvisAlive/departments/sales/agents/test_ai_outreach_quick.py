#!/usr/bin/env python3
"""
Quick test for AI-enhanced Outreach Composer
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from outreach_composer_implementation import OutreachComposerAgent, OutreachConfig, ToneStyle

# Simple mock classes for testing
class MockCompany:
    def __init__(self):
        self.name = "TechCorp Solutions"
        self.industry = "SaaS"
        self.employee_count = 250
        self.location = "San Francisco, CA"
        self.description = "Leading SaaS company"
        self.pain_points = ["Scaling customer acquisition", "Improving retention"]
        self.recent_news = [type('News', (), {'title': 'Raised $50M Series B'})()]

class MockContact:
    def __init__(self):
        self.first_name = "Sarah"
        self.last_name = "Johnson"
        self.full_name = "Sarah Johnson"
        self.title = "VP of Sales"
        self.email = "sarah@techcorp.com"
        self.seniority = "VP"
        self.department = "Sales"

class MockScore:
    def __init__(self, score):
        self.total_score = score

class MockLead:
    def __init__(self, score=85):
        self.lead_id = "lead_test_123"
        self.company = MockCompany()
        self.contact = MockContact()
        self.score = MockScore(score)
        if score >= 80:
            self.enrichment_data = {
                "company_insights": {
                    "priorities": ["Growth", "Efficiency"],
                    "pain_points": ["Scale challenges", "Automation needs"]
                }
            }
        else:
            self.enrichment_data = None

async def quick_test():
    """Quick test of all modes"""
    print("🧪 Quick AI Outreach Composer Test")
    print("=" * 50)
    
    config = OutreachConfig(
        tone=ToneStyle.CASUAL,
        max_length=200,
        sender_info={
            "name": "Alex Smith",
            "title": "Sales Rep",
            "company": "TestCorp"
        }
    )
    
    # Test Template Mode
    print("1. Template Mode:")
    agent_template = OutreachComposerAgent(mode="template")
    lead = MockLead(70)
    
    try:
        message = await agent_template.compose_outreach(lead, config)
        print(f"   ✅ Template: {message.subject}")
        print(f"   Mode: {message.generation_mode}")
    except Exception as e:
        print(f"   ❌ Template failed: {e}")
    
    # Test AI Mode
    print("\n2. AI Mode:")
    agent_ai = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    try:
        message = await agent_ai.compose_outreach(lead, config)
        print(f"   ✅ AI: {message.subject}")
        print(f"   Mode: {message.generation_mode}")
        print(f"   AI Provider: {message.metadata.get('ai_provider', 'unknown')}")
    except Exception as e:
        print(f"   ❌ AI failed: {e}")
    
    # Test Hybrid Mode
    print("\n3. Hybrid Mode:")
    agent_hybrid = OutreachComposerAgent(mode="hybrid", config={"ai_provider": "mock"})
    
    # High value lead (should use AI)
    high_lead = MockLead(85)
    try:
        message = await agent_hybrid.compose_outreach(high_lead, config)
        print(f"   ✅ High-value lead: {message.generation_mode}")
    except Exception as e:
        print(f"   ❌ High-value failed: {e}")
    
    # Standard lead (should use template)
    std_lead = MockLead(65)
    try:
        message = await agent_hybrid.compose_outreach(std_lead, config)
        print(f"   ✅ Standard lead: {message.generation_mode}")
    except Exception as e:
        print(f"   ❌ Standard failed: {e}")
    
    # Test quality checks
    print("\n4. Quality Checks:")
    if agent_ai.ai_engine:
        test_message = f"Hi {lead.contact.first_name}, I noticed {lead.company.name} recently raised funding..."
        quality = await agent_ai._quality_check_ai_message(test_message, lead)
        print(f"   ✅ Quality check: {'Passed' if quality['passed'] else 'Failed'}")
        print(f"   Issues: {quality.get('issues', [])}")
    
    # Test response prediction
    print("\n5. Response Prediction:")
    test_msg = {
        "subject": "Question about TechCorp's growth",
        "body": test_message
    }
    
    try:
        prediction = await agent_ai._predict_response_rate_ai(test_msg, lead)
        print(f"   ✅ AI prediction: {prediction:.1%}")
    except Exception as e:
        print(f"   ⚠️ AI prediction failed, using heuristic")
        heuristic = agent_ai._calculate_response_probability_heuristic(test_msg, lead)
        print(f"   ✅ Heuristic prediction: {heuristic:.1%}")
    
    print("\n🎉 Quick test completed!")
    
    # Show budget if available
    if agent_ai.ai_engine:
        budget = agent_ai.ai_engine.get_budget_info()
        print(f"\nBudget: ${budget.total_spent_usd:.4f}, {budget.requests_made} requests")

if __name__ == "__main__":
    asyncio.run(quick_test())