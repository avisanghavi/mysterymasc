#!/usr/bin/env python3
"""
Test script for Lead Scanner Agent Implementation
"""
import asyncio
import sys
import os
sys.path.append('/Users/avisanghavi/Desktop/ProjectSpace_Jarvis/Jarvolution/Hey..J/JarvisAlive')

from lead_scanner_implementation import LeadScannerAgent, ScanCriteria


async def test_lead_scanner():
    """Test the Lead Scanner Agent with various criteria"""
    
    print("🔍 Testing Lead Scanner Agent Implementation")
    print("=" * 50)
    
    # Initialize the agent
    agent = LeadScannerAgent(mode="mock")
    
    # Test 1: Basic scan
    print("\n📊 Test 1: Basic scan with default criteria")
    criteria = ScanCriteria(min_score=50, max_results=10)
    
    try:
        leads = await agent.scan_for_leads(criteria)
        print(f"✅ Found {len(leads)} leads")
        
        if leads:
            top_lead = leads[0]
            print(f"   Top lead: {top_lead.contact.full_name} at {top_lead.company.name}")
            print(f"   Score: {top_lead.score.total_score}")
            print(f"   Priority: {top_lead.outreach_priority}")
            print(f"   Explanation: {top_lead.score.explanation}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Industry-specific scan
    print("\n🏭 Test 2: SaaS industry scan")
    criteria = ScanCriteria(
        industries=["SaaS"],
        min_score=60,
        max_results=5
    )
    
    try:
        leads = await agent.scan_for_leads(criteria)
        print(f"✅ Found {len(leads)} SaaS leads")
        
        for lead in leads[:3]:
            print(f"   - {lead.contact.full_name} ({lead.contact.title}) at {lead.company.name}")
            print(f"     Score: {lead.score.total_score} | Industry: {lead.score.industry_match}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Title-specific scan
    print("\n👔 Test 3: VP-level scan")
    criteria = ScanCriteria(
        titles=["VP", "Vice President"],
        min_score=55,
        max_results=8
    )
    
    try:
        leads = await agent.scan_for_leads(criteria)
        print(f"✅ Found {len(leads)} VP-level leads")
        
        for lead in leads[:3]:
            print(f"   - {lead.contact.full_name} ({lead.contact.title}) at {lead.company.name}")
            print(f"     Score: {lead.score.total_score} | Title: {lead.score.title_relevance}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Combined criteria
    print("\n🎯 Test 4: Combined criteria (SaaS + VP + High score)")
    criteria = ScanCriteria(
        industries=["SaaS", "FinTech"],
        titles=["VP", "Director", "Chief"],
        min_score=70,
        max_results=3
    )
    
    try:
        leads = await agent.scan_for_leads(criteria)
        print(f"✅ Found {len(leads)} high-quality leads")
        
        for lead in leads:
            print(f"   - {lead.contact.full_name} ({lead.contact.title}) at {lead.company.name}")
            print(f"     Score: {lead.score.total_score} | Priority: {lead.outreach_priority}")
            print(f"     Breakdown: Industry={lead.score.industry_match}, Title={lead.score.title_relevance}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n🎉 Lead Scanner Agent test completed!")


if __name__ == "__main__":
    asyncio.run(test_lead_scanner())