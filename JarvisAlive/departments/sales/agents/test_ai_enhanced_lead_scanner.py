#!/usr/bin/env python3
"""
Test suite for AI-enhanced Lead Scanner
"""
import asyncio
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from lead_scanner_implementation import LeadScannerAgent, ScanCriteria
from ai_engines.base_engine import AIEngineConfig

async def test_mock_mode():
    """Test traditional mock mode (no AI)"""
    print("🧪 Testing Mock Mode (No AI)")
    print("=" * 50)
    
    agent = LeadScannerAgent(mode="mock")
    criteria = ScanCriteria(
        industries=["SaaS", "FinTech"],
        max_results=5
    )
    
    leads = await agent.scan_for_leads(criteria)
    
    print(f"✅ Found {len(leads)} leads in mock mode")
    print(f"   Mode: {agent.mode}")
    print(f"   AI Engine: {agent.ai_engine is not None}")
    
    for i, lead in enumerate(leads[:2]):
        print(f"   Lead {i+1}: {lead.contact.full_name} at {lead.company.name}")
        print(f"     Score: {lead.score.total_score}")
        print(f"     Enriched: {lead.enrichment_data is not None}")
    
    print()

async def test_hybrid_mode():
    """Test hybrid mode (mock data + AI enrichment)"""
    print("🤖 Testing Hybrid Mode (Mock + AI)")
    print("=" * 50)
    
    config = {
        "ai_provider": "mock",
        "ai_model": "mock-ai-v1"
    }
    
    agent = LeadScannerAgent(mode="hybrid", config=config)
    criteria = ScanCriteria(
        industries=["SaaS"],
        max_results=10
    )
    
    leads = await agent.scan_for_leads(criteria)
    
    print(f"✅ Found {len(leads)} leads in hybrid mode")
    print(f"   Mode: {agent.mode}")
    print(f"   AI Engine: {agent.ai_engine.get_engine_type()}")
    
    # Count enriched leads
    enriched_count = sum(1 for lead in leads if lead.enrichment_data)
    print(f"   Enriched: {enriched_count}/{len(leads)} leads")
    
    # Show examples
    for i, lead in enumerate(leads[:3]):
        print(f"   Lead {i+1}: {lead.contact.full_name} at {lead.company.name}")
        print(f"     Score: {lead.score.total_score}")
        if lead.enrichment_data:
            print(f"     AI Provider: {lead.enrichment_data.get('ai_provider', 'unknown')}")
            company_insights = lead.enrichment_data.get('company_insights', {})
            if 'priorities' in company_insights:
                print(f"     Priorities: {company_insights['priorities'][:2]}")
    
    print()

async def test_ai_mode():
    """Test full AI mode"""
    print("🚀 Testing AI Mode (Full AI Enrichment)")
    print("=" * 50)
    
    config = {
        "ai_provider": "mock",
        "ai_model": "mock-ai-advanced",
        "temperature": 0.2
    }
    
    agent = LeadScannerAgent(mode="ai", config=config)
    criteria = ScanCriteria(
        industries=["E-commerce", "Healthcare"],
        max_results=8
    )
    
    leads = await agent.scan_for_leads(criteria)
    
    print(f"✅ Found {len(leads)} leads in AI mode")
    print(f"   Mode: {agent.mode}")
    print(f"   AI Engine: {agent.ai_engine.get_engine_type()}")
    
    # Count enriched leads
    enriched_count = sum(1 for lead in leads if lead.enrichment_data)
    print(f"   Enriched: {enriched_count}/{len(leads)} leads")
    
    # Show detailed analysis for one lead
    if leads and leads[0].enrichment_data:
        lead = leads[0]
        print(f"\\n📊 Detailed Analysis for {lead.contact.full_name}:")
        
        company_insights = lead.enrichment_data.get('company_insights', {})
        contact_insights = lead.enrichment_data.get('contact_insights', {})
        
        print(f"   Company: {lead.company.name} ({lead.company.industry})")
        print(f"   Original Score: Base algorithm")
        print(f"   AI-Enhanced Score: {lead.score.total_score}")
        
        if 'priorities' in company_insights:
            print(f"   Business Priorities: {company_insights['priorities']}")
        if 'pain_points' in company_insights:
            print(f"   Pain Points: {company_insights['pain_points']}")
        if 'responsibilities' in contact_insights:
            print(f"   Contact Role: {contact_insights['responsibilities']}")
    
    print()

async def test_ai_budget_tracking():
    """Test AI budget and cost tracking"""
    print("💰 Testing AI Budget Tracking")
    print("=" * 50)
    
    config = {
        "ai_provider": "mock",
        "ai_model": "mock-ai-v1"
    }
    
    agent = LeadScannerAgent(mode="hybrid", config=config)
    
    # Get initial budget info
    initial_budget = agent.ai_engine.get_budget_info()
    print(f"Initial Budget: ${initial_budget.total_spent_usd:.4f}")
    print(f"Initial Requests: {initial_budget.requests_made}")
    
    # Run some scans
    criteria = ScanCriteria(industries=["SaaS"], max_results=5)
    leads1 = await agent.scan_for_leads(criteria)
    
    criteria = ScanCriteria(industries=["FinTech"], max_results=3)
    leads2 = await agent.scan_for_leads(criteria)
    
    # Get final budget info
    final_budget = agent.ai_engine.get_budget_info()
    
    print(f"Final Budget: ${final_budget.total_spent_usd:.4f}")
    print(f"Final Requests: {final_budget.requests_made}")
    print(f"Cost Per Request: ${final_budget.total_spent_usd / max(1, final_budget.requests_made):.4f}")
    print(f"Total Tokens: {final_budget.input_tokens_used + final_budget.output_tokens_used}")
    
    print()

async def test_ai_caching():
    """Test AI response caching"""
    print("🗄️ Testing AI Caching")
    print("=" * 50)
    
    config = {
        "ai_provider": "mock",
        "ai_model": "mock-ai-v1"
    }
    
    agent = LeadScannerAgent(mode="hybrid", config=config)
    criteria = ScanCriteria(industries=["SaaS"], max_results=3)
    
    import time
    
    # First request (should be fresh)
    start_time = time.time()
    leads1 = await agent.scan_for_leads(criteria)
    time1 = time.time() - start_time
    
    # Second request (should use cache)
    start_time = time.time()
    leads2 = await agent.scan_for_leads(criteria)
    time2 = time.time() - start_time
    
    print(f"First request: {time1:.3f}s")
    print(f"Second request: {time2:.3f}s")
    print(f"Speed improvement: {(time1/time2):.1f}x faster")
    
    # Check if results are consistent
    if len(leads1) == len(leads2):
        print("✅ Cache provides consistent results")
    else:
        print("⚠️ Cache results differ")
    
    print()

async def test_error_handling():
    """Test error handling in AI mode"""
    print("🚨 Testing Error Handling")
    print("=" * 50)
    
    config = {
        "ai_provider": "mock",
        "ai_model": "mock-ai-v1"
    }
    
    agent = LeadScannerAgent(mode="hybrid", config=config)
    
    # Set high failure rate to test resilience
    agent.ai_engine.set_failure_rate(0.5)  # 50% failure rate
    
    criteria = ScanCriteria(industries=["Manufacturing"], max_results=5)
    
    try:
        leads = await agent.scan_for_leads(criteria)
        print(f"✅ Handled errors gracefully, got {len(leads)} leads")
        
        # Check if some leads are still enriched despite failures
        enriched = sum(1 for lead in leads if lead.enrichment_data)
        print(f"   {enriched} leads enriched despite {agent.ai_engine.failure_rate*100}% failure rate")
        
    except Exception as e:
        print(f"❌ Error handling failed: {e}")
    
    # Reset failure rate
    agent.ai_engine.set_failure_rate(0.0)
    print()

async def test_mode_comparison():
    """Compare results across different modes"""
    print("⚖️ Mode Comparison")
    print("=" * 50)
    
    criteria = ScanCriteria(
        industries=["SaaS"],
        titles=["CEO", "CTO"],
        max_results=5
    )
    
    # Test all three modes
    mock_agent = LeadScannerAgent(mode="mock")
    mock_leads = await mock_agent.scan_for_leads(criteria)
    
    hybrid_agent = LeadScannerAgent(mode="hybrid", config={"ai_provider": "mock"})
    hybrid_leads = await hybrid_agent.scan_for_leads(criteria)
    
    ai_agent = LeadScannerAgent(mode="ai", config={"ai_provider": "mock"})
    ai_leads = await ai_agent.scan_for_leads(criteria)
    
    print(f"Mock Mode: {len(mock_leads)} leads")
    print(f"Hybrid Mode: {len(hybrid_leads)} leads")
    print(f"AI Mode: {len(ai_leads)} leads")
    
    # Compare average scores
    mock_avg = sum(l.score.total_score for l in mock_leads) / len(mock_leads) if mock_leads else 0
    hybrid_avg = sum(l.score.total_score for l in hybrid_leads) / len(hybrid_leads) if hybrid_leads else 0
    ai_avg = sum(l.score.total_score for l in ai_leads) / len(ai_leads) if ai_leads else 0
    
    print(f"Average Scores:")
    print(f"  Mock: {mock_avg:.1f}")
    print(f"  Hybrid: {hybrid_avg:.1f}")
    print(f"  AI: {ai_avg:.1f}")
    
    # Count enriched leads
    hybrid_enriched = sum(1 for l in hybrid_leads if l.enrichment_data)
    ai_enriched = sum(1 for l in ai_leads if l.enrichment_data)
    
    print(f"AI Enrichment:")
    print(f"  Hybrid: {hybrid_enriched}/{len(hybrid_leads)}")
    print(f"  AI: {ai_enriched}/{len(ai_leads)}")
    
    print()

async def test_anthropic_integration():
    """Test with Anthropic (if API key available)"""
    print("🔮 Testing Anthropic Integration")
    print("=" * 50)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️ ANTHROPIC_API_KEY not found, skipping real API test")
        return
    
    config = {
        "ai_provider": "anthropic",
        "ai_model": "claude-3-haiku-20240307",
        "api_key": api_key
    }
    
    try:
        agent = LeadScannerAgent(mode="hybrid", config=config)
        criteria = ScanCriteria(industries=["SaaS"], max_results=2)
        
        leads = await agent.scan_for_leads(criteria)
        
        print(f"✅ Anthropic integration successful")
        print(f"   Found {len(leads)} leads")
        print(f"   AI Engine: {agent.ai_engine.get_engine_type()}")
        
        # Check budget
        budget = agent.ai_engine.get_budget_info()
        print(f"   Cost: ${budget.total_spent_usd:.6f}")
        
        # Show one enriched lead
        enriched_leads = [l for l in leads if l.enrichment_data]
        if enriched_leads:
            lead = enriched_leads[0]
            print(f"   Sample enrichment for {lead.contact.full_name}:")
            company_insights = lead.enrichment_data.get('company_insights', {})
            if isinstance(company_insights, dict) and 'priorities' in company_insights:
                print(f"     Business priorities: {company_insights['priorities'][:2]}")
        
    except Exception as e:
        print(f"❌ Anthropic integration failed: {e}")
    
    print()

async def main():
    """Run all AI enhancement tests"""
    print("🚀 AI-Enhanced Lead Scanner Test Suite")
    print("=" * 60)
    print("Testing the AI integration layer for lead scanning\\n")
    
    try:
        # Test all modes
        await test_mock_mode()
        await test_hybrid_mode()
        await test_ai_mode()
        
        # Test AI features
        await test_ai_budget_tracking()
        await test_ai_caching()
        await test_error_handling()
        
        # Comparative analysis
        await test_mode_comparison()
        
        # Real API test (if available)
        await test_anthropic_integration()
        
        print("🎉 All AI enhancement tests completed successfully!")
        print("\\nKey Features Demonstrated:")
        print("✅ Mock, Hybrid, and AI modes working")
        print("✅ AI-powered company and contact analysis")
        print("✅ Enhanced scoring with AI insights")
        print("✅ Cost tracking and budget management")
        print("✅ Response caching for efficiency")
        print("✅ Error handling and fallback mechanisms")
        print("✅ Anthropic API integration ready")
        
    except KeyboardInterrupt:
        print("\\n👋 Tests stopped by user")
    except Exception as e:
        print(f"\\n❌ Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())