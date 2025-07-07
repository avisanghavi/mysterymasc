"""Pytest configuration and shared fixtures for Jarvis integration tests."""

import pytest
import asyncio
import sys
import os
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.jarvis import Jarvis, JarvisConfig
from orchestration.orchestrator import OrchestratorConfig
from orchestration.business_context import BusinessContext
from departments.sales.sales_department import SalesDepartment
from conversation.jarvis_conversation_manager import JarvisConversationManager


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_config():
    """Provide test configuration for Jarvis."""
    return {
        "anthropic_api_key": "test_key_12345",
        "redis_url": "redis://localhost:6379",
        "max_retries": 2,
        "session_timeout": 1800,
        "max_departments": 3,
        "enable_autonomous_creation": True,
        "enable_coordination": True
    }


@pytest.fixture
async def orchestrator_config(test_config):
    """Create test orchestrator configuration."""
    return OrchestratorConfig(
        anthropic_api_key=test_config["anthropic_api_key"],
        redis_url=test_config["redis_url"],
        max_retries=test_config["max_retries"],
        session_timeout=test_config["session_timeout"]
    )


@pytest.fixture
async def jarvis_config(orchestrator_config, test_config):
    """Create test Jarvis configuration."""
    return JarvisConfig(
        orchestrator_config=orchestrator_config,
        max_concurrent_departments=test_config["max_departments"],
        enable_autonomous_department_creation=test_config["enable_autonomous_creation"],
        enable_cross_department_coordination=test_config["enable_coordination"]
    )


@pytest.fixture
async def mock_business_context():
    """Create mock business context with default metrics."""
    context = Mock(spec=BusinessContext)
    
    # Mock key metrics
    context.key_metrics = Mock()
    context.key_metrics.leads_generated = 0
    context.key_metrics.pipeline_value = 0
    context.key_metrics.conversion_rate = 0.0
    context.key_metrics.revenue = 0
    context.key_metrics.customer_count = 0
    
    # Mock methods
    context.update_metric = Mock()
    context.get_metric_history = Mock(return_value=[])
    context.get_current_metrics = Mock(return_value={})
    context.add_business_event = Mock()
    
    return context


@pytest.fixture
async def mock_conversation_manager():
    """Create mock conversation manager."""
    manager = Mock(spec=JarvisConversationManager)
    
    # Mock methods
    manager.add_user_message = Mock()
    manager.add_assistant_message = Mock()
    manager.add_system_message = Mock()
    manager.identify_department_needs = Mock(return_value=[])
    manager.extract_business_metrics = Mock(return_value=[])
    manager.generate_executive_summary = Mock(return_value="Test summary")
    manager.get_business_context_for_ai = Mock(return_value={})
    manager.track_business_outcome = Mock()
    
    # Mock attributes
    manager.current_business_goals = []
    manager.active_departments = []
    manager.key_metrics_history = []
    
    return manager


@pytest.fixture
async def mock_sales_department():
    """Create mock sales department with realistic behavior."""
    dept = Mock(spec=SalesDepartment)
    
    # Basic attributes
    dept.name = "sales"
    dept.is_active = False
    dept.micro_agents = []
    dept.coordination_enabled = True
    
    # Mock activation process
    async def mock_activate():
        dept.is_active = True
        dept.micro_agents = [
            Mock(name="Lead Scanner Agent", agent_type="lead_scanner", status="active"),
            Mock(name="Outreach Composer Agent", agent_type="outreach_composer", status="active"),
            Mock(name="Meeting Scheduler Agent", agent_type="meeting_scheduler", status="active"),
            Mock(name="Pipeline Tracker Agent", agent_type="pipeline_tracker", status="active")
        ]
        return {"status": "activated", "agents_created": 4}
    
    dept.activate = AsyncMock(side_effect=mock_activate)
    dept.deactivate = AsyncMock()
    dept.get_status = Mock(return_value={"status": "inactive", "agents": 0})
    dept.send_coordination_message = AsyncMock()
    dept.receive_coordination_message = AsyncMock()
    
    return dept


@pytest.fixture
async def mock_marketing_department():
    """Create mock marketing department for coordination tests."""
    dept = Mock()
    
    dept.name = "marketing"
    dept.is_active = False
    dept.micro_agents = []
    dept.coordination_enabled = True
    
    async def mock_activate():
        dept.is_active = True
        dept.micro_agents = [
            Mock(name="Content Creator Agent", agent_type="content_creator", status="active"),
            Mock(name="Campaign Manager Agent", agent_type="campaign_manager", status="active"),
            Mock(name="Social Media Agent", agent_type="social_media", status="active")
        ]
        return {"status": "activated", "agents_created": 3}
    
    dept.activate = AsyncMock(side_effect=mock_activate)
    dept.deactivate = AsyncMock()
    dept.get_status = Mock(return_value={"status": "inactive", "agents": 0})
    dept.send_coordination_message = AsyncMock()
    dept.receive_coordination_message = AsyncMock()
    
    return dept


@pytest.fixture
async def jarvis_instance(jarvis_config, mock_business_context, mock_conversation_manager):
    """Create a fully mocked Jarvis instance for testing."""
    jarvis = Mock(spec=Jarvis)
    
    # Configuration
    jarvis.config = jarvis_config
    
    # Mock dependencies
    jarvis.business_context = mock_business_context
    jarvis.conversation_manager = mock_conversation_manager
    
    # Mock state
    jarvis.active_departments = {}
    jarvis.departments = {}
    jarvis.session_id = "test_session_123"
    
    # Mock state manager
    jarvis.state_manager = Mock()
    jarvis.state_manager.get_session_state = AsyncMock(return_value={})
    jarvis.state_manager.save_session_state = AsyncMock()
    
    # Mock orchestrator for fallback
    jarvis.orchestrator = Mock()
    jarvis.orchestrator.process_request = AsyncMock()
    
    # Mock methods
    jarvis.initialize = AsyncMock()
    jarvis.process_business_request = AsyncMock()
    jarvis.activate_department = AsyncMock()
    jarvis.coordinate_departments = AsyncMock()
    jarvis.get_business_summary = Mock()
    
    return jarvis


@pytest.fixture
async def mock_websocket_handler():
    """Create mock WebSocket handler for testing real-time updates."""
    with patch('conversation.websocket_handler.websocket_handler') as mock_ws:
        # Mock WebSocket methods
        mock_ws.send_department_activated = AsyncMock()
        mock_ws.send_business_metric_updated = AsyncMock()
        mock_ws.send_workflow_progress = AsyncMock()
        mock_ws.send_agent_coordination = AsyncMock()
        mock_ws.send_business_insight = AsyncMock()
        mock_ws.send_optimization_suggestion = AsyncMock()
        mock_ws.send_kpi_alert = AsyncMock()
        
        # Mock connection management
        mock_ws.add_connection = AsyncMock(return_value="test_conn_123")
        mock_ws.remove_connection = AsyncMock()
        mock_ws.subscribe_to_session = AsyncMock()
        mock_ws.broadcast_to_session = AsyncMock()
        
        yield mock_ws


@pytest.fixture
async def performance_tracker():
    """Utility for tracking performance metrics during tests."""
    class PerformanceTracker:
        def __init__(self):
            self.metrics = {}
            self.start_times = {}
        
        def start_timer(self, name: str):
            import time
            self.start_times[name] = time.time()
        
        def end_timer(self, name: str) -> float:
            import time
            if name in self.start_times:
                elapsed = time.time() - self.start_times[name]
                self.metrics[name] = elapsed
                return elapsed
            return 0.0
        
        def get_metric(self, name: str) -> float:
            return self.metrics.get(name, 0.0)
        
        def get_all_metrics(self) -> dict:
            return self.metrics.copy()
        
        def assert_performance(self, name: str, max_time: float):
            actual_time = self.get_metric(name)
            assert actual_time <= max_time, f"{name} took {actual_time:.2f}s, should be <= {max_time}s"
    
    return PerformanceTracker()


@pytest.fixture
async def resource_monitor():
    """Mock resource monitoring for testing."""
    class ResourceMonitor:
        def __init__(self):
            self.memory_usage = 0
            self.cpu_usage = 0
            self.network_calls = 0
            self.active_connections = 0
        
        def track_department_activation(self):
            self.memory_usage = 50  # MB
            self.cpu_usage = 20     # %
            self.network_calls = 1
            self.active_connections = 4
        
        def track_individual_agents(self, count: int = 4):
            self.memory_usage = 80      # MB (higher)
            self.cpu_usage = 35         # % (higher)
            self.network_calls = count  # One per agent
            self.active_connections = count
        
        def get_memory_savings(self, baseline: 'ResourceMonitor') -> float:
            if baseline.memory_usage == 0:
                return 0.0
            return ((baseline.memory_usage - self.memory_usage) / baseline.memory_usage) * 100
        
        def get_cpu_savings(self, baseline: 'ResourceMonitor') -> float:
            if baseline.cpu_usage == 0:
                return 0.0
            return ((baseline.cpu_usage - self.cpu_usage) / baseline.cpu_usage) * 100
        
        def get_network_savings(self, baseline: 'ResourceMonitor') -> float:
            if baseline.network_calls == 0:
                return 0.0
            return ((baseline.network_calls - self.network_calls) / baseline.network_calls) * 100
    
    return ResourceMonitor()


@pytest.fixture
async def test_data():
    """Provide test data for various scenarios."""
    return {
        "business_requests": [
            "I need more sales and better lead generation",
            "We need to improve customer support response times",
            "Marketing campaigns need optimization",
            "Revenue target is $1M this quarter"
        ],
        "technical_requests": [
            "Create a Twitter monitoring agent",
            "Build a file processor for CSV data",
            "Set up automated email alerts",
            "Create a web scraper for competitor pricing"
        ],
        "coordination_scenarios": [
            {
                "from": "sales",
                "to": "marketing",
                "message": "High-quality leads ready for nurturing",
                "data": {"lead_count": 25, "avg_score": 8.5}
            },
            {
                "from": "marketing", 
                "to": "sales",
                "message": "Campaign generated 50 new prospects",
                "data": {"campaign_id": "Q1_enterprise", "conversion_rate": 0.12}
            }
        ],
        "expected_metrics": {
            "leads_generated": 50,
            "pipeline_value": 100000,
            "conversion_rate": 0.15,
            "revenue": 250000,
            "customer_count": 150
        }
    }


# Pytest hooks for better test reporting
def pytest_runtest_setup(item):
    """Setup hook for each test."""
    print(f"\n🧪 Running test: {item.name}")


def pytest_runtest_teardown(item):
    """Teardown hook for each test."""
    print(f"✅ Completed test: {item.name}")


# Custom markers
pytest.mark.integration = pytest.mark.mark(name="integration")
pytest.mark.performance = pytest.mark.mark(name="performance") 
pytest.mark.coordination = pytest.mark.mark(name="coordination")