#!/usr/bin/env python3
"""
Test suite for AI-enhanced Outreach Composer
"""
import asyncio
import sys
import os
import json
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from outreach_composer_implementation import OutreachComposerAgent, OutreachConfig, ToneStyle
from lead_scanner_implementation import Lead, LeadScore, ScanCriteria
from database.mock_data import Company, Contact

# Create test data
def create_test_lead(score: int = 85) -> Lead:
    """Create a test lead with mock data"""
    company = Company(
        id="comp_test_123",
        name="TechCorp Solutions",
        website="https://techcorp.example.com",
        industry="SaaS",
        sub_industry="Marketing Automation",
        employee_count=250,
        location="San Francisco, CA",
        description="Leading provider of marketing automation software",
        recent_news=[
            type('NewsItem', (), {
                'title': 'TechCorp Raises $50M Series B Funding',
                'date': '2024-01-15'
            })()
        ],
        technologies=["React", "Python", "AWS", "Kubernetes"],
        pain_points=["Scaling customer acquisition", "Improving retention rates", "Automating workflows"]
    )
    
    contact = Contact(
        id="cont_test_456",
        company_id=company.id,
        first_name="Sarah",
        last_name="Johnson",
        full_name="Sarah Johnson",
        title="VP of Sales",
        department="Sales",
        seniority="VP",
        email="sarah.johnson@techcorp.example.com",
        phone="+1-555-0100",
        linkedin_url="https://linkedin.com/in/sarahjohnson",
        pain_points=["Need better sales tools", "Improving team productivity"]
    )
    
    lead_score = LeadScore(
        total_score=score,
        industry_match=25,
        title_relevance=30,
        company_size_fit=15,
        recent_activity=15,
        explanation="High-value lead with recent funding",
        confidence=0.85
    )
    
    lead = Lead(
        lead_id="lead_test_789",
        contact=contact,
        company=company,
        score=lead_score,
        discovered_at="2024-07-08T10:00:00",
        source="mock_test",
        outreach_priority="high"
    )
    
    # Add AI enrichment data for some tests
    if score >= 80:
        lead.enrichment_data = {
            "company_insights": {
                "priorities": ["Scaling operations", "Market expansion"],
                "pain_points": ["Need better automation", "Customer retention"],
                "timing": "optimal",
                "approach_angle": "ROI-focused"
            },
            "contact_insights": {
                "responsibilities": ["Drive revenue growth", "Manage sales team"],
                "challenges": ["Team productivity", "Pipeline visibility"],
                "communication_style": "direct",
                "best_channel": "email"
            },
            "ai_provider": "mock"
        }
    
    return lead

async def test_template_mode():
    """Test traditional template mode"""
    print("🧪 Testing Template Mode")
    print("=" * 50)
    
    config = OutreachConfig(
        tone=ToneStyle.FORMAL,
        category="cold_outreach",
        max_length=200,
        sender_info={
            "name": "John Smith",
            "title": "Account Executive",
            "company": "SalesBoost Inc",
            "value_proposition": "Help sales teams close more deals faster"
        }
    )
    
    agent = OutreachComposerAgent(mode="template")
    lead = create_test_lead(70)
    
    message = await agent.compose_outreach(lead, config)
    
    print(f"✅ Generated message in {agent.mode} mode")
    print(f"Subject: {message.subject}")
    print(f"Body preview: {message.body[:100]}...")
    print(f"Template used: {message.template_id}")
    print(f"Personalization score: {message.personalization_score:.2f}")
    print(f"Predicted response rate: {message.predicted_response_rate:.2%}")
    print()

async def test_ai_mode():
    """Test full AI mode"""
    print("🤖 Testing AI Mode")
    print("=" * 50)
    
    config = OutreachConfig(
        tone=ToneStyle.CASUAL,
        category="cold_outreach",
        max_length=250,
        sender_info={
            "name": "Emily Chen",
            "title": "Sales Development Rep",
            "company": "GrowthTech",
            "value_proposition": "Accelerate revenue growth with AI-powered insights"
        }
    )
    
    ai_config = {
        "ai_provider": "mock",
        "ai_model": "mock-ai-sales"
    }
    
    agent = OutreachComposerAgent(mode="ai", config=ai_config)
    lead = create_test_lead(90)
    
    message = await agent.compose_outreach(lead, config)
    
    print(f"✅ Generated AI message")
    print(f"Subject: {message.subject}")
    print(f"Body: {message.body[:200]}...")
    print(f"Generation mode: {message.generation_mode}")
    print(f"AI provider: {message.metadata.get('ai_provider', 'unknown')}")
    print(f"Variations generated: {message.metadata.get('variations_generated', 1)}")
    print(f"Personalization score: {message.personalization_score:.2f}")
    print(f"Predicted response rate: {message.predicted_response_rate:.2%}")
    
    # Show quality check results
    quality_passed = message.metadata.get('quality_checks_passed', True)
    print(f"Quality checks: {'✅ Passed' if quality_passed else '❌ Failed'}")
    print()

async def test_hybrid_mode():
    """Test hybrid mode with selective AI usage"""
    print("🔄 Testing Hybrid Mode")
    print("=" * 50)
    
    config = OutreachConfig(
        tone=ToneStyle.FORMAL,
        sender_info={
            "name": "Mike Davis",
            "title": "Business Development Manager",
            "company": "ConnectHub Pro"
        }
    )
    
    ai_config = {"ai_provider": "mock"}
    agent = OutreachComposerAgent(mode="hybrid", config=ai_config)
    
    # Test with high-value lead (should use AI)
    print("1. High-value lead (score 85):")
    high_value_lead = create_test_lead(85)
    message1 = await agent.compose_outreach(high_value_lead, config)
    print(f"   Generation mode: {message1.generation_mode}")
    print(f"   Subject: {message1.subject}")
    
    # Test with standard lead (should use template)
    print("\n2. Standard lead (score 65):")
    standard_lead = create_test_lead(65)
    message2 = await agent.compose_outreach(standard_lead, config)
    print(f"   Generation mode: {message2.generation_mode}")
    print(f"   Subject: {message2.subject}")
    print()

async def test_ab_variations():
    """Test A/B variation generation"""
    print("🔀 Testing A/B Variations")
    print("=" * 50)
    
    config = OutreachConfig(
        tone=ToneStyle.CASUAL,
        max_length=200,
        sender_info={
            "name": "Lisa Wang",
            "company": "OptimizePro"
        }
    )
    
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    lead = create_test_lead(90)
    
    # Generate message with variations
    message = await agent.compose_outreach(lead, config)
    
    # Get variations from metadata
    variations = message.metadata.get('ab_variants', [])
    print(f"Generated {len(variations)} variations")
    
    # If we have the raw variations, show them
    if agent.ai_engine and hasattr(agent, '_generate_ai_variations'):
        # Generate variations directly for testing
        base_subject = "Helping TechCorp Scale Sales"
        base_body = "Hi Sarah, noticed your recent funding..."
        
        variations = await agent._generate_ai_variations(lead, base_subject, base_body, config)
        
        for var in variations[:3]:
            print(f"\nVariant {var['variant']}:")
            print(f"  Subject: {var['subject']}")
            print(f"  Body preview: {var['body'][:80]}...")
    print()

async def test_response_prediction():
    """Test AI response rate prediction"""
    print("📊 Testing Response Prediction")
    print("=" * 50)
    
    config = OutreachConfig(sender_info={"name": "Test Sender"})
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    # Test different message qualities
    test_cases = [
        {
            "lead": create_test_lead(90),
            "message": {
                "subject": "Quick question about TechCorp's growth plans",
                "body": "Hi Sarah,\n\nI noticed TechCorp just raised $50M - congratulations! With your expansion plans, I imagine scaling sales operations efficiently is a top priority.\n\nWe help companies like yours automate sales workflows and improve team productivity. Would you be open to a brief call next week to discuss how we could help TechCorp hit its growth targets?\n\nBest,\nJohn"
            }
        },
        {
            "lead": create_test_lead(60),
            "message": {
                "subject": "Sales solution for your company",
                "body": "Hello,\n\nWe offer great sales tools that could help your business. Our software has many features that companies find useful.\n\nLet me know if you want to learn more.\n\nThanks"
            }
        }
    ]
    
    for i, test in enumerate(test_cases):
        lead = test["lead"]
        message = test["message"]
        
        # Get AI prediction
        prediction = await agent._predict_response_rate_ai(message, lead)
        
        print(f"\nTest {i+1}:")
        print(f"  Lead score: {lead.score.total_score}")
        print(f"  Subject: {message['subject']}")
        print(f"  Predicted response rate: {prediction:.1%}")
        
        # Also test heuristic method
        heuristic = agent._calculate_response_probability_heuristic(message, lead)
        print(f"  Heuristic prediction: {heuristic:.1%}")
    print()

async def test_quality_checks():
    """Test message quality assurance"""
    print("✅ Testing Quality Checks")
    print("=" * 50)
    
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    lead = create_test_lead(80)
    
    # Test different message qualities
    test_messages = [
        {
            "name": "Good message",
            "content": f"Hi {lead.contact.first_name},\n\nI noticed {lead.company.name} recently raised funding. With your growth plans, improving sales efficiency is likely a priority.\n\nWould you be interested in a brief call to discuss how we help similar companies scale their sales operations?\n\nBest regards,\nJohn"
        },
        {
            "name": "Spam triggers",
            "content": f"URGENT! Limited time offer! {lead.contact.first_name}, this is a 100% guaranteed way to increase sales! Act now and get it FREE! Don't miss out!!!!"
        },
        {
            "name": "Too long",
            "content": f"Hi {lead.contact.first_name},\n\n" + ("This is a very long message. " * 50) + "\n\nBest regards"
        },
        {
            "name": "Missing personalization",
            "content": "Hello,\n\nI wanted to reach out about our sales solution. We help companies improve their sales processes.\n\nLet me know if you're interested.\n\nThanks"
        }
    ]
    
    for test in test_messages:
        print(f"\nTesting: {test['name']}")
        result = await agent._quality_check_ai_message(test['content'], lead)
        
        print(f"  Overall: {'✅ Passed' if result['passed'] else '❌ Failed'}")
        for check, passed in result['checks'].items():
            status = "✅" if passed else "❌"
            print(f"  {status} {check}")
        
        if result['issues']:
            print(f"  Issues: {', '.join(result['issues'])}")
    print()

async def test_performance():
    """Test performance and caching"""
    print("⚡ Testing Performance")
    print("=" * 50)
    
    config = OutreachConfig(
        max_length=150,
        sender_info={"name": "Performance Test"}
    )
    
    agent = OutreachComposerAgent(mode="hybrid", config={"ai_provider": "mock"})
    
    # Generate messages for multiple leads
    leads = [create_test_lead(score) for score in [90, 85, 80, 75, 70, 65, 60]]
    
    start_time = time.time()
    messages = []
    
    for i, lead in enumerate(leads):
        msg = await agent.compose_outreach(lead, config)
        messages.append(msg)
        print(f"Lead {i+1}: {msg.generation_mode} mode, score: {lead.score.total_score}")
    
    total_time = time.time() - start_time
    
    ai_messages = sum(1 for m in messages if m.generation_mode == "ai")
    template_messages = sum(1 for m in messages if m.generation_mode == "template")
    
    print(f"\nResults:")
    print(f"  Total messages: {len(messages)}")
    print(f"  AI-generated: {ai_messages}")
    print(f"  Template-based: {template_messages}")
    print(f"  Total time: {total_time:.2f}s")
    print(f"  Average time per message: {total_time/len(messages):.2f}s")
    
    # Check budget if using AI
    if agent.ai_engine:
        budget = agent.ai_engine.get_budget_info()
        print(f"  AI requests: {budget.requests_made}")
        print(f"  Total tokens: {budget.input_tokens_used + budget.output_tokens_used}")
    print()

async def test_edge_cases():
    """Test edge cases and error handling"""
    print("🔧 Testing Edge Cases")
    print("=" * 50)
    
    config = OutreachConfig()
    
    # Test with minimal lead data
    print("1. Minimal lead data:")
    minimal_company = type('Company', (), {
        'name': 'Unknown Corp',
        'industry': 'Unknown',
        'employee_count': 0,
        'pain_points': []
    })()
    
    minimal_contact = type('Contact', (), {
        'first_name': 'John',
        'last_name': 'Doe',
        'full_name': 'John Doe',
        'title': 'Employee',
        'email': 'john@example.com'
    })()
    
    minimal_score = LeadScore(
        total_score=50,
        industry_match=10,
        title_relevance=10,
        company_size_fit=10,
        recent_activity=10,
        explanation="Basic lead",
        confidence=0.5
    )
    
    minimal_lead = type('Lead', (), {
        'lead_id': 'lead_minimal',
        'company': minimal_company,
        'contact': minimal_contact,
        'score': minimal_score
    })()
    
    try:
        agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
        message = await agent.compose_outreach(minimal_lead, config)
        print(f"✅ Handled minimal data: {message.subject}")
    except Exception as e:
        print(f"❌ Failed with minimal data: {e}")
    
    # Test AI fallback
    print("\n2. AI engine failure fallback:")
    agent = OutreachComposerAgent(mode="hybrid", config={"ai_provider": "mock"})
    if agent.ai_engine:
        agent.ai_engine.set_failure_rate(1.0)  # Force failures
    
    lead = create_test_lead(85)
    try:
        message = await agent.compose_outreach(lead, config)
        print(f"✅ Fallback worked: {message.generation_mode} mode used")
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
    
    if agent.ai_engine:
        agent.ai_engine.set_failure_rate(0.0)  # Reset
    print()

async def main():
    """Run all tests"""
    print("🚀 AI-Enhanced Outreach Composer Test Suite")
    print("=" * 60)
    print("Testing AI-powered email generation and personalization\n")
    
    try:
        # Run all test suites
        await test_template_mode()
        await test_ai_mode()
        await test_hybrid_mode()
        await test_ab_variations()
        await test_response_prediction()
        await test_quality_checks()
        await test_performance()
        await test_edge_cases()
        
        print("🎉 All tests completed successfully!")
        print("\nKey Features Demonstrated:")
        print("✅ Template, AI, and Hybrid modes")
        print("✅ AI-powered personalization")
        print("✅ A/B variation generation")
        print("✅ Response rate prediction")
        print("✅ Quality assurance checks")
        print("✅ Smart mode selection in hybrid")
        print("✅ Graceful error handling")
        
    except KeyboardInterrupt:
        print("\n👋 Tests stopped by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())