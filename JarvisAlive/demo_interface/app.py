#!/usr/bin/env python3
"""
TASK 14: Demo Web Interface
FastAPI application for demonstrating HeyJarvis capabilities
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import uuid
import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
import logging

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock Redis for demo purposes
class MockRedis:
    def __init__(self):
        self.data = {}
        self.pubsub_data = {}
        
    async def get(self, key: str):
        return self.data.get(key)
        
    async def set(self, key: str, value: str):
        self.data[key] = value
        
    async def setex(self, key: str, ttl: int, value: str):
        self.data[key] = value
        
    async def publish(self, channel: str, message: str):
        if channel not in self.pubsub_data:
            self.pubsub_data[channel] = []
        self.pubsub_data[channel].append(message)
        
        # Notify WebSocket connections
        if channel in active_subscriptions:
            for callback in active_subscriptions[channel]:
                try:
                    await callback(message)
                except Exception as e:
                    logging.error(f"Error in pubsub callback: {e}")
    
    def pubsub(self):
        return MockPubSub()
        
    async def close(self):
        pass

class MockPubSub:
    def __init__(self):
        self.channels = []
        
    async def subscribe(self, channel: str):
        self.channels.append(channel)
        
    async def unsubscribe(self):
        self.channels.clear()
        
    async def close(self):
        pass
        
    async def listen(self):
        # Mock implementation - in reality would listen to Redis
        while True:
            await asyncio.sleep(0.1)
            # Mock messages for demo
            yield {"type": "message", "data": json.dumps({"demo": "message"})}

# Import enhanced Jarvis (with error handling for demo)
try:
    from orchestration.jarvis import Jarvis, JarvisConfig
    from orchestration.orchestrator import OrchestratorConfig
    JARVIS_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Jarvis not available: {e}")
    JARVIS_AVAILABLE = False

app = FastAPI(
    title="HeyJarvis Demo Interface",
    description="Interactive demo of HeyJarvis sales automation capabilities",
    version="1.0.0"
)

# Store active connections and subscriptions
connections: Dict[str, WebSocket] = {}
active_subscriptions: Dict[str, List] = {}

# Redis client
redis_client = MockRedis()

# Pydantic models
class BusinessRequest(BaseModel):
    request: str
    session_id: Optional[str] = None
    demo_scenario: Optional[str] = None
    
class DemoScenario(BaseModel):
    id: str
    name: str
    description: str
    example_request: str
    expected_duration: str

@app.on_event("startup")
async def startup():
    """Initialize the application"""
    logging.info("HeyJarvis Demo Interface starting up")
    
@app.on_event("shutdown")  
async def shutdown():
    """Cleanup on shutdown"""
    if redis_client:
        await redis_client.close()
    logging.info("HeyJarvis Demo Interface shutting down")

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    connections[session_id] = websocket
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connection",
            "status": "connected", 
            "session_id": session_id,
            "timestamp": datetime.now().isoformat()
        })
        
        # Subscribe to progress updates
        channel = f"progress:{session_id}"
        if channel not in active_subscriptions:
            active_subscriptions[channel] = []
        
        async def progress_callback(message):
            try:
                data = json.loads(message)
                await websocket.send_json({
                    "type": "progress",
                    **data
                })
            except Exception as e:
                logging.error(f"Error sending progress update: {e}")
        
        active_subscriptions[channel].append(progress_callback)
        
        # Keep connection alive
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
    finally:
        connections.pop(session_id, None)
        # Clean up subscriptions
        for channel in active_subscriptions:
            active_subscriptions[channel] = [
                cb for cb in active_subscriptions[channel] 
                if cb != progress_callback
            ]

@app.post("/api/process")
async def process_request(request: BusinessRequest):
    """Process a business request"""
    
    # Generate session ID if not provided
    if not request.session_id:
        request.session_id = f"demo_{uuid.uuid4()}"
        
    # Process request in background
    asyncio.create_task(
        process_request_background(request)
    )
    
    return {
        "session_id": request.session_id,
        "status": "processing",
        "message": "Request received and being processed"
    }

async def process_request_background(request: BusinessRequest):
    """Process request in background with progress updates"""
    session_id = request.session_id
    
    try:
        # Send initial progress update
        await redis_client.publish(f"progress:{session_id}", json.dumps({
            "status": "started",
            "progress": 0,
            "message": "Starting request processing...",
            "step": "Initialization"
        }))
        
        # Get actual request text
        if request.demo_scenario:
            actual_request = get_demo_scenario_request(request.demo_scenario)
        else:
            actual_request = request.request
            
        # Simulate processing steps with progress updates
        await simulate_processing_steps(session_id, actual_request)
        
        # Generate final result
        result = await generate_demo_result(actual_request, session_id)
        
        # Send completion update
        await redis_client.publish(f"progress:{session_id}", json.dumps({
            "status": "completed",
            "progress": 100,
            "message": "Request completed successfully!",
            "step": "Complete"
        }))
        
        # Store results in Redis for export
        results_key = f"session:{session_id}:results"
        await redis_client.setex(results_key, 3600, json.dumps(result))  # Store for 1 hour
        
        # Send final result via WebSocket
        if session_id in connections:
            await connections[session_id].send_json({
                "type": "complete",
                "result": result,
                "timestamp": datetime.now().isoformat()
            })
            
    except Exception as e:
        logging.error(f"Error processing request: {e}")
        
        # Send error update
        await redis_client.publish(f"progress:{session_id}", json.dumps({
            "status": "error",
            "progress": 0,
            "message": f"Error: {str(e)}",
            "step": "Error"
        }))
        
        if session_id in connections:
            await connections[session_id].send_json({
                "type": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })

async def simulate_processing_steps(session_id: str, request: str):
    """Simulate processing steps with realistic progress updates"""
    
    # Step 1: Analyze request
    await redis_client.publish(f"progress:{session_id}", json.dumps({
        "status": "running",
        "progress": 10,
        "message": "Analyzing request and determining intent...",
        "step": "Intent Analysis"
    }))
    await asyncio.sleep(0.5)
    
    # Step 2: Lead scanning
    await redis_client.publish(f"progress:{session_id}", json.dumps({
        "status": "running",
        "progress": 30,
        "message": "Scanning for qualified leads...",
        "step": "Lead Scanning"
    }))
    await asyncio.sleep(1.0)
    
    # Step 3: AI enrichment
    await redis_client.publish(f"progress:{session_id}", json.dumps({
        "status": "running",
        "progress": 60,
        "message": "Enriching leads with AI insights...",
        "step": "AI Enrichment"
    }))
    await asyncio.sleep(0.8)
    
    # Step 4: Scoring and ranking
    await redis_client.publish(f"progress:{session_id}", json.dumps({
        "status": "running",
        "progress": 80,
        "message": "Scoring and ranking prospects...",
        "step": "Lead Scoring"
    }))
    await asyncio.sleep(0.5)
    
    # Step 5: Finalizing results
    await redis_client.publish(f"progress:{session_id}", json.dumps({
        "status": "running",
        "progress": 95,
        "message": "Finalizing results and generating summary...",
        "step": "Results Generation"
    }))
    await asyncio.sleep(0.3)

async def generate_demo_result(request: str, session_id: str):
    """Generate demo result based on request"""
    
    # Determine request type
    request_lower = request.lower()
    
    if "leads" in request_lower or "prospects" in request_lower or "saas" in request_lower or "companies" in request_lower:
        return generate_leads_result(request)
    elif "quick wins" in request_lower or "best" in request_lower:
        return generate_quick_wins_result(request)
    elif "campaign" in request_lower or "outreach" in request_lower:
        return generate_campaign_result(request)
    elif "cto" in request_lower or "executive" in request_lower or "fintech" in request_lower:
        return generate_campaign_result(request)
    else:
        # Default to leads for demo scenarios
        return generate_leads_result(request)

def generate_leads_result(request: str):
    """Generate mock leads result"""
    
    # Extract number from request
    import re
    numbers = re.findall(r'\b(\d+)\b', request)
    lead_count = int(numbers[0]) if numbers else 10
    
    # Generate mock leads
    mock_leads = []
    companies = [
        ("TechFlow Inc", "SaaS", "Cloud Infrastructure"),
        ("DataSync Pro", "SaaS", "Data Analytics"),
        ("CloudWorks", "SaaS", "Workflow Automation"),
        ("FinanceAI", "FinTech", "AI-Powered Finance"),
        ("SecureChat", "SaaS", "Communication Platform"),
        ("AutoScale", "SaaS", "DevOps Tools"),
        ("SmartCRM", "SaaS", "Customer Management"),
        ("DevTools Pro", "SaaS", "Developer Tools"),
        ("HealthTech", "Healthcare", "Medical Software"),
        ("EduPlatform", "SaaS", "Learning Management")
    ]
    
    contacts = [
        ("Sarah Chen", "VP Engineering", "sarah.chen@"),
        ("Michael Rodriguez", "CTO", "m.rodriguez@"),
        ("Emily Johnson", "Director of Technology", "emily.j@"),
        ("David Kim", "VP of Product", "d.kim@"),
        ("Lisa Wang", "Chief Technology Officer", "lisa.wang@"),
        ("James Brown", "Engineering Manager", "james.brown@"),
        ("Maria Garcia", "VP Engineering", "maria.g@"),
        ("Robert Taylor", "Director of Engineering", "r.taylor@"),
        ("Jennifer Lee", "CTO", "jennifer.lee@"),
        ("Christopher Wilson", "VP Technology", "c.wilson@")
    ]
    
    for i in range(min(lead_count, len(companies))):
        company = companies[i]
        contact = contacts[i]
        
        mock_leads.append({
            "lead_id": f"lead_{uuid.uuid4()}",
            "contact": {
                "full_name": contact[0],
                "title": contact[1],
                "email": f"{contact[2]}{company[0].lower().replace(' ', '')}.com"
            },
            "company": {
                "name": company[0],
                "industry": company[1],
                "description": company[2],
                "employee_count": 50 + (i * 25)
            },
            "score": {
                "total_score": 85 - (i * 3),
                "industry_match": 28 - i,
                "title_relevance": 26 - i,
                "company_size_fit": 18 - (i // 2),
                "recent_activity": 15 - (i // 3)
            }
        })
    
    return {
        "summary": {
            "headline": f"Found {len(mock_leads)} Qualified Leads",
            "details": f"Successfully identified {len(mock_leads)} high-quality prospects matching your criteria. {sum(1 for l in mock_leads if l['score']['total_score'] > 80)} leads scored above 80/100."
        },
        "results": {
            "leads": mock_leads,
            "total_found": len(mock_leads),
            "high_quality": sum(1 for l in mock_leads if l['score']['total_score'] > 80),
            "processing_time": "2.3 seconds"
        }
    }

def generate_quick_wins_result(request: str):
    """Generate mock quick wins result"""
    
    # Extract number from request
    import re
    numbers = re.findall(r'\b(\d+)\b', request)
    count = int(numbers[0]) if numbers else 5
    
    mock_leads = [
        {
            "lead_id": f"lead_{uuid.uuid4()}",
            "contact": {
                "full_name": "Sarah Chen",
                "title": "VP Engineering",
                "email": "sarah.chen@techflow.com"
            },
            "company": {
                "name": "TechFlow Inc", 
                "industry": "SaaS",
                "employee_count": 150
            },
            "score": {"total_score": 92},
            "why_now": "Recently posted about scaling challenges"
        },
        {
            "lead_id": f"lead_{uuid.uuid4()}",
            "contact": {
                "full_name": "Michael Rodriguez",
                "title": "CTO",
                "email": "m.rodriguez@datasync.com"
            },
            "company": {
                "name": "DataSync Pro",
                "industry": "SaaS", 
                "employee_count": 200
            },
            "score": {"total_score": 89},
            "why_now": "Company just raised Series B funding"
        },
        {
            "lead_id": f"lead_{uuid.uuid4()}",
            "contact": {
                "full_name": "Emily Johnson",
                "title": "Director of Technology",
                "email": "emily.j@cloudworks.com"
            },
            "company": {
                "name": "CloudWorks",
                "industry": "SaaS",
                "employee_count": 120
            },
            "score": {"total_score": 87},
            "why_now": "Mentioned automation needs in recent interview"
        }
    ]
    
    return {
        "summary": {
            "headline": f"Identified {count} Quick Win Opportunities",
            "details": f"Found {count} high-scoring prospects ready for immediate outreach. Combined revenue potential: ${count * 25000:,}."
        },
        "results": {
            "top_leads": mock_leads[:count],
            "avg_score": sum(l['score']['total_score'] for l in mock_leads[:count]) / count,
            "revenue_potential": f"${count * 25000:,}",
            "estimated_close_time": "2-4 weeks"
        }
    }

def generate_campaign_result(request: str):
    """Generate mock campaign result"""
    
    campaign_id = f"campaign_{uuid.uuid4()}"
    
    return {
        "summary": {
            "headline": "Outreach Campaign Created Successfully",
            "details": f"Created campaign '{campaign_id}' with 3 message templates and 5-touch follow-up sequence. Ready to reach 500+ prospects."
        },
        "results": {
            "campaign_id": campaign_id,
            "templates_created": 3,
            "follow_up_sequence": 5,
            "estimated_reach": 500,
            "messages": [
                {
                    "template_id": "temp_1",
                    "subject": "Quick question about your scaling challenges",
                    "personalization_score": 0.85
                },
                {
                    "template_id": "temp_2", 
                    "subject": "Solving [Company] engineering bottlenecks",
                    "personalization_score": 0.92
                },
                {
                    "template_id": "temp_3",
                    "subject": "How [Similar Company] cut deployment time by 60%",
                    "personalization_score": 0.78
                }
            ]
        }
    }

def generate_default_result(request: str):
    """Generate default result for unknown requests"""
    
    return {
        "summary": {
            "headline": "Request Processed Successfully",
            "details": "Your request has been processed and analyzed. Here are the key insights and recommendations."
        },
        "results": {
            "analysis": "Request analyzed and processed through HeyJarvis AI system",
            "insights": [
                "Intent successfully classified",
                "Relevant data sources identified",
                "Recommendations generated"
            ],
            "next_steps": [
                "Review generated insights",
                "Apply recommendations", 
                "Monitor results"
            ]
        }
    }

@app.get("/api/scenarios")
async def get_demo_scenarios() -> List[DemoScenario]:
    """Get available demo scenarios"""
    return [
        DemoScenario(
            id="quick_leads",
            name="Quick Lead Generation",
            description="Find 10 qualified B2B SaaS leads",
            example_request="Find me 10 SaaS companies with 50-200 employees",
            expected_duration="15-20 seconds"
        ),
        DemoScenario(
            id="executive_outreach",
            name="Executive Outreach",
            description="Find and prepare outreach to C-level executives",
            example_request="Find CTOs at Series A fintech companies and prepare personalized outreach",
            expected_duration="30-45 seconds"
        ),
        DemoScenario(
            id="quick_wins",
            name="Quick Wins Analysis",
            description="Identify the 5 best prospects to contact right now",
            example_request="Show me quick wins - find the best 5 leads to contact today",
            expected_duration="25-35 seconds"
        ),
        DemoScenario(
            id="full_campaign",
            name="Full Outreach Campaign",
            description="Complete campaign from lead finding to message preparation",
            example_request="Create an outreach campaign targeting VP Sales at growing SaaS companies",
            expected_duration="45-60 seconds"
        )
    ]

def get_demo_scenario_request(scenario_id: str) -> str:
    """Get the request text for a demo scenario"""
    scenarios = {
        "quick_leads": "Find me 10 SaaS companies with 50-200 employees, focusing on those using cloud infrastructure",
        "executive_outreach": "Find CTOs and VP Engineering at Series A fintech companies and create personalized outreach messages",
        "quick_wins": "Show me quick wins - find the 5 highest-scoring leads from enterprise software companies",
        "full_campaign": "Create a complete outreach campaign targeting VP Sales at B2B SaaS companies with 100-500 employees"
    }
    
    return scenarios.get(scenario_id, "Find me 10 qualified leads")

@app.get("/api/export/{session_id}")
async def export_results(session_id: str, format: str = "json"):
    """Export session results"""
    
    # Get results from Redis
    results_key = f"session:{session_id}:results"
    results_data = await redis_client.get(results_key)
    
    if not results_data:
        raise HTTPException(status_code=404, detail="Results not found")
        
    results = json.loads(results_data)
    
    if format == "json":
        return results
    elif format == "csv":
        # Convert to CSV format
        import csv
        import io
        
        output = io.StringIO()
        
        # Handle different result structures
        leads_data = []
        if "results" in results and "leads" in results["results"]:
            leads_data = results["results"]["leads"]
        elif "leads" in results:
            leads_data = results["leads"]
        
        if leads_data:
            writer = csv.writer(output)
            writer.writerow(["Name", "Title", "Company", "Email", "Score"])
            
            for lead in leads_data:
                writer.writerow([
                    lead["contact"]["full_name"],
                    lead["contact"]["title"],
                    lead["company"]["name"],
                    lead["contact"]["email"],
                    lead["score"]["total_score"]
                ])
        else:
            writer = csv.writer(output)
            writer.writerow(["Data"])
            writer.writerow([str(results)])
                
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=leads_{session_id}.csv"}
        )
    else:
        raise HTTPException(status_code=400, detail="Unsupported format")

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "jarvis_available": JARVIS_AVAILABLE
    }

@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the demo interface"""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HeyJarvis - Sales Automation Demo</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0a0b0d;
            color: #ffffff;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            padding: 1.5rem 2rem;
        }
        
        .header h1 {
            font-size: 2rem;
            font-weight: 700;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        
        .header p {
            color: #8b92a3;
            margin-top: 0.5rem;
        }
        
        .container {
            flex: 1;
            display: flex;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
            padding: 2rem;
            gap: 2rem;
        }
        
        .sidebar {
            width: 300px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 1.5rem;
            height: fit-content;
        }
        
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }
        
        .scenarios {
            margin-top: 1rem;
        }
        
        .scenario {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 0.5rem;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .scenario:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: #667eea;
            transform: translateY(-2px);
        }
        
        .scenario h3 {
            font-size: 1rem;
            margin-bottom: 0.25rem;
        }
        
        .scenario p {
            font-size: 0.875rem;
            color: #8b92a3;
        }
        
        .scenario .duration {
            font-size: 0.75rem;
            color: #667eea;
            margin-top: 0.5rem;
        }
        
        .input-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 2rem;
        }
        
        .input-group {
            position: relative;
        }
        
        #requestInput {
            width: 100%;
            padding: 1rem 1.5rem;
            padding-right: 120px;
            background: rgba(255, 255, 255, 0.05);
            border: 2px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            color: #ffffff;
            font-size: 1rem;
            transition: all 0.3s;
        }
        
        #requestInput:focus {
            outline: none;
            border-color: #667eea;
            background: rgba(255, 255, 255, 0.08);
        }
        
        #requestInput::placeholder {
            color: #8b92a3;
        }
        
        .submit-btn {
            position: absolute;
            right: 8px;
            top: 50%;
            transform: translateY(-50%);
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .submit-btn:hover {
            transform: translateY(-50%) scale(1.05);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        .submit-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: translateY(-50%);
        }
        
        .progress-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 2rem;
            min-height: 300px;
            position: relative;
            overflow: hidden;
        }
        
        .progress-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1.5rem;
        }
        
        .progress-header h2 {
            font-size: 1.25rem;
        }
        
        .status-badge {
            padding: 0.25rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
        }
        
        .status-pending {
            background: rgba(255, 193, 7, 0.2);
            color: #ffc107;
        }
        
        .status-running {
            background: rgba(33, 150, 243, 0.2);
            color: #2196f3;
        }
        
        .status-completed {
            background: rgba(76, 175, 80, 0.2);
            color: #4caf50;
        }
        
        .status-error {
            background: rgba(244, 67, 54, 0.2);
            color: #f44336;
        }
        
        .progress-steps {
            position: relative;
            padding-left: 2rem;
            min-height: 200px;
        }
        
        .progress-step {
            margin-bottom: 1.5rem;
            opacity: 0;
            animation: fadeIn 0.5s forwards;
        }
        
        .progress-step::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0.5rem;
            width: 12px;
            height: 12px;
            background: #8b92a3;
            border-radius: 50%;
        }
        
        .progress-step.active::before {
            background: #2196f3;
            box-shadow: 0 0 0 4px rgba(33, 150, 243, 0.2);
        }
        
        .progress-step.completed::before {
            background: #4caf50;
        }
        
        .progress-step h3 {
            font-size: 1rem;
            margin-bottom: 0.25rem;
        }
        
        .progress-step p {
            font-size: 0.875rem;
            color: #8b92a3;
        }
        
        .progress-bar {
            position: absolute;
            bottom: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
        }
        
        .progress-bar-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.5s ease;
        }
        
        .results-section {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 12px;
            padding: 2rem;
            display: none;
        }
        
        .results-section.show {
            display: block;
            animation: fadeIn 0.5s;
        }
        
        .result-summary {
            background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
            border: 1px solid rgba(102, 126, 234, 0.3);
            border-radius: 8px;
            padding: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .result-summary h3 {
            font-size: 1.5rem;
            margin-bottom: 0.5rem;
        }
        
        .result-metrics {
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
            flex-wrap: wrap;
        }
        
        .metric {
            text-align: center;
            min-width: 100px;
        }
        
        .metric-value {
            font-size: 2rem;
            font-weight: 700;
            color: #667eea;
        }
        
        .metric-label {
            font-size: 0.875rem;
            color: #8b92a3;
        }
        
        .result-cards {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }
        
        .result-card {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 8px;
            padding: 1.5rem;
            transition: all 0.3s;
        }
        
        .result-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
        }
        
        .result-card h4 {
            font-size: 1.1rem;
            margin-bottom: 0.5rem;
        }
        
        .result-card p {
            color: #8b92a3;
            margin-bottom: 0.5rem;
        }
        
        .lead-score {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: rgba(76, 175, 80, 0.2);
            color: #4caf50;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.875rem;
        }
        
        .export-btn {
            background: rgba(102, 126, 234, 0.2);
            color: #667eea;
            border: 1px solid #667eea;
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
            margin-top: 1rem;
        }
        
        .export-btn:hover {
            background: rgba(102, 126, 234, 0.3);
            transform: translateY(-2px);
        }
        
        .connection-status {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.875rem;
            font-weight: 600;
            z-index: 1000;
        }
        
        .connection-status.connected {
            background: rgba(76, 175, 80, 0.2);
            color: #4caf50;
        }
        
        .connection-status.disconnected {
            background: rgba(244, 67, 54, 0.2);
            color: #f44336;
        }
        
        @keyframes fadeIn {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        @keyframes pulse {
            0% {
                transform: scale(1);
            }
            50% {
                transform: scale(1.05);
            }
            100% {
                transform: scale(1);
            }
        }
        
        .loading {
            animation: pulse 1.5s infinite;
        }
        
        @media (max-width: 768px) {
            .container {
                flex-direction: column;
                padding: 1rem;
            }
            
            .sidebar {
                width: 100%;
            }
            
            .result-metrics {
                justify-content: space-around;
            }
        }
    </style>
</head>
<body>
    <header class="header">
        <h1>HeyJarvis</h1>
        <p>AI-Powered Sales Automation Demo</p>
    </header>
    
    <div class="connection-status disconnected" id="connectionStatus">
        Disconnected
    </div>
    
    <div class="container">
        <aside class="sidebar">
            <h2>Demo Scenarios</h2>
            <div class="scenarios" id="scenarios">
                <!-- Scenarios will be loaded here -->
            </div>
        </aside>
        
        <main class="main">
            <section class="input-section">
                <h2>What can I help you with?</h2>
                <div class="input-group">
                    <input 
                        type="text" 
                        id="requestInput" 
                        placeholder="E.g., Find me 20 SaaS leads with 50-200 employees"
                        autocomplete="off"
                    />
                    <button class="submit-btn" id="submitBtn">Process</button>
                </div>
            </section>
            
            <section class="progress-section" id="progressSection">
                <div class="progress-header">
                    <h2>Progress</h2>
                    <span class="status-badge status-pending" id="statusBadge">Waiting</span>
                </div>
                <div class="progress-steps" id="progressSteps">
                    <div class="progress-step">
                        <h3>Ready</h3>
                        <p>Enter your request above to begin processing</p>
                    </div>
                </div>
                <div class="progress-bar">
                    <div class="progress-bar-fill" id="progressBarFill" style="width: 0%"></div>
                </div>
            </section>
            
            <section class="results-section" id="resultsSection">
                <!-- Results will be displayed here -->
            </section>
        </main>
    </div>
    
    <script>
        let ws = null;
        let currentSessionId = null;
        let isProcessing = false;
        
        // Load demo scenarios
        async function loadScenarios() {
            try {
                const response = await fetch('/api/scenarios');
                const scenarios = await response.json();
                
                const container = document.getElementById('scenarios');
                container.innerHTML = scenarios.map(scenario => `
                    <div class="scenario" onclick="selectScenario('${scenario.id}', '${scenario.example_request}')">
                        <h3>${scenario.name}</h3>
                        <p>${scenario.description}</p>
                        <div class="duration">⏱ ${scenario.expected_duration}</div>
                    </div>
                `).join('');
            } catch (error) {
                console.error('Failed to load scenarios:', error);
            }
        }
        
        // Select a demo scenario
        function selectScenario(scenarioId, exampleRequest) {
            document.getElementById('requestInput').value = exampleRequest;
            document.getElementById('submitBtn').focus();
        }
        
        // Initialize WebSocket connection
        function initWebSocket(sessionId) {
            if (ws) {
                ws.close();
            }
            
            const wsUrl = `ws://localhost:8000/ws/${sessionId}`;
            ws = new WebSocket(wsUrl);
            
            ws.onopen = () => {
                console.log('WebSocket connected');
                updateConnectionStatus(true);
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleWebSocketMessage(data);
            };
            
            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                updateConnectionStatus(false);
            };
            
            ws.onclose = () => {
                console.log('WebSocket disconnected');
                updateConnectionStatus(false);
            };
        }
        
        // Update connection status
        function updateConnectionStatus(connected) {
            const statusEl = document.getElementById('connectionStatus');
            if (connected) {
                statusEl.className = 'connection-status connected';
                statusEl.textContent = 'Connected';
            } else {
                statusEl.className = 'connection-status disconnected';
                statusEl.textContent = 'Disconnected';
            }
        }
        
        // Handle WebSocket messages
        function handleWebSocketMessage(data) {
            console.log('WebSocket message:', data);
            
            if (data.type === 'connection') {
                updateConnectionStatus(true);
            } else if (data.type === 'progress') {
                updateProgress(data);
            } else if (data.type === 'complete') {
                showResults(data.result);
                isProcessing = false;
            } else if (data.type === 'error') {
                showError(data.error);
                isProcessing = false;
            }
        }
        
        // Update progress display
        function updateProgress(data) {
            const statusBadge = document.getElementById('statusBadge');
            const progressSteps = document.getElementById('progressSteps');
            const progressBarFill = document.getElementById('progressBarFill');
            
            // Update status badge
            if (data.status === 'running') {
                statusBadge.className = 'status-badge status-running';
                statusBadge.textContent = 'Processing';
            } else if (data.status === 'completed') {
                statusBadge.className = 'status-badge status-completed';
                statusBadge.textContent = 'Completed';
            } else if (data.status === 'error') {
                statusBadge.className = 'status-badge status-error';
                statusBadge.textContent = 'Error';
            }
            
            // Add progress step
            if (data.message && data.step) {
                const step = document.createElement('div');
                step.className = 'progress-step active';
                step.innerHTML = `
                    <h3>${data.step}</h3>
                    <p>${data.message}</p>
                `;
                progressSteps.appendChild(step);
                
                // Mark previous steps as completed
                const allSteps = progressSteps.querySelectorAll('.progress-step');
                allSteps.forEach((s, i) => {
                    if (i < allSteps.length - 1) {
                        s.classList.remove('active');
                        s.classList.add('completed');
                    }
                });
                
                // Scroll to latest step
                step.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
            }
            
            // Update progress bar
            if (data.progress !== undefined) {
                progressBarFill.style.width = `${data.progress}%`;
            }
        }
        
        // Show results
        function showResults(result) {
            const resultsSection = document.getElementById('resultsSection');
            
            let resultsHTML = `
                <div class="result-summary">
                    <h3>${result.summary.headline}</h3>
                    <p>${result.summary.details}</p>
                    <div class="result-metrics">
            `;
            
            // Add metrics based on result type
            if (result.results.leads) {
                resultsHTML += `
                    <div class="metric">
                        <div class="metric-value">${result.results.leads.length}</div>
                        <div class="metric-label">Leads Found</div>
                    </div>
                `;
            }
            
            if (result.results.top_leads) {
                resultsHTML += `
                    <div class="metric">
                        <div class="metric-value">${result.results.top_leads.length}</div>
                        <div class="metric-label">Top Prospects</div>
                    </div>
                `;
            }
            
            if (result.results.high_quality) {
                resultsHTML += `
                    <div class="metric">
                        <div class="metric-value">${result.results.high_quality}</div>
                        <div class="metric-label">High Quality</div>
                    </div>
                `;
            }
            
            if (result.results.messages) {
                resultsHTML += `
                    <div class="metric">
                        <div class="metric-value">${result.results.messages.length}</div>
                        <div class="metric-label">Messages</div>
                    </div>
                `;
            }
            
            if (result.results.avg_score) {
                resultsHTML += `
                    <div class="metric">
                        <div class="metric-value">${result.results.avg_score.toFixed(0)}</div>
                        <div class="metric-label">Avg Score</div>
                    </div>
                `;
            }
            
            resultsHTML += `
                    </div>
                    <a href="/api/export/${currentSessionId}?format=json" class="export-btn" target="_blank">
                        Export Results (JSON)
                    </a>
                </div>
            `;
            
            // Add lead cards if available
            const leads = result.results.leads || result.results.top_leads;
            if (leads) {
                resultsHTML += '<div class="result-cards">';
                
                leads.slice(0, 6).forEach(lead => {
                    resultsHTML += `
                        <div class="result-card">
                            <h4>${lead.contact.full_name}</h4>
                            <p>${lead.contact.title} at ${lead.company.name}</p>
                            <p style="color: #8b92a3; font-size: 0.875rem; margin-top: 0.5rem;">
                                ${lead.company.industry} • ${lead.company.employee_count} employees
                            </p>
                            <div style="margin-top: 1rem;">
                                <span class="lead-score">Score: ${lead.score.total_score}/100</span>
                            </div>
                        </div>
                    `;
                });
                
                resultsHTML += '</div>';
            }
            
            // Add message templates if available
            if (result.results.messages) {
                resultsHTML += '<h3 style="margin-top: 2rem; margin-bottom: 1rem;">Generated Messages</h3>';
                resultsHTML += '<div class="result-cards">';
                
                result.results.messages.forEach(message => {
                    resultsHTML += `
                        <div class="result-card">
                            <h4>${message.subject || 'Message Template'}</h4>
                            <p style="color: #8b92a3;">Template ID: ${message.template_id || message.message_id}</p>
                            <div style="margin-top: 1rem;">
                                <span class="lead-score">Score: ${Math.round((message.personalization_score || 0.8) * 100)}/100</span>
                            </div>
                        </div>
                    `;
                });
                
                resultsHTML += '</div>';
            }
            
            resultsSection.innerHTML = resultsHTML;
            resultsSection.classList.add('show');
            
            // Scroll to results
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }
        
        // Show error
        function showError(error) {
            const statusBadge = document.getElementById('statusBadge');
            statusBadge.className = 'status-badge status-error';
            statusBadge.textContent = 'Error';
            
            const progressSteps = document.getElementById('progressSteps');
            const errorStep = document.createElement('div');
            errorStep.className = 'progress-step active';
            errorStep.innerHTML = `
                <h3>Error</h3>
                <p style="color: #f44336;">${error}</p>
            `;
            progressSteps.appendChild(errorStep);
            
            // Re-enable submit button
            document.getElementById('submitBtn').disabled = false;
            document.getElementById('submitBtn').classList.remove('loading');
        }
        
        // Submit request
        async function submitRequest() {
            if (isProcessing) return;
            
            const input = document.getElementById('requestInput');
            const submitBtn = document.getElementById('submitBtn');
            const request = input.value.trim();
            
            if (!request) {
                alert('Please enter a request');
                return;
            }
            
            isProcessing = true;
            
            // Reset UI
            document.getElementById('progressSteps').innerHTML = '';
            document.getElementById('progressBarFill').style.width = '0%';
            document.getElementById('resultsSection').classList.remove('show');
            document.getElementById('statusBadge').className = 'status-badge status-pending';
            document.getElementById('statusBadge').textContent = 'Starting...';
            
            // Update submit button
            submitBtn.disabled = true;
            submitBtn.classList.add('loading');
            submitBtn.textContent = 'Processing...';
            
            try {
                // Send request
                const response = await fetch('/api/process', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ request })
                });
                
                const data = await response.json();
                currentSessionId = data.session_id;
                
                // Initialize WebSocket
                initWebSocket(currentSessionId);
                
            } catch (error) {
                console.error('Failed to submit request:', error);
                showError('Failed to process request. Please try again.');
                isProcessing = false;
            } finally {
                // Reset submit button after delay
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.classList.remove('loading');
                    submitBtn.textContent = 'Process';
                }, 1000);
            }
        }
        
        // Event listeners
        document.getElementById('submitBtn').addEventListener('click', submitRequest);
        document.getElementById('requestInput').addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !isProcessing) {
                submitRequest();
            }
        });
        
        // Load scenarios on page load
        loadScenarios();
    </script>
</body>
</html>
    """

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")