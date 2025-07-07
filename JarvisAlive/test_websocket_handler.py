#!/usr/bin/env python3
"""Test script for WebSocket handler with Jarvis integration."""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conversation.websocket_handler import (
    WebSocketHandler, 
    WebSocketMessage, 
    MessageType, 
    OperatingMode,
    websocket_handler
)


class MockWebSocket:
    """Mock WebSocket connection for testing."""
    
    def __init__(self, name: str):
        self.name = name
        self.messages = []
        self.closed = False
    
    async def send(self, message: str):
        """Mock send method."""
        if not self.closed:
            self.messages.append(message)
            print(f"[{self.name}] Received: {message}")
    
    async def close(self):
        """Mock close method."""
        self.closed = True
        print(f"[{self.name}] Connection closed")


async def test_websocket_handler():
    """Test WebSocket handler functionality."""
    print("Testing WebSocket Handler with Jarvis Integration")
    print("=" * 60)
    
    handler = WebSocketHandler()
    await handler.start()
    
    # Create mock WebSocket connections
    agent_ws = MockWebSocket("AgentBuilder")
    jarvis_ws = MockWebSocket("Jarvis")
    hybrid_ws = MockWebSocket("Hybrid")
    
    # Add connections with different modes
    agent_conn_id = await handler.add_connection(agent_ws, mode=OperatingMode.AGENT_BUILDER)
    jarvis_conn_id = await handler.add_connection(jarvis_ws, mode=OperatingMode.JARVIS)
    hybrid_conn_id = await handler.add_connection(hybrid_ws, mode=OperatingMode.HYBRID)
    
    # Subscribe to session
    session_id = "test_session_001"
    await handler.subscribe_to_session(agent_conn_id, session_id)
    await handler.subscribe_to_session(jarvis_conn_id, session_id)
    await handler.subscribe_to_session(hybrid_conn_id, session_id)
    
    print(f"\nCreated connections:")
    print(f"- Agent Builder: {agent_conn_id}")
    print(f"- Jarvis: {jarvis_conn_id}")
    print(f"- Hybrid: {hybrid_conn_id}")
    
    return handler, session_id, [agent_ws, jarvis_ws, hybrid_ws]


async def test_backward_compatibility(handler: WebSocketHandler, session_id: str):
    """Test backward compatibility with existing agent builder messages."""
    print("\n" + "="*60)
    print("TESTING BACKWARD COMPATIBILITY")
    print("="*60)
    
    # Test agent created message (should only go to agent builder connections)
    print("\n1. Testing agent created message...")
    await handler.send_agent_created(session_id, {
        "name": "Email Monitor Agent",
        "description": "Monitors email for urgent messages",
        "capabilities": ["email_monitoring", "alert_sending"]
    })
    
    # Test progress update
    print("\n2. Testing progress update...")
    await handler.send_progress(session_id, 75, "Generating agent code...")
    
    # Test error message
    print("\n3. Testing error message...")
    await handler.send_error(session_id, "Failed to connect to email service", {
        "error_code": "EMAIL_CONNECTION_FAILED",
        "retry_after": 30
    })


async def test_jarvis_features(handler: WebSocketHandler, session_id: str):
    """Test new Jarvis-specific features."""
    print("\n" + "="*60)
    print("TESTING JARVIS FEATURES")
    print("="*60)
    
    # Test department activation
    print("\n1. Testing department activation...")
    await handler.send_department_activated(session_id, "Sales", 4, {
        "agents": ["Lead Scanner", "Outreach Composer", "Meeting Scheduler", "Pipeline Tracker"],
        "activation_time": "2024-01-15T10:00:00Z"
    })
    
    # Test workflow progress
    print("\n2. Testing workflow progress...")
    await handler.send_workflow_progress(session_id, "Sales Growth", 40, "Initializing Lead Scanner Agent")
    await handler.send_workflow_progress(session_id, "Sales Growth", 60, "Configuring Outreach Templates")
    await handler.send_workflow_progress(session_id, "Sales Growth", 80, "Setting up Meeting Scheduler")
    
    # Test business metrics
    print("\n3. Testing business metric updates...")
    await handler.send_business_metric_updated(session_id, "Monthly Leads", 45, change=15.2)
    await handler.send_business_metric_updated(session_id, "Pipeline Value", "$125,000", change=8.7)
    await handler.send_business_metric_updated(session_id, "Conversion Rate", "15%", change=-2.1)
    
    # Test optimization suggestions
    print("\n4. Testing optimization suggestions...")
    await handler.send_optimization_suggestion(
        session_id,
        "Increase outreach frequency to enterprise accounts",
        "Could improve lead quality by 25%",
        priority="high"
    )
    
    # Test agent coordination
    print("\n5. Testing agent coordination...")
    await handler.send_agent_coordination(
        session_id,
        "Lead Scanner Agent",
        "Outreach Composer Agent",
        "New qualified lead found",
        {"lead_id": "lead_12345", "company": "TechCorp", "score": 8.5}
    )
    
    # Test business insights
    print("\n6. Testing business insights...")
    await handler.send_business_insight(
        session_id,
        "Current lead generation rate is 23% above industry average",
        "performance",
        confidence=0.92
    )
    
    # Test department status
    print("\n7. Testing department status...")
    await handler.send_department_status(session_id, "Sales", "active", 4, {
        "leads_processed": 150,
        "emails_sent": 89,
        "meetings_booked": 12
    })
    
    # Test KPI alerts
    print("\n8. Testing KPI alerts...")
    await handler.send_kpi_alert(
        session_id,
        "Conversion Rate",
        "warning",
        "Conversion rate dropped below 15% threshold",
        threshold=15.0
    )


async def test_sales_batch_updates(handler: WebSocketHandler, session_id: str):
    """Test batch sales updates example."""
    print("\n" + "="*60)
    print("TESTING SALES BATCH UPDATES")
    print("="*60)
    
    # Simulate sales department updates
    sales_updates = {
        "new_leads": 15,
        "leads_change": 23.5,
        "meetings_scheduled": 3,
        "pipeline_increase": 45000,
        "pipeline_change_percentage": 12.8,
        "agent_actions": [
            {
                "from": "Lead Scanner Agent",
                "to": "Outreach Composer Agent", 
                "action": "New qualified lead: TechCorp VP Engineering",
                "data": {"lead_score": 9.1, "company_size": "200-500"}
            },
            {
                "from": "Outreach Composer Agent",
                "to": "Meeting Scheduler Agent",
                "action": "Positive response from TechCorp, needs meeting",
                "data": {"response_sentiment": "positive", "urgency": "high"}
            }
        ]
    }
    
    print("Sending batch sales updates...")
    await handler.send_sales_updates(session_id, sales_updates)


async def test_mode_filtering(handler: WebSocketHandler, session_id: str):
    """Test that messages are properly filtered by mode."""
    print("\n" + "="*60)
    print("TESTING MODE FILTERING")
    print("="*60)
    
    print("\nSending messages to test mode filtering...")
    
    # Agent builder message (should only go to agent builder connections)
    await handler.send_agent_created(session_id, {"name": "Test Agent"})
    
    # Jarvis message (should only go to Jarvis connections)
    await handler.send_department_activated(session_id, "Marketing", 3)
    
    # Hybrid message (should go to all connections)
    hybrid_msg = WebSocketMessage(
        id="test_hybrid_001",
        type=MessageType.PROGRESS,
        mode=OperatingMode.HYBRID,
        timestamp=datetime.now().isoformat(),
        content="System maintenance in progress",
        details={"maintenance_type": "database_optimization"}
    )
    await handler.broadcast_to_session(session_id, hybrid_msg)


def analyze_message_distribution(websockets):
    """Analyze how messages were distributed across connections."""
    print("\n" + "="*60)
    print("MESSAGE DISTRIBUTION ANALYSIS")
    print("="*60)
    
    for ws in websockets:
        print(f"\n{ws.name} Connection:")
        print(f"- Total messages received: {len(ws.messages)}")
        
        # Count by message type
        type_counts = {}
        for msg_json in ws.messages:
            try:
                msg_data = json.loads(msg_json)
                msg_type = msg_data.get("type", "unknown")
                type_counts[msg_type] = type_counts.get(msg_type, 0) + 1
            except:
                type_counts["malformed"] = type_counts.get("malformed", 0) + 1
        
        for msg_type, count in type_counts.items():
            print(f"  • {msg_type}: {count}")


async def main():
    """Run WebSocket handler tests."""
    print("Starting WebSocket Handler Tests...")
    
    try:
        # Initialize handler and connections
        handler, session_id, websockets = await test_websocket_handler()
        
        # Test backward compatibility
        await test_backward_compatibility(handler, session_id)
        
        # Test new Jarvis features
        await test_jarvis_features(handler, session_id)
        
        # Test batch updates
        await test_sales_batch_updates(handler, session_id)
        
        # Test mode filtering
        await test_mode_filtering(handler, session_id)
        
        # Give messages time to process
        await asyncio.sleep(1)
        
        # Analyze results
        analyze_message_distribution(websockets)
        
        # Test connection cleanup
        print("\n" + "="*60)
        print("TESTING CONNECTION CLEANUP")
        print("="*60)
        
        await handler.stop()
        print("WebSocket handler stopped successfully")
        
        print("\n🎉 All WebSocket tests completed successfully!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)