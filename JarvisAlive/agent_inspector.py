#!/usr/bin/env python3
"""Agent Inspector - Debug stored agents in Redis and examine generated code."""

import asyncio
import json
import sys
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
import argparse

import redis.asyncio as redis
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree
from rich.prompt import Prompt

console = Console()

class AgentInspector:
    """Inspector for debugging HeyJarvis agents."""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis_client = None
    
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(self.redis_url)
            await self.redis_client.ping()
            console.print("[green]✓ Connected to Redis[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to connect to Redis: {e}[/red]")
            return False
        return True
    
    async def list_all_agents(self) -> List[Dict[str, Any]]:
        """List all stored agents."""
        try:
            # Look for agent-related keys
            agent_keys = []
            
            # Search for different key patterns
            patterns = [
                "session:*:agent_spec",
                "agent:*",
                "deployed_agent:*",
                "*:agent_spec",
                "session:*"
            ]
            
            for pattern in patterns:
                keys = await self.redis_client.keys(pattern)
                agent_keys.extend(keys)
            
            # Remove duplicates
            agent_keys = list(set(agent_keys))
            
            agents = []
            for key in agent_keys:
                try:
                    data = await self.redis_client.get(key)
                    if data:
                        if isinstance(data, bytes):
                            data = data.decode('utf-8')
                        
                        # Try to parse as JSON
                        try:
                            agent_data = json.loads(data)
                            if isinstance(agent_data, dict):
                                agent_data['_redis_key'] = key.decode('utf-8') if isinstance(key, bytes) else key
                                agents.append(agent_data)
                        except json.JSONDecodeError:
                            # If not JSON, treat as raw data
                            agents.append({
                                '_redis_key': key.decode('utf-8') if isinstance(key, bytes) else key,
                                '_raw_data': data[:500] + "..." if len(data) > 500 else data
                            })
                except Exception as e:
                    console.print(f"[yellow]Warning: Could not read key {key}: {e}[/yellow]")
            
            return agents
            
        except Exception as e:
            console.print(f"[red]Error listing agents: {e}[/red]")
            return []
    
    async def get_session_data(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get specific session data."""
        try:
            # Try different key formats
            possible_keys = [
                f"session:{session_id}",
                f"session:{session_id}:agent_spec",
                f"checkpoint:{session_id}",
                f"agent:{session_id}"
            ]
            
            for key in possible_keys:
                data = await self.redis_client.get(key)
                if data:
                    if isinstance(data, bytes):
                        data = data.decode('utf-8')
                    try:
                        return json.loads(data)
                    except json.JSONDecodeError:
                        return {'_raw_data': data}
            
            return None
            
        except Exception as e:
            console.print(f"[red]Error getting session data: {e}[/red]")
            return None
    
    def display_agents_table(self, agents: List[Dict[str, Any]]):
        """Display agents in a formatted table."""
        if not agents:
            console.print("[yellow]No agents found in Redis[/yellow]")
            return
        
        table = Table(title="Stored Agents", show_header=True, header_style="bold magenta")
        table.add_column("Key", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Status", style="blue")
        table.add_column("Capabilities", style="yellow")
        table.add_column("Code Size", style="red")
        table.add_column("Created", style="dim")
        
        for agent in agents:
            key = agent.get('_redis_key', 'unknown')
            name = agent.get('name', agent.get('agent_spec', {}).get('name', 'N/A'))
            status = agent.get('status', agent.get('deployment_status', 'unknown'))
            
            # Handle different data structures
            capabilities = []
            if 'capabilities' in agent:
                capabilities = agent['capabilities']
            elif 'agent_spec' in agent and 'capabilities' in agent['agent_spec']:
                capabilities = agent['agent_spec']['capabilities']
            
            capabilities_str = ", ".join(capabilities[:3]) if capabilities else "N/A"
            if len(capabilities) > 3:
                capabilities_str += f" (+{len(capabilities)-3} more)"
            
            # Check for generated code
            code_size = "N/A"
            if 'code' in agent and agent['code']:
                code_size = f"{len(agent['code'])} chars"
            elif 'agent_spec' in agent and 'code' in agent['agent_spec'] and agent['agent_spec']['code']:
                code_size = f"{len(agent['agent_spec']['code'])} chars"
            elif '_raw_data' in agent:
                code_size = f"{len(agent['_raw_data'])} chars (raw)"
            
            created = agent.get('created_at', agent.get('timestamp', 'unknown'))
            if created and created != 'unknown':
                try:
                    if 'T' in created:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        created = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            table.add_row(
                key[:40] + "..." if len(key) > 40 else key,
                name[:30] + "..." if len(str(name)) > 30 else str(name),
                str(status),
                capabilities_str,
                code_size,
                str(created)
            )
        
        console.print(table)
    
    def display_agent_details(self, agent: Dict[str, Any]):
        """Display detailed information about a specific agent."""
        key = agent.get('_redis_key', 'unknown')
        
        # Create a tree structure for the agent data
        tree = Tree(f"[bold blue]Agent: {key}[/bold blue]")
        
        # Basic info
        info_branch = tree.add("[bold green]Basic Information[/bold green]")
        name = agent.get('name', agent.get('agent_spec', {}).get('name', 'N/A'))
        info_branch.add(f"Name: {name}")
        info_branch.add(f"Status: {agent.get('status', 'unknown')}")
        info_branch.add(f"Version: {agent.get('version', 'unknown')}")
        
        # Capabilities
        capabilities = agent.get('capabilities', agent.get('agent_spec', {}).get('capabilities', []))
        if capabilities:
            cap_branch = tree.add("[bold yellow]Capabilities[/bold yellow]")
            for cap in capabilities:
                cap_branch.add(cap)
        
        # Integrations
        integrations = agent.get('integrations', agent.get('agent_spec', {}).get('integrations', {}))
        if integrations:
            int_branch = tree.add("[bold cyan]Integrations[/bold cyan]")
            for name, config in integrations.items():
                if isinstance(config, dict):
                    int_branch.add(f"{name}: {config.get('service_name', 'unknown')} ({config.get('auth_type', 'unknown')})")
                else:
                    int_branch.add(f"{name}: {config}")
        
        # Resource limits
        limits = agent.get('resource_limits', agent.get('agent_spec', {}).get('resource_limits', {}))
        if limits:
            limits_branch = tree.add("[bold red]Resource Limits[/bold red]")
            limits_branch.add(f"CPU: {limits.get('cpu', 'unknown')}")
            limits_branch.add(f"Memory: {limits.get('memory', 'unknown')} MB")
            limits_branch.add(f"Timeout: {limits.get('timeout', 'unknown')} seconds")
        
        console.print(tree)
        
        # Show generated code if available
        code = None
        if 'code' in agent and agent['code']:
            code = agent['code']
        elif 'agent_spec' in agent and 'code' in agent['agent_spec'] and agent['agent_spec']['code']:
            code = agent['agent_spec']['code']
        
        if code:
            console.print("\n")
            console.print(Panel(
                Syntax(code, "python", theme="monokai", line_numbers=True),
                title="[bold blue]Generated Code[/bold blue]",
                border_style="blue"
            ))
            
            # Analyze the code
            self.analyze_code(code)
        else:
            console.print("\n[yellow]No generated code found for this agent[/yellow]")
    
    def analyze_code(self, code: str):
        """Analyze the generated code for common issues."""
        console.print("\n")
        analysis = Tree("[bold magenta]Code Analysis[/bold magenta]")
        
        issues = []
        warnings = []
        
        # Check for class definition
        if "class " not in code:
            issues.append("No class definition found")
        elif "SandboxAgent" not in code and "BaseAgent" not in code:
            issues.append("Class does not inherit from SandboxAgent or BaseAgent")
        
        # Check for required imports
        if "from base_agent import" not in code and "import base_agent" not in code:
            issues.append("Missing base_agent import")
        
        # Check for required methods
        required_methods = ["__init__", "initialize", "execute", "cleanup"]
        for method in required_methods:
            if f"def {method}" not in code and f"async def {method}" not in code:
                issues.append(f"Missing required method: {method}")
        
        # Check for syntax issues
        try:
            import ast
            ast.parse(code)
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        except Exception as e:
            warnings.append(f"Parse warning: {e}")
        
        # Check for empty methods
        lines = code.split('\n')
        in_method = False
        method_name = ""
        for i, line in enumerate(lines):
            if "def " in line and ":" in line:
                in_method = True
                method_name = line.strip().split("def ")[1].split("(")[0]
            elif in_method and line.strip() and not line.startswith(' ') and not line.startswith('\t'):
                in_method = False
            elif in_method and i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                if next_line and not next_line.startswith('#') and "pass" not in next_line and not next_line.startswith('"""'):
                    if "def " in next_line or "class " in next_line or not next_line:
                        warnings.append(f"Method {method_name} might be empty")
        
        # Display results
        if issues:
            issues_branch = analysis.add("[bold red]Issues Found[/bold red]")
            for issue in issues:
                issues_branch.add(f"❌ {issue}")
        
        if warnings:
            warnings_branch = analysis.add("[bold yellow]Warnings[/bold yellow]")
            for warning in warnings:
                warnings_branch.add(f"⚠️  {warning}")
        
        if not issues and not warnings:
            analysis.add("[bold green]✓ No obvious issues found[/bold green]")
        
        console.print(analysis)
    
    async def close(self):
        """Close Redis connection."""
        if self.redis_client:
            await self.redis_client.close()

async def main():
    parser = argparse.ArgumentParser(description="HeyJarvis Agent Inspector")
    parser.add_argument("--session", help="Inspect specific session ID")
    parser.add_argument("--redis-url", default="redis://localhost:6379", help="Redis URL")
    parser.add_argument("--list", action="store_true", help="List all agents")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    inspector = AgentInspector(args.redis_url)
    
    if not await inspector.connect():
        return 1
    
    try:
        if args.session:
            # Inspect specific session
            console.print(f"[bold]Inspecting session: {args.session}[/bold]\n")
            session_data = await inspector.get_session_data(args.session)
            if session_data:
                inspector.display_agent_details(session_data)
            else:
                console.print(f"[red]Session {args.session} not found[/red]")
        
        elif args.interactive:
            # Interactive mode
            while True:
                console.print("\n[bold blue]HeyJarvis Agent Inspector[/bold blue]")
                console.print("1. List all agents")
                console.print("2. Inspect specific session")
                console.print("3. Search by keyword")
                console.print("4. Exit")
                
                choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"])
                
                if choice == "1":
                    agents = await inspector.list_all_agents()
                    inspector.display_agents_table(agents)
                    
                    if agents:
                        detail_choice = Prompt.ask("Enter agent number for details (or press Enter to continue)", default="")
                        if detail_choice.isdigit():
                            idx = int(detail_choice) - 1
                            if 0 <= idx < len(agents):
                                inspector.display_agent_details(agents[idx])
                
                elif choice == "2":
                    session_id = Prompt.ask("Enter session ID")
                    session_data = await inspector.get_session_data(session_id)
                    if session_data:
                        inspector.display_agent_details(session_data)
                    else:
                        console.print(f"[red]Session {session_id} not found[/red]")
                
                elif choice == "3":
                    keyword = Prompt.ask("Enter search keyword")
                    agents = await inspector.list_all_agents()
                    filtered_agents = []
                    for agent in agents:
                        agent_str = json.dumps(agent, default=str).lower()
                        if keyword.lower() in agent_str:
                            filtered_agents.append(agent)
                    
                    if filtered_agents:
                        inspector.display_agents_table(filtered_agents)
                    else:
                        console.print(f"[yellow]No agents found matching '{keyword}'[/yellow]")
                
                elif choice == "4":
                    break
        
        else:
            # Default: list all agents
            agents = await inspector.list_all_agents()
            inspector.display_agents_table(agents)
    
    finally:
        await inspector.close()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)