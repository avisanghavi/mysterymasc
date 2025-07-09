#!/usr/bin/env python3
"""
Test color coding implementation
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from metrics_dashboard import MetricsDashboard
import asyncio

async def test_color_coding():
    dashboard = MetricsDashboard()
    dashboard.mock_mode = True
    await dashboard.initialize('test')
    
    # Test different success rates for color coding
    test_metrics = [
        {'success_rate': 95.0},  # Should be green
        {'success_rate': 80.0},  # Should be yellow  
        {'success_rate': 60.0}   # Should be red
    ]
    
    for i, metrics in enumerate(test_metrics):
        panel = dashboard.create_performance_panel(metrics)
        panel_str = str(panel)
        
        print(f'Test {i+1}: Success rate {metrics["success_rate"]}%')
        if 'green' in panel_str:
            print('   ✅ Contains green color coding')
        elif 'yellow' in panel_str:
            print('   ✅ Contains yellow color coding')
        elif 'red' in panel_str:
            print('   ✅ Contains red color coding')
        else:
            print('   ❌ No color coding found')
            
        # Check status indicators
        if 'Excellent' in panel_str:
            print('   ✅ Shows "Excellent" status')
        elif 'Good' in panel_str:
            print('   ✅ Shows "Good" status')
        elif 'Needs Attention' in panel_str:
            print('   ✅ Shows "Needs Attention" status')
            
        print()

if __name__ == "__main__":
    asyncio.run(test_color_coding())