#!/usr/bin/env python3
"""Demo script showing Jarvis integration with main.py."""

import sys
import os
import asyncio
from rich.console import Console
from rich.panel import Panel

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import is_technical_request

console = Console()


async def demo_request_routing():
    """Demo the request routing functionality."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]🤖 Jarvis Integration Demo[/bold blue]\n\n"
        "This demo shows how Jarvis integrates with the existing system\n"
        "to provide dual-mode operation without breaking functionality.",
        title="Integration Demo",
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]Request Routing Demo[/bold yellow]")
    console.print("Jarvis intelligently routes requests between business and technical modes:\n")
    
    test_requests = [
        # Business requests (go to Jarvis)
        ("Grow our sales by 30% this quarter", "Business 💼"),
        ("Reduce operational costs by 20%", "Business 💼"),
        ("Scale our marketing department", "Business 💼"),
        ("Improve customer satisfaction", "Business 💼"),
        
        # Technical requests (go to agent builder)
        ("Create an email monitoring agent", "Technical 🔧"),
        ("Build automation for file backup", "Technical 🔧"),
        ("Set up API integration with Slack", "Technical 🔧"),
        ("Monitor system resources", "Technical 🔧"),
    ]
    
    for request, expected_mode in test_requests:
        is_technical = await is_technical_request(request)
        actual_mode = "Technical 🔧" if is_technical else "Business 💼"
        
        status = "✓" if actual_mode == expected_mode else "✗"
        color = "green" if actual_mode == expected_mode else "red"
        
        console.print(f"[{color}]{status}[/{color}] '{request}' → {actual_mode}")
        await asyncio.sleep(0.5)  # Dramatic effect
    
    console.input("\n[dim]Press Enter to see mode descriptions...[/dim]")


def show_mode_descriptions():
    """Show descriptions of different modes."""
    console.print("\n[bold green]🎯 Operating Modes[/bold green]\n")
    
    # Normal mode
    console.print("[bold cyan]Normal Mode (default):[/bold cyan]")
    console.print("• Command: [dim]python main.py[/dim]")
    console.print("• Focus: Individual agent creation")
    console.print("• Best for: Technical users, specific automation tasks")
    console.print("• Interface: HeyJarvis technical assistant\n")
    
    # Demo mode
    console.print("[bold yellow]Demo Mode:[/bold yellow]")
    console.print("• Command: [dim]python main.py --demo[/dim]")
    console.print("• Focus: Interactive tutorials and examples")
    console.print("• Best for: Learning the system, exploring capabilities")
    console.print("• Interface: Guided demo scenarios\n")
    
    # Jarvis mode
    console.print("[bold magenta]Jarvis Mode:[/bold magenta]")
    console.print("• Command: [dim]python main.py --jarvis[/dim]")
    console.print("• Focus: Business-level orchestration and departments")
    console.print("• Best for: Business users, complex workflows, growth goals")
    console.print("• Interface: Business-aware meta-orchestrator\n")
    
    console.input("[dim]Press Enter to see business demo preview...[/dim]")


def show_business_demo_preview():
    """Show preview of business demo capabilities."""
    console.print("\n[bold blue]💼 Jarvis Business Demo Preview[/bold blue]\n")
    
    console.print("When you run [bold]python main.py --jarvis[/bold] and type [bold]'demo'[/bold]:")
    console.print("\n[bold green]Demo: 'Grow sales by 30%'[/bold green]")
    console.print("1. 🧠 Jarvis analyzes business intent: GROW_REVENUE")
    console.print("2. 🏛️ Activates Sales Department automatically")
    console.print("3. 🤖 Initializes 4 coordinated micro-agents:")
    console.print("   • Lead Scanner Agent (LinkedIn, Sales Navigator)")
    console.print("   • Outreach Composer Agent (AI-powered emails)")
    console.print("   • Meeting Scheduler Agent (Calendar coordination)")
    console.print("   • Pipeline Tracker Agent (CRM monitoring)")
    console.print("4. 📊 Shows real-time business KPIs and metrics")
    console.print("5. 🔄 Demonstrates agent coordination and messaging")
    console.print("6. 🔮 Provides AI-powered forecasting and recommendations")
    
    console.print("\n[bold yellow]Key Features:[/bold yellow]")
    console.print("• Business intent understanding")
    console.print("• Department-level coordination")
    console.print("• Real-time metrics and KPI tracking")
    console.print("• Cross-agent communication")
    console.print("• Automated business impact calculation")
    
    console.input("\n[dim]Press Enter to see integration benefits...[/dim]")


def show_integration_benefits():
    """Show the benefits of the Jarvis integration."""
    console.print("\n[bold green]🎉 Integration Benefits[/bold green]\n")
    
    console.print("[bold]✅ Backward Compatibility:[/bold]")
    console.print("• Existing functionality unchanged")
    console.print("• Normal mode works exactly as before")
    console.print("• No breaking changes to current users\n")
    
    console.print("[bold]🚀 Enhanced Capabilities:[/bold]")
    console.print("• Business-level orchestration with Jarvis")
    console.print("• Department coordination and management")
    console.print("• Intelligent request routing")
    console.print("• Business context awareness\n")
    
    console.print("[bold]🎯 Smart Request Handling:[/bold]")
    console.print("• Technical requests → Agent builder (existing system)")
    console.print("• Business requests → Jarvis (new meta-orchestrator)")
    console.print("• Seamless switching between modes")
    console.print("• Context-aware decision making\n")
    
    console.print("[bold]📊 Business Intelligence:[/bold]")
    console.print("• Real-time KPI tracking")
    console.print("• Business impact calculations")
    console.print("• Department performance metrics")
    console.print("• AI-powered insights and recommendations\n")
    
    console.print("[bold]🔧 Developer Experience:[/bold]")
    console.print("• Same codebase, multiple interfaces")
    console.print("• Consistent progress callback system")
    console.print("• Unified configuration management")
    console.print("• Rich console UI across all modes")


def show_usage_examples():
    """Show practical usage examples."""
    console.print("\n[bold blue]💡 Usage Examples[/bold blue]\n")
    
    console.print("[bold yellow]For Business Users:[/bold yellow]")
    console.print("```bash")
    console.print("# Start Jarvis business mode")
    console.print("python main.py --jarvis")
    console.print("")
    console.print("# Example business requests:")
    console.print("You: Grow sales by 30%")
    console.print("You: Reduce customer support costs")
    console.print("You: Scale our marketing efforts")
    console.print("You: demo  # Run business demo")
    console.print("```\n")
    
    console.print("[bold cyan]For Technical Users:[/bold cyan]")
    console.print("```bash")
    console.print("# Start normal technical mode")
    console.print("python main.py")
    console.print("")
    console.print("# Example technical requests:")
    console.print("You: Create an email monitoring agent")
    console.print("You: Build file backup automation")
    console.print("You: Set up Slack integration")
    console.print("```\n")
    
    console.print("[bold green]For New Users:[/bold green]")
    console.print("```bash")
    console.print("# Start interactive demo")
    console.print("python main.py --demo")
    console.print("")
    console.print("# Follow guided tutorials")
    console.print("# Learn system capabilities")
    console.print("# Explore different scenarios")
    console.print("```\n")


async def main():
    """Run the integration demo."""
    console.print("[bold green]Welcome to the Jarvis Integration Demo![/bold green]\n")
    
    # Demo request routing
    await demo_request_routing()
    
    # Show mode descriptions
    show_mode_descriptions()
    
    # Show business demo preview
    show_business_demo_preview()
    
    # Show integration benefits
    show_integration_benefits()
    
    # Show usage examples
    show_usage_examples()
    
    # Final summary
    console.print(Panel(
        "[bold green]🎯 Integration Complete![/bold green]\n\n"
        "Jarvis is now fully integrated with your existing system:\n\n"
        "• [bold]Normal mode:[/bold] python main.py (unchanged)\n"
        "• [bold]Demo mode:[/bold] python main.py --demo (enhanced)\n"
        "• [bold]Jarvis mode:[/bold] python main.py --jarvis (new!)\n\n"
        "All modes use the same codebase with intelligent request routing.\n"
        "Business users get department coordination, technical users get\n"
        "individual agents, and everyone benefits from the enhanced capabilities!",
        title="Integration Summary",
        border_style="green"
    ))
    
    console.print("\n[dim]Ready to try it out? Run: python main.py --jarvis[/dim]")


if __name__ == "__main__":
    asyncio.run(main())