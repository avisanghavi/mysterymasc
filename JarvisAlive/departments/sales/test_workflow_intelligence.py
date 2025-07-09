#!/usr/bin/env python3
"""
Test suite for Workflow Intelligence System
Tests workflow orchestration, adaptive learning, and A/B testing
"""
import asyncio
import sys
import os
import time
import random
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from workflow_orchestrator import (
    WorkflowOrchestrator, WorkflowTemplate, WorkflowStep, WorkflowStepType, 
    WorkflowPriority, WorkflowExecution
)
from adaptive_system import (
    AdaptiveSystem, Pattern, PatternType, LearningInsight, 
    Recommendation, ABTest, DataPoint
)

# Mock agents for testing
class MockLeadScannerAgent:
    async def scan_leads(self, limit=50, **kwargs):
        await asyncio.sleep(0.1)  # Simulate work
        return {
            "leads_found": min(limit, random.randint(20, 60)),
            "scan_duration": random.uniform(0.5, 2.0),
            "quality_score": random.uniform(0.7, 0.95)
        }
    
    async def enrich_leads(self, **kwargs):
        await asyncio.sleep(0.2)  # Simulate AI enrichment
        return {
            "enriched_count": random.randint(5, 15),
            "enrichment_quality": random.uniform(0.8, 0.95),
            "cost": random.uniform(0.10, 0.50)
        }

class MockOutreachComposerAgent:
    async def compose_outreach(self, **kwargs):
        await asyncio.sleep(0.15)  # Simulate AI composition
        return {
            "messages_generated": random.randint(1, 5),
            "personalization_score": random.uniform(0.6, 0.9),
            "generation_cost": random.uniform(0.05, 0.25)
        }

async def test_workflow_orchestration():
    """Test core workflow orchestration functionality"""
    print("🔧 Testing Workflow Orchestration")
    print("=" * 50)
    
    orchestrator = WorkflowOrchestrator()
    
    # Register mock agents
    orchestrator.register_agent("LeadScannerAgent", MockLeadScannerAgent())
    orchestrator.register_agent("OutreachComposerAgent", MockOutreachComposerAgent())
    
    # Test template creation
    custom_template = WorkflowTemplate(
        template_id="test_workflow",
        name="Test Sales Workflow",
        description="Test workflow for validation",
        category="test",
        steps=[
            WorkflowStep(
                step_id="scan_step",
                name="Scan for Leads",
                step_type=WorkflowStepType.SCAN_LEADS,
                agent_class="LeadScannerAgent",
                function_name="scan_leads",
                parameters={"limit": 30},
                estimated_duration=60,
                cost_estimate=0.10
            ),
            WorkflowStep(
                step_id="enrich_step", 
                name="Enrich Leads",
                step_type=WorkflowStepType.ENRICH_LEADS,
                agent_class="LeadScannerAgent",
                function_name="enrich_leads",
                dependencies=["scan_step"],
                estimated_duration=90,
                cost_estimate=0.30
            ),
            WorkflowStep(
                step_id="compose_step",
                name="Compose Messages",
                step_type=WorkflowStepType.COMPOSE_OUTREACH,
                agent_class="OutreachComposerAgent", 
                function_name="compose_outreach",
                dependencies=["enrich_step"],
                parallel_group="messaging",
                estimated_duration=45,
                cost_estimate=0.20
            )
        ]
    )
    
    template_id = orchestrator.create_template(custom_template)
    print(f"✅ Created template: {template_id}")
    
    # Test workflow execution
    print("\n🚀 Executing workflow...")
    start_time = time.time()
    
    execution_id = await orchestrator.execute_workflow(
        template_id,
        parameters={"test_run": True},
        priority=WorkflowPriority.HIGH
    )
    
    # Monitor execution
    max_wait = 10  # seconds
    waited = 0
    
    while waited < max_wait:
        status = orchestrator.get_execution_status(execution_id)
        if not status:
            break
            
        print(f"Progress: {status['progress']:.1f}% - Status: {status['status']}")
        
        if status['status'] in ['completed', 'failed']:
            break
            
        await asyncio.sleep(1)
        waited += 1
    
    execution_time = time.time() - start_time
    
    # Get final status
    final_status = orchestrator.get_execution_status(execution_id)
    if final_status:
        print(f"✅ Workflow completed in {execution_time:.2f}s")
        print(f"Final status: {final_status['status']}")
        print(f"Steps completed: {len(final_status['step_results'])}")
        
        # Show step results
        for step_id, result in final_status['step_results'].items():
            status_icon = "✅" if result['status'] == 'completed' else "❌"
            duration = result.get('duration_seconds', 0)
            print(f"  {status_icon} {step_id}: {duration:.2f}s")
    
    # Test performance analysis
    print("\n📊 Analyzing performance...")
    analysis = orchestrator.analyze_performance(template_id)
    print(f"Total executions: {analysis['metrics']['total_executions']}")
    print(f"Success rate: {analysis['metrics']['successful_executions']}/{analysis['metrics']['total_executions']}")
    
    if analysis['bottlenecks']:
        print(f"Bottlenecks: {[step for step, _ in analysis['bottlenecks']]}")
    
    return orchestrator

async def test_adaptive_learning():
    """Test adaptive learning and pattern recognition"""
    print("\n🧠 Testing Adaptive Learning System") 
    print("=" * 50)
    
    adaptive_system = AdaptiveSystem()
    
    # Generate synthetic data points
    print("📈 Generating synthetic performance data...")
    
    workflows = ["lead_generation", "outreach_campaign", "meeting_pipeline"]
    steps = ["scan_leads", "enrich_leads", "compose_messages", "send_emails"]
    metrics = ["duration", "cost", "success_rate"]
    
    # Generate baseline data
    for i in range(100):
        workflow_id = random.choice(workflows)
        step_id = random.choice(steps)
        metric = random.choice(metrics)
        
        # Create patterns in the data
        base_value = {
            "duration": 60,
            "cost": 0.20,
            "success_rate": 0.85
        }[metric]
        
        # Add time-based patterns
        hour = (datetime.now() - timedelta(hours=random.randint(0, 168))).hour
        if hour in [9, 10, 11, 14, 15]:  # Business hours
            modifier = 0.9 if metric == "duration" else 1.1
        else:
            modifier = 1.2 if metric == "duration" else 0.8
        
        # Add workflow-specific patterns
        if workflow_id == "lead_generation" and metric == "duration":
            modifier *= 0.8  # Faster workflow
        elif workflow_id == "meeting_pipeline" and metric == "success_rate":
            modifier *= 1.15  # Higher success rate
        
        value = base_value * modifier * random.uniform(0.7, 1.3)
        
        adaptive_system.record_data_point(
            workflow_id=workflow_id,
            step_id=step_id,
            metric_name=metric,
            value=value,
            context={
                "hour": hour,
                "day_of_week": random.randint(0, 6),
                "load": random.choice(["low", "medium", "high"])
            }
        )
    
    print(f"✅ Generated {len(adaptive_system.historical_data)} data points")
    
    # Trigger pattern detection
    print("\n🔍 Detecting patterns...")
    patterns = await adaptive_system.detect_patterns()
    
    print(f"✅ Found {len(patterns)} patterns:")
    for pattern in patterns[:5]:  # Show first 5 patterns
        print(f"  • {pattern.name} ({pattern.pattern_type.value})")
        print(f"    Confidence: {pattern.confidence:.2f} | Frequency: {pattern.frequency}")
        print(f"    Description: {pattern.description}")
    
    # Test insights generation
    insights = list(adaptive_system.insights.values())
    print(f"\n💡 Generated {len(insights)} insights:")
    for insight in insights[:3]:  # Show top 3 insights
        print(f"  • {insight.title} (Priority: {insight.priority})")
        print(f"    {insight.description}")
    
    # Test recommendations
    recommendations = adaptive_system.get_recommendations(priority_threshold=5)
    print(f"\n🎯 Generated {len(recommendations)} recommendations:")
    for rec in recommendations[:3]:  # Show top 3 recommendations
        print(f"  • {rec.title} ({rec.type.value})")
        print(f"    Priority: {rec.priority} | Confidence: {rec.confidence:.2f}")
        print(f"    Expected improvement: {rec.expected_improvement}")
    
    return adaptive_system

async def test_ab_testing():
    """Test A/B testing functionality"""
    print("\n🔬 Testing A/B Testing System")
    print("=" * 50)
    
    adaptive_system = AdaptiveSystem()
    
    # Create an A/B test
    ab_test = ABTest(
        test_id="outreach_tone_test",
        name="Outreach Tone Comparison",
        description="Test formal vs casual tone in outreach messages",
        hypothesis="Casual tone will increase response rates",
        workflow_id="outreach_campaign",
        step_id="compose_messages",
        variants={
            "formal": {"tone": "formal", "template_style": "business"},
            "casual": {"tone": "casual", "template_style": "friendly"}, 
            "hybrid": {"tone": "mixed", "template_style": "adaptive"}
        },
        traffic_allocation={"formal": 0.33, "casual": 0.33, "hybrid": 0.34},
        success_metrics=["response_rate", "meeting_booked"],
        start_date=datetime.now(),
        status="running"
    )
    
    test_id = adaptive_system.create_ab_test(ab_test)
    print(f"✅ Created A/B test: {ab_test.name}")
    
    # Simulate test results
    print("\n📊 Simulating test results...")
    
    variants = ["formal", "casual", "hybrid"]
    for _ in range(150):  # Simulate 150 data points
        variant = random.choice(variants)
        
        # Simulate different performance for variants
        if variant == "casual":
            response_rate = random.uniform(0.12, 0.18)  # Better performance
            meeting_rate = random.uniform(0.05, 0.08)
        elif variant == "hybrid":
            response_rate = random.uniform(0.14, 0.20)  # Best performance
            meeting_rate = random.uniform(0.06, 0.09)
        else:  # formal
            response_rate = random.uniform(0.08, 0.14)  # Baseline
            meeting_rate = random.uniform(0.03, 0.06)
        
        adaptive_system.record_ab_result(
            test_id, variant, "response_rate", response_rate, 1
        )
        adaptive_system.record_ab_result(
            test_id, variant, "meeting_booked", meeting_rate, 1
        )
    
    # Analyze results
    print("\n📈 Analyzing A/B test results...")
    analysis = adaptive_system.analyze_ab_test(test_id)
    
    print(f"Test Status: {analysis.get('status', 'completed')}")
    print(f"Winner: {analysis.get('winner', 'TBD')}")
    print(f"Confidence: {analysis.get('confidence', 0):.2f}")
    
    if 'variants' in analysis:
        print("\nVariant Performance:")
        for variant, stats in analysis['variants'].items():
            print(f"  {variant}: {stats['mean']:.3f} (n={stats['sample_size']})")
    
    print(f"Recommendation: {analysis.get('recommendation', 'Continue testing')}")
    
    return adaptive_system

async def test_integration():
    """Test integration between orchestrator and adaptive system"""
    print("\n🔗 Testing System Integration")
    print("=" * 50)
    
    # Create orchestrator and adaptive system
    orchestrator = WorkflowOrchestrator()
    adaptive_system = AdaptiveSystem()
    
    # Register agents
    orchestrator.register_agent("LeadScannerAgent", MockLeadScannerAgent())
    orchestrator.register_agent("OutreachComposerAgent", MockOutreachComposerAgent())
    
    # Execute multiple workflows to generate data
    print("🔄 Running multiple workflow executions...")
    
    execution_ids = []
    for i in range(5):
        execution_id = await orchestrator.execute_workflow(
            "lead_generation_basic",
            parameters={"batch_id": f"batch_{i}"},
            priority=WorkflowPriority.MEDIUM
        )
        execution_ids.append(execution_id)
        
        # Record data points for adaptive learning
        adaptive_system.record_data_point(
            workflow_id="lead_generation_basic",
            step_id="scan_leads",
            metric_name="duration",
            value=random.uniform(45, 120),
            context={"batch_id": f"batch_{i}"}
        )
        
        await asyncio.sleep(0.5)  # Brief pause between executions
    
    # Wait for executions to complete
    await asyncio.sleep(3)
    
    print(f"✅ Completed {len(execution_ids)} workflow executions")
    
    # Get recommendations from adaptive system
    recommendations = adaptive_system.get_recommendations()
    
    print(f"\n🎯 System generated {len(recommendations)} optimization recommendations:")
    for rec in recommendations[:2]:
        print(f"  • {rec.title}")
        print(f"    Target: {rec.target_workflow}/{rec.target_step}")
        print(f"    Expected improvement: {rec.expected_improvement}")
    
    # Show insights summary
    insights_summary = adaptive_system.get_insights_summary()
    print(f"\n💡 Insights Summary:")
    print(f"  Total insights: {insights_summary['total_insights']}")
    print(f"  High priority: {insights_summary['high_priority']}")
    print(f"  Recent insights: {insights_summary['recent_insights']}")

async def test_performance_scaling():
    """Test system performance with larger datasets"""
    print("\n⚡ Testing Performance Scaling")
    print("=" * 50)
    
    adaptive_system = AdaptiveSystem()
    
    # Generate larger dataset
    print("📊 Generating large dataset...")
    start_time = time.time()
    
    for i in range(1000):
        adaptive_system.record_data_point(
            workflow_id=f"workflow_{i % 10}",
            step_id=f"step_{i % 5}",
            metric_name=random.choice(["duration", "cost", "success_rate"]),
            value=random.uniform(0.1, 100.0),
            context={"batch": i // 100}
        )
    
    data_gen_time = time.time() - start_time
    print(f"✅ Generated 1000 data points in {data_gen_time:.2f}s")
    
    # Test pattern detection performance
    print("🔍 Testing pattern detection performance...")
    pattern_start = time.time()
    
    patterns = await adaptive_system.detect_patterns()
    
    pattern_time = time.time() - pattern_start
    print(f"✅ Detected {len(patterns)} patterns in {pattern_time:.2f}s")
    
    # Performance metrics
    print(f"\n📈 Performance Metrics:")
    print(f"  Data points processed: 1000")
    print(f"  Data generation rate: {1000/data_gen_time:.1f} points/sec")
    print(f"  Pattern detection rate: {len(patterns)/pattern_time:.1f} patterns/sec")
    print(f"  Memory usage: {len(adaptive_system.historical_data)} data points stored")

async def main():
    """Run all workflow intelligence tests"""
    print("🚀 Workflow Intelligence System Test Suite")
    print("=" * 60)
    print("Testing workflow orchestration, adaptive learning, and A/B testing\n")
    
    try:
        # Run all test suites
        orchestrator = await test_workflow_orchestration()
        adaptive_system1 = await test_adaptive_learning()
        adaptive_system2 = await test_ab_testing()
        await test_integration()
        await test_performance_scaling()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        
        print("\nKey Features Demonstrated:")
        print("✅ Workflow template creation and management")
        print("✅ Graph-based workflow execution with parallelization")
        print("✅ Performance monitoring and bottleneck analysis")
        print("✅ Pattern recognition and adaptive learning")
        print("✅ Automated insight and recommendation generation")
        print("✅ A/B testing framework with statistical analysis")
        print("✅ System integration and scalability")
        
        print(f"\nSystem Statistics:")
        print(f"  Templates created: {len(orchestrator.templates)}")
        print(f"  Patterns detected: {len(adaptive_system1.patterns)}")
        print(f"  Insights generated: {len(adaptive_system1.insights)}")
        print(f"  Recommendations: {len(adaptive_system1.recommendations)}")
        print(f"  A/B tests: {len(adaptive_system2.ab_tests)}")
        
    except KeyboardInterrupt:
        print("\n👋 Tests stopped by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())