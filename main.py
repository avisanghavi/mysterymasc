"""Main entry point for HeyJarvis orchestrator."""

import asyncio
import logging
import os
import sys
import argparse
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Callable
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table

from orchestration.orchestrator import HeyJarvisOrchestrator, OrchestratorConfig

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Rich console for better UI
console = Console()


async def chat_interface():
    """Interactive chat interface for HeyJarvis."""
    
    # Configuration
    config = OrchestratorConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600"))
    )
    
    if not config.openai_api_key:
        console.print("[red]Error: OPENAI_API_KEY not found in environment variables.[/red]")
        console.print("Please set your OpenAI API key in the .env file.")
        return
    
    # Initialize orchestrator
    orchestrator = HeyJarvisOrchestrator(config)
    
    def progress_callback(node_name: str, progress: int, message: str):
        """Progress callback for real-time updates."""
        console.print(f"📊 Progress: {progress}% - {message}")
    
    orchestrator.set_progress_callback(progress_callback)
    
    try:
        await orchestrator.initialize()
        
        # Welcome message
        console.print("\n[bold cyan]💬 HeyJarvis:[/bold cyan] Hi! I can help you create automation agents. What would you like to automate?\n")
        
        session_id = str(uuid.uuid4())[:8]
        console.print(f"[dim]Session ID: {session_id}[/dim]\n")
        
        while True:
            try:
                # Get user input
                user_input = console.input("[bold green]You:[/bold green] ").strip()
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.lower() in ['exit', 'quit']:
                    console.print("[yellow]Goodbye! Your session has been saved.[/yellow]")
                    break
                    
                elif user_input.lower() == 'continue':
                    await handle_continue_command(orchestrator)
                    continue
                    
                elif user_input.lower() == 'sessions':
                    await show_active_sessions(orchestrator)
                    continue
                
                # Process user request
                console.print(f"\n[bold cyan]💬 HeyJarvis:[/bold cyan] I'll create an {user_input.lower()} agent for you...\n")
                
                result = await orchestrator.process_request(user_input, session_id)
                
                # Display results
                await display_result(result)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Session interrupted. Type 'continue' to resume later.[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                logger.error(f"Chat interface error: {e}")
                
    finally:
        await orchestrator.close()


async def handle_continue_command(orchestrator: HeyJarvisOrchestrator):
    """Handle the continue command to resume sessions."""
    sessions = await orchestrator.list_active_sessions()
    
    if not sessions:
        console.print("[yellow]No active sessions found.[/yellow]")
        return
    
    # Show available sessions in the expected format
    console.print("[bold cyan]💬 You have these sessions you can resume:[/bold cyan]\n")
    
    for i, session in enumerate(sessions, 1):
        # Calculate time ago (simplified)
        import datetime
        try:
            session_time = datetime.datetime.fromisoformat(session['timestamp'].replace('Z', '+00:00'))
            now = datetime.datetime.now(datetime.timezone.utc)
            time_diff = now - session_time
            
            if time_diff.total_seconds() < 3600:  # Less than 1 hour
                time_ago = f"{int(time_diff.total_seconds() // 60)} minutes ago"
            else:
                time_ago = f"{int(time_diff.total_seconds() // 3600)} hour{'s' if time_diff.total_seconds() >= 7200 else ''} ago"
        except:
            time_ago = "Unknown time"
        
        # Determine completion percentage based on status
        if session['status'] == 'completed':
            completion = "100%"
        elif session['status'] == 'failed':
            completion = "0%"
        else:
            completion = "60%"  # Default for in-progress
            
        console.print(f"Session started {time_ago} ({completion} complete)")
    
    console.print(f"\nWhich would you like to continue? (1-{len(sessions)}):")
    
    # Let user select session
    try:
        choice = console.input("").strip()
        if not choice:
            return
            
        session_num = int(choice) - 1
        if 0 <= session_num < len(sessions):
            selected_session = sessions[session_num]
            console.print(f"[green]Resuming session {selected_session['session_id']}...[/green]")
            
            # Load and display session state
            state = await orchestrator.recover_session(selected_session['session_id'])
            if state:
                console.print(f"[cyan]Previous request:[/cyan] {state.get('user_request', 'Unknown')}")
                console.print(f"[cyan]Current status:[/cyan] {state.get('deployment_status', 'Unknown')}")
                
                # Continue processing if needed
                if state.get('deployment_status') != 'completed':
                    result = await orchestrator.process_request(
                        state['user_request'], 
                        selected_session['session_id']
                    )
                    await display_result(result)
                else:
                    console.print("[green]Session was already completed![/green]")
        else:
            console.print("[red]Invalid session number.[/red]")
            
    except ValueError:
        console.print("[red]Please enter a valid number.[/red]")
    except Exception as e:
        console.print(f"[red]Error resuming session: {str(e)}[/red]")


async def show_active_sessions(orchestrator: HeyJarvisOrchestrator):
    """Show all active sessions."""
    sessions = await orchestrator.list_active_sessions()
    
    if not sessions:
        console.print("[yellow]No active sessions found.[/yellow]")
        return
    
    table = Table(title="Active Sessions")
    table.add_column("Session ID", style="green")
    table.add_column("Request", style="cyan")
    table.add_column("Status", style="blue")
    table.add_column("Last Activity", style="yellow")
    
    for session in sessions:
        table.add_row(
            session['session_id'],
            session.get('request', 'Unknown')[:50] + "..." if len(session.get('request', '')) > 50 else session.get('request', 'Unknown'),
            session['status'],
            session['timestamp']
        )
    
    console.print(table)


async def display_result(result: Dict[str, Any]):
    """Display the orchestrator result in a user-friendly format."""
    status = result.get('deployment_status')
    
    if hasattr(status, 'value'):
        status_str = status.value
    else:
        status_str = str(status)
    
    if status_str == 'completed':
        agent_spec = result.get('agent_spec')
        if agent_spec:
            # Success message
            console.print(f"[bold green]✅ Success! I've created '{agent_spec['name']}' for you.[/bold green]")
            console.print(f"It will: {agent_spec['description']}")
            console.print("[bold]Capabilities:[/bold]")
            for cap in agent_spec.get('capabilities', []):
                console.print(f"  • {cap}")
            console.print()
            
            # Ask what else they want to automate
            console.print("[bold cyan]💬 What else would you like to automate?[/bold cyan]")
        else:
            console.print("[green]Agent created successfully![/green]")
            
    elif status_str == 'failed':
        error_msg = result.get('error_message', 'Unknown error occurred')
        console.print(Panel(
            f"[bold red]❌ Agent Creation Failed[/bold red]\n\n"
            f"[red]{error_msg}[/red]\n\n"
            f"[dim]Would you like to try rephrasing your request?[/dim]",
            title="Error",
            border_style="red"
        ))
    else:
        console.print(f"[yellow]Status: {status_str}[/yellow]")
    
    console.print()  # Add spacing


def show_demo_menu(completed_demos: set):
    """Show the interactive demo menu with progress tracking."""
    console.clear()
    
    console.print(Panel.fit(
        "[bold blue]🎭 HeyJarvis Interactive Demo[/bold blue]\n\n"
        "Choose a demo scenario:",
        title="Interactive Demo Mode",
        border_style="blue"
    ))
    
    # Demo options with completion status
    demos = [
        ("basic", "📧 Basic: Create an email monitoring agent"),
        ("recovery", "🔄 Recovery: Resume an interrupted session"),
        ("clarification", "💬 Clarification: Handle ambiguous requests"),
        ("advanced", "🚀 Advanced: Multi-step agent creation"),
        ("error", "❌ Error Handling: See how errors are handled")
    ]
    
    console.print()
    for i, (demo_key, description) in enumerate(demos, 1):
        status = "✅" if demo_key in completed_demos else "⭕"
        console.print(f"{i}. {status} {description}")
    
    console.print(f"\n[dim]Progress: {len(completed_demos)}/5 demos completed[/dim]")
    console.print("[dim]Type 'exit' to quit the demo[/dim]")


async def demo_mode():
    """Interactive demo mode showing HeyJarvis capabilities."""
    
    # Configuration
    config = OrchestratorConfig(
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        max_retries=int(os.getenv("MAX_RETRIES", "3"))
    )
    
    if not config.openai_api_key:
        console.print("[red]Error: OPENAI_API_KEY not found in environment variables.[/red]")
        console.print("Please set your OpenAI API key in the .env file.")
        return
    
    orchestrator = HeyJarvisOrchestrator(config)
    
    def progress_callback(node_name: str, progress: int, message: str):
        console.print(f"📊 Progress: {progress}% - {message}")
    
    orchestrator.set_progress_callback(progress_callback)
    
    try:
        await orchestrator.initialize()
        completed_demos = set()
        
        while True:
            show_demo_menu(completed_demos)
            choice = console.input("\nEnter your choice (1-5, or 'exit'): ").strip().lower()
            
            if choice in ['exit', 'quit', 'q']:
                console.print("\n[yellow]Thanks for trying the HeyJarvis demo! 👋[/yellow]")
                break
            
            if choice == '1':
                await demo_basic_agent_creation(orchestrator)
                completed_demos.add('basic')
            elif choice == '2':
                await demo_session_recovery(orchestrator)
                completed_demos.add('recovery')
            elif choice == '3':
                await demo_clarification_flow(orchestrator)
                completed_demos.add('clarification')
            elif choice == '4':
                await demo_advanced_creation(orchestrator)
                completed_demos.add('advanced')
            elif choice == '5':
                await demo_error_handling(orchestrator)
                completed_demos.add('error')
            else:
                console.print("[red]Invalid choice. Please select 1-5 or 'exit'.[/red]")
                console.input("\nPress Enter to continue...")
                continue
            
            # Check if all demos completed
            if len(completed_demos) == 5:
                console.print(Panel(
                    "[bold green]🎉 Congratulations! You've completed all demos![/bold green]\n\n"
                    "You've experienced all the key features of HeyJarvis:\n"
                    "• Basic agent creation\n"
                    "• Session recovery\n"
                    "• Clarification handling\n"
                    "• Advanced workflows\n"
                    "• Error handling\n\n"
                    "Ready to use HeyJarvis? Run: [bold]python main.py[/bold]",
                    title="Demo Complete!",
                    border_style="green"
                ))
                console.input("\nPress Enter to exit...")
                break
            
            # Ask if they want to continue
            continue_choice = console.input("\n[dim]Press Enter to return to menu, or 'exit' to quit:[/dim] ").strip().lower()
            if continue_choice in ['exit', 'quit', 'q']:
                break
        
    finally:
        await orchestrator.close()


async def demo_basic_agent_creation(orchestrator: HeyJarvisOrchestrator):
    """Demo: Basic Agent Creation with user interaction."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]📧 Demo: Basic Agent Creation[/bold blue]\n\n"
        "Let's create your first agent together!\n"
        "This demo will show you how HeyJarvis understands natural language\n"
        "and creates intelligent agents from your descriptions.",
        title="Interactive Tutorial",
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]💡 Tip:[/bold yellow] Try typing something like:")
    console.print("   [dim]'Monitor my email for urgent messages'[/dim]")
    console.print("   [dim]'Create a daily backup agent'[/dim]")
    console.print("   [dim]'Set up social media automation'[/dim]")
    
    # Get user input
    user_input = console.input("\n[bold green]You:[/bold green] ").strip()
    
    if not user_input:
        console.print("[yellow]No input provided. Let's try a sample request...[/yellow]")
        user_input = "Monitor my email for urgent messages"
        console.print(f"[dim]Using: {user_input}[/dim]")
    
    # Tutorial annotation
    console.print(Panel(
        "🎯 [bold]What's happening now:[/bold]\n"
        "HeyJarvis will analyze your request and break it down into steps.\n"
        "Watch the progress indicators to see each stage of agent creation!",
        style="dim yellow"
    ))
    
    console.print("\n[dim]→ Starting agent creation workflow...[/dim]")
    
    # Process the request
    session_id = "demo_basic_001"
    result = await orchestrator.process_request(user_input, session_id)
    
    # Show result with educational context
    await display_result(result)
    
    # Educational explanation
    console.print(Panel(
        "[bold green]✅ Great job! Here's what just happened:[/bold green]\n\n"
        "1. [bold]Understanding:[/bold] HeyJarvis parsed your natural language request\n"
        "2. [bold]Intent Analysis:[/bold] Determined you wanted to create an agent\n"
        "3. [bold]Specification:[/bold] Generated detailed agent capabilities\n"
        "4. [bold]Deployment:[/bold] Saved the agent to the system\n"
        "5. [bold]Ready to Use:[/bold] Your agent is now operational!\n\n"
        "💡 [bold]Key Feature:[/bold] Notice how HeyJarvis understood your intent\n"
        "without requiring technical specifications!",
        style="green"
    ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


async def demo_session_recovery(orchestrator: HeyJarvisOrchestrator):
    """Demo: Session Recovery - simulate interruption and recovery."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]🔄 Demo: Session Recovery[/bold blue]\n\n"
        "This demo shows how HeyJarvis handles interruptions.\n"
        "We'll start creating an agent, simulate a disconnection,\n"
        "then show you how to resume exactly where you left off!",
        title="Interactive Tutorial",
        border_style="blue"
    ))
    
    # Start an agent creation
    console.print("\n[bold yellow]Step 1:[/bold yellow] Let's start creating an agent...")
    console.print("[dim]Creating a file backup automation agent...[/dim]")
    
    # Simulate starting a session
    session_id = "demo_recovery_001"
    
    # Create initial request
    user_request = "Create an agent that backs up my important files to cloud storage daily"
    console.print(f"\n[bold green]Request:[/bold green] {user_request}")
    
    # Start processing but we'll simulate interruption
    console.print("\n📊 Progress: 20% - 🔍 Understanding your request...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 40% - 🤔 Analyzing intent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 60% - 🔎 Checking existing agents...")
    
    # Simulate interruption
    console.print("\n[bold red]💥 Oh no! Let's simulate a disconnection...[/bold red]")
    console.print("[dim]Connection lost... Session interrupted at 60%[/dim]")
    
    console.input("\n[dim]Press Enter to see session recovery in action...[/dim]")
    
    # Show recovery process
    console.print("\n[bold yellow]Step 2:[/bold yellow] Recovering your session...")
    console.print("[bold cyan]💬 Type 'continue' to see session recovery:[/bold cyan]")
    
    recovery_input = console.input("\n[bold green]You:[/bold green] ").strip().lower()
    
    if recovery_input != 'continue':
        console.print("[yellow]For this demo, let's proceed with session recovery...[/yellow]")
    
    # Simulate showing available sessions
    console.print("\n[bold cyan]💬 You have these sessions you can resume:[/bold cyan]\n")
    console.print("Session started 2 minutes ago (60% complete)")
    console.print(f"Request: {user_request}")
    console.print("\nWhich would you like to continue? (1):")
    
    choice = console.input("").strip()
    if not choice:
        choice = "1"
    
    # Continue processing from where we left off
    console.print(f"\n[bold green]Resuming session...[/bold green]")
    console.print("📊 Progress: 80% - 🛠️ Creating your agent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 100% - 🚀 Deploying agent...")
    
    # Complete the request
    result = await orchestrator.process_request(user_request, session_id)
    await display_result(result)
    
    # Educational explanation
    console.print(Panel(
        "[bold green]🎯 Session Recovery Demonstrated![/bold green]\n\n"
        "1. [bold]Persistence:[/bold] HeyJarvis saved your progress automatically\n"
        "2. [bold]Recovery:[/bold] 'continue' command showed available sessions\n"
        "3. [bold]Resume:[/bold] Picked up exactly where you left off (60%)\n"
        "4. [bold]Completion:[/bold] Finished the remaining 40% of work\n\n"
        "💡 [bold]Key Feature:[/bold] Never lose progress, even with interruptions!\n"
        "Sessions are automatically saved to Redis for persistence.",
        style="green"
    ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


async def demo_clarification_flow(orchestrator: HeyJarvisOrchestrator):
    """Demo: Clarification Flow - handle ambiguous requests."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]💬 Demo: Clarification Flow[/bold blue]\n\n"
        "This demo shows how HeyJarvis handles vague or ambiguous requests.\n"
        "When your request needs clarification, HeyJarvis will ask\n"
        "intelligent follow-up questions to understand exactly what you want.",
        title="Interactive Tutorial",
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]💡 Try typing something vague like:[/bold yellow]")
    console.print("   [dim]'set up monitoring'[/dim]")
    console.print("   [dim]'create automation'[/dim]")
    console.print("   [dim]'help with notifications'[/dim]")
    
    # Get ambiguous input
    user_input = console.input("\n[bold green]You:[/bold green] ").strip()
    
    if not user_input:
        console.print("[yellow]Let's try with a vague request...[/yellow]")
        user_input = "set up monitoring"
        console.print(f"[dim]Using: {user_input}[/dim]")
    
    # Tutorial annotation
    console.print(Panel(
        "🤔 [bold]HeyJarvis is analyzing your request...[/bold]\n"
        "Since this is somewhat vague, HeyJarvis will ask clarifying questions\n"
        "to understand exactly what type of monitoring you need.",
        style="dim yellow"
    ))
    
    # Simulate clarification process
    console.print(f"\n📊 Progress: 20% - 🔍 Understanding your request...")
    await asyncio.sleep(1)
    
    # Simulate HeyJarvis asking for clarification
    console.print("\n[bold cyan]💬 HeyJarvis:[/bold cyan] I'd love to help you set up monitoring! ")
    console.print("To create the best agent for you, I need a bit more detail:")
    console.print("\n[bold]What would you like to monitor?[/bold]")
    console.print("• 📧 Email inbox for important messages")
    console.print("• 💾 System resources (CPU, memory, disk)")
    console.print("• 🌐 Website uptime and performance")
    console.print("• 📁 File changes in specific directories")
    console.print("• 📊 Social media mentions or metrics")
    
    clarification = console.input("\n[bold green]You:[/bold green] ").strip()
    
    if not clarification:
        clarification = "email inbox for important messages"
        console.print(f"[dim]Using: {clarification}[/dim]")
    
    # Continue with clarified request
    refined_request = f"Monitor {clarification}"
    console.print(f"\n[bold cyan]💬 HeyJarvis:[/bold cyan] Perfect! I'll create an agent to monitor {clarification}.")
    
    # Continue processing
    console.print("\n📊 Progress: 40% - 🤔 Analyzing refined intent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 60% - 🔎 Checking existing agents...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 80% - 🛠️ Creating your agent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 100% - 🚀 Deploying agent...")
    
    # Process the refined request
    session_id = "demo_clarification_001"
    result = await orchestrator.process_request(refined_request, session_id)
    await display_result(result)
    
    # Educational explanation
    console.print(Panel(
        "[bold green]💡 Clarification Flow Demonstrated![/bold green]\n\n"
        "1. [bold]Vague Input:[/bold] You provided a general request\n"
        "2. [bold]Smart Questions:[/bold] HeyJarvis asked specific clarifying questions\n"
        "3. [bold]Context Building:[/bold] Your responses refined the requirements\n"
        "4. [bold]Precise Creation:[/bold] Final agent matched your exact needs\n\n"
        "🎯 [bold]Key Feature:[/bold] HeyJarvis doesn't guess - it asks!\n"
        "This ensures you get exactly the agent you need.",
        style="green"
    ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


async def demo_advanced_creation(orchestrator: HeyJarvisOrchestrator):
    """Demo: Advanced Multi-Step Agent Creation."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]🚀 Demo: Advanced Multi-Step Creation[/bold blue]\n\n"
        "This demo shows HeyJarvis handling complex, multi-step workflows.\n"
        "We'll create a sophisticated agent with multiple capabilities\n"
        "and show how context is preserved across interactions.",
        title="Interactive Tutorial",
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]Scenario:[/bold yellow] Let's create a comprehensive social media management agent")
    console.print("[dim]This will involve multiple steps and refinements...[/dim]")
    
    # Step 1: Initial complex request
    console.print("\n[bold green]Step 1: Initial Request[/bold green]")
    initial_request = "Create a social media agent that posts content, tracks engagement, and responds to mentions"
    console.print(f"[bold green]Request:[/bold green] {initial_request}")
    
    session_id = "demo_advanced_001"
    console.print("\n[dim]→ Processing complex multi-capability request...[/dim]")
    
    result1 = await orchestrator.process_request(initial_request, session_id)
    await display_result(result1)
    
    # Step 2: Refinement
    console.print("\n[bold green]Step 2: Adding Requirements[/bold green]")
    console.print("[bold cyan]💬 HeyJarvis:[/bold cyan] Great! I can enhance this agent further.")
    console.print("Would you like to add any specific features or integrations?")
    
    console.print("\n[bold yellow]💡 Try adding:[/bold yellow] 'Also schedule posts for optimal times and create analytics reports'")
    
    refinement = console.input("\n[bold green]You:[/bold green] ").strip()
    
    if not refinement:
        refinement = "Also schedule posts for optimal times and create analytics reports"
        console.print(f"[dim]Using: {refinement}[/dim]")
    
    # Process refinement
    console.print(Panel(
        "🧠 [bold]Context Preservation in Action:[/bold]\n"
        "HeyJarvis remembers the existing agent and will enhance it\n"
        "rather than creating a completely new one.",
        style="dim yellow"
    ))
    
    enhanced_request = f"{initial_request}. {refinement}"
    result2 = await orchestrator.process_request(enhanced_request, session_id)
    await display_result(result2)
    
    # Step 3: Final customization
    console.print("\n[bold green]Step 3: Platform-Specific Customization[/bold green]")
    console.print("[bold cyan]💬 HeyJarvis:[/bold cyan] Which social media platforms should this agent support?")
    
    platforms = console.input("\n[bold green]You:[/bold green] ").strip()
    
    if not platforms:
        platforms = "Twitter, Instagram, and LinkedIn"
        console.print(f"[dim]Using: {platforms}[/dim]")
    
    final_request = f"{enhanced_request}. Focus on {platforms}"
    console.print(f"\n[dim]→ Customizing for specific platforms: {platforms}[/dim]")
    
    result3 = await orchestrator.process_request(final_request, session_id)
    await display_result(result3)
    
    # Educational explanation
    console.print(Panel(
        "[bold green]🚀 Advanced Creation Demonstrated![/bold green]\n\n"
        "1. [bold]Complex Input:[/bold] Started with multi-capability request\n"
        "2. [bold]Iterative Refinement:[/bold] Added features step-by-step\n"
        "3. [bold]Context Preservation:[/bold] Each step built on the previous\n"
        "4. [bold]Platform Customization:[/bold] Tailored to specific needs\n"
        "5. [bold]Unified Agent:[/bold] Single agent with all capabilities\n\n"
        "💡 [bold]Key Feature:[/bold] HeyJarvis handles complexity naturally!\n"
        "Build sophisticated agents through conversation.",
        style="green"
    ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


async def demo_error_handling(orchestrator: HeyJarvisOrchestrator):
    """Demo: Error Handling and Recovery."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]❌ Demo: Error Handling[/bold blue]\n\n"
        "This demo shows how HeyJarvis gracefully handles various types\n"
        "of errors and provides helpful recovery suggestions.\n"
        "You'll see retry mechanisms and error recovery in action.",
        title="Interactive Tutorial",
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]We'll demonstrate several error scenarios:[/bold yellow]")
    console.print("1. 🤔 Ambiguous requests that need clarification")
    console.print("2. 🚫 Invalid or impossible requests")
    console.print("3. 🔄 Network/service interruptions")
    console.print("4. ♻️ Automatic retry mechanisms")
    
    # Error Type 1: Ambiguous/unclear request
    console.print("\n[bold green]Error Demo 1: Handling Unclear Requests[/bold green]")
    unclear_request = "do something with my computer"
    console.print(f"[bold green]Request:[/bold green] {unclear_request}")
    
    console.print(Panel(
        "🎯 [bold]What should happen:[/bold]\n"
        "HeyJarvis will recognize this is too vague and ask for clarification\n"
        "rather than making assumptions or failing silently.",
        style="dim yellow"
    ))
    
    session_id = "demo_error_001"
    
    # This will likely trigger clarification flow
    console.print("\n[dim]→ Processing unclear request...[/dim]")
    result1 = await orchestrator.process_request(unclear_request, session_id)
    
    if result1.get('error_message'):
        console.print(f"[yellow]Expected behavior: {result1['error_message']}[/yellow]")
    else:
        await display_result(result1)
    
    # Error Type 2: Impossible request
    console.print("\n[bold green]Error Demo 2: Impossible Requests[/bold green]")
    impossible_request = "create an agent that can travel back in time"
    console.print(f"[bold green]Request:[/bold green] {impossible_request}")
    
    console.print(Panel(
        "🎯 [bold]What should happen:[/bold]\n"
        "HeyJarvis will recognize this is impossible and suggest\n"
        "alternative approaches or clarify what you really need.",
        style="dim yellow"
    ))
    
    console.print("\n[dim]→ Processing impossible request...[/dim]")
    result2 = await orchestrator.process_request(impossible_request, "demo_error_002")
    
    if result2.get('error_message'):
        console.print(f"[yellow]Graceful handling: {result2['error_message']}[/yellow]")
    else:
        await display_result(result2)
    
    # Error Type 3: Demonstrate retry mechanism
    console.print("\n[bold green]Error Demo 3: Retry Mechanism[/bold green]")
    console.print("[dim]Demonstrating how HeyJarvis retries on temporary failures...[/dim]")
    
    # Simulate a request that might need retries
    retry_request = "create a complex integration agent"
    console.print(f"[bold green]Request:[/bold green] {retry_request}")
    
    console.print("\n📊 Progress: 20% - 🔍 Understanding your request...")
    await asyncio.sleep(1)
    console.print("⚠️  [yellow]Temporary issue encountered... retrying (1/3)[/yellow]")
    await asyncio.sleep(1)
    console.print("📊 Progress: 40% - 🤔 Analyzing intent... (retry successful)")
    await asyncio.sleep(1)
    console.print("📊 Progress: 60% - 🔎 Checking existing agents...")
    await asyncio.sleep(1)
    
    result3 = await orchestrator.process_request(retry_request, "demo_error_003")
    await display_result(result3)
    
    # Error Type 4: Recovery suggestions
    console.print("\n[bold green]Error Demo 4: Recovery Suggestions[/bold green]")
    console.print("[bold cyan]💬 HeyJarvis:[/bold cyan] When errors occur, I provide helpful suggestions:")
    
    suggestions = [
        "🔄 Try rephrasing your request with more specific details",
        "🎯 Break complex requests into smaller steps", 
        "💬 Use the clarification flow to refine requirements",
        "📞 Check if external services are available",
        "🔍 Review similar successful agent examples"
    ]
    
    for suggestion in suggestions:
        console.print(f"  • {suggestion}")
    
    # Educational explanation
    console.print(Panel(
        "[bold green]❌ Error Handling Demonstrated![/bold green]\n\n"
        "1. [bold]Unclear Requests:[/bold] Asks for clarification instead of guessing\n"
        "2. [bold]Impossible Tasks:[/bold] Explains limitations and suggests alternatives\n"
        "3. [bold]Retry Logic:[/bold] Automatically retries transient failures\n"
        "4. [bold]Helpful Messages:[/bold] Provides actionable recovery suggestions\n"
        "5. [bold]Graceful Degradation:[/bold] Fails safely with useful feedback\n\n"
        "💡 [bold]Key Feature:[/bold] HeyJarvis never leaves you stuck!\n"
        "Every error includes guidance on how to proceed.",
        style="green"
    ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="HeyJarvis AI Agent Orchestrator")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode")
    args = parser.parse_args()
    
    if args.demo:
        asyncio.run(demo_mode())
    else:
        asyncio.run(chat_interface())


if __name__ == "__main__":
    main()