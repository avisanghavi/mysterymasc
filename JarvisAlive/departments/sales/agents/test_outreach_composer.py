#!/usr/bin/env python3
"""
Test script for Outreach Composer Implementation
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from outreach_composer_implementation import OutreachComposerAgent, OutreachConfig, ToneStyle
from lead_scanner_implementation import LeadScannerAgent, ScanCriteria


async def test_outreach_composer():
    """Test the Outreach Composer Agent with various scenarios"""
    
    print("📧 Testing Outreach Composer Agent Implementation")
    print("=" * 60)
    
    # Initialize agents
    lead_scanner = LeadScannerAgent(mode="mock")
    outreach_composer = OutreachComposerAgent(mode="template")
    
    # Get some leads to test with
    criteria = ScanCriteria(
        industries=["SaaS", "FinTech"],
        titles=["CTO", "VP", "Director"],
        min_score=70,
        max_results=5
    )
    
    leads = await lead_scanner.scan_for_leads(criteria)
    print(f"✅ Found {len(leads)} leads for testing")
    
    if not leads:
        print("❌ No leads found for testing")
        return
    
    # Test 1: Basic template composition
    print("\n📝 Test 1: Basic template composition")
    lead = leads[0]
    config = OutreachConfig(
        category="cold_outreach",
        tone=ToneStyle.FORMAL,
        sender_info={
            "sender_name": "John Smith",
            "sender_title": "Account Executive",
            "sender_company": "SalesBoost Inc"
        }
    )
    
    try:
        message = await outreach_composer.compose_outreach(lead, config)
        print(f"✅ Generated message for {lead.contact.full_name} at {lead.company.name}")
        print(f"   Subject: {message.subject}")
        print(f"   Body length: {len(message.body.split())} words")
        print(f"   Personalization score: {message.personalization_score:.2f}")
        print(f"   Predicted response rate: {message.predicted_response_rate:.2f}")
        print(f"   Template used: {message.template_id}")
        
        # Show message preview
        print("\n📧 Message Preview:")
        print("-" * 40)
        print(f"Subject: {message.subject}")
        print(f"\n{message.body[:200]}...")
        print("-" * 40)
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Different tone styles
    print("\n🎨 Test 2: Testing different tone styles")
    
    tones = [ToneStyle.CASUAL, ToneStyle.TECHNICAL, ToneStyle.EXECUTIVE]
    for tone in tones:
        config = OutreachConfig(
            category="cold_outreach",
            tone=tone,
            sender_info={
                "sender_name": "Jane Doe",
                "sender_title": "Sales Engineer",
                "sender_company": "TechSolutions"
            }
        )
        
        try:
            message = await outreach_composer.compose_outreach(lead, config)
            print(f"✅ {tone.value.upper()} tone - Template: {message.template_id}")
            print(f"   Subject: {message.subject}")
            print(f"   Personalization: {message.personalization_score:.2f}")
            
        except Exception as e:
            print(f"❌ {tone.value} tone error: {e}")
    
    # Test 3: Different categories
    print("\n📂 Test 3: Testing different categories")
    
    categories = ["cold_outreach", "follow_up", "meeting_request", "revival"]
    for category in categories:
        config = OutreachConfig(
            category=category,
            sender_info={
                "sender_name": "Mike Johnson",
                "sender_title": "Business Development",
                "sender_company": "GrowthCorp"
            }
        )
        
        try:
            message = await outreach_composer.compose_outreach(lead, config)
            print(f"✅ {category.upper()} - Template: {message.template_id}")
            print(f"   Subject: {message.subject}")
            print(f"   Response rate: {message.predicted_response_rate:.2f}")
            
        except Exception as e:
            print(f"❌ {category} error: {e}")
    
    # Test 4: Personalization depth
    print("\n🎯 Test 4: Testing personalization depth")
    
    depths = ["basic", "moderate", "deep"]
    for depth in depths:
        config = OutreachConfig(
            category="cold_outreach",
            personalization_depth=depth,
            sender_info={
                "sender_name": "Sarah Wilson",
                "sender_title": "Sales Manager",
                "sender_company": "PersonalizeIt"
            }
        )
        
        try:
            message = await outreach_composer.compose_outreach(lead, config)
            print(f"✅ {depth.upper()} depth - Personalization: {message.personalization_score:.2f}")
            print(f"   Variables used: {len(message.metadata.get('variables_used', []))}")
            
        except Exception as e:
            print(f"❌ {depth} depth error: {e}")
    
    # Test 5: A/B testing variants
    print("\n🔬 Test 5: A/B testing variants")
    
    config = OutreachConfig(
        category="cold_outreach",
        tone=ToneStyle.FORMAL,
        sender_info={
            "sender_name": "David Chen",
            "sender_title": "Head of Sales",
            "sender_company": "ABTestPro"
        }
    )
    
    try:
        message = await outreach_composer.compose_outreach(lead, config)
        variants = message.metadata.get("ab_variants", [])
        print(f"✅ Generated {len(variants)} A/B variants")
        
        for i, variant in enumerate(variants[:3]):
            print(f"   Variant {variant['variant']}: {variant['subject']}")
            print(f"   Changes: {variant['changes']}")
        
    except Exception as e:
        print(f"❌ A/B testing error: {e}")
    
    # Test 6: Multiple industries
    print("\n🏭 Test 6: Testing different industries")
    
    for lead in leads[:3]:
        config = OutreachConfig(
            category="cold_outreach",
            sender_info={
                "sender_name": "Lisa Rodriguez",
                "sender_title": "Industry Specialist",
                "sender_company": "IndustrySolutions"
            }
        )
        
        try:
            message = await outreach_composer.compose_outreach(lead, config)
            print(f"✅ {lead.company.industry} - {lead.contact.full_name}")
            print(f"   Template: {message.template_id}")
            print(f"   Personalization: {message.personalization_score:.2f}")
            print(f"   Response rate: {message.predicted_response_rate:.2f}")
            
        except Exception as e:
            print(f"❌ {lead.company.industry} error: {e}")
    
    # Test 7: Template selection logic
    print("\n🎯 Test 7: Template selection logic")
    
    test_lead = leads[0]
    composer = OutreachComposerAgent(mode="template")
    
    # Test with different lead scores
    original_score = test_lead.score.total_score
    
    test_scores = [95, 75, 55]
    for score in test_scores:
        test_lead.score.total_score = score
        
        config = OutreachConfig(category="cold_outreach")
        selected_template = composer.select_template(test_lead, config)
        
        print(f"✅ Score {score} → Template: {selected_template}")
    
    # Restore original score
    test_lead.score.total_score = original_score
    
    # Test 8: Quality scoring
    print("\n📊 Test 8: Quality scoring analysis")
    
    config = OutreachConfig(
        category="cold_outreach",
        tone=ToneStyle.FORMAL,
        sender_info={
            "sender_name": "Quality Tester",
            "sender_title": "Test Engineer",
            "sender_company": "QualityCheck"
        }
    )
    
    try:
        message = await outreach_composer.compose_outreach(leads[0], config)
        
        print(f"✅ Quality Analysis for {leads[0].contact.full_name}:")
        print(f"   Personalization Score: {message.personalization_score:.2f}")
        print(f"   Predicted Response Rate: {message.predicted_response_rate:.2f}")
        print(f"   Message Length: {len(message.body.split())} words")
        print(f"   Subject Length: {len(message.subject.split())} words")
        print(f"   Template Category: {message.category}")
        print(f"   Tone Style: {message.tone}")
        
    except Exception as e:
        print(f"❌ Quality scoring error: {e}")
    
    print("\n🎉 Outreach Composer Agent testing completed!")


if __name__ == "__main__":
    asyncio.run(test_outreach_composer())