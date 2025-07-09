#!/usr/bin/env python3
"""
Test Rich rendering and color output
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from metrics_dashboard import MetricsDashboard
import asyncio
from rich.console import Console

async def test_rich_rendering():
    dashboard = MetricsDashboard()
    dashboard.mock_mode = True
    await dashboard.initialize('test')
    
    console = Console()
    
    # Test performance panel with different success rates
    print("Testing performance panel color coding:")
    test_metrics = [
        {'success_rate': 95.0, 'personalization_score': 0.8, 'response_rate': 0.3, 'average_execution_time': 2.5},
        {'success_rate': 80.0, 'personalization_score': 0.7, 'response_rate': 0.2, 'average_execution_time': 3.0},
        {'success_rate': 60.0, 'personalization_score': 0.6, 'response_rate': 0.1, 'average_execution_time': 4.0}
    ]
    
    for i, metrics in enumerate(test_metrics):
        print(f"\nTest {i+1}: Success rate {metrics['success_rate']}%")
        panel = dashboard.create_performance_panel(metrics)
        console.print(panel)
    
    # Test workflow panel
    print("\nTesting workflow panel:")
    test_workflows = [
        {'name': 'Running Task', 'status': 'running', 'progress': 65, 'elapsed_time': 12.4, 'eta': 6.2},
        {'name': 'Completed Task', 'status': 'completed', 'progress': 100, 'elapsed_time': 8.7, 'eta': 0},
        {'name': 'Failed Task', 'status': 'failed', 'progress': 30, 'elapsed_time': 15.0, 'eta': 0},
        {'name': 'Queued Task', 'status': 'queued', 'progress': 0, 'elapsed_time': 0, 'eta': 45.0}
    ]
    
    workflow_panel = dashboard.create_workflow_panel(test_workflows)
    console.print(workflow_panel)

if __name__ == "__main__":
    asyncio.run(test_rich_rendering())