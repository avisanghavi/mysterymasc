#!/usr/bin/env python3
"""
Validate success criteria for AI-enhanced Outreach Composer
"""
import asyncio
import sys
import os
import time
import hashlib
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from outreach_composer_implementation import OutreachComposerAgent, OutreachConfig, ToneStyle

# Simple mock classes for testing (complete version)
class MockCompany:
    def __init__(self, name="TechCorp Solutions"):
        self.name = name
        self.industry = "SaaS"
        self.employee_count = 250
        self.location = "San Francisco, CA"
        self.description = "Leading SaaS company"
        self.pain_points = ["Scaling customer acquisition", "Improving retention"]
        self.recent_news = [type('News', (), {'title': f'{name} Raises $50M Series B'})()]
        self.founded_year = 2018

class MockContact:
    def __init__(self, name="Sarah Johnson"):
        self.first_name = name.split()[0]
        self.last_name = name.split()[1] if len(name.split()) > 1 else "Doe"
        self.full_name = name
        self.title = "VP of Sales"
        self.email = f"{name.lower().replace(' ', '.')}@company.com"
        self.seniority = "VP"
        self.department = "Sales"

class MockScore:
    def __init__(self, score):
        self.total_score = score

class MockLead:
    def __init__(self, score=85, company_name="TechCorp Solutions", contact_name="Sarah Johnson"):
        self.lead_id = f"lead_{hash(company_name + contact_name) % 1000}"
        self.company = MockCompany(company_name)
        self.contact = MockContact(contact_name)
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

async def test_uniqueness():
    """✅ AI-generated messages are unique (no duplicates)"""
    print("1. Testing Message Uniqueness")
    print("-" * 40)
    
    config = OutreachConfig(
        tone=ToneStyle.CASUAL,
        max_length=200,
        sender_info={"name": "Alex Smith", "company": "TestCorp"}
    )
    
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    # Generate messages for different leads
    leads = [
        MockLead(85, "TechCorp Solutions", "Sarah Johnson"),
        MockLead(90, "DataFlow Inc", "Mike Chen"),
        MockLead(88, "CloudTech Pro", "Lisa Wang"),
        MockLead(87, "ScaleUp Systems", "John Smith")
    ]
    
    messages = []
    for lead in leads:
        try:
            message = await agent.compose_outreach(lead, config)
            messages.append(message)
        except:
            continue
    
    # Check uniqueness by comparing subject lines and body content
    subjects = [m.subject for m in messages]
    bodies = [m.body for m in messages]
    
    unique_subjects = len(set(subjects)) == len(subjects)
    unique_bodies = len(set(bodies)) == len(bodies)
    
    print(f"Messages generated: {len(messages)}")
    print(f"Unique subjects: {len(set(subjects))}/{len(subjects)} ({'✅' if unique_subjects else '❌'})")
    print(f"Unique bodies: {len(set(bodies))}/{len(bodies)} ({'✅' if unique_bodies else '❌'})")
    
    # Show sample subjects for verification
    for i, subj in enumerate(subjects[:3]):
        print(f"  Sample {i+1}: {subj}")
    
    return unique_subjects and unique_bodies

async def test_specific_details():
    """✅ Messages reference specific lead details"""
    print("\n2. Testing Specific Lead Details Reference")
    print("-" * 40)
    
    config = OutreachConfig(sender_info={"name": "Test Sender"})
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    lead = MockLead(85, "InnovateTech Corp", "Emma Rodriguez")
    
    try:
        message = await agent.compose_outreach(lead, config)
        
        # Check if message contains specific lead details
        content = f"{message.subject} {message.body}".lower()
        
        checks = {
            "company_name": lead.company.name.lower() in content,
            "contact_name": lead.contact.first_name.lower() in content,
            "industry": lead.company.industry.lower() in content,
            "recent_news": any(word in content for word in ["raise", "funding", "series"]),
            "pain_points": any(pain.lower() in content for pain in lead.company.pain_points)
        }
        
        print(f"Message generated for {lead.contact.full_name} at {lead.company.name}")
        print(f"Subject: {message.subject}")
        
        for check, passed in checks.items():
            print(f"  {'✅' if passed else '❌'} {check}: {passed}")
        
        total_checks = sum(checks.values())
        print(f"Personalization elements: {total_checks}/{len(checks)}")
        
        return total_checks >= 3  # At least 3 out of 5 elements
        
    except Exception as e:
        print(f"❌ Failed to generate message: {e}")
        return False

async def test_ab_variations():
    """✅ A/B variations have different angles/hooks"""
    print("\n3. Testing A/B Variation Angles")
    print("-" * 40)
    
    config = OutreachConfig(max_length=150)
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    lead = MockLead(90, "GrowthTech", "David Kim")
    
    try:
        # Generate variations directly
        base_subject = "Partnership opportunity with GrowthTech"
        base_body = "Hi David, I noticed GrowthTech's recent growth..."
        
        variations = await agent._generate_ai_variations(lead, base_subject, base_body, config)
        
        print(f"Generated {len(variations)} variations:")
        
        if len(variations) >= 2:
            # Compare first two variations
            var_a = variations[0]
            var_b = variations[1] if len(variations) > 1 else variations[0]
            
            print(f"\nVariation A:")
            print(f"  Subject: {var_a['subject']}")
            print(f"  Body preview: {var_a['body'][:80]}...")
            
            print(f"\nVariation B:")
            print(f"  Subject: {var_b['subject']}")
            print(f"  Body preview: {var_b['body'][:80]}...")
            
            # Check if they're different
            different_subjects = var_a['subject'] != var_b['subject']
            different_bodies = var_a['body'] != var_b['body']
            
            print(f"\nDifferent subjects: {'✅' if different_subjects else '❌'}")
            print(f"Different bodies: {'✅' if different_bodies else '❌'}")
            
            return different_subjects and different_bodies
        else:
            print("❌ Insufficient variations generated")
            return False
            
    except Exception as e:
        print(f"❌ Failed to generate variations: {e}")
        return False

async def test_response_prediction_quality():
    """✅ Response prediction score correlates with quality"""
    print("\n4. Testing Response Prediction Correlation")
    print("-" * 40)
    
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    lead = MockLead(85)
    
    # Test messages of different quality levels
    test_messages = [
        {
            "name": "High Quality",
            "message": {
                "subject": f"Quick question about {lead.company.name}'s growth plans",
                "body": f"Hi {lead.contact.first_name},\n\nI noticed {lead.company.name} recently raised funding - congratulations! With your expansion plans, I imagine scaling sales operations efficiently is a top priority.\n\nWe help companies like yours automate sales workflows and improve team productivity. Would you be open to a brief call next week?\n\nBest regards,\nAlex"
            }
        },
        {
            "name": "Medium Quality", 
            "message": {
                "subject": "Sales solution for your team",
                "body": f"Hello {lead.contact.first_name},\n\nI wanted to reach out about our sales automation platform. We've helped many companies improve their sales processes.\n\nWould you be interested in learning more?\n\nThanks"
            }
        },
        {
            "name": "Low Quality",
            "message": {
                "subject": "Great opportunity!!!",
                "body": "Hello,\n\nWe have amazing sales tools that will definitely help your business. This is a limited time offer with guaranteed results!\n\nReply now!"
            }
        }
    ]
    
    predictions = []
    
    for test in test_messages:
        try:
            prediction = await agent._predict_response_rate_ai(test["message"], lead)
            predictions.append((test["name"], prediction))
            print(f"{test['name']}: {prediction:.1%} predicted response rate")
        except:
            # Use heuristic fallback
            prediction = agent._calculate_response_probability_heuristic(test["message"], lead)
            predictions.append((test["name"], prediction))
            print(f"{test['name']}: {prediction:.1%} (heuristic)")
    
    # Check if high quality > medium > low quality
    if len(predictions) >= 3:
        high_pred = predictions[0][1]
        med_pred = predictions[1][1] 
        low_pred = predictions[2][1]
        
        correlation_correct = high_pred > med_pred > low_pred
        print(f"Quality correlation: {'✅' if correlation_correct else '❌'}")
        print(f"  High ({high_pred:.1%}) > Medium ({med_pred:.1%}) > Low ({low_pred:.1%})")
        
        return correlation_correct
    
    return False

async def test_spam_check():
    """✅ AI messages pass spam check (<3 spam score)"""
    print("\n5. Testing Spam Score Check")
    print("-" * 40)
    
    config = OutreachConfig(sender_info={"name": "Test Sender"})
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    lead = MockLead(85)
    
    try:
        # Generate AI message
        message = await agent.compose_outreach(lead, config)
        
        # Check spam score
        spam_score = agent._check_spam_score(message.body)
        
        print(f"Generated message spam score: {spam_score:.1f}")
        print(f"Target: <3.0")
        print(f"Spam check: {'✅ Passed' if spam_score < 3.0 else '❌ Failed'}")
        
        # Also test the quality check system
        quality_result = await agent._quality_check_ai_message(message.body, lead)
        no_spam_triggers = quality_result["checks"].get("no_spam_triggers", False)
        
        print(f"Quality system spam check: {'✅' if no_spam_triggers else '❌'}")
        
        return spam_score < 3.0 and no_spam_triggers
        
    except Exception as e:
        print(f"❌ Failed to test spam check: {e}")
        return False

async def test_fallback():
    """✅ Fallback to template if AI fails"""
    print("\n6. Testing AI Fallback Mechanism")
    print("-" * 40)
    
    config = OutreachConfig(sender_info={"name": "Test Sender"})
    agent = OutreachComposerAgent(mode="hybrid", config={"ai_provider": "mock"})
    
    # Force AI failure
    if agent.ai_engine:
        agent.ai_engine.set_failure_rate(1.0)  # 100% failure rate
    
    lead = MockLead(85)  # High score should trigger AI, but it will fail
    
    try:
        message = await agent.compose_outreach(lead, config)
        
        # Should fallback to template mode
        fallback_success = message.generation_mode == "template"
        
        print(f"AI failure forced: ✅")
        print(f"Message generated: ✅")
        print(f"Generation mode: {message.generation_mode}")
        print(f"Fallback success: {'✅' if fallback_success else '❌'}")
        
        # Reset failure rate
        if agent.ai_engine:
            agent.ai_engine.set_failure_rate(0.0)
        
        return fallback_success
        
    except Exception as e:
        print(f"❌ Fallback failed: {e}")
        if agent.ai_engine:
            agent.ai_engine.set_failure_rate(0.0)
        return False

async def test_generation_time():
    """✅ Generation time <5 seconds per message"""
    print("\n7. Testing Generation Time")
    print("-" * 40)
    
    config = OutreachConfig(max_length=200)
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    lead = MockLead(85)
    
    # Test multiple generations for average
    times = []
    
    for i in range(3):
        try:
            start_time = time.time()
            message = await agent.compose_outreach(lead, config)
            generation_time = time.time() - start_time
            times.append(generation_time)
            print(f"Generation {i+1}: {generation_time:.2f}s")
        except:
            continue
    
    if times:
        avg_time = sum(times) / len(times)
        max_time = max(times)
        
        print(f"Average time: {avg_time:.2f}s")
        print(f"Maximum time: {max_time:.2f}s")
        print(f"Target: <5.0s")
        print(f"Time check: {'✅' if max_time < 5.0 else '❌'}")
        
        return max_time < 5.0
    
    return False

async def test_cost_per_message():
    """✅ Cost <$0.05 per message"""
    print("\n8. Testing Cost Per Message")
    print("-" * 40)
    
    config = OutreachConfig()
    agent = OutreachComposerAgent(mode="ai", config={"ai_provider": "mock"})
    
    # Reset budget
    if agent.ai_engine:
        agent.ai_engine.reset_budget()
    
    # Generate multiple messages
    leads = [MockLead(85 + i, f"Company{i}", f"Contact{i}") for i in range(5)]
    
    messages_generated = 0
    for lead in leads:
        try:
            message = await agent.compose_outreach(lead, config)
            messages_generated += 1
        except:
            continue
    
    # Check budget
    if agent.ai_engine and messages_generated > 0:
        budget = agent.ai_engine.get_budget_info()
        cost_per_message = budget.total_spent_usd / messages_generated
        
        print(f"Messages generated: {messages_generated}")
        print(f"Total cost: ${budget.total_spent_usd:.6f}")
        print(f"Cost per message: ${cost_per_message:.6f}")
        print(f"Target: <$0.05")
        print(f"Cost check: {'✅' if cost_per_message < 0.05 else '❌'}")
        print(f"AI requests: {budget.requests_made}")
        print(f"Total tokens: {budget.input_tokens_used + budget.output_tokens_used}")
        
        return cost_per_message < 0.05
    
    return False

async def main():
    """Run all success criteria validation"""
    print("🎯 AI Outreach Composer Success Criteria Validation")
    print("=" * 60)
    
    results = {}
    
    try:
        results['uniqueness'] = await test_uniqueness()
        results['specific_details'] = await test_specific_details()
        results['ab_variations'] = await test_ab_variations()
        results['response_prediction'] = await test_response_prediction_quality()
        results['spam_check'] = await test_spam_check()
        results['fallback'] = await test_fallback()
        results['generation_time'] = await test_generation_time()
        results['cost_per_message'] = await test_cost_per_message()
        
        # Summary
        print("\n" + "=" * 60)
        print("SUCCESS CRITERIA VALIDATION RESULTS")
        print("=" * 60)
        
        criteria_names = [
            "AI-generated messages are unique",
            "Messages reference specific lead details", 
            "A/B variations have different angles",
            "Response prediction correlates with quality",
            "AI messages pass spam check (<3 score)",
            "Fallback to template if AI fails",
            "Generation time <5 seconds per message",
            "Cost <$0.05 per message"
        ]
        
        passed = 0
        for i, (key, result) in enumerate(results.items()):
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {criteria_names[i]}")
            if result:
                passed += 1
        
        total = len(results)
        print(f"\nOVERALL SCORE: {passed}/{total} ({passed/total:.1%})")
        
        if passed == total:
            print("🎉 ALL SUCCESS CRITERIA MET!")
        elif passed >= 6:
            print("✨ Most criteria met - excellent performance!")
        else:
            print("⚠️ Some criteria need attention")
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())