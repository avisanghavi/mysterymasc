#!/usr/bin/env python3
"""Container Debugger - Debug Docker containers running HeyJarvis agents."""

import asyncio
import sys
import os
import json
import argparse
from typing import Dict, Any, List, Optional
from datetime import datetime

import docker
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
from rich.tree import Tree
from rich.prompt import Prompt

console = Console()

class ContainerDebugger:
    """Debugger for HeyJarvis Docker containers."""
    
    def __init__(self):
        try:
            self.docker_client = docker.from_env()
            console.print("[green]✓ Connected to Docker[/green]")
        except Exception as e:
            console.print(f"[red]✗ Failed to connect to Docker: {e}[/red]")
            self.docker_client = None
    
    def list_heyjarvis_containers(self) -> List[docker.models.containers.Container]:
        """List all HeyJarvis-related containers."""
        if not self.docker_client:
            return []
        
        containers = []
        try:
            # Get all containers (including stopped ones)
            all_containers = self.docker_client.containers.list(all=True)
            
            for container in all_containers:
                # Check if container is related to HeyJarvis
                if (container.image.tags and 
                    any('heyjarvis' in tag.lower() for tag in container.image.tags)) or \
                   ('heyjarvis' in container.name.lower()):
                    containers.append(container)
            
            return containers
            
        except Exception as e:
            console.print(f"[red]Error listing containers: {e}[/red]")
            return []
    
    def display_containers_table(self, containers: List[docker.models.containers.Container]):
        """Display containers in a formatted table."""
        if not containers:
            console.print("[yellow]No HeyJarvis containers found[/yellow]")
            return
        
        table = Table(title="HeyJarvis Containers", show_header=True, header_style="bold magenta")
        table.add_column("Container ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="green")
        table.add_column("Image", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="dim")
        table.add_column("Ports", style="purple")
        
        for container in containers:
            # Format creation time
            created = container.attrs.get('Created', '')
            if created:
                try:
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    created = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            
            # Format ports
            ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
            port_str = ", ".join([f"{k}" for k in ports.keys()]) if ports else "None"
            
            # Status with color coding
            status = container.status
            if status == 'running':
                status = f"[green]{status}[/green]"
            elif status == 'exited':
                exit_code = container.attrs.get('State', {}).get('ExitCode', 0)
                if exit_code == 0:
                    status = f"[yellow]{status} ({exit_code})[/yellow]"
                else:
                    status = f"[red]{status} ({exit_code})[/red]"
            else:
                status = f"[blue]{status}[/blue]"
            
            table.add_row(
                container.short_id,
                container.name,
                container.image.tags[0] if container.image.tags else container.image.id[:12],
                status,
                created,
                port_str[:30] + "..." if len(port_str) > 30 else port_str
            )
        
        console.print(table)
    
    def get_container_logs(self, container: docker.models.containers.Container, tail: int = 100) -> str:
        """Get container logs."""
        try:
            logs = container.logs(tail=tail, timestamps=True).decode('utf-8')
            return logs
        except Exception as e:
            return f"Error getting logs: {e}"
    
    def inspect_container_files(self, container: docker.models.containers.Container) -> Dict[str, Any]:
        """Inspect files inside the container."""
        inspection = {
            'agent_files': [],
            'python_files': [],
            'config_files': [],
            'errors': []
        }
        
        try:
            # Common paths to check
            paths_to_check = [
                '/app/',
                '/app/agent.py',
                '/app/main.py',
                '/app/base_agent.py',
                '/tmp/',
                '/home/',
                '/'
            ]
            
            for path in paths_to_check:
                try:
                    # Use exec to list directory contents
                    result = container.exec_run(f'ls -la {path}', workdir='/')
                    if result.exit_code == 0:
                        output = result.output.decode('utf-8')
                        inspection['agent_files'].append({
                            'path': path,
                            'contents': output,
                            'type': 'directory_listing'
                        })
                        
                        # If it's a Python file, try to get its contents
                        if path.endswith('.py'):
                            file_result = container.exec_run(f'cat {path}')
                            if file_result.exit_code == 0:
                                file_content = file_result.output.decode('utf-8')
                                inspection['python_files'].append({
                                    'path': path,
                                    'content': file_content,
                                    'size': len(file_content)
                                })
                except Exception as e:
                    inspection['errors'].append(f"Error checking {path}: {e}")
            
            # Try to find Python files
            try:
                find_result = container.exec_run('find / -name "*.py" -type f 2>/dev/null | head -20')
                if find_result.exit_code == 0:
                    python_files = find_result.output.decode('utf-8').strip().split('\n')
                    for py_file in python_files:
                        if py_file and py_file not in [f['path'] for f in inspection['python_files']]:
                            try:
                                content_result = container.exec_run(f'cat "{py_file}"')
                                if content_result.exit_code == 0:
                                    content = content_result.output.decode('utf-8')
                                    inspection['python_files'].append({
                                        'path': py_file,
                                        'content': content,
                                        'size': len(content)
                                    })
                            except:
                                pass
            except Exception as e:
                inspection['errors'].append(f"Error finding Python files: {e}")
                
        except Exception as e:
            inspection['errors'].append(f"General inspection error: {e}")
        
        return inspection
    
    def analyze_container_crash(self, container: docker.models.containers.Container):
        """Analyze why a container crashed."""
        console.print(f"\n[bold blue]Analyzing crashed container: {container.name}[/bold blue]\n")
        
        # Basic container info
        info_tree = Tree("[bold green]Container Information[/bold green]")
        info_tree.add(f"ID: {container.id[:12]}")
        info_tree.add(f"Name: {container.name}")
        info_tree.add(f"Status: {container.status}")
        
        state = container.attrs.get('State', {})
        if state:
            info_tree.add(f"Exit Code: {state.get('ExitCode', 'unknown')}")
            info_tree.add(f"Error: {state.get('Error', 'none')}")
            info_tree.add(f"Started At: {state.get('StartedAt', 'unknown')}")
            info_tree.add(f"Finished At: {state.get('FinishedAt', 'unknown')}")
        
        console.print(info_tree)
        
        # Container logs
        console.print("\n[bold yellow]Container Logs (last 50 lines):[/bold yellow]")
        logs = self.get_container_logs(container, tail=50)
        if logs:
            console.print(Panel(
                Text(logs, style="dim"),
                title="Logs",
                border_style="yellow"
            ))
        else:
            console.print("[red]No logs available[/red]")
        
        # File inspection
        console.print("\n[bold cyan]File Inspection:[/bold cyan]")
        inspection = self.inspect_container_files(container)
        
        if inspection['errors']:
            error_tree = Tree("[bold red]Inspection Errors[/bold red]")
            for error in inspection['errors']:
                error_tree.add(error)
            console.print(error_tree)
        
        if inspection['python_files']:
            console.print("\n[bold magenta]Python Files Found:[/bold magenta]")
            py_table = Table()
            py_table.add_column("Path", style="cyan")
            py_table.add_column("Size", style="green")
            py_table.add_column("Has Class", style="yellow")
            py_table.add_column("Has SandboxAgent", style="blue")
            
            for py_file in inspection['python_files']:
                path = py_file['path']
                size = f"{py_file['size']} chars"
                content = py_file['content']
                
                has_class = "✓" if "class " in content else "✗"
                has_sandbox = "✓" if "SandboxAgent" in content or "BaseAgent" in content else "✗"
                
                py_table.add_row(path, size, has_class, has_sandbox)
            
            console.print(py_table)
            
            # Show content of suspected agent files
            for py_file in inspection['python_files']:
                if ('agent' in py_file['path'].lower() or 
                    'SandboxAgent' in py_file['content'] or 
                    'BaseAgent' in py_file['content']):
                    
                    console.print(f"\n[bold blue]Content of {py_file['path']}:[/bold blue]")
                    console.print(Panel(
                        Syntax(py_file['content'], "python", theme="monokai", line_numbers=True),
                        title=f"Agent File: {py_file['path']}",
                        border_style="blue"
                    ))
                    
                    # Analyze the code
                    self.analyze_agent_code(py_file['content'], py_file['path'])
        
        # Directory listings
        if inspection['agent_files']:
            console.print("\n[bold green]Directory Listings:[/bold green]")
            for listing in inspection['agent_files']:
                if listing['type'] == 'directory_listing':
                    console.print(f"\n[cyan]{listing['path']}:[/cyan]")
                    console.print(Text(listing['contents'], style="dim"))
    
    def analyze_agent_code(self, code: str, file_path: str):
        """Analyze agent code for issues."""
        console.print(f"\n[bold magenta]Code Analysis for {file_path}:[/bold magenta]")
        
        issues = []
        warnings = []
        good_signs = []
        
        # Check for class definition
        if "class " not in code:
            issues.append("No class definition found")
        else:
            class_lines = [line for line in code.split('\n') if 'class ' in line and ':' in line]
            if class_lines:
                class_line = class_lines[0]
                if "SandboxAgent" in class_line or "BaseAgent" in class_line:
                    good_signs.append("Class inherits from SandboxAgent/BaseAgent")
                else:
                    issues.append("Class does not inherit from SandboxAgent or BaseAgent")
                
                # Extract class name
                try:
                    class_name = class_line.split("class ")[1].split("(")[0].strip()
                    good_signs.append(f"Found class: {class_name}")
                except:
                    warnings.append("Could not parse class name")
        
        # Check for required imports
        required_imports = ["base_agent", "SandboxAgent"]
        has_import = False
        for imp in required_imports:
            if imp in code:
                has_import = True
                good_signs.append(f"Found import: {imp}")
                break
        
        if not has_import:
            issues.append("Missing base_agent import")
        
        # Check for required methods
        required_methods = ["__init__", "initialize", "execute", "cleanup"]
        for method in required_methods:
            if f"def {method}" in code or f"async def {method}" in code:
                good_signs.append(f"Found method: {method}")
            else:
                issues.append(f"Missing required method: {method}")
        
        # Check for syntax issues
        try:
            import ast
            ast.parse(code)
            good_signs.append("Code has valid Python syntax")
        except SyntaxError as e:
            issues.append(f"Syntax error: {e}")
        except Exception as e:
            warnings.append(f"Parse warning: {e}")
        
        # Check for common patterns
        if "super().__init__()" in code:
            good_signs.append("Calls super().__init__()")
        else:
            warnings.append("Does not call super().__init__() in __init__")
        
        if "self.name =" in code:
            good_signs.append("Sets self.name")
        else:
            warnings.append("Does not set self.name")
        
        # Display analysis
        analysis_tree = Tree("[bold magenta]Analysis Results[/bold magenta]")
        
        if good_signs:
            good_branch = analysis_tree.add("[bold green]✓ Good Signs[/bold green]")
            for sign in good_signs:
                good_branch.add(sign)
        
        if warnings:
            warn_branch = analysis_tree.add("[bold yellow]⚠️  Warnings[/bold yellow]")
            for warning in warnings:
                warn_branch.add(warning)
        
        if issues:
            issue_branch = analysis_tree.add("[bold red]❌ Issues[/bold red]")
            for issue in issues:
                issue_branch.add(issue)
        
        console.print(analysis_tree)
        
        # Provide recommendations
        if issues:
            console.print("\n[bold red]Recommendations:[/bold red]")
            if "No class definition found" in issues:
                console.print("• The file needs a class definition inheriting from SandboxAgent")
            if "Missing base_agent import" in issues:
                console.print("• Add: from base_agent import SandboxAgent")
            if any("Missing required method" in issue for issue in issues):
                console.print("• Implement all required methods: __init__, initialize, execute, cleanup")
            if any("Syntax error" in issue for issue in issues):
                console.print("• Fix Python syntax errors before deployment")

def main():
    parser = argparse.ArgumentParser(description="HeyJarvis Container Debugger")
    parser.add_argument("--container", help="Specific container ID or name to debug")
    parser.add_argument("--list", action="store_true", help="List all HeyJarvis containers")
    parser.add_argument("--logs", action="store_true", help="Show logs for containers")
    parser.add_argument("--analyze", action="store_true", help="Analyze crashed containers")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    
    args = parser.parse_args()
    
    debugger = ContainerDebugger()
    
    if not debugger.docker_client:
        return 1
    
    containers = debugger.list_heyjarvis_containers()
    
    if args.container:
        # Debug specific container
        target_container = None
        for container in containers:
            if (container.id.startswith(args.container) or 
                container.name == args.container or
                container.short_id == args.container):
                target_container = container
                break
        
        if target_container:
            debugger.analyze_container_crash(target_container)
        else:
            console.print(f"[red]Container {args.container} not found[/red]")
            debugger.display_containers_table(containers)
        return 0
    
    if args.interactive:
        # Interactive mode
        while True:
            console.print("\n[bold blue]HeyJarvis Container Debugger[/bold blue]")
            debugger.display_containers_table(containers)
            
            if not containers:
                console.print("No containers to debug.")
                break
            
            console.print("\nOptions:")
            console.print("1. Analyze specific container")
            console.print("2. Show logs for container")
            console.print("3. Refresh container list")
            console.print("4. Exit")
            
            choice = Prompt.ask("Choose an option", choices=["1", "2", "3", "4"])
            
            if choice == "1":
                container_id = Prompt.ask("Enter container ID or name")
                target_container = None
                for container in containers:
                    if (container.id.startswith(container_id) or 
                        container.name == container_id or
                        container.short_id == container_id):
                        target_container = container
                        break
                
                if target_container:
                    debugger.analyze_container_crash(target_container)
                else:
                    console.print(f"[red]Container {container_id} not found[/red]")
            
            elif choice == "2":
                container_id = Prompt.ask("Enter container ID or name")
                target_container = None
                for container in containers:
                    if (container.id.startswith(container_id) or 
                        container.name == container_id or
                        container.short_id == container_id):
                        target_container = container
                        break
                
                if target_container:
                    logs = debugger.get_container_logs(target_container, tail=100)
                    console.print(Panel(
                        Text(logs, style="dim"),
                        title=f"Logs for {target_container.name}",
                        border_style="blue"
                    ))
                else:
                    console.print(f"[red]Container {container_id} not found[/red]")
            
            elif choice == "3":
                containers = debugger.list_heyjarvis_containers()
            
            elif choice == "4":
                break
    
    else:
        # Default behavior
        debugger.display_containers_table(containers)
        
        if args.analyze:
            # Analyze crashed containers
            crashed_containers = [c for c in containers if c.status == 'exited']
            if crashed_containers:
                console.print(f"\n[bold red]Found {len(crashed_containers)} crashed containers[/bold red]")
                for container in crashed_containers:
                    debugger.analyze_container_crash(container)
            else:
                console.print("\n[green]No crashed containers found[/green]")
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)