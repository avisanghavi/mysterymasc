#!/usr/bin/env python3
"""
Simple test runner for Lead Scanner tests
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from departments.sales.agents.lead_scanner_implementation import (
    LeadScannerAgent, ScanCriteria
)


async def run_simple_tests():
    """Run basic tests to verify implementation"""
    print("🧪 Running Lead Scanner Simple Tests")
    print("=" * 50)
    
    # Initialize scanner
    scanner = LeadScannerAgent(mode="mock")
    print("✅ Scanner initialized successfully")
    
    # Test 1: Basic scan
    print("\n📊 Test 1: Basic scan")
    criteria = ScanCriteria(min_score=50, max_results=5)
    results = await scanner.scan_for_leads(criteria)
    print(f"✅ Found {len(results)} leads (max 5 requested)")
    assert len(results) <= 5
    
    # Test 2: Industry filtering
    print("\n🏭 Test 2: Industry filtering")
    criteria = ScanCriteria(industries=["SaaS"], min_score=60)
    results = await scanner.scan_for_leads(criteria)
    print(f"✅ Found {len(results)} SaaS leads")
    for lead in results[:3]:
        assert lead.company.industry == "SaaS"
        print(f"   - {lead.contact.full_name} at {lead.company.name} (Score: {lead.score.total_score})")
    
    # Test 3: Title filtering
    print("\n👔 Test 3: Title filtering")
    criteria = ScanCriteria(titles=["CTO", "Chief Technology Officer"], min_score=50)
    results = await scanner.scan_for_leads(criteria)
    print(f"✅ Found {len(results)} CTO-level leads")
    for lead in results[:3]:
        assert "CTO" in lead.contact.title.upper() or "CHIEF TECHNOLOGY" in lead.contact.title.upper()
        print(f"   - {lead.contact.full_name} ({lead.contact.title}) - Score: {lead.score.total_score}")
    
    # Test 4: Scoring breakdown
    print("\n🎯 Test 4: Scoring breakdown")
    if results:
        lead = results[0]
        print(f"Lead: {lead.contact.full_name} at {lead.company.name}")
        print(f"  Total Score: {lead.score.total_score}")
        print(f"  - Industry Match: {lead.score.industry_match}/30")
        print(f"  - Title Relevance: {lead.score.title_relevance}/30")
        print(f"  - Company Size: {lead.score.company_size_fit}/20")
        print(f"  - Recent Activity: {lead.score.recent_activity}/20")
        print(f"  - Confidence: {lead.score.confidence:.2f}")
        print(f"  - Priority: {lead.outreach_priority}")
        
        # Verify score components
        total = (lead.score.industry_match + lead.score.title_relevance + 
                lead.score.company_size_fit + lead.score.recent_activity)
        assert total == lead.score.total_score
    
    # Test 5: Performance
    print("\n⚡ Test 5: Performance test")
    import time
    start = time.time()
    criteria = ScanCriteria(min_score=0, max_results=50)
    results = await scanner.scan_for_leads(criteria)
    duration = time.time() - start
    print(f"✅ Scanned {len(results)} leads in {duration:.3f} seconds")
    assert duration < 1.0, f"Scan too slow: {duration}s"
    
    print("\n🎉 All tests passed!")


if __name__ == "__main__":
    asyncio.run(run_simple_tests())