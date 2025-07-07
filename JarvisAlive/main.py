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
from orchestration.jarvis import Jarvis, JarvisConfig
from conversation.websocket_handler import websocket_handler, OperatingMode

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


async def jarvis_mode():
    """Business-level orchestration mode with Jarvis."""
    # Initialize Jarvis with existing config
    orchestrator_config = OrchestratorConfig(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600"))
    )
    
    jarvis_config = JarvisConfig(
        orchestrator_config=orchestrator_config,
        max_concurrent_departments=int(os.getenv("MAX_DEPARTMENTS", "5")),
        enable_autonomous_department_creation=os.getenv("AUTO_DEPARTMENTS", "true").lower() == "true",
        enable_cross_department_coordination=os.getenv("CROSS_DEPT_COORD", "true").lower() == "true"
    )
    
    if not orchestrator_config.anthropic_api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment variables.[/red]")
        console.print("Please set your Anthropic API key in the .env file.")
        return
    
    jarvis = Jarvis(jarvis_config)
    await jarvis.initialize()
    
    # Reuse existing chat interface with Jarvis routing
    console.print("[bold cyan]💼 Jarvis Business Mode Active[/bold cyan]")
    console.print("[dim]Business-level orchestration with department coordination[/dim]\n")
    
    def progress_callback(node_name: str, progress: int, message: str):
        """Progress callback for real-time updates."""
        console.print(f"📊 Progress: {progress}% - {message}")
        # Send WebSocket update for Jarvis mode
        try:
            asyncio.create_task(websocket_handler.send_workflow_progress(
                session_id if 'session_id' in locals() else "unknown", 
                "Business Workflow", progress, message
            ))
        except:
            pass  # WebSocket updates are optional
    
    jarvis.set_progress_callback(progress_callback)
    
    try:
        session_id = str(uuid.uuid4())[:8]
        console.print(f"[dim]Session ID: {session_id}[/dim]\n")
        
        # Enhanced commands for Jarvis mode
        console.print("[dim]💡 Commands: 'insights', 'departments', 'business', 'demo', or any business request[/dim]\n")
        
        while True:
            try:
                user_input = console.input("[bold cyan]You:[/bold cyan] ").strip()
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.lower() in ['exit', 'quit']:
                    console.print("[yellow]Goodbye! Your business context has been saved.[/yellow]")
                    break
                elif user_input.lower() == 'demo':
                    await business_demo_mode(jarvis, session_id)
                    continue
                elif user_input.lower() == 'insights':
                    await show_business_insights(jarvis, session_id)
                    continue
                elif user_input.lower() == 'departments':
                    await show_departments(jarvis)
                    continue
                elif user_input.lower() == 'business':
                    await show_business_context(jarvis, session_id)
                    continue
                
                # Route requests based on mode
                # Check if this is a technical request that should go to agent builder
                if await is_technical_request(user_input):
                    console.print("[yellow]🔧 Technical request detected - forwarding to agent builder...[/yellow]")
                    result = await jarvis.process_business_request(user_input, session_id)
                else:
                    # Business request - use Jarvis for business-level orchestration
                    console.print(f"\n[bold cyan]💼 Jarvis:[/bold cyan] Processing business request with department coordination...\n")
                    result = await jarvis.process_business_request(user_input, session_id)
                
                await display_jarvis_result(result)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Session interrupted. Type 'continue' to resume later.[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                logger.error(f"Jarvis mode error: {e}")
                
    finally:
        await jarvis.close()


async def jarvis_interface():
    """Interactive chat interface for Jarvis Meta-Orchestrator."""
    
    # Configuration for Jarvis
    orchestrator_config = OrchestratorConfig(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600"))
    )
    
    jarvis_config = JarvisConfig(
        orchestrator_config=orchestrator_config,
        max_concurrent_departments=int(os.getenv("MAX_DEPARTMENTS", "5")),
        enable_autonomous_department_creation=os.getenv("AUTO_DEPARTMENTS", "true").lower() == "true",
        enable_cross_department_coordination=os.getenv("CROSS_DEPT_COORD", "true").lower() == "true"
    )
    
    if not orchestrator_config.anthropic_api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment variables.[/red]")
        console.print("Please set your Anthropic API key in the .env file.")
        return
    
    # Initialize Jarvis
    jarvis = Jarvis(jarvis_config)
    
    def progress_callback(node_name: str, progress: int, message: str):
        """Progress callback for real-time updates."""
        console.print(f"📊 Progress: {progress}% - {message}")
    
    jarvis.set_progress_callback(progress_callback)
    
    try:
        await jarvis.initialize()
        
        # Welcome message for Jarvis
        console.print("\n[bold magenta]🧠 Jarvis Meta-Orchestrator:[/bold magenta] Welcome! I'm your business-level AI orchestrator.")
        console.print("I can help you create individual agents or coordinate entire departments.")
        console.print("I understand your business context and can optimize for your company's goals.\n")
        
        session_id = str(uuid.uuid4())[:8]
        console.print(f"[dim]Session ID: {session_id}[/dim]\n")
        
        # Show additional Jarvis commands
        console.print("[dim]💡 Jarvis commands: 'insights', 'departments', 'business', or any agent request[/dim]\n")
        
        while True:
            try:
                # Get user input
                user_input = console.input("[bold magenta]You:[/bold magenta] ").strip()
                
                if not user_input:
                    continue
                    
                # Handle commands
                if user_input.lower() in ['exit', 'quit']:
                    console.print("[yellow]Goodbye! Your business context has been saved.[/yellow]")
                    break
                    
                elif user_input.lower() == 'continue':
                    await handle_jarvis_continue_command(jarvis)
                    continue
                    
                elif user_input.lower() == 'sessions':
                    await show_jarvis_active_sessions(jarvis)
                    continue
                    
                elif user_input.lower() == 'insights':
                    await show_business_insights(jarvis, session_id)
                    continue
                    
                elif user_input.lower() == 'departments':
                    await show_departments(jarvis)
                    continue
                    
                elif user_input.lower() == 'business':
                    await show_business_context(jarvis, session_id)
                    continue
                
                # Process business request through Jarvis
                console.print(f"\n[bold magenta]🧠 Jarvis:[/bold magenta] I'll process your business request with full context awareness...\n")
                
                result = await jarvis.process_business_request(user_input, session_id)
                
                # Display results with Jarvis metadata
                await display_jarvis_result(result)
                
            except KeyboardInterrupt:
                console.print("\n[yellow]Session interrupted. Type 'continue' to resume later.[/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {str(e)}[/red]")
                logger.error(f"Jarvis interface error: {e}")
                
    finally:
        await jarvis.close()


async def chat_interface():
    """Interactive chat interface for HeyJarvis."""
    
    # Configuration
    config = OrchestratorConfig(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        session_timeout=int(os.getenv("SESSION_TIMEOUT", "3600"))
    )
    
    if not config.anthropic_api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment variables.[/red]")
        console.print("Please set your Anthropic API key in the .env file.")
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
    
    # Check if clarification is needed
    needs_clarification = result.get('needs_clarification', False)
    clarification_questions = result.get('clarification_questions', [])
    suggestions = result.get('suggestions', [])
    
    if needs_clarification and clarification_questions:
        # Pick the most important question (first one) and top 2 suggestions
        main_question = clarification_questions[0] if clarification_questions else "Could you provide more details?"
        top_suggestions = suggestions[:2] if suggestions else []
        
        console.print(f"[bold cyan]💬 HeyJarvis:[/bold cyan] {main_question}")
        
        # Show only top 2 suggestions to keep it concise
        if top_suggestions:
            console.print("\n[bold yellow]💡 For example:[/bold yellow]")
            for suggestion in top_suggestions:
                console.print(f"  • {suggestion}")
        
        console.print()
        return
    
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
        ("error", "❌ Error Handling: See how errors are handled"),
        ("jarvis_sales", "💼 Jarvis: Grow revenue with Sales department"),
        ("jarvis_costs", "💰 Jarvis: Reduce operational costs")
    ]
    
    console.print()
    for i, (demo_key, description) in enumerate(demos, 1):
        status = "✅" if demo_key in completed_demos else "⭕"
        console.print(f"{i}. {status} {description}")
    
    console.print(f"\n[dim]Progress: {len(completed_demos)}/7 demos completed[/dim]")
    console.print("[dim]Type 'exit' to quit the demo[/dim]")


async def demo_mode():
    """Interactive demo mode showing HeyJarvis capabilities."""
    
    # Configuration
    config = OrchestratorConfig(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
        max_retries=int(os.getenv("MAX_RETRIES", "3"))
    )
    
    if not config.anthropic_api_key:
        console.print("[red]Error: ANTHROPIC_API_KEY not found in environment variables.[/red]")
        console.print("Please set your Anthropic API key in the .env file.")
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
            choice = console.input("\nEnter your choice (1-7, or 'exit'): ").strip().lower()
            
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
            elif choice == '6':
                await jarvis_demo_sales_growth(orchestrator)
                completed_demos.add('jarvis_sales')
            elif choice == '7':
                await jarvis_demo_cost_reduction(orchestrator)
                completed_demos.add('jarvis_costs')
            else:
                console.print("[red]Invalid choice. Please select 1-7 or 'exit'.[/red]")
                console.input("\nPress Enter to continue...")
                continue
            
            # Check if all demos completed
            if len(completed_demos) == 7:
                console.print(Panel(
                    "[bold green]🎉 Congratulations! You've completed all demos![/bold green]\n\n"
                    "You've experienced all the key features of HeyJarvis:\n"
                    "• Basic agent creation\n"
                    "• Session recovery\n"
                    "• Clarification handling\n"
                    "• Advanced workflows\n"
                    "• Error handling\n"
                    "• Jarvis business automation\n"
                    "• Department coordination\n\n"
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


async def handle_jarvis_continue_command(jarvis: Jarvis):
    """Handle the continue command for Jarvis sessions."""
    sessions = await jarvis.list_active_sessions()
    
    if not sessions:
        console.print("[yellow]No active sessions found.[/yellow]")
        return
    
    # Show available sessions
    console.print("[bold magenta]🧠 Jarvis:[/bold magenta] You have these sessions you can resume:\n")
    
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
            state = await jarvis.recover_session(selected_session['session_id'])
            if state:
                console.print(f"[magenta]Previous request:[/magenta] {state.get('user_request', 'Unknown')}")
                console.print(f"[magenta]Current status:[/magenta] {state.get('deployment_status', 'Unknown')}")
                
                # Continue processing if needed
                if state.get('deployment_status') != 'completed':
                    result = await jarvis.process_business_request(
                        state['user_request'], 
                        selected_session['session_id']
                    )
                    await display_jarvis_result(result)
                else:
                    console.print("[green]Session was already completed![/green]")
        else:
            console.print("[red]Invalid session number.[/red]")
            
    except ValueError:
        console.print("[red]Please enter a valid number.[/red]")
    except Exception as e:
        console.print(f"[red]Error resuming session: {str(e)}[/red]")


async def show_jarvis_active_sessions(jarvis: Jarvis):
    """Show all active Jarvis sessions."""
    sessions = await jarvis.list_active_sessions()
    
    if not sessions:
        console.print("[yellow]No active sessions found.[/yellow]")
        return
    
    table = Table(title="Active Jarvis Sessions")
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


async def show_business_insights(jarvis: Jarvis, session_id: str):
    """Show business insights and optimization suggestions."""
    try:
        insights = await jarvis.get_business_insights(session_id)
        
        if "error" in insights:
            console.print(f"[yellow]Business insights not available: {insights['error']}[/yellow]")
            console.print("[dim]Tip: Create some agents first to build business context[/dim]")
            return
        
        business_data = insights.get("business_insights", {})
        
        # Show optimization suggestions
        suggestions = business_data.get("optimization_suggestions", [])
        if suggestions:
            console.print("\n[bold blue]💡 Business Optimization Suggestions:[/bold blue]")
            for suggestion in suggestions[:3]:  # Show top 3
                priority_color = {"critical": "red", "high": "yellow", "medium": "blue", "low": "dim"}.get(suggestion.get("priority", "medium"), "white")
                console.print(f"[{priority_color}]• {suggestion.get('title', 'Unknown')}[/{priority_color}]")
                console.print(f"  {suggestion.get('description', '')}")
                if suggestion.get('action'):
                    console.print(f"  [dim]Action: {suggestion['action']}[/dim]")
                console.print()
        
        # Show goal progress
        goal_progress = business_data.get("goal_progress", [])
        if goal_progress:
            console.print("[bold blue]🎯 Goal Progress:[/bold blue]")
            for goal in goal_progress[:3]:  # Show top 3
                progress = goal.get("progress", 0) * 100
                status = goal.get("status", "unknown")
                status_color = {"completed": "green", "on_track": "blue", "at_risk": "yellow", "overdue": "red"}.get(status, "white")
                console.print(f"[{status_color}]• {goal.get('title', 'Unknown')} ({progress:.0f}%)[/{status_color}]")
                console.print(f"  Priority: {goal.get('priority', 'unknown').title()}")
                console.print()
        
        # Show context summary
        context = business_data.get("context_summary", {})
        if context.get("company"):
            company = context["company"]
            console.print("[bold blue]🏢 Company Context:[/bold blue]")
            console.print(f"• Stage: {company.get('stage', 'unknown').title()}")
            console.print(f"• Industry: {company.get('industry', 'unknown').title()}")
            console.print(f"• Team Size: {company.get('team_size', 'unknown')}")
            console.print()
        
        # Show active departments
        departments = business_data.get("active_departments", {})
        if departments:
            console.print("[bold blue]🏛️ Active Departments:[/bold blue]")
            for dept_id, dept_info in departments.items():
                console.print(f"• {dept_info.get('name', dept_id)}: {dept_info.get('active_agents', 0)} agents")
            console.print()
        
    except Exception as e:
        console.print(f"[red]Error getting business insights: {str(e)}[/red]")


async def show_departments(jarvis: Jarvis):
    """Show all active departments."""
    try:
        departments = await jarvis.list_departments()
        
        if not departments:
            console.print("[yellow]No active departments found.[/yellow]")
            console.print("[dim]Departments will be created automatically as you build complex workflows[/dim]")
            return
        
        table = Table(title="Active Departments")
        table.add_column("Name", style="green")
        table.add_column("Status", style="blue")
        table.add_column("Agents", style="cyan")
        table.add_column("Last Activity", style="yellow")
        
        for dept in departments:
            status_color = {"active": "green", "coordinating": "blue", "paused": "yellow", "error": "red"}.get(dept.get("status", "unknown"), "white")
            table.add_row(
                dept.get("name", "Unknown"),
                f"[{status_color}]{dept.get('status', 'unknown').title()}[/{status_color}]",
                str(dept.get("agent_count", 0)),
                dept.get("last_activity", "Unknown")
            )
        
        console.print(table)
        
    except Exception as e:
        console.print(f"[red]Error getting departments: {str(e)}[/red]")


async def show_business_context(jarvis: Jarvis, session_id: str):
    """Show detailed business context."""
    console.print("[bold blue]📊 Business Context Management[/bold blue]\n")
    console.print("This feature allows you to set company profile, metrics, and goals.")
    console.print("Currently showing available context...\n")
    
    try:
        insights = await jarvis.get_business_insights(session_id)
        
        if "error" not in insights:
            business_data = insights.get("business_insights", {})
            context = business_data.get("context_summary", {})
            
            if context.get("has_profile"):
                console.print("[green]✅ Company profile configured[/green]")
            else:
                console.print("[yellow]⭕ Company profile not set[/yellow]")
                
            if context.get("has_metrics"):
                console.print("[green]✅ Business metrics tracked[/green]")
            else:
                console.print("[yellow]⭕ Business metrics not set[/yellow]")
                
            if context.get("goal_count", 0) > 0:
                console.print(f"[green]✅ {context['goal_count']} business goals defined[/green]")
            else:
                console.print("[yellow]⭕ No business goals set[/yellow]")
        else:
            console.print("[yellow]Business context not yet available[/yellow]")
        
        console.print("\n[dim]Future versions will allow interactive business context setup[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error accessing business context: {str(e)}[/red]")


async def display_jarvis_result(result: Dict[str, Any]):
    """Display Jarvis orchestrator result in a user-friendly format."""
    # First display the normal result
    await display_result(result)
    
    # Then show Jarvis-specific metadata
    jarvis_metadata = result.get('jarvis_metadata', {})
    if jarvis_metadata:
        console.print("[bold blue]🧠 Jarvis Analysis:[/bold blue]")
        
        processing_time = jarvis_metadata.get('processing_time_ms', 0)
        console.print(f"• Processing time: {processing_time}ms")
        
        # Show business intent analysis
        business_intent = jarvis_metadata.get('business_intent', {})
        if business_intent:
            category = business_intent.get('category', 'unknown')
            confidence = business_intent.get('confidence', 0)
            complexity = business_intent.get('complexity', 'unknown')
            timeline = business_intent.get('estimated_timeline', 'unknown')
            
            # Color code by category
            category_colors = {
                "GROW_REVENUE": "green",
                "REDUCE_COSTS": "blue",
                "IMPROVE_EFFICIENCY": "yellow",
                "LAUNCH_PRODUCT": "magenta",
                "CUSTOM_AUTOMATION": "cyan"
            }
            category_color = category_colors.get(category, "white")
            
            console.print(f"• 🎯 Intent: [{category_color}]{category.replace('_', ' ').title()}[/{category_color}] ({confidence:.0%} confidence)")
            console.print(f"• 📊 Complexity: {complexity.title()} ({timeline})")
        
        if jarvis_metadata.get('business_context_available'):
            console.print("• ✅ Business context applied")
        else:
            console.print("• ⭕ Business context not available")
        
        active_depts = jarvis_metadata.get('active_departments', [])
        if active_depts:
            console.print(f"• 🏛️ Active departments: {len(active_depts)}")
        
        if jarvis_metadata.get('error_handled_by_jarvis'):
            console.print("• 🛡️ Error handled gracefully by Jarvis")
        
        console.print()
    
    # Show business guidance if available
    business_guidance = result.get('business_guidance', {})
    if business_guidance and not business_guidance.get('note'):
        console.print("[bold blue]📋 Business Guidance:[/bold blue]")
        
        intent_category = business_guidance.get('intent_category', '')
        if intent_category:
            console.print(f"• Category: {intent_category.replace('_', ' ').title()}")
        
        suggested_depts = business_guidance.get('suggested_departments', [])
        if suggested_depts:
            console.print(f"• Suggested departments: {', '.join(suggested_depts)}")
        
        key_metrics = business_guidance.get('key_metrics', [])
        if key_metrics:
            console.print(f"• Key metrics to track: {', '.join(key_metrics[:3])}")
        
        reasoning = business_guidance.get('reasoning', '')
        if reasoning:
            console.print(f"• Strategic purpose: {reasoning}")
        
        console.print()


async def is_technical_request(user_input: str) -> bool:
    """Determine if a request is technical (agent builder) vs business (Jarvis)."""
    technical_keywords = [
        'create agent', 'build agent', 'agent that', 'automation for',
        'monitor', 'sync', 'backup', 'email agent', 'file agent',
        'integration', 'webhook', 'api'
    ]
    
    business_keywords = [
        'grow sales', 'increase revenue', 'reduce costs', 'improve efficiency',
        'sales department', 'marketing', 'hire', 'scale', 'business',
        'profit', 'customers', 'leads', 'pipeline', 'department', 'for sales'
    ]
    
    user_lower = user_input.lower()
    
    # Check for business keywords first (higher priority)
    if any(keyword in user_lower for keyword in business_keywords):
        return False  # Business request
    
    # Check for technical keywords, but be more specific
    technical_score = sum(1 for keyword in technical_keywords if keyword in user_lower)
    
    # If we have strong technical indicators and no business context, treat as technical
    if technical_score >= 2 or ('create agent' in user_lower or 'build agent' in user_lower):
        return True  # Technical request
    elif technical_score == 1 and 'technical' in user_lower and 'business' not in user_lower:
        return True  # Single technical keyword with explicit "technical"
    
    # Default to business request in Jarvis mode
    return False


async def jarvis_demo_sales_growth(orchestrator: HeyJarvisOrchestrator):
    """Demo: Jarvis Sales Growth - business department coordination."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]💼 Jarvis Demo: Sales Growth[/bold blue]\n\n"
        "Experience how Jarvis transforms business requests into coordinated\n"
        "department actions with real-time metrics and insights.\n\n"
        "This demo shows business-level orchestration vs technical agent creation.",
        title="Business Automation Demo",
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]📈 Business Scenario:[/bold yellow]")
    console.print("Company wants to grow revenue 30% this quarter")
    console.print("Current revenue: $2.5M → Target: $3.25M")
    console.print("Timeline: Q4 2024 (3 months remaining)")
    
    console.print("\n[dim]Let's see how Jarvis handles this business challenge...[/dim]")
    console.input("\n[dim]Press Enter to start the demo...[/dim]")
    
    # Simulate user business request
    business_request = "I need to grow revenue 30% this quarter"
    console.print(f"\n[bold green]You:[/bold green] {business_request}")
    
    # Show Jarvis analyzing business context
    console.print(Panel(
        "🧠 [bold]Jarvis is analyzing your business request:[/bold]\n\n"
        "• Identifying intent: Revenue growth (30% increase)\n"
        "• Business context: Quarterly target, $750K additional revenue needed\n"
        "• Department assessment: Sales capacity and current pipeline\n"
        "• Strategic planning: Multi-agent coordination required",
        style="dim yellow"
    ))
    
    # Simulate progress with business context
    console.print("\n[bold magenta]🧠 Jarvis:[/bold magenta] I'll activate the Sales department to achieve your 30% revenue growth target...\n")
    
    # Progress updates with business context
    progress_updates = [
        (20, "🔍 Analyzing current sales pipeline ($2.5M revenue)"),
        (35, "🎯 Identifying growth opportunities and bottlenecks"),
        (50, "🏢 Activating Sales Department with 4 specialized agents"),
        (65, "📊 Setting up revenue tracking and KPI monitoring"),
        (80, "🤝 Coordinating lead generation and pipeline optimization"),
        (95, "✅ Sales Department operational with 30% growth target"),
        (100, "🚀 Real-time revenue tracking activated")
    ]
    
    for progress, message in progress_updates:
        console.print(f"📊 Progress: {progress}% - {message}")
        await asyncio.sleep(0.8)
    
    # Show department activation results
    console.print("\n[bold green]✅ Sales Department Activated![/bold green]")
    
    # Create a metrics table
    metrics_table = Table(title="Live Business Metrics")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Current", style="white")
    metrics_table.add_column("Target", style="green")
    metrics_table.add_column("Progress", style="yellow")
    
    metrics_table.add_row("Revenue", "$2.5M", "$3.25M", "🎯 Target Set")
    metrics_table.add_row("Lead Pipeline", "150 leads", "250 leads", "📈 +67% needed")
    metrics_table.add_row("Conversion Rate", "12%", "15%", "🔄 Optimizing")
    metrics_table.add_row("Avg Deal Size", "$16.7K", "$20K", "💰 Upselling")
    
    console.print(metrics_table)
    
    # Show activated agents
    console.print(Panel(
        "[bold green]🤖 Sales Department Agents Deployed:[/bold green]\n\n"
        "• [bold]Lead Scanner Agent[/bold] - Identifying high-value prospects\n"
        "• [bold]Outreach Composer Agent[/bold] - Personalizing sales communications\n"
        "• [bold]Meeting Scheduler Agent[/bold] - Optimizing demo scheduling\n"
        "• [bold]Pipeline Tracker Agent[/bold] - Monitoring deal progression\n\n"
        "💡 [bold]Coordination:[/bold] All agents share data and optimize together",
        style="green"
    ))
    
    # Simulate live metrics updates
    console.print("\n[bold yellow]📊 Simulating live metrics (5 seconds)...[/bold yellow]")
    
    live_updates = [
        "💼 Lead Scanner found 8 qualified prospects (Score: 8.5/10)",
        "📧 Outreach Composer sent 15 personalized emails (18% response rate)", 
        "📅 Meeting Scheduler booked 3 demos for this week",
        "💰 Pipeline Tracker: $45K in new opportunities added",
        "🎯 Revenue projection: +$125K this month (on track for 30% growth)"
    ]
    
    for update in live_updates:
        await asyncio.sleep(1)
        console.print(f"  {update}")
    
    # Show projected impact
    console.print(Panel(
        "[bold green]📈 Projected Business Impact:[/bold green]\n\n"
        "• [bold]Revenue Growth:[/bold] On track for 32% increase ($800K additional)\n"
        "• [bold]Timeline:[/bold] Target achievable 2 weeks ahead of schedule\n"
        "• [bold]Efficiency:[/bold] 40% improvement in sales process automation\n"
        "• [bold]ROI:[/bold] $800K revenue / $50K automation cost = 1600% ROI\n\n"
        "🚀 [bold]Key Difference:[/bold] Jarvis coordinates business outcomes,\n"
        "not just individual agent tasks!",
        style="green"
    ))
    
    # Educational comparison
    console.print(Panel(
        "[bold blue]🎭 Demo Comparison: Jarvis vs Traditional Agents[/bold blue]\n\n"
        "[bold yellow]Traditional Approach:[/bold yellow]\n"
        "• Create individual agents one by one\n"
        "• Manual coordination between agents\n"
        "• Technical focus: 'Create a lead generation agent'\n"
        "• Limited business context awareness\n\n"
        "[bold magenta]Jarvis Approach:[/bold magenta]\n"
        "• Business goal: 'Grow revenue 30%'\n"
        "• Automatic department activation\n"
        "• Coordinated multi-agent strategy\n"
        "• Real-time business metrics tracking\n"
        "• Strategic business outcome focus",
        style="dim"
    ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


async def jarvis_demo_cost_reduction(orchestrator: HeyJarvisOrchestrator):
    """Demo: Jarvis Cost Reduction - operational efficiency."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]💰 Jarvis Demo: Cost Reduction[/bold blue]\n\n"
        "See how Jarvis identifies cost-saving opportunities across\n"
        "multiple departments and implements coordinated efficiency solutions.\n\n"
        "This demo showcases cross-department optimization.",
        title="Operational Efficiency Demo", 
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]💸 Business Challenge:[/bold yellow]")
    console.print("Operational costs too high: $500K/month")
    console.print("Target: Reduce costs by 20% ($100K/month savings)")
    console.print("Focus: Automation and process optimization")
    
    console.print("\n[dim]Let's see Jarvis analyze and optimize operational costs...[/dim]")
    console.input("\n[dim]Press Enter to start cost analysis...[/dim]")
    
    # Simulate business request
    cost_request = "Reduce our operational costs by 20% through automation"
    console.print(f"\n[bold green]You:[/bold green] {cost_request}")
    
    # Show Jarvis cost analysis
    console.print(Panel(
        "🧠 [bold]Jarvis Cost Analysis in Progress:[/bold]\n\n"
        "• Scanning operational expenses across all departments\n"
        "• Identifying automation opportunities\n"
        "• Calculating potential savings and ROI\n"
        "• Planning cross-department efficiency improvements",
        style="dim yellow"
    ))
    
    console.print("\n[bold magenta]🧠 Jarvis:[/bold magenta] I've identified cost reduction opportunities across multiple departments...\n")
    
    # Cost analysis progress
    analysis_steps = [
        (15, "📊 Analyzing current operational costs ($500K/month)"),
        (30, "🔍 Identifying inefficiencies in manual processes"),
        (45, "🤖 Planning automation for repetitive tasks"),
        (60, "🏢 Activating Operations Department for efficiency"),
        (75, "📈 Coordinating with HR and IT for process optimization"),
        (90, "💰 Calculating projected savings and implementation timeline"),
        (100, "✅ Cost reduction strategy activated")
    ]
    
    for progress, message in analysis_steps:
        console.print(f"📊 Progress: {progress}% - {message}")
        await asyncio.sleep(0.7)
    
    # Show cost breakdown analysis
    cost_table = Table(title="Cost Reduction Analysis")
    cost_table.add_column("Department", style="cyan")
    cost_table.add_column("Current Cost", style="red")
    cost_table.add_column("Automation Savings", style="green")
    cost_table.add_column("Efficiency Gain", style="yellow")
    
    cost_table.add_row("HR Operations", "$80K/month", "$24K/month", "30% faster hiring")
    cost_table.add_row("Customer Service", "$120K/month", "$36K/month", "50% fewer manual tickets")
    cost_table.add_row("Data Processing", "$60K/month", "$24K/month", "80% automated reports")
    cost_table.add_row("Administrative", "$90K/month", "$18K/month", "40% less manual work")
    cost_table.add_row("[bold]Total", "[bold]$350K/month", "[bold]$102K/month", "[bold]20.4% reduction")
    
    console.print(cost_table)
    
    # Show department coordination
    console.print(Panel(
        "[bold green]🏢 Multi-Department Coordination:[/bold green]\n\n"
        "• [bold]Operations Dept:[/bold] Process automation and workflow optimization\n"
        "• [bold]HR Dept:[/bold] Automated recruiting and onboarding systems\n"
        "• [bold]IT Dept:[/bold] Infrastructure optimization and tool consolidation\n"
        "• [bold]Finance Dept:[/bold] Automated reporting and expense tracking\n\n"
        "💡 [bold]Smart Coordination:[/bold] Departments share data and optimize together",
        style="green"
    ))
    
    # Simulate implementation progress
    console.print("\n[bold yellow]⚙️  Implementing cost reduction measures...[/bold yellow]")
    
    implementation_updates = [
        "🤖 HR: Automated candidate screening (saves 15 hours/week)",
        "📞 Customer Service: Chatbot handling 60% of routine inquiries",
        "📊 Finance: Automated expense reporting (saves 8 hours/week)",
        "💻 IT: Consolidated 5 tools into 1 platform (saves $12K/month)",
        "📈 Operations: Workflow automation reduces processing time by 45%"
    ]
    
    for update in implementation_updates:
        await asyncio.sleep(1)
        console.print(f"  {update}")
    
    # Show savings projection
    savings_table = Table(title="Projected Monthly Savings")
    savings_table.add_column("Category", style="cyan")
    savings_table.add_column("Savings", style="green")
    savings_table.add_column("Implementation", style="yellow")
    
    savings_table.add_row("Labor Cost Reduction", "$78K", "✅ Active")
    savings_table.add_row("Tool Consolidation", "$15K", "✅ Active") 
    savings_table.add_row("Process Efficiency", "$9K", "✅ Active")
    savings_table.add_row("[bold]Total Monthly Savings", "[bold]$102K", "[bold]20.4% reduction")
    
    console.print(savings_table)
    
    # Show business impact
    console.print(Panel(
        "[bold green]💰 Business Impact Summary:[/bold green]\n\n"
        "• [bold]Cost Reduction:[/bold] $102K/month ($1.2M annually)\n"
        "• [bold]Target Achievement:[/bold] 102% of 20% reduction goal\n"
        "• [bold]Efficiency Gains:[/bold] 40% improvement in operational speed\n"
        "• [bold]Employee Satisfaction:[/bold] Less repetitive work, more strategic focus\n"
        "• [bold]ROI Timeline:[/bold] Implementation cost recovered in 2 months\n\n"
        "🎯 [bold]Strategic Value:[/bold] Sustainable, scalable cost optimization!",
        style="green"
    ))
    
    # Educational insights
    console.print(Panel(
        "[bold blue]🎓 Key Learning: Cross-Department Optimization[/bold blue]\n\n"
        "[bold]Traditional Approach:[/bold]\n"
        "• Department silos optimize independently\n"
        "• Limited visibility into cross-department impacts\n"
        "• Suboptimal overall results\n\n"
        "[bold]Jarvis Approach:[/bold]\n"
        "• Holistic view of entire organization\n"
        "• Coordinated optimization across departments\n"
        "• Synergistic effects amplify savings\n"
        "• Sustainable long-term efficiency gains",
        style="dim"
    ))
    
    console.input("\n[dim]Press Enter to continue...[/dim]")


async def business_demo_mode(jarvis: Jarvis, session_id: str):
    """Business demo mode showing sales growth scenario."""
    console.clear()
    
    console.print(Panel(
        "[bold blue]💼 Business Demo: Sales Growth[/bold blue]\n\n"
        "Experience how Jarvis coordinates departments to achieve business goals.\n"
        "Demo scenario: 'Grow sales by 30%' → Sales activation → Show metrics",
        title="Jarvis Business Demo",
        border_style="blue"
    ))
    
    console.print("\n[bold yellow]Demo Scenario:[/bold yellow] Your company wants to grow sales by 30% this quarter")
    console.print("[dim]Watch as Jarvis activates the Sales Department and coordinates multiple agents...[/dim]")
    
    console.input("\n[dim]Press Enter to start the demo...[/dim]")
    
    # Demo: "Grow sales by 30%" request
    demo_request = "Grow sales by 30% this quarter"
    console.print(f"\n[bold cyan]💼 Demo Request:[/bold cyan] {demo_request}")
    
    # Show Jarvis analyzing the request
    console.print("\n📊 Progress: 10% - 🧠 Jarvis analyzing business intent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 20% - 🎯 Intent identified: GROW_REVENUE")
    await asyncio.sleep(1)
    console.print("📊 Progress: 30% - 🏛️ Activating Sales Department...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 40% - 🤖 Initializing Lead Scanner Agent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 50% - 📧 Initializing Outreach Composer Agent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 60% - 📅 Initializing Meeting Scheduler Agent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 70% - 📊 Initializing Pipeline Tracker Agent...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 80% - ⚙️ Configuring department coordination...")
    await asyncio.sleep(1)
    console.print("📊 Progress: 90% - 🚀 Sales Department operational!")
    await asyncio.sleep(1)
    console.print("📊 Progress: 100% - ✅ Business goal workflow activated!")
    
    # Display business KPI dashboard
    console.print("\n" + "="*60)
    console.print("[bold green]🎯 SALES DEPARTMENT ACTIVATED[/bold green]")
    console.print("="*60)
    
    # Show metrics updating
    metrics_table = Table(title="Live Business KPIs")
    metrics_table.add_column("Metric", style="cyan")
    metrics_table.add_column("Current", style="yellow")
    metrics_table.add_column("Target", style="green")
    metrics_table.add_column("Progress", style="blue")
    
    metrics_table.add_row("Monthly Leads", "45", "100", "45%")
    metrics_table.add_row("Meetings Booked", "12", "20", "60%")
    metrics_table.add_row("Pipeline Value", "$125K", "$200K", "62%")
    metrics_table.add_row("Conversion Rate", "15%", "20%", "75%")
    
    console.print(metrics_table)
    
    console.print("\n[bold blue]🤖 Active Sales Agents:[/bold blue]")
    console.print("• 🔍 Lead Scanner Agent: Monitoring LinkedIn, Sales Navigator")
    console.print("• 📧 Outreach Composer Agent: Generating personalized emails")
    console.print("• 📅 Meeting Scheduler Agent: Coordinating calendars")
    console.print("• 📊 Pipeline Tracker Agent: Monitoring CRM, tracking deals")
    
    console.print("\n[bold green]📈 Projected Impact:[/bold green]")
    console.print("• Lead generation: +120% (estimated 25 new leads/week)")
    console.print("• Meeting booking: +85% (estimated 8 additional meetings/week)")
    console.print("• Pipeline velocity: +40% (faster deal progression)")
    console.print("• Overall sales growth: +30% (target achievement likely)")
    
    console.print("\n[bold yellow]⚡ Real-time Activities:[/bold yellow]")
    console.print("• Lead Scanner found 8 new qualified prospects")
    console.print("• Outreach Composer sent 15 personalized emails")
    console.print("• Meeting Scheduler booked 3 discovery calls")
    console.print("• Pipeline Tracker identified 2 at-risk deals")
    
    console.input("\n[dim]Press Enter to see department coordination...[/dim]")
    
    # Show department coordination
    console.print("\n[bold blue]🔄 Department Coordination in Action:[/bold blue]")
    console.print("1. 🔍 Lead Scanner → 📧 Outreach Composer: 'New qualified lead: TechCorp VP Engineering'")
    console.print("2. 📧 Outreach Composer → 📅 Meeting Scheduler: 'Positive response from TechCorp, needs meeting'")
    console.print("3. 📅 Meeting Scheduler → 📊 Pipeline Tracker: 'Demo scheduled for $50K opportunity'")
    console.print("4. 📊 Pipeline Tracker → 🔍 Lead Scanner: 'Focus on enterprise accounts like TechCorp'")
    
    console.print("\n[bold green]🎯 Business Impact Tracking:[/bold green]")
    console.print("• Automation time saved: 160 hours/month")
    console.print("• Cost per lead reduced: $150 → $85 (43% improvement)")
    console.print("• Sales cycle shortened: 65 → 45 days (31% faster)")
    console.print("• Team productivity increased: +75% effective selling time")
    
    console.input("\n[dim]Press Enter to continue...[/dim]")
    
    # Show next quarter projections
    console.print("\n[bold magenta]🔮 AI-Powered Forecasting:[/bold magenta]")
    console.print("Based on current agent performance and market conditions:")
    console.print("• Q1 sales target: $500K (90% confidence)")
    console.print("• Lead quality score: 8.5/10 (improving)")
    console.print("• Pipeline health: Excellent (low risk)")
    console.print("• Recommended actions: Scale outreach, hire 1 sales rep")
    
    console.print(Panel(
        "[bold green]🎉 Demo Complete![/bold green]\n\n"
        "This is the power of Jarvis:\n"
        "• [bold]Business Intent Understanding:[/bold] 'Grow sales by 30%' → Department activation\n"
        "• [bold]Autonomous Coordination:[/bold] 4 agents working together seamlessly\n"
        "• [bold]Real-time Metrics:[/bold] Live KPI tracking and business impact\n"
        "• [bold]Intelligent Forecasting:[/bold] AI-driven predictions and recommendations\n\n"
        "Ready to activate your own departments? Try: 'Reduce operational costs by 20%'",
        title="Jarvis Business Demo Summary",
        border_style="green"
    ))


def main():
    """Main entry point with argument parsing."""
    parser = argparse.ArgumentParser(description="HeyJarvis AI Agent Orchestrator")
    parser.add_argument("--demo", action="store_true", help="Run in demo mode")
    parser.add_argument("--jarvis", action="store_true", 
                       help="Enable business-level orchestration with Jarvis")
    args = parser.parse_args()
    
    if args.demo:
        asyncio.run(demo_mode())
    elif args.jarvis:
        asyncio.run(jarvis_mode())
    else:
        asyncio.run(chat_interface())


if __name__ == "__main__":
    main()