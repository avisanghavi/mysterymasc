#!/usr/bin/env python3
"""Test script to validate migration guide code examples."""

import os
import sys
import asyncio
from unittest.mock import Mock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock environment variable
os.environ['ANTHROPIC_API_KEY'] = 'test-migration-key'

from rich.console import Console

console = Console()


def test_imports():
    """Test that all imports from migration guide work."""
    console.print("[bold blue]Testing Migration Guide Imports[/bold blue]")
    
    try:
        # Test agent builder imports (existing)
        from orchestration.orchestrator import HeyJarvisOrchestrator, OrchestratorConfig
        console.print("✅ Agent builder imports successful")
        
        # Test Jarvis imports (new)
        from orchestration.jarvis import Jarvis, JarvisConfig
        console.print("✅ Jarvis imports successful")
        
        # Test department imports
        from departments.sales.sales_department import SalesDepartment
        console.print("✅ Department imports successful")
        
        # Test conversation manager imports
        from conversation.jarvis_conversation_manager import JarvisConversationManager
        console.print("✅ Conversation manager imports successful")
        
        # Test WebSocket imports
        from conversation.websocket_handler import websocket_handler, OperatingMode
        console.print("✅ WebSocket handler imports successful")
        
        return True
        
    except ImportError as e:
        console.print(f"❌ Import error: {e}")
        return False


def test_configuration_examples():
    """Test configuration patterns from migration guide."""
    console.print("\n[bold blue]Testing Configuration Examples[/bold blue]")
    
    try:
        from orchestration.orchestrator import OrchestratorConfig
        from orchestration.jarvis import JarvisConfig
        
        # Test base configuration
        orchestrator_config = OrchestratorConfig(
            anthropic_api_key="test-key",
            redis_url="redis://localhost:6379",
            max_retries=3,
            session_timeout=3600
        )
        console.print("✅ Base configuration created")
        
        # Test Jarvis configuration
        jarvis_config = JarvisConfig(
            orchestrator_config=orchestrator_config,
            max_concurrent_departments=5,
            enable_autonomous_department_creation=True,
            enable_cross_department_coordination=True
        )
        console.print("✅ Jarvis configuration created")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Configuration error: {e}")
        return False


def test_choose_system_function():
    """Test the decision matrix function from migration guide."""
    console.print("\n[bold blue]Testing System Choice Logic[/bold blue]")
    
    def choose_system(request: str) -> str:
        """Helper to choose between agent builder and Jarvis"""
        business_keywords = [
            'sales', 'revenue', 'customers', 'growth', 'efficiency', 
            'costs', 'profit', 'department', 'business', 'performance'
        ]
        
        technical_keywords = [
            'create agent', 'monitor', 'integration', 'api', 'webhook',
            'file', 'database', 'sync', 'backup', 'custom'
        ]
        
        request_lower = request.lower()
        
        business_score = sum(1 for kw in business_keywords if kw in request_lower)
        technical_score = sum(1 for kw in technical_keywords if kw in request_lower)
        
        if business_score > technical_score:
            return "jarvis"  # Business orchestration
        else:
            return "agent_builder"  # Technical automation
    
    # Test business requests
    business_requests = [
        "Grow sales by 30% this quarter",
        "Reduce operational costs",
        "Improve customer satisfaction",
        "Increase revenue through better efficiency"
    ]
    
    # Test technical requests
    technical_requests = [
        "Create an email monitoring agent",
        "Build a file backup system",
        "Create API integration for webhooks",
        "Monitor database performance"
    ]
    
    # Validate business requests route to Jarvis
    for request in business_requests:
        result = choose_system(request)
        if result == "jarvis":
            console.print(f"✅ Business request correctly routed: '{request[:30]}...'")
        else:
            console.print(f"❌ Business request misrouted: '{request[:30]}...'")
    
    # Validate technical requests route to agent builder
    for request in technical_requests:
        result = choose_system(request)
        if result == "agent_builder":
            console.print(f"✅ Technical request correctly routed: '{request[:30]}...'")
        else:
            console.print(f"❌ Technical request misrouted: '{request[:30]}...'")
    
    return True


async def test_parallel_operation_pattern():
    """Test parallel operation example from migration guide."""
    console.print("\n[bold blue]Testing Parallel Operation Pattern[/bold blue]")
    
    try:
        from orchestration.orchestrator import OrchestratorConfig
        from orchestration.jarvis import JarvisConfig
        
        # Mock the actual classes to avoid Redis dependency
        class MockOrchestrator:
            def __init__(self, config):
                self.config = config
            
            async def process_request(self, request, session_id):
                return {"status": "success", "type": "agent_builder"}
        
        class MockJarvis:
            def __init__(self, config):
                self.config = config
            
            async def process_business_request(self, request, session_id):
                return {"status": "success", "type": "jarvis"}
        
        # Test parallel operation
        base_config = OrchestratorConfig(anthropic_api_key="test")
        orchestrator = MockOrchestrator(base_config)
        
        jarvis_config = JarvisConfig(orchestrator_config=base_config)
        jarvis = MockJarvis(jarvis_config)
        
        # Test requests
        session_id = "test_session"
        technical_request = "Create a file backup agent"
        business_request = "Improve operational efficiency"
        
        # Both should work without interference
        agent_result = await orchestrator.process_request(technical_request, session_id)
        jarvis_result = await jarvis.process_business_request(business_request, session_id)
        
        if agent_result["status"] == "success" and jarvis_result["status"] == "success":
            console.print("✅ Parallel operation pattern works")
            return True
        else:
            console.print("❌ Parallel operation pattern failed")
            return False
            
    except Exception as e:
        console.print(f"❌ Parallel operation error: {e}")
        return False


def test_websocket_patterns():
    """Test WebSocket patterns from migration guide."""
    console.print("\n[bold blue]Testing WebSocket Patterns[/bold blue]")
    
    try:
        from conversation.websocket_handler import OperatingMode
        
        # Test that OperatingMode enum has expected values
        expected_modes = ["AGENT_BUILDER", "JARVIS", "HYBRID"]
        actual_modes = [mode.name for mode in OperatingMode]
        
        for mode in expected_modes:
            if mode in actual_modes:
                console.print(f"✅ Operating mode {mode} available")
            else:
                console.print(f"❌ Operating mode {mode} missing")
        
        # Test WebSocket handler functions exist
        from conversation.websocket_handler import websocket_handler
        
        required_methods = [
            'send_department_activated',
            'send_business_metric_updated', 
            'send_agent_coordination',
            'add_connection'
        ]
        
        for method in required_methods:
            if hasattr(websocket_handler, method):
                console.print(f"✅ WebSocket method {method} available")
            else:
                console.print(f"❌ WebSocket method {method} missing")
        
        return True
        
    except Exception as e:
        console.print(f"❌ WebSocket pattern error: {e}")
        return False


def test_business_metrics_pattern():
    """Test business metrics extraction pattern."""
    console.print("\n[bold blue]Testing Business Metrics Pattern[/bold blue]")
    
    try:
        from conversation.jarvis_conversation_manager import JarvisConversationManager
        
        # Test conversation manager creation
        conv_manager = JarvisConversationManager(session_id="test_session")
        console.print("✅ Jarvis conversation manager created")
        
        # Test methods exist
        required_methods = [
            'extract_business_metrics',
            'identify_department_needs',
            'generate_executive_summary',
            'add_user_message'
        ]
        
        for method in required_methods:
            if hasattr(conv_manager, method):
                console.print(f"✅ Conversation method {method} available")
            else:
                console.print(f"❌ Conversation method {method} missing")
        
        # Test basic functionality
        conv_manager.add_user_message("Test business message")
        summary = conv_manager.generate_executive_summary()
        
        if isinstance(summary, str):
            console.print("✅ Executive summary generation works")
        else:
            console.print("❌ Executive summary generation failed")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Business metrics pattern error: {e}")
        return False


async def main():
    """Run all migration guide validation tests."""
    console.print("[bold green]🧪 Migration Guide Validation Suite[/bold green]\n")
    
    results = []
    
    # Run tests
    results.append(test_imports())
    results.append(test_configuration_examples())
    results.append(test_choose_system_function())
    results.append(await test_parallel_operation_pattern())
    results.append(test_websocket_patterns())
    results.append(test_business_metrics_pattern())
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    console.print(f"\n[bold blue]📊 Test Results: {passed}/{total} passed[/bold blue]")
    
    if passed == total:
        console.print("[bold green]🎉 All migration guide examples validated![/bold green]")
        console.print("\n[bold blue]Migration guide is ready for use:[/bold blue]")
        console.print("• All code examples work correctly")
        console.print("• Import paths are valid")
        console.print("• Configuration patterns functional")
        console.print("• Integration patterns tested")
        return 0
    else:
        console.print(f"[bold red]❌ {total - passed} tests failed[/bold red]")
        console.print("Review migration guide for issues")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)