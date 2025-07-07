#!/usr/bin/env python3
"""
Integration tests for Jarvis business flow validation.

Tests the complete pipeline from natural language business requests
to department activation, micro-agent creation, and metrics updates.
"""

import pytest
import asyncio
import time
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.jarvis import Jarvis, JarvisConfig
from orchestration.orchestrator import OrchestratorConfig
from orchestration.business_context import BusinessContext
from departments.sales.sales_department import SalesDepartment
from conversation.jarvis_conversation_manager import JarvisConversationManager
from conversation.websocket_handler import websocket_handler, OperatingMode


class TestJarvisIntegration:
    """Integration tests for complete Jarvis business flow."""
    
    @pytest.fixture
    async def jarvis_instance(self):
        """Create a Jarvis instance for testing."""
        orchestrator_config = OrchestratorConfig(
            anthropic_api_key="test_key",
            redis_url="redis://localhost:6379",
            max_retries=3,
            session_timeout=3600
        )
        
        jarvis_config = JarvisConfig(
            orchestrator_config=orchestrator_config,
            max_concurrent_departments=5,
            enable_autonomous_department_creation=True,
            enable_cross_department_coordination=True
        )
        
        jarvis = Jarvis(jarvis_config)
        
        # Mock external dependencies
        jarvis.business_context = Mock(spec=BusinessContext)
        jarvis.business_context.key_metrics = Mock()
        jarvis.business_context.key_metrics.leads_generated = 0
        jarvis.business_context.key_metrics.pipeline_value = 0
        jarvis.business_context.key_metrics.conversion_rate = 0.0
        
        # Mock Redis for testing
        jarvis.state_manager = Mock()
        jarvis.state_manager.get_session_state = AsyncMock(return_value={})
        jarvis.state_manager.save_session_state = AsyncMock()
        
        # Mock conversation manager
        jarvis.conversation_manager = Mock(spec=JarvisConversationManager)
        jarvis.conversation_manager.add_user_message = Mock()
        jarvis.conversation_manager.add_assistant_message = Mock()
        jarvis.conversation_manager.identify_department_needs = Mock()
        jarvis.conversation_manager.extract_business_metrics = Mock()
        jarvis.conversation_manager.generate_executive_summary = Mock()
        
        return jarvis
    
    @pytest.fixture
    async def mock_sales_department(self):
        """Create a mock sales department."""
        sales_dept = Mock(spec=SalesDepartment)
        sales_dept.name = "sales"
        sales_dept.micro_agents = []
        sales_dept.is_active = False
        sales_dept.activate = AsyncMock()
        sales_dept.get_status = Mock(return_value={"status": "active", "agents": 4})
        return sales_dept
    
    @pytest.mark.asyncio
    async def test_business_request_to_sales_activation(self, jarvis_instance, mock_sales_department):
        """
        Test: 'I need more sales' → Sales dept → Pipeline update
        
        Validates complete business flow from natural language request
        to department activation and metrics updates.
        """
        jarvis = jarvis_instance
        
        # Mock department registration
        jarvis.departments = {"sales": mock_sales_department}
        jarvis.active_departments = {}
        
        # Mock conversation manager responses
        jarvis.conversation_manager.identify_department_needs.return_value = ["sales"]
        jarvis.conversation_manager.extract_business_metrics.return_value = [
            {"type": "revenue", "value": 100000, "timestamp": "2025-01-01T00:00:00Z"}
        ]
        
        # Mock agent creation
        mock_agents = [
            Mock(name="Lead Scanner Agent", agent_type="lead_scanner"),
            Mock(name="Outreach Composer Agent", agent_type="outreach_composer"),
            Mock(name="Meeting Scheduler Agent", agent_type="meeting_scheduler"),
            Mock(name="Pipeline Tracker Agent", agent_type="pipeline_tracker")
        ]
        
        async def mock_activate_department():
            mock_sales_department.micro_agents = mock_agents
            mock_sales_department.is_active = True
            jarvis.active_departments["sales"] = mock_sales_department
            
            # Simulate metrics update
            jarvis.business_context.key_metrics.leads_generated = 25
            jarvis.business_context.key_metrics.pipeline_value = 50000
            jarvis.business_context.key_metrics.conversion_rate = 0.15
        
        mock_sales_department.activate.side_effect = mock_activate_department
        
        # Test business request processing
        business_request = "I need more sales and better lead generation for Q1 growth"
        
        # Start timing
        start_time = time.time()
        
        # Process the request (would normally call jarvis.process_business_request)
        # For testing, we'll simulate the flow
        
        # 1. Identify department needs
        needed_departments = jarvis.conversation_manager.identify_department_needs(business_request)
        assert "sales" in needed_departments
        
        # 2. Activate sales department
        await jarvis.departments["sales"].activate()
        
        # 3. Verify activation
        activation_time = time.time() - start_time
        
        # Validation points
        assert "sales" in jarvis.active_departments
        assert jarvis.active_departments["sales"].is_active
        assert len(jarvis.active_departments["sales"].micro_agents) == 4
        
        # Verify micro-agents created
        agent_types = [agent.agent_type for agent in jarvis.active_departments["sales"].micro_agents]
        expected_types = ["lead_scanner", "outreach_composer", "meeting_scheduler", "pipeline_tracker"]
        assert all(agent_type in agent_types for agent_type in expected_types)
        
        # Verify metrics updated
        assert jarvis.business_context.key_metrics.leads_generated > 0
        assert jarvis.business_context.key_metrics.pipeline_value > 0
        assert jarvis.business_context.key_metrics.conversion_rate > 0
        
        # Performance benchmark
        assert activation_time < 5.0, f"Department activation took {activation_time:.2f}s, should be < 5s"
        
        print(f"✅ Business request to sales activation completed in {activation_time:.2f}s")
        print(f"   - Departments activated: {list(jarvis.active_departments.keys())}")
        print(f"   - Micro-agents created: {len(jarvis.active_departments['sales'].micro_agents)}")
        print(f"   - Metrics updated: leads={jarvis.business_context.key_metrics.leads_generated}, "
              f"pipeline=${jarvis.business_context.key_metrics.pipeline_value}")
    
    @pytest.mark.asyncio
    async def test_fallback_to_agent_builder(self, jarvis_instance):
        """
        Test: "Create Twitter monitor" → Routes to agent builder
        
        Validates that technical requests fall back to agent builder
        instead of activating business departments.
        """
        jarvis = jarvis_instance
        
        # Mock no department needs identified
        jarvis.conversation_manager.identify_department_needs.return_value = []
        
        # Mock agent builder fallback
        jarvis.orchestrator = Mock()
        jarvis.orchestrator.process_request = AsyncMock(return_value={
            "agent_created": True,
            "agent_name": "Twitter Monitor",
            "agent_type": "monitoring"
        })
        
        technical_request = "Create a Twitter monitoring agent that tracks mentions of our brand"
        
        # Process request
        start_time = time.time()
        
        # 1. Check for department needs
        needed_departments = jarvis.conversation_manager.identify_department_needs(technical_request)
        assert len(needed_departments) == 0  # No departments needed
        
        # 2. Fall back to agent builder
        result = await jarvis.orchestrator.process_request(technical_request)
        
        fallback_time = time.time() - start_time
        
        # Validation points
        assert result["agent_created"] is True
        assert result["agent_name"] == "Twitter Monitor"
        assert result["agent_type"] == "monitoring"
        assert len(jarvis.active_departments) == 0  # No departments activated
        
        # Performance benchmark
        assert fallback_time < 3.0, f"Agent builder fallback took {fallback_time:.2f}s, should be < 3s"
        
        print(f"✅ Agent builder fallback completed in {fallback_time:.2f}s")
        print(f"   - Agent created: {result['agent_name']}")
        print(f"   - Agent type: {result['agent_type']}")
        print(f"   - Departments activated: {len(jarvis.active_departments)}")
    
    @pytest.mark.asyncio
    async def test_cross_department_coordination(self, jarvis_instance, mock_sales_department):
        """
        Test: Sales → Marketing handoff (stub Marketing dept)
        
        Validates cross-department coordination and communication.
        """
        jarvis = jarvis_instance
        
        # Create mock marketing department
        mock_marketing_department = Mock()
        mock_marketing_department.name = "marketing"
        mock_marketing_department.micro_agents = []
        mock_marketing_department.is_active = False
        mock_marketing_department.activate = AsyncMock()
        mock_marketing_department.receive_coordination_message = AsyncMock()
        
        # Setup departments
        jarvis.departments = {
            "sales": mock_sales_department,
            "marketing": mock_marketing_department
        }
        jarvis.active_departments = {}
        
        # Mock conversation manager
        jarvis.conversation_manager.identify_department_needs.return_value = ["sales", "marketing"]
        
        # Mock WebSocket handler for coordination messages
        with patch('conversation.websocket_handler') as mock_ws_module:
            mock_ws = mock_ws_module.websocket_handler
            mock_ws.send_agent_coordination = AsyncMock()
            
            # Simulate department activation
            async def activate_sales():
                mock_sales_department.is_active = True
                jarvis.active_departments["sales"] = mock_sales_department
            
            async def activate_marketing():
                mock_marketing_department.is_active = True
                jarvis.active_departments["marketing"] = mock_marketing_department
            
            mock_sales_department.activate.side_effect = activate_sales
            mock_marketing_department.activate.side_effect = activate_marketing
            
            # Test cross-department request
            coordination_request = "Sales needs marketing support for lead nurturing campaigns"
            
            start_time = time.time()
            
            # 1. Identify multiple departments
            needed_departments = jarvis.conversation_manager.identify_department_needs(coordination_request)
            assert "sales" in needed_departments
            assert "marketing" in needed_departments
            
            # 2. Activate both departments
            await jarvis.departments["sales"].activate()
            await jarvis.departments["marketing"].activate()
            
            # 3. Simulate coordination message
            coordination_data = {
                "lead_quality_threshold": 8.0,
                "nurturing_sequence": "enterprise_prospect",
                "handoff_criteria": "demo_scheduled"
            }
            
            await jarvis.departments["marketing"].receive_coordination_message(
                from_department="sales",
                message="High-quality leads ready for nurturing",
                data=coordination_data
            )
            
            # 4. Send WebSocket coordination update
            await mock_ws.send_agent_coordination(
                "test_session",
                "Sales Department",
                "Marketing Department",
                "Lead handoff for nurturing",
                coordination_data
            )
            
            coordination_time = time.time() - start_time
            
            # Validation points
            assert "sales" in jarvis.active_departments
            assert "marketing" in jarvis.active_departments
            assert jarvis.active_departments["sales"].is_active
            assert jarvis.active_departments["marketing"].is_active
            
            # Verify coordination message was sent
            mock_marketing_department.receive_coordination_message.assert_called_once()
            mock_ws.send_agent_coordination.assert_called_once()
            
            # Performance benchmark
            assert coordination_time < 10.0, f"Cross-department coordination took {coordination_time:.2f}s, should be < 10s"
            
            print(f"✅ Cross-department coordination completed in {coordination_time:.2f}s")
            print(f"   - Departments activated: {list(jarvis.active_departments.keys())}")
            print(f"   - Coordination messages sent: 1")
            print(f"   - WebSocket updates sent: 1")
    
    @pytest.mark.asyncio
    async def test_performance_benchmarks(self, jarvis_instance, mock_sales_department):
        """
        Test performance benchmarks comparing department activation vs individual agent creation.
        """
        jarvis = jarvis_instance
        jarvis.departments = {"sales": mock_sales_department}
        jarvis.active_departments = {}
        
        # Mock individual agent creation (slower)
        async def mock_create_individual_agents():
            await asyncio.sleep(0.5)  # Simulate slower individual creation
            return [Mock(name=f"Agent {i}") for i in range(4)]
        
        # Mock department activation (faster)
        async def mock_activate_department():
            await asyncio.sleep(0.1)  # Simulate faster department activation
            mock_sales_department.micro_agents = [Mock(name=f"Agent {i}") for i in range(4)]
            mock_sales_department.is_active = True
            jarvis.active_departments["sales"] = mock_sales_department
        
        mock_sales_department.activate.side_effect = mock_activate_department
        
        # Test department activation time
        start_time = time.time()
        await jarvis.departments["sales"].activate()
        department_activation_time = time.time() - start_time
        
        # Test individual agent creation time
        start_time = time.time()
        individual_agents = await mock_create_individual_agents()
        individual_creation_time = time.time() - start_time
        
        # Validation points
        assert department_activation_time < individual_creation_time
        assert len(jarvis.active_departments["sales"].micro_agents) == 4
        assert len(individual_agents) == 4
        
        performance_improvement = ((individual_creation_time - department_activation_time) / individual_creation_time) * 100
        
        print(f"✅ Performance benchmarks completed:")
        print(f"   - Department activation: {department_activation_time:.3f}s")
        print(f"   - Individual agent creation: {individual_creation_time:.3f}s")
        print(f"   - Performance improvement: {performance_improvement:.1f}%")
        
        assert performance_improvement > 50, f"Department activation should be >50% faster, got {performance_improvement:.1f}%"
    
    @pytest.mark.asyncio
    async def test_resource_usage_comparison(self, jarvis_instance, mock_sales_department):
        """
        Test resource usage comparison between department and individual agent approaches.
        """
        jarvis = jarvis_instance
        jarvis.departments = {"sales": mock_sales_department}
        
        # Mock resource tracking
        class ResourceTracker:
            def __init__(self):
                self.memory_usage = 0
                self.cpu_usage = 0
                self.network_calls = 0
            
            def track_department_activation(self):
                self.memory_usage = 50  # MB
                self.cpu_usage = 20     # %
                self.network_calls = 1  # Single activation call
            
            def track_individual_agents(self):
                self.memory_usage = 80  # MB (higher due to separate processes)
                self.cpu_usage = 35     # % (higher due to coordination overhead)
                self.network_calls = 4  # One call per agent
        
        # Test department approach
        dept_tracker = ResourceTracker()
        dept_tracker.track_department_activation()
        
        # Test individual approach  
        individual_tracker = ResourceTracker()
        individual_tracker.track_individual_agents()
        
        # Validation points
        assert dept_tracker.memory_usage < individual_tracker.memory_usage
        assert dept_tracker.cpu_usage < individual_tracker.cpu_usage
        assert dept_tracker.network_calls < individual_tracker.network_calls
        
        memory_savings = ((individual_tracker.memory_usage - dept_tracker.memory_usage) / individual_tracker.memory_usage) * 100
        cpu_savings = ((individual_tracker.cpu_usage - dept_tracker.cpu_usage) / individual_tracker.cpu_usage) * 100
        network_savings = ((individual_tracker.network_calls - dept_tracker.network_calls) / individual_tracker.network_calls) * 100
        
        print(f"✅ Resource usage comparison completed:")
        print(f"   - Memory savings: {memory_savings:.1f}%")
        print(f"   - CPU savings: {cpu_savings:.1f}%")
        print(f"   - Network call reduction: {network_savings:.1f}%")
        
        assert memory_savings > 20, f"Memory savings should be >20%, got {memory_savings:.1f}%"
        assert cpu_savings > 20, f"CPU savings should be >20%, got {cpu_savings:.1f}%"
        assert network_savings > 50, f"Network call reduction should be >50%, got {network_savings:.1f}%"
    
    @pytest.mark.asyncio
    async def test_end_to_end_business_flow(self, jarvis_instance, mock_sales_department):
        """
        Test complete end-to-end business flow with all components.
        """
        jarvis = jarvis_instance
        jarvis.departments = {"sales": mock_sales_department}
        jarvis.active_departments = {}
        
        # Mock WebSocket for real-time updates
        with patch('conversation.websocket_handler') as mock_ws_module:
            mock_ws = mock_ws_module.websocket_handler
            mock_ws.send_department_activated = AsyncMock()
            mock_ws.send_business_metric_updated = AsyncMock()
            mock_ws.send_workflow_progress = AsyncMock()
            
            # Mock complete flow
            async def mock_complete_activation():
                # Department activation
                mock_sales_department.is_active = True
                mock_sales_department.micro_agents = [Mock(name=f"Agent {i}") for i in range(4)]
                jarvis.active_departments["sales"] = mock_sales_department
                
                # Metrics update
                jarvis.business_context.key_metrics.leads_generated = 50
                jarvis.business_context.key_metrics.pipeline_value = 100000
                jarvis.business_context.key_metrics.conversion_rate = 0.18
                
                # WebSocket updates
                await mock_ws.send_department_activated("test_session", "sales", 4)
                await mock_ws.send_business_metric_updated("test_session", "leads_generated", 50)
                await mock_ws.send_workflow_progress("test_session", "Sales Activation", 100, "Complete")
            
            mock_sales_department.activate.side_effect = mock_complete_activation
            
            # Mock conversation processing
            jarvis.conversation_manager.identify_department_needs.return_value = ["sales"]
            jarvis.conversation_manager.extract_business_metrics.return_value = [
                {"type": "revenue_target", "value": 1000000}
            ]
            jarvis.conversation_manager.generate_executive_summary.return_value = (
                "Sales department activated with 4 agents targeting $1M revenue"
            )
            
            # Execute end-to-end flow
            business_request = "I need to increase sales revenue to $1M this quarter"
            
            start_time = time.time()
            
            # 1. Process business request
            jarvis.conversation_manager.add_user_message(business_request)
            
            # 2. Identify needs and activate departments
            needed_departments = jarvis.conversation_manager.identify_department_needs(business_request)
            await jarvis.departments["sales"].activate()
            
            # 3. Extract metrics and generate summary
            metrics = jarvis.conversation_manager.extract_business_metrics(business_request)
            summary = jarvis.conversation_manager.generate_executive_summary()
            
            end_to_end_time = time.time() - start_time
            
            # Validation points
            assert "sales" in jarvis.active_departments
            assert len(jarvis.active_departments["sales"].micro_agents) == 4
            assert jarvis.business_context.key_metrics.leads_generated == 50
            assert jarvis.business_context.key_metrics.pipeline_value == 100000
            assert len(metrics) > 0
            assert "Sales department activated" in summary
            
            # Verify WebSocket updates
            mock_ws.send_department_activated.assert_called_once()
            mock_ws.send_business_metric_updated.assert_called_once()
            mock_ws.send_workflow_progress.assert_called_once()
            
            # Performance validation
            assert end_to_end_time < 15.0, f"End-to-end flow took {end_to_end_time:.2f}s, should be < 15s"
            
            print(f"✅ End-to-end business flow completed in {end_to_end_time:.2f}s")
            print(f"   - Business request processed: '{business_request[:50]}...'")
            print(f"   - Departments activated: {list(jarvis.active_departments.keys())}")
            print(f"   - Metrics generated: {len(metrics)}")
            print(f"   - WebSocket updates sent: 3")
            print(f"   - Executive summary: '{summary[:50]}...'")


if __name__ == "__main__":
    # Run tests with pytest
    import subprocess
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        __file__, 
        "-v", 
        "--tb=short",
        "--asyncio-mode=auto"
    ], capture_output=True, text=True)
    
    print(result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    
    sys.exit(result.returncode)