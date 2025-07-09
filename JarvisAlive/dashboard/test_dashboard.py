#!/usr/bin/env python3
"""
Test script for the Rich CLI Dashboard
"""
import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from metrics_dashboard import MetricsDashboard


async def test_dashboard_features():
    """Test dashboard features without live mode"""
    
    print("🧪 Testing HeyJarvis Dashboard Features")
    print("=" * 50)
    
    # Initialize dashboard
    dashboard = MetricsDashboard()
    dashboard.mock_mode = True
    await dashboard.initialize("test_session_demo")
    
    print("✅ Dashboard initialized in mock mode")
    
    # Test 1: Fetch metrics
    print("\n📊 Test 1: Metrics Fetching")
    metrics = await dashboard.fetch_metrics()
    print(f"✅ Fetched {len(metrics)} metrics")
    print(f"   Sample: Leads Generated = {metrics.get('leads_generated', 0)}")
    
    # Test 2: Fetch workflows
    print("\n🔄 Test 2: Workflows Fetching")
    workflows = await dashboard.fetch_workflows()
    print(f"✅ Fetched {len(workflows)} workflows")
    for wf in workflows:
        print(f"   - {wf['name']}: {wf['status']} ({wf['progress']}%)")
    
    # Test 3: Fetch current task
    print("\n📋 Test 3: Current Task Fetching")
    current_task = await dashboard.fetch_current_task()
    if current_task:
        print(f"✅ Current task: {current_task['name']}")
        print(f"   Progress: {current_task['progress']}% ({current_task['status']})")
    
    # Test 4: Layout creation
    print("\n🎨 Test 4: Layout Creation")
    layout = dashboard.create_layout()
    print("✅ Layout created successfully")
    print(f"   Layout sections: {list(layout.map.keys())}")
    
    # Test 5: Panel creation
    print("\n🖼️ Test 5: Panel Creation")
    stats_panel = dashboard.create_stats_panel(metrics)
    perf_panel = dashboard.create_performance_panel(metrics)
    workflow_panel = dashboard.create_workflow_panel(workflows)
    progress_panel = dashboard.create_progress_panel(current_task)
    header_panel = dashboard.create_header()
    footer_panel = dashboard.create_footer()
    
    print("✅ All panels created successfully")
    
    # Test 6: Export functionality
    print("\n💾 Test 6: Export Functionality")
    test_filename = "test_export.json"
    await dashboard.export_metrics(test_filename)
    
    # Check if file was created
    if os.path.exists(test_filename):
        print("✅ Export file created successfully")
        # Clean up
        os.remove(test_filename)
        print("✅ Test file cleaned up")
    
    # Test 7: Summary display
    print("\n📋 Test 7: Summary Display")
    await dashboard.print_summary()
    
    print("\n🎉 All dashboard features tested successfully!")
    print("\n💡 To see the live dashboard, run:")
    print("   python3 metrics_dashboard.py your_session_id --mock")


async def demo_live_dashboard_brief():
    """Brief demo of live dashboard (5 seconds)"""
    print("\n🚀 Starting 5-second live dashboard demo...")
    print("   (Press Ctrl+C to exit early)")
    
    dashboard = MetricsDashboard()
    dashboard.mock_mode = True
    await dashboard.initialize("demo_session")
    
    # Run for 5 seconds then auto-stop
    dashboard.running = True
    layout = dashboard.create_layout()
    
    from rich.live import Live
    
    with Live(layout, refresh_per_second=2, screen=True) as live:
        try:
            # Update loop with timeout
            for i in range(10):  # 5 seconds at 0.5s intervals
                metrics = await dashboard.fetch_metrics()
                workflows = await dashboard.fetch_workflows()
                current_task = await dashboard.fetch_current_task()
                
                layout["header"].update(dashboard.create_header())
                layout["stats"].update(dashboard.create_stats_panel(metrics))
                layout["performance"].update(dashboard.create_performance_panel(metrics))
                layout["workflows"].update(dashboard.create_workflow_panel(workflows))
                layout["progress"].update(dashboard.create_progress_panel(current_task))
                layout["footer"].update(dashboard.create_footer())
                
                await asyncio.sleep(0.5)
                
        except KeyboardInterrupt:
            pass
    
    print("\n✅ Live dashboard demo completed!")


if __name__ == "__main__":
    async def main():
        await test_dashboard_features()
        
        # Ask user if they want to see live demo
        try:
            response = input("\n🎮 Would you like to see a 5-second live dashboard demo? (y/n): ")
            if response.lower().startswith('y'):
                await demo_live_dashboard_brief()
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Test stopped by user")
    except Exception as e:
        print(f"❌ Test error: {e}")
        sys.exit(1)