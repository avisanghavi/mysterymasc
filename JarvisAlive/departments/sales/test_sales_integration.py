#!/usr/bin/env python3
"""
Test script for Sales Department Integration
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sales_department import SalesDepartment


async def test_sales_department_integration():
    """Test the integrated Sales Department with real agents"""
    
    print("🏢 Testing Sales Department Integration")
    print("=" * 50)
    
    # Initialize Sales Department
    try:
        department = SalesDepartment(
            redis_client=None,  # Mock Redis for testing
            session_id="test_session_123"
        )
        print("✅ Sales Department initialized successfully")
        
        # Test agent status
        agent_status = department.get_agent_status()
        print(f"📊 Agent Status: {agent_status}")
        
        # Test workflow options
        workflow_options = department.get_workflow_options()
        print(f"🔧 Available workflows: {len(workflow_options)}")
        for workflow in workflow_options:
            print(f"   - {workflow['name']}: {workflow['description']}")
        
    except Exception as e:
        print(f"❌ Initialization error: {e}")
        return
    
    # Test 1: Lead Generation Workflow
    print("\n📈 Test 1: Lead Generation Workflow")
    config = {
        "workflow_type": "lead_generation",
        "industries": ["SaaS", "FinTech"],
        "titles": ["CTO", "VP Engineering"],
        "max_results": 10
    }
    
    try:
        result = await department.execute_workflow(config)
        if result.get("success"):
            print(f"✅ Found {result.get('leads_found', 0)} leads")
            print(f"   Execution time: {result.get('execution_time', 0):.2f}s")
            
            # Show sample leads
            leads = result.get("leads", [])
            for lead in leads[:3]:
                print(f"   - {lead.get('contact', {}).get('full_name', 'Unknown')} at {lead.get('company', {}).get('name', 'Unknown Company')}")
        else:
            print(f"❌ Lead generation failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Lead generation error: {e}")
    
    # Test 2: Quick Wins Workflow
    print("\n🎯 Test 2: Quick Wins Workflow")
    config = {
        "workflow_type": "quick_wins",
        "industries": ["SaaS"],
        "titles": ["CTO"],
        "sender_name": "John Smith",
        "sender_title": "Account Executive",
        "sender_company": "TestCorp"
    }
    
    try:
        result = await department.execute_workflow(config)
        if result.get("success"):
            print(f"✅ Generated {result.get('messages_generated', 0)} outreach messages")
            print(f"   High-quality leads: {result.get('leads_found', 0)}")
            print(f"   Execution time: {result.get('execution_time', 0):.2f}s")
            
            # Show sample outreach
            quick_wins = result.get("quick_wins", [])
            if quick_wins:
                sample = quick_wins[0]
                lead_info = sample.get("lead", {})
                message_info = sample.get("message", {})
                print(f"   📧 Sample outreach to {lead_info.get('contact', {}).get('full_name', 'Unknown')}:")
                print(f"      Subject: {message_info.get('subject', 'No subject')}")
                print(f"      Personalization: {message_info.get('personalization_score', 0):.2f}")
        else:
            print(f"❌ Quick wins failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Quick wins error: {e}")
    
    # Test 3: Full Outreach Workflow (smaller campaign)
    print("\n📨 Test 3: Full Outreach Campaign")
    config = {
        "workflow_type": "full_outreach",
        "industries": ["SaaS", "FinTech"],
        "titles": ["VP", "Director"],
        "campaign_size": 5,
        "message_tone": "formal",
        "sender_name": "Sarah Johnson",
        "sender_title": "Business Development Manager",
        "sender_company": "SolutionsCorp"
    }
    
    try:
        result = await department.execute_workflow(config)
        if result.get("success"):
            campaign = result.get("campaign_summary", {})
            print(f"✅ Campaign generated successfully")
            print(f"   Leads found: {campaign.get('leads_found', 0)}")
            print(f"   Messages generated: {campaign.get('messages_generated', 0)}")
            print(f"   Avg personalization: {campaign.get('avg_personalization_score', 0):.2f}")
            print(f"   Avg response rate: {campaign.get('avg_response_rate', 0):.2f}")
            print(f"   Estimated responses: {campaign.get('estimated_responses', 0)}")
            print(f"   Execution time: {result.get('execution_time', 0):.2f}s")
            
            # Show sample messages
            messages = result.get("messages", [])
            if messages:
                print(f"   📧 Sample messages:")
                for msg in messages[:2]:
                    print(f"      - {msg.get('contact_name', 'Unknown')} at {msg.get('company_name', 'Unknown')}")
                    print(f"        Subject: {msg.get('subject', 'No subject')}")
                    print(f"        Score: {msg.get('personalization_score', 0):.2f}")
        else:
            print(f"❌ Full outreach failed: {result.get('error', 'Unknown error')}")
    except Exception as e:
        print(f"❌ Full outreach error: {e}")
    
    # Test 4: Department Metrics
    print("\n📊 Test 4: Department Metrics")
    try:
        metrics = department.metrics.dict()
        print(f"✅ Department Metrics:")
        print(f"   Leads generated: {metrics.get('leads_generated', 0)}")
        print(f"   Leads qualified: {metrics.get('leads_qualified', 0)}")
        print(f"   Messages composed: {metrics.get('messages_composed', 0)}")
        print(f"   Workflows executed: {metrics.get('total_workflows_executed', 0)}")
        print(f"   Average execution time: {metrics.get('average_execution_time', 0):.2f}s")
        print(f"   Success rate: {metrics.get('success_rate', 0):.2f}")
        print(f"   Personalization score: {metrics.get('personalization_score', 0):.2f}")
        print(f"   Response rate: {metrics.get('response_rate', 0):.2f}")
    except Exception as e:
        print(f"❌ Metrics error: {e}")
    
    # Test 5: Execution Time Estimation
    print("\n⏱️ Test 5: Execution Time Estimation")
    try:
        workflows = ["lead_generation", "quick_wins", "full_outreach"]
        for workflow in workflows:
            estimated_time = department.estimate_execution_time(workflow, 10)
            print(f"   {workflow}: ~{estimated_time:.1f}s for 10 items")
    except Exception as e:
        print(f"❌ Estimation error: {e}")
    
    print("\n🎉 Sales Department Integration test completed!")


if __name__ == "__main__":
    asyncio.run(test_sales_department_integration())