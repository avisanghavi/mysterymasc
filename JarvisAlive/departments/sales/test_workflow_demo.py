#!/usr/bin/env python3
"""
Demo of Sales Department workflow capabilities
"""
import asyncio


class MockSalesDepartment:
    """Mock Sales Department to demonstrate workflow capabilities"""
    
    def __init__(self):
        self.metrics = {
            "leads_generated": 0,
            "leads_qualified": 0,
            "messages_composed": 0,
            "total_workflows_executed": 0,
            "success_rate": 1.0
        }
    
    def get_agent_status(self):
        """Demonstrate agent status checking"""
        return {
            "lead_scanner": "active",
            "outreach_composer": "active", 
            "response_handler": "not_implemented",
            "meeting_scheduler": "not_implemented"
        }
    
    def get_workflow_options(self):
        """Demonstrate workflow options"""
        return [
            {
                "id": "lead_generation",
                "name": "Lead Generation",
                "description": "Find and qualify potential leads",
                "estimated_time": "10-30 seconds",
                "parameters": ["industries", "titles", "company_sizes", "max_results"]
            },
            {
                "id": "quick_wins", 
                "name": "Quick Wins",
                "description": "Find top 5 leads and prepare outreach",
                "estimated_time": "20-40 seconds",
                "parameters": ["industries", "titles"]
            },
            {
                "id": "full_outreach",
                "name": "Full Outreach Campaign",
                "description": "Find leads and generate personalized messages",
                "estimated_time": "30-60 seconds",
                "parameters": ["industries", "titles", "company_sizes", "message_tone", "campaign_size"]
            }
        ]
    
    async def execute_workflow(self, config):
        """Mock workflow execution to demonstrate capabilities"""
        import time
        import random
        
        workflow_type = config.get("workflow_type", "lead_generation")
        
        # Simulate processing time
        await asyncio.sleep(0.1)
        
        if workflow_type == "lead_generation":
            leads_found = random.randint(5, 15)
            self.metrics["leads_generated"] += leads_found
            
            return {
                "success": True,
                "workflow_type": "lead_generation",
                "leads_found": leads_found,
                "execution_time": 0.25,
                "leads": [
                    {
                        "contact": {"full_name": f"Contact {i}", "title": "CTO"},
                        "company": {"name": f"TechCorp {i}", "industry": "SaaS"},
                        "score": {"total_score": random.randint(70, 95)}
                    }
                    for i in range(min(3, leads_found))
                ]
            }
        
        elif workflow_type == "quick_wins":
            leads_found = 5
            messages_generated = 5
            self.metrics["leads_qualified"] += leads_found
            self.metrics["messages_composed"] += messages_generated
            
            return {
                "success": True,
                "workflow_type": "quick_wins",
                "leads_found": leads_found,
                "messages_generated": messages_generated,
                "execution_time": 0.35,
                "quick_wins": [
                    {
                        "lead": {
                            "contact": {"full_name": f"Executive {i}"},
                            "company": {"name": f"Corp {i}"},
                            "score": {"total_score": random.randint(80, 95)}
                        },
                        "message": {
                            "subject": f"Quick question about Corp {i}'s growth",
                            "personalization_score": random.uniform(0.7, 0.9),
                            "predicted_response_rate": random.uniform(0.6, 0.8)
                        }
                    }
                    for i in range(3)
                ]
            }
        
        elif workflow_type == "full_outreach":
            campaign_size = config.get("campaign_size", 10)
            leads_found = campaign_size
            messages_generated = campaign_size
            
            self.metrics["leads_qualified"] += leads_found
            self.metrics["messages_composed"] += messages_generated
            
            return {
                "success": True,
                "workflow_type": "full_outreach",
                "execution_time": 0.45,
                "campaign_summary": {
                    "leads_found": leads_found,
                    "messages_generated": messages_generated,
                    "avg_personalization_score": 0.75,
                    "avg_response_rate": 0.68,
                    "estimated_responses": int(messages_generated * 0.68),
                    "campaign_size": campaign_size
                },
                "messages": [
                    {
                        "contact_name": f"Contact {i}",
                        "company_name": f"Company {i}",
                        "subject": f"Partnership opportunity for Company {i}",
                        "personalization_score": random.uniform(0.6, 0.9),
                        "predicted_response_rate": random.uniform(0.5, 0.8)
                    }
                    for i in range(min(3, messages_generated))
                ]
            }
        
        self.metrics["total_workflows_executed"] += 1
        return {"success": False, "error": f"Unknown workflow: {workflow_type}"}


async def demo_sales_workflows():
    """Demonstrate Sales Department workflow capabilities"""
    
    print("🏢 Sales Department Workflow Demo")
    print("=" * 50)
    
    # Initialize department
    department = MockSalesDepartment()
    print("✅ Sales Department initialized")
    
    # Show agent status
    print(f"\n🤖 Agent Status: {department.get_agent_status()}")
    
    # Show available workflows
    print("\n🔧 Available Workflows:")
    for workflow in department.get_workflow_options():
        print(f"   • {workflow['name']}: {workflow['description']}")
        print(f"     Time: {workflow['estimated_time']}")
    
    # Demo 1: Lead Generation
    print("\n📈 Demo 1: Lead Generation Workflow")
    config = {
        "workflow_type": "lead_generation",
        "industries": ["SaaS", "FinTech"],
        "titles": ["CTO", "VP Engineering"],
        "max_results": 10
    }
    
    result = await department.execute_workflow(config)
    if result["success"]:
        print(f"✅ Generated {result['leads_found']} leads in {result['execution_time']}s")
        print("   Sample leads:")
        for lead in result["leads"][:2]:
            contact = lead["contact"]
            company = lead["company"]
            score = lead["score"]
            print(f"   • {contact['full_name']} ({contact['title']}) at {company['name']}")
            print(f"     Industry: {company['industry']} | Score: {score['total_score']}")
    
    # Demo 2: Quick Wins
    print("\n🎯 Demo 2: Quick Wins Workflow")
    config = {
        "workflow_type": "quick_wins",
        "industries": ["SaaS"],
        "titles": ["CTO"]
    }
    
    result = await department.execute_workflow(config)
    if result["success"]:
        print(f"✅ Found {result['leads_found']} high-quality leads")
        print(f"✅ Generated {result['messages_generated']} personalized messages")
        print("   Sample quick wins:")
        for win in result["quick_wins"][:2]:
            lead_info = win["lead"]
            message_info = win["message"]
            print(f"   • {lead_info['contact']['full_name']} at {lead_info['company']['name']}")
            print(f"     Score: {lead_info['score']['total_score']}")
            print(f"     Subject: {message_info['subject']}")
            print(f"     Personalization: {message_info['personalization_score']:.2f}")
    
    # Demo 3: Full Outreach Campaign
    print("\n📨 Demo 3: Full Outreach Campaign")
    config = {
        "workflow_type": "full_outreach",
        "industries": ["SaaS", "FinTech"],
        "campaign_size": 15,
        "message_tone": "formal"
    }
    
    result = await department.execute_workflow(config)
    if result["success"]:
        campaign = result["campaign_summary"]
        print(f"✅ Campaign completed in {result['execution_time']}s")
        print(f"   Leads processed: {campaign['leads_found']}")
        print(f"   Messages generated: {campaign['messages_generated']}")
        print(f"   Avg personalization: {campaign['avg_personalization_score']:.2f}")
        print(f"   Avg response rate: {campaign['avg_response_rate']:.2f}")
        print(f"   Estimated responses: {campaign['estimated_responses']}")
        
        print("\n   Sample campaign messages:")
        for msg in result["messages"][:2]:
            print(f"   • {msg['contact_name']} at {msg['company_name']}")
            print(f"     Subject: {msg['subject']}")
            print(f"     Quality: {msg['personalization_score']:.2f}")
    
    # Show final metrics
    print(f"\n📊 Department Metrics:")
    metrics = department.metrics
    print(f"   Leads generated: {metrics['leads_generated']}")
    print(f"   Leads qualified: {metrics['leads_qualified']}")
    print(f"   Messages composed: {metrics['messages_composed']}")
    print(f"   Workflows executed: {metrics['total_workflows_executed']}")
    print(f"   Success rate: {metrics['success_rate']:.2f}")
    
    print("\n🎉 Sales Department workflow demo completed!")
    print("\n💡 Key Integration Benefits:")
    print("   • Real agents provide authentic lead scoring and personalization")
    print("   • Template system ensures professional, varied outreach messages")
    print("   • Comprehensive metrics track performance across all workflows")
    print("   • Error handling ensures reliable operation")
    print("   • Scalable architecture supports future agent additions")


if __name__ == "__main__":
    asyncio.run(demo_sales_workflows())