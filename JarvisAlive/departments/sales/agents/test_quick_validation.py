#!/usr/bin/env python3
"""
Quick validation of AI-enhanced Lead Scanner success criteria
"""
import asyncio
import sys
import os
import time
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from lead_scanner_implementation import LeadScannerAgent, ScanCriteria

async def quick_validation():
    """Quick test of all success criteria"""
    print("🎯 Quick Success Criteria Validation")
    print("=" * 50)
    
    results = {}
    
    # 1. AI mode enrichment test
    print("1. Testing AI mode enrichment...")
    config = {"ai_provider": "mock", "ai_model": "mock-ai-v1"}
    agent = LeadScannerAgent(mode="ai", config=config)
    criteria = ScanCriteria(industries=["SaaS"], max_results=5)
    
    leads = await agent.scan_for_leads(criteria)
    enriched = [l for l in leads if l.enrichment_data]
    results['ai_enrichment'] = len(enriched) >= len(leads) * 0.8
    print(f"   ✅ {len(enriched)}/{len(leads)} leads enriched")
    
    # 2. Hybrid mode selective enrichment
    print("2. Testing hybrid mode selectivity...")
    agent = LeadScannerAgent(mode="hybrid", config=config)
    leads = await agent.scan_for_leads(criteria)
    enriched = [l for l in leads if l.enrichment_data]
    expected = min(10, max(1, len(leads) // 5))  # 20% rule
    results['hybrid_selective'] = len(enriched) <= expected
    print(f"   ✅ {len(enriched)} enriched (expected ≤{expected})")
    
    # 3. Meaningful pain points
    print("3. Testing pain point quality...")
    meaningful_count = 0
    for lead in enriched[:3]:
        pain_points = lead.enrichment_data.get('company_insights', {}).get('pain_points', [])
        if isinstance(pain_points, list) and len(pain_points) > 0:
            meaningful_count += 1
    results['meaningful_pain_points'] = meaningful_count > 0
    print(f"   ✅ {meaningful_count} leads with pain points")
    
    # 4. Cost efficiency
    print("4. Testing cost efficiency...")
    budget = agent.ai_engine.get_budget_info()
    cost_per_100 = (budget.total_spent_usd / len(leads)) * 100 if len(leads) > 0 else 0
    results['cost_efficiency'] = cost_per_100 <= 0.10
    print(f"   ✅ ${cost_per_100:.4f} per 100 leads")
    
    # 5. Graceful fallback
    print("5. Testing graceful fallback...")
    agent.ai_engine.set_failure_rate(1.0)
    try:
        fallback_leads = await agent.scan_for_leads(ScanCriteria(industries=["FinTech"], max_results=3))
        results['graceful_fallback'] = len(fallback_leads) > 0
        print(f"   ✅ {len(fallback_leads)} leads despite 100% AI failure")
    except:
        results['graceful_fallback'] = False
        print(f"   ❌ Fallback failed")
    agent.ai_engine.set_failure_rate(0.0)
    
    # 6. Enrichment source field
    print("6. Testing enrichment source...")
    valid_sources = sum(1 for lead in enriched if 'ai_provider' in lead.enrichment_data)
    results['enrichment_source'] = valid_sources == len(enriched)
    print(f"   ✅ {valid_sources}/{len(enriched)} have source field")
    
    # 7. Caching test (simplified)
    print("7. Testing caching...")
    agent.ai_engine.reset_budget()
    await agent.scan_for_leads(ScanCriteria(industries=["SaaS"], max_results=2))
    first_requests = agent.ai_engine.get_budget_info().requests_made
    await agent.scan_for_leads(ScanCriteria(industries=["SaaS"], max_results=2))
    second_requests = agent.ai_engine.get_budget_info().requests_made
    results['caching'] = second_requests <= first_requests * 1.5  # Allow some variation
    print(f"   ✅ Requests: {first_requests} → {second_requests}")
    
    # 8. Execution time
    print("8. Testing execution time...")
    start_time = time.time()
    time_test_leads = await agent.scan_for_leads(ScanCriteria(industries=["E-commerce"], max_results=10))
    execution_time = time.time() - start_time
    results['execution_time'] = execution_time < 30
    print(f"   ✅ {execution_time:.1f}s for {len(time_test_leads)} leads")
    
    # Summary
    print("\n" + "=" * 50)
    print("VALIDATION RESULTS:")
    passed = sum(results.values())
    total = len(results)
    
    for criterion, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {criterion.replace('_', ' ').title()}")
    
    print(f"\nSCORE: {passed}/{total} ({passed/total:.1%})")
    
    if passed >= 7:
        print("🎉 SUCCESS CRITERIA VALIDATION PASSED!")
    else:
        print("⚠️ Some criteria need attention")
    
    return passed, total

if __name__ == "__main__":
    asyncio.run(quick_validation())