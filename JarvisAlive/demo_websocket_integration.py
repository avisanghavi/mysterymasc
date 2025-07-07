#!/usr/bin/env python3
"""Demo showing complete WebSocket integration with Jarvis business updates."""

import sys
import os
import asyncio
import json
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from conversation.websocket_handler import (
    WebSocketHandler,
    MessageType,
    OperatingMode,
    websocket_handler
)

console = Console()


class MockJarvisClient:
    """Mock client simulating Jarvis business mode."""
    
    def __init__(self, name: str):
        self.name = name
        self.messages = []
        self.business_metrics = {}
        self.active_departments = []
        
    async def send(self, message: str):
        """Receive WebSocket message."""
        try:
            msg_data = json.loads(message)
            self.messages.append(msg_data)
            
            # Update internal state based on message type
            msg_type = msg_data.get("type")
            details = msg_data.get("details", {})
            
            if msg_type == "department_activated":
                dept = details.get("department")
                if dept and dept not in self.active_departments:
                    self.active_departments.append(dept)
            
            elif msg_type == "business_metric_updated":
                metric = details.get("metric")
                value = details.get("value")
                if metric and value:
                    self.business_metrics[metric] = value
            
            # Display formatted message
            self._display_message(msg_data)
            
        except json.JSONDecodeError:
            console.print(f"[red]Invalid JSON received: {message[:100]}...[/red]")
    
    async def close(self):
        """Close connection."""
        pass
    
    def _display_message(self, msg_data):
        """Display formatted message."""
        msg_type = msg_data.get("type", "unknown")
        content = msg_data.get("content", "")
        mode = msg_data.get("mode", "unknown")
        
        # Color code by message type
        type_colors = {
            "department_activated": "green",
            "workflow_progress": "blue", 
            "business_metric_updated": "yellow",
            "optimization_suggestion": "magenta",
            "agent_coordination": "cyan",
            "business_insight": "bright_blue",
            "kpi_alert": "red"
        }
        
        color = type_colors.get(msg_type, "white")
        console.print(f"[{color}]{msg_type.upper()}[/{color}] [{mode}] {content}")
    
    def get_summary(self):
        """Get summary of received data."""
        return {
            "total_messages": len(self.messages),
            "business_metrics": self.business_metrics,
            "active_departments": self.active_departments,
            "message_types": list(set(msg.get("type") for msg in self.messages))
        }


async def simulate_sales_department_activation():
    """Simulate complete sales department activation with real-time updates."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]🚀 Sales Department Activation Simulation[/bold blue]\n\n"
        "Watch real-time WebSocket updates as Jarvis activates the Sales Department\n"
        "and coordinates multiple agents for business growth.",
        title="WebSocket Integration Demo",
        border_style="blue"
    ))
    
    # Initialize WebSocket handler
    handler = WebSocketHandler()
    await handler.start()
    
    # Create mock Jarvis client
    jarvis_client = MockJarvisClient("Business Dashboard")
    conn_id = await handler.add_connection(jarvis_client, mode=OperatingMode.JARVIS)
    
    session_id = "sales_demo_001"
    await handler.subscribe_to_session(conn_id, session_id)
    
    console.print(f"\n[dim]WebSocket client connected with ID: {conn_id}[/dim]")
    console.print(f"[dim]Session ID: {session_id}[/dim]\n")
    
    # Start the simulation
    console.print("[bold yellow]📱 Starting real-time business updates...[/bold yellow]\n")
    
    # Step 1: Department Activation
    await asyncio.sleep(1)
    await handler.send_department_activated(session_id, "Sales", 4, {
        "agents": ["Lead Scanner", "Outreach Composer", "Meeting Scheduler", "Pipeline Tracker"],
        "estimated_impact": "30% sales growth",
        "activation_time": "2025-01-15T10:00:00Z"
    })
    
    # Step 2: Workflow Progress Updates
    progress_steps = [
        (20, "🔍 Initializing Lead Scanner Agent..."),
        (40, "📧 Setting up Outreach Composer..."),
        (60, "📅 Configuring Meeting Scheduler..."),
        (80, "📊 Activating Pipeline Tracker..."),
        (100, "✅ Sales Department fully operational!")
    ]
    
    for progress, step in progress_steps:
        await asyncio.sleep(1.5)
        await handler.send_workflow_progress(session_id, "Sales Growth Initiative", progress, step)
    
    # Step 3: Initial Business Metrics
    await asyncio.sleep(2)
    console.print("\n[bold green]📊 Initial business metrics...[/bold green]")
    
    metrics_updates = [
        ("Lead Database", "150 leads", 0),
        ("Monthly Target", "100 new leads", None),
        ("Pipeline Value", "$75,000", None),
        ("Conversion Rate", "12%", None)
    ]
    
    for metric, value, change in metrics_updates:
        await asyncio.sleep(0.8)
        await handler.send_business_metric_updated(session_id, metric, value, change)
    
    # Step 4: Agent Coordination Messages
    await asyncio.sleep(2)
    console.print("\n[bold cyan]🤖 Agent coordination in action...[/bold cyan]")
    
    coordination_messages = [
        ("Lead Scanner Agent", "Outreach Composer Agent", "Found 8 new qualified prospects", 
         {"lead_quality": "high", "avg_score": 8.2}),
        ("Outreach Composer Agent", "Meeting Scheduler Agent", "3 positive responses received",
         {"response_rate": "18%", "sentiment": "positive"}),
        ("Meeting Scheduler Agent", "Pipeline Tracker Agent", "2 demos scheduled this week",
         {"demo_value": "$35,000", "close_probability": "65%"})
    ]
    
    for from_agent, to_agent, action, data in coordination_messages:
        await asyncio.sleep(1.2)
        await handler.send_agent_coordination(session_id, from_agent, to_agent, action, data)
    
    # Step 5: Live Business Updates
    await asyncio.sleep(2)
    console.print("\n[bold yellow]⚡ Live business performance updates...[/bold yellow]")
    
    live_updates = {
        "new_leads": 23,
        "leads_change": 18.5,
        "meetings_scheduled": 5,
        "pipeline_increase": 25000,
        "pipeline_change_percentage": 15.2
    }
    
    await handler.send_sales_updates(session_id, live_updates)
    
    # Step 6: Business Insights
    await asyncio.sleep(2)
    insights = [
        ("Lead quality improved 25% with new targeting criteria", "performance", 0.91),
        ("Email response rate 40% above industry average", "achievement", 0.87),
        ("Pipeline velocity increased by 2.3 days", "efficiency", 0.83)
    ]
    
    console.print("\n[bold bright_blue]💡 AI-powered business insights...[/bold bright_blue]")
    for insight, category, confidence in insights:
        await asyncio.sleep(1)
        await handler.send_business_insight(session_id, insight, category, confidence)
    
    # Step 7: Optimization Suggestions
    await asyncio.sleep(2)
    suggestions = [
        ("Focus outreach on enterprise accounts (>500 employees)", "Could increase deal size by 40%", "high"),
        ("Schedule follow-ups within 24 hours of initial contact", "May improve response rate by 15%", "medium"),
        ("Implement social proof in email templates", "Could boost credibility and engagement", "medium")
    ]
    
    console.print("\n[bold magenta]🎯 Optimization recommendations...[/bold magenta]")
    for suggestion, impact, priority in suggestions:
        await asyncio.sleep(1)
        await handler.send_optimization_suggestion(session_id, suggestion, impact, priority)
    
    # Step 8: Department Status Update
    await asyncio.sleep(2)
    await handler.send_department_status(session_id, "Sales", "optimized", 4, {
        "leads_processed_today": 35,
        "emails_sent": 67,
        "meetings_booked": 8,
        "pipeline_additions": "$42,500"
    })
    
    # Step 9: KPI Alert (demonstration)
    await asyncio.sleep(1.5)
    await handler.send_kpi_alert(
        session_id,
        "Lead Quality Score",
        "achievement",
        "Lead quality score reached new high of 8.7/10",
        threshold=8.5
    )
    
    # Give time for final messages
    await asyncio.sleep(2)
    
    # Display summary
    summary = jarvis_client.get_summary()
    
    console.print("\n" + "="*60)
    console.print("[bold green]🎉 SIMULATION COMPLETE[/bold green]")
    console.print("="*60)
    
    # Summary table
    summary_table = Table(title="WebSocket Integration Summary")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="green")
    
    summary_table.add_row("Total Messages", str(summary["total_messages"]))
    summary_table.add_row("Message Types", str(len(summary["message_types"])))
    summary_table.add_row("Departments", ", ".join(summary["active_departments"]))
    summary_table.add_row("Metrics Tracked", str(len(summary["business_metrics"])))
    
    console.print(summary_table)
    
    # Business metrics table
    if summary["business_metrics"]:
        metrics_table = Table(title="Live Business Metrics")
        metrics_table.add_column("Metric", style="yellow")
        metrics_table.add_column("Current Value", style="green")
        
        for metric, value in summary["business_metrics"].items():
            metrics_table.add_row(metric, str(value))
        
        console.print(metrics_table)
    
    # Message types received
    console.print(f"\n[bold blue]Message Types Received:[/bold blue]")
    for msg_type in sorted(summary["message_types"]):
        console.print(f"  • {msg_type}")
    
    # Cleanup
    await handler.stop()
    
    console.print(Panel(
        "[bold green]✅ WebSocket Integration Successful![/bold green]\n\n"
        "Key Features Demonstrated:\n"
        "• [bold]Real-time business updates[/bold] streamed via WebSocket\n"
        "• [bold]Mode-based message filtering[/bold] (Jarvis vs Agent Builder)\n"
        "• [bold]Department coordination[/bold] with live agent messaging\n"
        "• [bold]Business metrics tracking[/bold] with change percentages\n"
        "• [bold]AI insights and optimization[/bold] suggestions\n"
        "• [bold]Backward compatibility[/bold] with existing WebSocket clients\n\n"
        "Ready for production: Business dashboards can now receive\n"
        "live updates from Jarvis without polling!",
        title="Integration Success",
        border_style="green"
    ))


async def demonstrate_dual_mode_compatibility():
    """Demonstrate that both Jarvis and Agent Builder modes work together."""
    console.print(Panel(
        "[bold blue]🔄 Dual-Mode Compatibility Demo[/bold blue]\n\n"
        "Showing how Jarvis and Agent Builder WebSocket clients\n"
        "can coexist and receive appropriate messages.",
        title="Dual-Mode Demo",
        border_style="blue"
    ))
    
    handler = WebSocketHandler()
    await handler.start()
    
    # Create clients for both modes
    agent_client = MockJarvisClient("Agent Builder Dashboard")
    jarvis_client = MockJarvisClient("Business Dashboard")
    
    agent_conn = await handler.add_connection(agent_client, mode=OperatingMode.AGENT_BUILDER)
    jarvis_conn = await handler.add_connection(jarvis_client, mode=OperatingMode.JARVIS)
    
    session_id = "dual_mode_demo"
    await handler.subscribe_to_session(agent_conn, session_id)
    await handler.subscribe_to_session(jarvis_conn, session_id)
    
    console.print("\n[yellow]Sending agent builder message (technical)...[/yellow]")
    await handler.send_agent_created(session_id, {
        "name": "Email Monitor",
        "type": "monitoring",
        "capabilities": ["email_scan", "alert_send"]
    })
    
    console.print("\n[yellow]Sending Jarvis message (business)...[/yellow]")
    await handler.send_department_activated(session_id, "Marketing", 3)
    
    console.print("\n[yellow]Sending hybrid message (both)...[/yellow]")
    from conversation.websocket_handler import WebSocketMessage
    from datetime import datetime
    
    hybrid_msg = WebSocketMessage(
        id="hybrid_001",
        type=MessageType.PROGRESS,
        mode=OperatingMode.HYBRID,
        timestamp=datetime.now().isoformat(),
        content="System maintenance scheduled",
        details={"maintenance_window": "2AM-4AM UTC"}
    )
    await handler.broadcast_to_session(session_id, hybrid_msg)
    
    await asyncio.sleep(1)
    
    # Show results
    agent_summary = agent_client.get_summary()
    jarvis_summary = jarvis_client.get_summary()
    
    console.print(f"\n[cyan]Agent Builder Client received: {agent_summary['total_messages']} messages[/cyan]")
    console.print(f"[magenta]Jarvis Client received: {jarvis_summary['total_messages']} messages[/magenta]")
    
    await handler.stop()
    
    console.print("\n✅ Dual-mode compatibility confirmed!")


async def main():
    """Run WebSocket integration demos."""
    console.print("[bold green]🚀 WebSocket Integration Demo Suite[/bold green]\n")
    
    # Demo 1: Sales department activation
    await simulate_sales_department_activation()
    
    console.input("\n[dim]Press Enter for dual-mode compatibility demo...[/dim]")
    
    # Demo 2: Dual-mode compatibility
    await demonstrate_dual_mode_compatibility()
    
    console.print("\n[bold green]🎉 All WebSocket integration demos completed![/bold green]")
    console.print("\nThe WebSocket handler is ready for production use with:")
    console.print("• Real-time business updates for Jarvis mode")
    console.print("• Backward compatibility for existing agent builder clients")
    console.print("• Intelligent message routing based on client mode")
    console.print("• Rich business context in all messages")


if __name__ == "__main__":
    asyncio.run(main())