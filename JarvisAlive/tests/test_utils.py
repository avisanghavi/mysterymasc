"""Test utilities and helpers for Jarvis integration tests."""

import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Callable
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass


@dataclass
class TestResult:
    """Represents the result of a test operation."""
    success: bool
    duration: float
    data: Dict[str, Any]
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class BusinessFlowTester:
    """Utility class for testing complete business flows."""
    
    def __init__(self, jarvis_instance, websocket_handler=None):
        self.jarvis = jarvis_instance
        self.websocket_handler = websocket_handler
        self.test_results = []
        self.performance_metrics = {}
    
    async def test_department_activation_flow(
        self, 
        business_request: str, 
        expected_departments: List[str],
        timeout: float = 10.0
    ) -> TestResult:
        """Test complete department activation flow."""
        start_time = time.time()
        errors = []
        
        try:
            # Step 1: Process business request
            self.jarvis.conversation_manager.add_user_message(business_request)
            
            # Step 2: Identify department needs
            identified_departments = self.jarvis.conversation_manager.identify_department_needs(business_request)
            
            # Validate department identification
            for expected_dept in expected_departments:
                if expected_dept not in identified_departments:
                    errors.append(f"Expected department '{expected_dept}' not identified")
            
            # Step 3: Activate departments
            activation_results = {}
            for dept_name in identified_departments:
                if dept_name in self.jarvis.departments:
                    result = await self.jarvis.departments[dept_name].activate()
                    activation_results[dept_name] = result
            
            # Step 4: Verify activations
            for dept_name in expected_departments:
                if dept_name not in self.jarvis.active_departments:
                    errors.append(f"Department '{dept_name}' not activated")
                elif not self.jarvis.active_departments[dept_name].is_active:
                    errors.append(f"Department '{dept_name}' marked inactive after activation")
            
            # Step 5: Check WebSocket updates (if handler provided)
            if self.websocket_handler:
                # Verify department activation messages were sent
                call_count = self.websocket_handler.send_department_activated.call_count
                if call_count < len(expected_departments):
                    errors.append(f"Expected {len(expected_departments)} WebSocket updates, got {call_count}")
            
            duration = time.time() - start_time
            
            # Check timeout
            if duration > timeout:
                errors.append(f"Flow took {duration:.2f}s, exceeded timeout of {timeout}s")
            
            return TestResult(
                success=len(errors) == 0,
                duration=duration,
                data={
                    "identified_departments": identified_departments,
                    "activation_results": activation_results,
                    "active_departments": list(self.jarvis.active_departments.keys())
                },
                errors=errors
            )
            
        except Exception as e:
            duration = time.time() - start_time
            errors.append(f"Exception during flow: {str(e)}")
            
            return TestResult(
                success=False,
                duration=duration,
                data={},
                errors=errors
            )
    
    async def test_coordination_flow(
        self,
        from_department: str,
        to_department: str,
        coordination_message: str,
        coordination_data: Dict[str, Any],
        timeout: float = 5.0
    ) -> TestResult:
        """Test department coordination flow."""
        start_time = time.time()
        errors = []
        
        try:
            # Ensure both departments are active
            if from_department not in self.jarvis.active_departments:
                errors.append(f"Source department '{from_department}' not active")
            if to_department not in self.jarvis.active_departments:
                errors.append(f"Target department '{to_department}' not active")
            
            if errors:
                return TestResult(False, time.time() - start_time, {}, errors)
            
            # Send coordination message
            await self.jarvis.active_departments[to_department].receive_coordination_message(
                from_department=from_department,
                message=coordination_message,
                data=coordination_data
            )
            
            # Verify WebSocket coordination update
            if self.websocket_handler:
                await self.websocket_handler.send_agent_coordination(
                    "test_session",
                    from_department,
                    to_department,
                    coordination_message,
                    coordination_data
                )
                
                # Check if call was made
                if not self.websocket_handler.send_agent_coordination.called:
                    errors.append("WebSocket coordination message not sent")
            
            duration = time.time() - start_time
            
            if duration > timeout:
                errors.append(f"Coordination took {duration:.2f}s, exceeded timeout of {timeout}s")
            
            return TestResult(
                success=len(errors) == 0,
                duration=duration,
                data={
                    "from_department": from_department,
                    "to_department": to_department,
                    "message": coordination_message,
                    "data": coordination_data
                },
                errors=errors
            )
            
        except Exception as e:
            duration = time.time() - start_time
            errors.append(f"Exception during coordination: {str(e)}")
            
            return TestResult(
                success=False,
                duration=duration,
                data={},
                errors=errors
            )
    
    async def test_fallback_flow(
        self,
        technical_request: str,
        expected_agent_type: str,
        timeout: float = 5.0
    ) -> TestResult:
        """Test fallback to agent builder."""
        start_time = time.time()
        errors = []
        
        try:
            # Check that no departments are identified
            identified_departments = self.jarvis.conversation_manager.identify_department_needs(technical_request)
            
            if identified_departments:
                errors.append(f"Technical request incorrectly identified departments: {identified_departments}")
            
            # Test fallback to orchestrator
            result = await self.jarvis.orchestrator.process_request(technical_request)
            
            # Validate result
            if not result.get("agent_created"):
                errors.append("Agent not created through fallback")
            
            if result.get("agent_type") != expected_agent_type:
                errors.append(f"Expected agent type '{expected_agent_type}', got '{result.get('agent_type')}'")
            
            # Ensure no departments were activated
            if self.jarvis.active_departments:
                errors.append(f"Departments incorrectly activated: {list(self.jarvis.active_departments.keys())}")
            
            duration = time.time() - start_time
            
            if duration > timeout:
                errors.append(f"Fallback took {duration:.2f}s, exceeded timeout of {timeout}s")
            
            return TestResult(
                success=len(errors) == 0,
                duration=duration,
                data={
                    "agent_result": result,
                    "identified_departments": identified_departments
                },
                errors=errors
            )
            
        except Exception as e:
            duration = time.time() - start_time
            errors.append(f"Exception during fallback: {str(e)}")
            
            return TestResult(
                success=False,
                duration=duration,
                data={},
                errors=errors
            )
    
    def add_performance_metric(self, name: str, value: float, unit: str = "seconds"):
        """Add a performance metric."""
        self.performance_metrics[name] = {
            "value": value,
            "unit": unit,
            "timestamp": time.time()
        }
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get summary of all performance metrics."""
        return {
            "metrics": self.performance_metrics,
            "test_count": len(self.test_results),
            "success_rate": len([r for r in self.test_results if r.success]) / max(len(self.test_results), 1)
        }


class MetricsValidator:
    """Utility for validating business metrics."""
    
    def __init__(self, business_context):
        self.business_context = business_context
        self.baseline_metrics = self._capture_baseline()
    
    def _capture_baseline(self) -> Dict[str, Any]:
        """Capture baseline metrics."""
        return {
            "leads_generated": self.business_context.key_metrics.leads_generated,
            "pipeline_value": self.business_context.key_metrics.pipeline_value,
            "conversion_rate": self.business_context.key_metrics.conversion_rate,
            "revenue": getattr(self.business_context.key_metrics, 'revenue', 0),
            "customer_count": getattr(self.business_context.key_metrics, 'customer_count', 0)
        }
    
    def validate_metric_increase(self, metric_name: str, minimum_increase: float = 0) -> bool:
        """Validate that a metric has increased."""
        current_value = getattr(self.business_context.key_metrics, metric_name, 0)
        baseline_value = self.baseline_metrics.get(metric_name, 0)
        
        increase = current_value - baseline_value
        return increase >= minimum_increase
    
    def validate_metric_range(self, metric_name: str, min_value: float, max_value: float) -> bool:
        """Validate that a metric is within range."""
        current_value = getattr(self.business_context.key_metrics, metric_name, 0)
        return min_value <= current_value <= max_value
    
    def get_metric_change(self, metric_name: str) -> Dict[str, Any]:
        """Get change in metric from baseline."""
        current_value = getattr(self.business_context.key_metrics, metric_name, 0)
        baseline_value = self.baseline_metrics.get(metric_name, 0)
        
        absolute_change = current_value - baseline_value
        percentage_change = (absolute_change / baseline_value * 100) if baseline_value > 0 else 0
        
        return {
            "baseline": baseline_value,
            "current": current_value,
            "absolute_change": absolute_change,
            "percentage_change": percentage_change
        }
    
    def validate_all_metrics(self, expected_changes: Dict[str, float]) -> List[str]:
        """Validate multiple metrics against expected changes."""
        errors = []
        
        for metric_name, expected_min_increase in expected_changes.items():
            if not self.validate_metric_increase(metric_name, expected_min_increase):
                change = self.get_metric_change(metric_name)
                errors.append(
                    f"Metric '{metric_name}' increase {change['absolute_change']} "
                    f"< expected {expected_min_increase}"
                )
        
        return errors


class PerformanceBenchmark:
    """Utility for performance benchmarking."""
    
    def __init__(self):
        self.benchmarks = {}
    
    async def benchmark_function(
        self, 
        name: str, 
        func: Callable, 
        *args, 
        iterations: int = 1,
        **kwargs
    ) -> Dict[str, Any]:
        """Benchmark a function's performance."""
        times = []
        results = []
        
        for i in range(iterations):
            start_time = time.time()
            
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
            
            duration = time.time() - start_time
            times.append(duration)
            results.append(result)
        
        benchmark_data = {
            "name": name,
            "iterations": iterations,
            "times": times,
            "avg_time": sum(times) / len(times),
            "min_time": min(times),
            "max_time": max(times),
            "total_time": sum(times),
            "results": results
        }
        
        self.benchmarks[name] = benchmark_data
        return benchmark_data
    
    def compare_benchmarks(self, name1: str, name2: str) -> Dict[str, Any]:
        """Compare two benchmarks."""
        if name1 not in self.benchmarks or name2 not in self.benchmarks:
            raise ValueError("Both benchmarks must exist")
        
        bench1 = self.benchmarks[name1]
        bench2 = self.benchmarks[name2]
        
        improvement = ((bench2["avg_time"] - bench1["avg_time"]) / bench2["avg_time"]) * 100
        
        return {
            "faster_benchmark": name1 if bench1["avg_time"] < bench2["avg_time"] else name2,
            "improvement_percentage": abs(improvement),
            "time_difference": abs(bench1["avg_time"] - bench2["avg_time"]),
            "benchmark1": {
                "name": name1,
                "avg_time": bench1["avg_time"]
            },
            "benchmark2": {
                "name": name2,
                "avg_time": bench2["avg_time"]
            }
        }
    
    def get_benchmark_report(self) -> str:
        """Generate a formatted benchmark report."""
        if not self.benchmarks:
            return "No benchmarks recorded."
        
        report_lines = ["Performance Benchmark Report", "=" * 30]
        
        for name, data in self.benchmarks.items():
            report_lines.extend([
                f"\n{name}:",
                f"  Average Time: {data['avg_time']:.4f}s",
                f"  Min Time: {data['min_time']:.4f}s",
                f"  Max Time: {data['max_time']:.4f}s",
                f"  Iterations: {data['iterations']}"
            ])
        
        return "\n".join(report_lines)


class MockDataGenerator:
    """Utility for generating mock test data."""
    
    @staticmethod
    def generate_business_request(department: str, complexity: str = "simple") -> str:
        """Generate realistic business requests."""
        templates = {
            "sales": {
                "simple": "I need more sales",
                "medium": "We need to improve our sales pipeline and increase conversion rates",
                "complex": "Our Q4 sales target is $2M but we're behind schedule. Need better lead generation, improved qualification process, and faster deal closure with enterprise accounts."
            },
            "marketing": {
                "simple": "Marketing needs improvement",
                "medium": "Our marketing campaigns aren't performing well, need better content",
                "complex": "Marketing ROI has dropped 15% this quarter. Need comprehensive campaign optimization, better targeting for enterprise segments, and improved lead nurturing sequences."
            },
            "customer_service": {
                "simple": "Customer support is slow",
                "medium": "Customer support tickets are piling up and response times are slow",
                "complex": "Customer satisfaction scores dropped to 3.2/5. Average response time is 48 hours, resolution time is 5 days. Need automated ticketing, priority routing, and proactive issue detection."
            }
        }
        
        return templates.get(department, {}).get(complexity, f"Help with {department}")
    
    @staticmethod
    def generate_technical_request(agent_type: str) -> str:
        """Generate technical agent requests."""
        templates = {
            "monitoring": "Create a Twitter monitoring agent that tracks mentions of our brand",
            "data_processing": "Build a CSV file processor that analyzes sales data",
            "notification": "Set up automated email alerts for system failures",
            "web_scraping": "Create a web scraper for competitor pricing data"
        }
        
        return templates.get(agent_type, f"Create a {agent_type} agent")
    
    @staticmethod
    def generate_coordination_scenario(from_dept: str, to_dept: str) -> Dict[str, Any]:
        """Generate coordination scenarios between departments."""
        scenarios = {
            ("sales", "marketing"): {
                "message": "High-quality leads ready for nurturing campaign",
                "data": {
                    "lead_count": 25,
                    "avg_lead_score": 8.5,
                    "industry_focus": "enterprise_saas",
                    "nurturing_priority": "high"
                }
            },
            ("marketing", "sales"): {
                "message": "Campaign generated qualified prospects",
                "data": {
                    "campaign_id": "Q1_enterprise_outreach",
                    "prospect_count": 50,
                    "conversion_rate": 0.12,
                    "follow_up_timeline": "72_hours"
                }
            },
            ("sales", "customer_service"): {
                "message": "New customers need onboarding support",
                "data": {
                    "customer_count": 8,
                    "account_values": [15000, 25000, 45000],
                    "priority_level": "high_value",
                    "onboarding_type": "enterprise"
                }
            }
        }
        
        return scenarios.get((from_dept, to_dept), {
            "message": f"Coordination from {from_dept} to {to_dept}",
            "data": {"coordination_type": "generic"}
        })


class TestReporter:
    """Utility for generating test reports."""
    
    def __init__(self):
        self.test_results = []
        self.benchmark_data = {}
        self.start_time = time.time()
    
    def add_test_result(self, test_name: str, result: TestResult):
        """Add a test result."""
        self.test_results.append({
            "name": test_name,
            "result": result,
            "timestamp": time.time()
        })
    
    def add_benchmark_data(self, name: str, data: Dict[str, Any]):
        """Add benchmark data."""
        self.benchmark_data[name] = data
    
    def generate_summary_report(self) -> str:
        """Generate a comprehensive test summary report."""
        total_tests = len(self.test_results)
        passed_tests = len([r for r in self.test_results if r["result"].success])
        failed_tests = total_tests - passed_tests
        total_duration = time.time() - self.start_time
        
        report_lines = [
            "🧪 JARVIS INTEGRATION TEST REPORT",
            "=" * 50,
            f"Total Tests: {total_tests}",
            f"Passed: {passed_tests} ✅",
            f"Failed: {failed_tests} ❌",
            f"Success Rate: {(passed_tests/total_tests*100):.1f}%" if total_tests > 0 else "N/A",
            f"Total Duration: {total_duration:.2f}s",
            ""
        ]
        
        # Test details
        if self.test_results:
            report_lines.extend(["Test Details:", "-" * 20])
            for test_data in self.test_results:
                name = test_data["name"]
                result = test_data["result"]
                status = "✅ PASS" if result.success else "❌ FAIL"
                duration = f"{result.duration:.3f}s"
                
                report_lines.append(f"{status} {name} ({duration})")
                
                if result.errors:
                    for error in result.errors:
                        report_lines.append(f"    • {error}")
        
        # Benchmark summary
        if self.benchmark_data:
            report_lines.extend(["", "Performance Benchmarks:", "-" * 20])
            for name, data in self.benchmark_data.items():
                avg_time = data.get("avg_time", 0)
                report_lines.append(f"📊 {name}: {avg_time:.4f}s avg")
        
        return "\n".join(report_lines)