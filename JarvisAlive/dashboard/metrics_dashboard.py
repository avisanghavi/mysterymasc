#!/usr/bin/env python3
"""
Rich CLI Dashboard for HeyJarvis Sales Metrics
Provides real-time visualization of sales department performance
"""

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.align import Align
from rich.columns import Columns
from datetime import datetime, timedelta
import asyncio
from typing import Dict, Optional, List
import json
import csv
import os
import sys
import logging

# Optional Redis support
try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("Redis not available - using mock data mode")


class MetricsDashboard:
    """Rich CLI Dashboard for HeyJarvis Sales Metrics"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.console = Console()
        self.redis_client = None
        self.redis_url = redis_url
        self.running = False
        self.session_id = None
        self.start_time = datetime.now()
        self.mock_mode = not REDIS_AVAILABLE
        
        # Mock data for testing
        self.mock_metrics = {
            "leads_generated": 47,
            "leads_qualified": 23,
            "messages_composed": 15,
            "emails_sent": 12,
            "responses_received": 3,
            "meetings_booked": 2,
            "total_workflows_executed": 8,
            "average_execution_time": 2.3,
            "success_rate": 87.5,
            "personalization_score": 0.76,
            "response_rate": 0.25,
            "active_workflows": 2
        }
        
        self.mock_workflows = [
            {
                "name": "Lead Generation",
                "status": "running",
                "progress": 65,
                "elapsed_time": 12.4,
                "eta": 6.2
            },
            {
                "name": "Quick Wins",
                "status": "completed",
                "progress": 100,
                "elapsed_time": 8.7,
                "eta": 0
            },
            {
                "name": "Full Outreach",
                "status": "queued",
                "progress": 0,
                "elapsed_time": 0,
                "eta": 45.0
            }
        ]
        
        self.mock_current_task = {
            "name": "Scanning SaaS CTOs",
            "status": "In Progress",
            "current_step": 3,
            "total_steps": 5,
            "progress": 60,
            "message": "Processing 25 potential leads...",
            "details": "Found 15 qualifying leads so far"
        }

    async def initialize(self, session_id: str):
        """Initialize dashboard with session"""
        self.session_id = session_id
        
        if REDIS_AVAILABLE and not self.mock_mode:
            try:
                self.redis_client = redis.from_url(self.redis_url)
                await self.redis_client.ping()
                self.console.print(f"[green]Connected to Redis: {self.redis_url}[/green]")
            except Exception as e:
                self.console.print(f"[yellow]Redis connection failed, using mock mode: {e}[/yellow]")
                self.mock_mode = True
        else:
            self.console.print("[yellow]Using mock data mode[/yellow]")

    def create_layout(self) -> Layout:
        """Create dashboard layout"""
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=4),
            Layout(name="body"),
            Layout(name="footer", size=3)
        )
        
        layout["body"].split_row(
            Layout(name="left_panel", ratio=1),
            Layout(name="right_panel", ratio=2)
        )
        
        layout["left_panel"].split_column(
            Layout(name="stats", ratio=1),
            Layout(name="performance", ratio=1)
        )
        
        layout["right_panel"].split_column(
            Layout(name="workflows", ratio=1),
            Layout(name="progress", ratio=1)
        )
        
        return layout

    def create_header(self) -> Panel:
        """Create header with title and session info"""
        uptime = datetime.now() - self.start_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        header_text = Text()
        header_text.append("🤖 ", style="bold blue")
        header_text.append("HeyJarvis Sales Dashboard", style="bold cyan")
        header_text.append(" 📊", style="bold blue")
        
        info_text = f"\nSession: {self.session_id or 'demo'} | "
        info_text += f"Time: {datetime.now().strftime('%H:%M:%S')} | "
        info_text += f"Uptime: {uptime_str}"
        
        if self.mock_mode:
            info_text += " | [yellow]DEMO MODE[/yellow]"
        
        header_content = f"{Align.center(header_text)}\n{info_text}"
        
        return Panel(
            header_content,
            style="white on blue",
            border_style="bright_blue"
        )

    def create_stats_panel(self, metrics: Dict) -> Panel:
        """Create statistics panel"""
        stats_table = Table(show_header=False, box=None, padding=(0, 1))
        stats_table.add_column("Metric", style="cyan", width=18)
        stats_table.add_column("Value", style="green bold", justify="right")
        
        # Core metrics
        stats_table.add_row("📈 Leads Generated", str(metrics.get("leads_generated", 0)))
        stats_table.add_row("🎯 Leads Qualified", str(metrics.get("leads_qualified", 0)))
        stats_table.add_row("✉️ Messages Composed", str(metrics.get("messages_composed", 0)))
        stats_table.add_row("📤 Emails Sent", str(metrics.get("emails_sent", 0)))
        stats_table.add_row("📥 Responses", str(metrics.get("responses_received", 0)))
        stats_table.add_row("🤝 Meetings Booked", str(metrics.get("meetings_booked", 0)))
        stats_table.add_row("🔄 Workflows Run", str(metrics.get("total_workflows_executed", 0)))
        
        return Panel(
            stats_table, 
            title="[bold cyan]📊 Key Metrics[/bold cyan]", 
            border_style="cyan"
        )

    def create_performance_panel(self, metrics: Dict) -> Panel:
        """Create performance metrics panel"""
        perf_table = Table(show_header=False, box=None, padding=(0, 1))
        perf_table.add_column("Metric", style="magenta", width=18)
        perf_table.add_column("Value", style="yellow bold", justify="right")
        
        # Performance metrics
        success_rate = metrics.get("success_rate", 0)
        personalization = metrics.get("personalization_score", 0) * 100
        response_rate = metrics.get("response_rate", 0) * 100
        avg_time = metrics.get("average_execution_time", 0)
        
        perf_table.add_row("✅ Success Rate", f"{success_rate:.1f}%")
        perf_table.add_row("🎨 Personalization", f"{personalization:.1f}%")
        perf_table.add_row("📞 Response Rate", f"{response_rate:.1f}%")
        perf_table.add_row("⏱️ Avg Time", f"{avg_time:.1f}s")
        
        # Add performance indicators
        if success_rate >= 90:
            perf_table.add_row("🏆 Status", "[green]Excellent[/green]")
        elif success_rate >= 75:
            perf_table.add_row("🏆 Status", "[yellow]Good[/yellow]")
        else:
            perf_table.add_row("🏆 Status", "[red]Needs Attention[/red]")
        
        return Panel(
            perf_table,
            title="[bold magenta]⚡ Performance[/bold magenta]",
            border_style="magenta"
        )

    def create_workflow_panel(self, workflows: List[Dict]) -> Panel:
        """Create active workflows panel"""
        workflow_table = Table()
        workflow_table.add_column("🔄 Workflow", style="cyan", width=16)
        workflow_table.add_column("Status", style="yellow", width=12)
        workflow_table.add_column("Progress", style="green", width=20)
        workflow_table.add_column("Time", style="blue", width=8)
        workflow_table.add_column("ETA", style="magenta", width=8)
        
        for wf in workflows:
            # Status icon and text
            status = wf["status"]
            if status == "running":
                status_display = "🟢 Running"
            elif status == "completed":
                status_display = "✅ Done"
            elif status == "queued":
                status_display = "⏳ Queued"
            elif status == "failed":
                status_display = "❌ Failed"
            else:
                status_display = f"⚪ {status}"
            
            # Progress bar
            progress = wf["progress"]
            bar_length = 15
            filled = int(progress / 100 * bar_length)
            bar = "█" * filled + "░" * (bar_length - filled)
            progress_display = f"[green]{bar}[/green] {progress}%"
            
            # Time formatting
            elapsed = wf["elapsed_time"]
            eta = wf.get("eta", 0)
            
            elapsed_str = f"{elapsed:.1f}s" if elapsed < 60 else f"{elapsed/60:.1f}m"
            eta_str = f"{eta:.1f}s" if eta < 60 else f"{eta/60:.1f}m" if eta > 0 else "-"
            
            workflow_table.add_row(
                wf["name"],
                status_display,
                progress_display,
                elapsed_str,
                eta_str
            )
        
        return Panel(
            workflow_table, 
            title="[bold yellow]🔄 Active Workflows[/bold yellow]", 
            border_style="yellow"
        )

    def create_progress_panel(self, current_task: Optional[Dict]) -> Panel:
        """Create progress panel for current task"""
        if not current_task:
            empty_content = Align.center(
                Text("No active task", style="dim italic")
            )
            return Panel(
                empty_content, 
                title="[bold blue]📋 Current Task[/bold blue]",
                border_style="blue"
            )
        
        # Task name and status
        task_header = Text()
        task_header.append("📋 ", style="blue")
        task_header.append(current_task['name'], style="bold white")
        task_header.append(f" ({current_task['status']})", style="yellow")
        
        # Progress information
        current_step = current_task['current_step']
        total_steps = current_task['total_steps']
        progress = current_task['progress']
        
        step_info = f"Step {current_step} of {total_steps}"
        
        # Progress bar
        bar_length = 30
        filled = int(progress / 100 * bar_length)
        progress_bar = "█" * filled + "░" * (bar_length - filled)
        
        # Combine content
        content = f"""{task_header}

[dim]Steps:[/dim] {step_info}
[dim]Progress:[/dim] [green]{progress_bar}[/green] {progress}%

[dim]Status:[/dim] {current_task['message']}
[dim]Details:[/dim] {current_task.get('details', 'Processing...')}
"""
        
        return Panel(
            content.strip(),
            title="[bold blue]📋 Current Task[/bold blue]",
            border_style="blue"
        )

    def create_footer(self) -> Panel:
        """Create footer with controls"""
        controls = [
            "[yellow]Ctrl+C[/yellow] Exit",
            "[yellow]E[/yellow] Export",
            "[yellow]R[/yellow] Reset",
            "[yellow]S[/yellow] Snapshot"
        ]
        
        footer_text = "[bold]Controls:[/bold] " + " | ".join(controls)
        
        if self.mock_mode:
            footer_text += " | [red]DEMO MODE - No live data[/red]"
        
        return Panel(
            footer_text,
            style="white on grey23",
            border_style="white"
        )

    async def fetch_metrics(self) -> Dict:
        """Fetch current metrics from Redis or return mock data"""
        if self.mock_mode:
            # Simulate changing metrics
            import random
            metrics = self.mock_metrics.copy()
            
            # Add some realistic variance
            metrics["leads_generated"] += random.randint(0, 2)
            metrics["responses_received"] += random.randint(0, 1)
            metrics["success_rate"] = max(70, min(100, metrics["success_rate"] + random.uniform(-2, 2)))
            
            return metrics
        
        try:
            metrics_key = f"session:{self.session_id}:metrics"
            metrics_data = await self.redis_client.get(metrics_key)
            
            if metrics_data:
                return json.loads(metrics_data)
            else:
                return {
                    "leads_generated": 0,
                    "messages_composed": 0,
                    "active_workflows": 0,
                    "success_rate": 100.0
                }
        except Exception as e:
            self.console.print(f"[red]Error fetching metrics: {e}[/red]")
            return self.mock_metrics

    async def fetch_workflows(self) -> List[Dict]:
        """Fetch active workflows"""
        if self.mock_mode:
            # Simulate workflow progress
            import random
            workflows = []
            
            for wf in self.mock_workflows:
                wf_copy = wf.copy()
                if wf_copy["status"] == "running":
                    wf_copy["progress"] = min(100, wf_copy["progress"] + random.randint(0, 5))
                    wf_copy["elapsed_time"] += 1.0
                    wf_copy["eta"] = max(0, wf_copy["eta"] - 1.0)
                    
                    if wf_copy["progress"] >= 100:
                        wf_copy["status"] = "completed"
                        wf_copy["eta"] = 0
                
                workflows.append(wf_copy)
            
            return workflows
        
        try:
            workflows_key = f"session:{self.session_id}:workflows"
            workflows_data = await self.redis_client.get(workflows_key)
            
            if workflows_data:
                return json.loads(workflows_data)
            else:
                return []
        except Exception as e:
            return self.mock_workflows

    async def fetch_current_task(self) -> Optional[Dict]:
        """Fetch current task progress"""
        if self.mock_mode:
            # Simulate task progress
            import random
            task = self.mock_current_task.copy()
            task["progress"] = min(100, task["progress"] + random.randint(0, 3))
            
            if task["progress"] >= 100:
                task["status"] = "Completed"
                task["message"] = "Task completed successfully!"
                task["current_step"] = task["total_steps"]
            elif task["progress"] >= 80:
                task["current_step"] = 4
                task["message"] = "Finalizing results..."
            elif task["progress"] >= 60:
                task["current_step"] = 3
                task["message"] = "Processing 25 potential leads..."
            
            return task
        
        try:
            task_key = f"session:{self.session_id}:current_task"
            task_data = await self.redis_client.get(task_key)
            
            if task_data:
                return json.loads(task_data)
            else:
                return None
        except Exception as e:
            return self.mock_current_task

    async def update_dashboard(self, layout: Layout):
        """Update dashboard with latest data"""
        update_count = 0
        
        while self.running:
            try:
                # Fetch latest data
                metrics = await self.fetch_metrics()
                workflows = await self.fetch_workflows()
                current_task = await self.fetch_current_task()
                
                # Update layout components
                layout["header"].update(self.create_header())
                layout["stats"].update(self.create_stats_panel(metrics))
                layout["performance"].update(self.create_performance_panel(metrics))
                layout["workflows"].update(self.create_workflow_panel(workflows))
                layout["progress"].update(self.create_progress_panel(current_task))
                layout["footer"].update(self.create_footer())
                
                update_count += 1
                
                await asyncio.sleep(1)  # Update every second
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                self.console.print(f"[red]Dashboard error: {e}[/red]")
                await asyncio.sleep(5)

    async def start_live_dashboard(self):
        """Start the live dashboard"""
        self.running = True
        layout = self.create_layout()
        
        # Initialize layout
        layout["header"].update(self.create_header())
        layout["stats"].update(self.create_stats_panel({}))
        layout["performance"].update(self.create_performance_panel({}))
        layout["workflows"].update(self.create_workflow_panel([]))
        layout["progress"].update(self.create_progress_panel(None))
        layout["footer"].update(self.create_footer())
        
        with Live(layout, refresh_per_second=2, screen=True) as live:
            try:
                await self.update_dashboard(layout)
            except KeyboardInterrupt:
                self.running = False
                self.console.print("\n[yellow]Dashboard stopped by user[/yellow]")
            except Exception as e:
                self.console.print(f"\n[red]Dashboard crashed: {e}[/red]")
            finally:
                if self.redis_client:
                    await self.redis_client.close()

    def get_snapshot(self) -> Dict:
        """Get single snapshot of metrics (sync method for compatibility)"""
        async def _get():
            if not self.mock_mode:
                await self.initialize("snapshot")
            
            metrics = await self.fetch_metrics()
            workflows = await self.fetch_workflows()
            current_task = await self.fetch_current_task()
            
            if self.redis_client:
                await self.redis_client.close()
            
            return {
                "metrics": metrics,
                "workflows": workflows,
                "current_task": current_task,
                "timestamp": datetime.now().isoformat()
            }
        
        return asyncio.run(_get())

    async def export_metrics(self, filepath: str, format_type: str = "json"):
        """Export current metrics to file"""
        try:
            metrics = await self.fetch_metrics()
            workflows = await self.fetch_workflows()
            current_task = await self.fetch_current_task()
            
            export_data = {
                "timestamp": datetime.now().isoformat(),
                "session_id": self.session_id,
                "metrics": metrics,
                "workflows": workflows,
                "current_task": current_task,
                "export_format": format_type
            }
            
            if format_type == "json":
                with open(filepath, "w") as f:
                    json.dump(export_data, f, indent=2)
            elif format_type == "csv":
                # Convert metrics to CSV format
                with open(filepath, "w", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Metric", "Value"])
                    for key, value in metrics.items():
                        writer.writerow([key, value])
            
            self.console.print(f"[green]✅ Metrics exported to {filepath}[/green]")
            
        except Exception as e:
            self.console.print(f"[red]❌ Export failed: {e}[/red]")

    async def print_summary(self):
        """Print a summary table of current metrics"""
        try:
            metrics = await self.fetch_metrics()
            
            summary_table = Table(title="🤖 HeyJarvis Sales Metrics Summary")
            summary_table.add_column("📊 Metric", style="cyan", width=20)
            summary_table.add_column("📈 Value", style="green", justify="right", width=15)
            
            for key, value in metrics.items():
                formatted_key = key.replace("_", " ").title()
                if isinstance(value, float):
                    if value < 1:
                        formatted_value = f"{value:.2%}"
                    else:
                        formatted_value = f"{value:.2f}"
                else:
                    formatted_value = str(value)
                
                summary_table.add_row(formatted_key, formatted_value)
            
            self.console.print(summary_table)
            
        except Exception as e:
            self.console.print(f"[red]Error generating summary: {e}[/red]")


# Standalone dashboard script
if __name__ == "__main__":
    async def main():
        if len(sys.argv) < 2:
            print("Usage: python metrics_dashboard.py <session_id> [--export] [--summary]")
            print("Options:")
            print("  --export    Export metrics and exit")
            print("  --summary   Show summary table and exit")
            print("  --mock      Force mock mode")
            sys.exit(1)
        
        session_id = sys.argv[1]
        
        # Parse options
        export_mode = "--export" in sys.argv
        summary_mode = "--summary" in sys.argv
        mock_mode = "--mock" in sys.argv
        
        dashboard = MetricsDashboard()
        
        if mock_mode:
            dashboard.mock_mode = True
        
        await dashboard.initialize(session_id)
        
        if export_mode:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"metrics_export_{session_id}_{timestamp}.json"
            await dashboard.export_metrics(filename)
        elif summary_mode:
            await dashboard.print_summary()
        else:
            dashboard.console.print(f"[bold green]🚀 Starting HeyJarvis Sales Dashboard[/bold green]")
            dashboard.console.print(f"[dim]Session: {session_id}[/dim]")
            await dashboard.start_live_dashboard()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        sys.exit(1)