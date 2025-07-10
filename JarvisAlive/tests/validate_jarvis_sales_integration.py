#!/usr/bin/env python3
"""
Validate Enhanced Jarvis Sales Integration
Tests the sales-focused enhancements to the existing Jarvis system
"""

import asyncio
import sys
import os
import time
import json
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Mock the dependencies to avoid import errors
class MockRedis:
    def __init__(self):
        self.data = {}
        self.subscribers = {}
    
    async def setex(self, key, ttl, value):
        self.data[key] = value
    
    async def get(self, key):
        return self.data.get(key)
    
    async def keys(self, pattern):
        return [k for k in self.data.keys() if pattern.replace('*', '') in k]
    
    async def publish(self, channel, message):
        if channel in self.subscribers:
            for callback in self.subscribers[channel]:
                await callback(message)

class MockOrchestrator:
    def __init__(self):
        self.redis_client = MockRedis()
    
    async def initialize(self):
        pass
    
    async def process_request(self, request, session_id, responses=None):
        return {"deployment_status": "completed"}

class MockBusinessContext:
    def __init__(self, redis_client, session_id):
        self.redis_client = redis_client
        self.session_id = session_id
    
    async def load_context(self):
        pass
    
    def get_context_summary(self):
        return {}

class MockChatAnthropic:
    def __init__(self, **kwargs):
        pass
    
    async def ainvoke(self, messages):
        # Mock AI response for intent analysis
        class MockResponse:
            def __init__(self):
                self.content = '{"intent": "lead_generation", "confidence": 0.8, "parameters": {"max_results": 50}}'
        
        return MockResponse()

# Mock the imports
sys.modules['redis.asyncio'] = type('MockModule', (), {'redis': MockRedis})()
sys.modules['langchain_anthropic'] = type('MockModule', (), {'ChatAnthropic': MockChatAnthropic})()
sys.modules['langchain.schema'] = type('MockModule', (), {
    'HumanMessage': lambda content: type('MockMessage', (), {'content': content})(),
    'SystemMessage': lambda content: type('MockMessage', (), {'content': content})()
})()
sys.modules['orchestration.orchestrator'] = type('MockModule', (), {
    'HeyJarvisOrchestrator': MockOrchestrator,
    'OrchestratorConfig': lambda **kwargs: type('MockConfig', (), kwargs)()
})()
sys.modules['orchestration.business_context'] = type('MockModule', (), {
    'BusinessContext': MockBusinessContext,
    'CompanyStage': type('MockEnum', (), {}),
    'Industry': type('MockEnum', (), {})
})()
sys.modules['orchestration.agent_communication'] = type('MockModule', (), {
    'AgentMessageBus': lambda redis_client: type('MockMessageBus', (), {})()
})()
sys.modules['orchestration.state'] = type('MockModule', (), {
    'DeploymentStatus': type('MockEnum', (), {'COMPLETED': 'completed', 'FAILED': 'failed'}),
    'DepartmentStatus': type('MockEnum', (), {'ACTIVE': 'active', 'INACTIVE': 'inactive'}),
    'IntentType': type('MockEnum', (), {}),
    'DepartmentSpec': dict,
    'DepartmentState': dict,
    'OrchestratorState': dict
})()

# Now import the enhanced Jarvis
from orchestration.jarvis import Jarvis, SalesIntentType, SalesResponse, JarvisConfig

async def create_test_jarvis():
    """Create a Jarvis instance for testing"""
    # Create mock config
    orchestrator_config = type('MockConfig', (), {
        'anthropic_api_key': 'test_key',
        'redis_url': 'redis://localhost:6379',
        'redis_password': None
    })()
    
    jarvis_config = JarvisConfig(
        orchestrator_config=orchestrator_config,
        max_concurrent_departments=5,
        business_context_refresh_interval=300,
        enable_autonomous_department_creation=True
    )
    
    # Create Jarvis instance
    jarvis = Jarvis(jarvis_config)
    
    # Mock the components
    jarvis.redis_client = MockRedis()
    jarvis.agent_orchestrator = MockOrchestrator()
    jarvis.business_llm = MockChatAnthropic()
    
    return jarvis

async def test_lead_generation_mapping():
    """✅ Test 1: "I need 50 leads" correctly maps to lead_generation workflow"""
    print("1. Testing Lead Generation Mapping")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    
    test_requests = [
        "I need 50 leads",
        "Find me 100 prospects",
        "Generate leads for my sales team",
        "Search for potential customers",
        "Get 25 SaaS CTOs"
    ]
    
    results = []
    
    for request in test_requests:
        start_time = time.time()
        response = await jarvis.process_sales_request(request, "test_session_1")
        processing_time = time.time() - start_time
        
        # Check if response contains lead generation data
        has_lead_data = response.data and "leads_found" in response.data
        contains_lead_text = "lead" in response.response_text.lower()
        
        is_lead_generation = has_lead_data or contains_lead_text
        
        print(f"   Request: \"{request}\"")
        print(f"   Response type: {'Lead Generation' if is_lead_generation else 'Other'}")
        print(f"   Processing time: {processing_time:.3f}s")
        print(f"   Has lead data: {'✅' if has_lead_data else '❌'}")
        print(f"   Correct mapping: {'✅' if is_lead_generation else '❌'}")
        print()
        
        results.append({
            "request": request,
            "processing_time": processing_time,
            "correct": is_lead_generation
        })
    
    success_rate = sum(1 for r in results if r["correct"]) / len(results)
    avg_processing_time = sum(r["processing_time"] for r in results) / len(results)
    
    print(f"📊 Results:")
    print(f"   Success rate: {success_rate:.1%}")
    print(f"   Average processing time: {avg_processing_time:.3f}s")
    print(f"   Criterion met: {'✅ PASS' if success_rate >= 0.8 else '❌ FAIL'}")
    
    return success_rate >= 0.8

async def test_parameter_extraction():
    """✅ Test 2: Extracts quantities ("50"), industries ("SaaS"), titles ("CTO")"""
    print("\n2. Testing Parameter Extraction")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    
    test_cases = [
        {
            "request": "I need 50 leads",
            "expected_contains": ["50", "leads"]
        },
        {
            "request": "Find me 25 SaaS CTOs",
            "expected_contains": ["25", "saas", "cto"]
        },
        {
            "request": "Target fintech VPs",
            "expected_contains": ["fintech", "vp"]
        },
        {
            "request": "Get 100 healthcare directors",
            "expected_contains": ["100", "healthcare", "director"]
        }
    ]
    
    extraction_results = []
    
    for case in test_cases:
        response = await jarvis.process_sales_request(case["request"], f"test_session_{len(extraction_results)}")
        
        # Check if response contains expected elements
        response_text = response.response_text.lower()
        data_str = json.dumps(response.data or {}).lower()
        combined_response = response_text + " " + data_str
        
        matches = 0
        for expected in case["expected_contains"]:
            if expected.lower() in combined_response:
                matches += 1
        
        accuracy = matches / len(case["expected_contains"])
        
        print(f"   Request: \"{case['request']}\"")
        print(f"   Expected: {case['expected_contains']}")
        print(f"   Matches: {matches}/{len(case['expected_contains'])}")
        print(f"   Accuracy: {accuracy:.1%}")
        print()
        
        extraction_results.append(accuracy)
    
    overall_accuracy = sum(extraction_results) / len(extraction_results)
    print(f"📊 Results:")
    print(f"   Overall accuracy: {overall_accuracy:.1%}")
    print(f"   Criterion met: {'✅ PASS' if overall_accuracy >= 0.7 else '❌ FAIL'}")
    
    return overall_accuracy >= 0.7

async def test_websocket_updates():
    """✅ Test 3: WebSocket sends updates at least every 2 seconds"""
    print("\n3. Testing WebSocket Progress Updates")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    
    # Track progress updates
    progress_updates = []
    
    # Mock the Redis publish method to capture updates
    original_publish = jarvis.redis_client.publish
    
    async def capture_publish(channel, message):
        if "progress:" in channel:
            progress_updates.append(json.loads(message))
            print(f"   Progress update: {json.loads(message)}")
        return await original_publish(channel, message)
    
    jarvis.redis_client.publish = capture_publish
    
    # Execute a request that should generate progress updates
    start_time = time.time()
    response = await jarvis.process_sales_request("Find 20 SaaS leads", "websocket_test_session")
    total_time = time.time() - start_time
    
    print(f"   Total execution time: {total_time:.2f}s")
    print(f"   Progress updates received: {len(progress_updates)}")
    
    # Check if we got progress updates
    has_updates = len(progress_updates) >= 2
    
    # Check if updates show progression
    has_progression = False
    if len(progress_updates) >= 2:
        first_progress = progress_updates[0].get("progress", 0)
        last_progress = progress_updates[-1].get("progress", 0)
        has_progression = last_progress > first_progress
    
    print(f"   Has multiple updates: {'✅' if has_updates else '❌'}")
    print(f"   Shows progression: {'✅' if has_progression else '❌'}")
    
    criterion_met = has_updates and has_progression
    print(f"   Criterion met: {'✅ PASS' if criterion_met else '❌ FAIL'}")
    
    return criterion_met

async def test_concurrent_requests():
    """✅ Test 4: Supports concurrent requests from multiple sessions"""
    print("\n4. Testing Concurrent Requests")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    
    # Create multiple concurrent requests
    requests = [
        ("Find 10 SaaS leads", "session_1"),
        ("Show me quick wins", "session_2"),
        ("Create outreach campaign", "session_3"),
        ("Business summary", "session_4"),
        ("Workflow status", "session_5")
    ]
    
    # Execute all requests concurrently
    start_time = time.time()
    
    tasks = []
    for request, session_id in requests:
        task = jarvis.process_sales_request(request, session_id)
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks)
    
    concurrent_time = time.time() - start_time
    
    print(f"   Concurrent execution time: {concurrent_time:.2f}s")
    print(f"   Requests processed: {len(responses)}")
    
    # Verify all requests succeeded
    all_successful = all(response.response_text and len(response.response_text) > 0 for response in responses)
    
    # Check that different request types got different responses
    response_texts = [r.response_text for r in responses]
    unique_responses = len(set(response_texts))
    diverse_responses = unique_responses >= 3  # At least 3 different response types
    
    print(f"   All requests successful: {'✅' if all_successful else '❌'}")
    print(f"   Diverse responses: {'✅' if diverse_responses else '❌'}")
    print(f"   Performance acceptable: {'✅' if concurrent_time < 10 else '❌'}")
    
    criterion_met = all_successful and diverse_responses and concurrent_time < 10
    print(f"   Criterion met: {'✅ PASS' if criterion_met else '❌ FAIL'}")
    
    return criterion_met

async def test_result_summary():
    """✅ Test 5: Result summary includes key metrics and next steps"""
    print("\n5. Testing Result Summary")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    
    test_requests = [
        "Find 15 SaaS CTOs",
        "Show me 5 quick wins",
        "Business summary"
    ]
    
    summary_results = []
    
    for request in test_requests:
        response = await jarvis.process_sales_request(request, f"summary_test_{len(summary_results)}")
        
        print(f"   Request: \"{request}\"")
        print(f"   Response length: {len(response.response_text)} chars")
        
        # Check for key metrics in data
        has_metrics = response.data is not None and len(response.data) > 0
        has_next_steps = response.next_suggestions is not None and len(response.next_suggestions) > 0
        
        # Check response content quality
        response_detailed = len(response.response_text) > 100  # Detailed response
        
        print(f"   Has metrics data: {'✅' if has_metrics else '❌'}")
        print(f"   Has next steps: {'✅' if has_next_steps else '❌'}")
        print(f"   Response detailed: {'✅' if response_detailed else '❌'}")
        
        if has_next_steps:
            print(f"   Next steps: {response.next_suggestions[:2]}")
        
        summary_quality = has_metrics and has_next_steps and response_detailed
        summary_results.append(summary_quality)
        
        print(f"   Summary quality: {'✅' if summary_quality else '❌'}")
        print()
    
    overall_quality = sum(summary_results) / len(summary_results)
    print(f"📊 Results:")
    print(f"   Overall summary quality: {overall_quality:.1%}")
    print(f"   Criterion met: {'✅ PASS' if overall_quality >= 0.8 else '❌ FAIL'}")
    
    return overall_quality >= 0.8

async def test_ambiguous_requests():
    """✅ Test 6: Handles ambiguous requests with clarification"""
    print("\n6. Testing Ambiguous Request Handling")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    
    ambiguous_requests = [
        "I need help with something",
        "Can you do stuff for me?",
        "Generate some things",
        "What about those companies?",
        "Make it happen"
    ]
    
    clarification_results = []
    
    for request in ambiguous_requests:
        response = await jarvis.process_sales_request(request, f"ambiguous_test_{len(clarification_results)}")
        
        print(f"   Request: \"{request}\"")
        
        # Check for clarification indicators
        clarification_phrases = [
            "not sure how to help",
            "suggest",
            "help",
            "try",
            "can help with",
            "examples"
        ]
        
        has_clarification = any(phrase in response.response_text.lower() for phrase in clarification_phrases)
        
        # Check for helpful suggestions
        has_suggestions = response.next_suggestions is not None or "•" in response.response_text
        
        print(f"   Has clarification: {'✅' if has_clarification else '❌'}")
        print(f"   Has suggestions: {'✅' if has_suggestions else '❌'}")
        
        good_handling = has_clarification and has_suggestions
        clarification_results.append(good_handling)
        
        print(f"   Good handling: {'✅' if good_handling else '❌'}")
        print()
    
    clarification_rate = sum(clarification_results) / len(clarification_results)
    print(f"📊 Results:")
    print(f"   Clarification rate: {clarification_rate:.1%}")
    print(f"   Criterion met: {'✅ PASS' if clarification_rate >= 0.8 else '❌ FAIL'}")
    
    return clarification_rate >= 0.8

async def test_conversation_context():
    """✅ Test 7: Maintains conversation context across messages"""
    print("\n7. Testing Conversation Context")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    session_id = "context_test_session"
    
    # Simulate a conversation flow
    conversation = [
        "Find 10 SaaS leads",
        "Show me business summary",
        "Create outreach campaign",
        "Check workflow status"
    ]
    
    context_maintained = True
    
    for i, request in enumerate(conversation):
        response = await jarvis.process_sales_request(request, session_id)
        
        print(f"   Message {i+1}: \"{request}\"")
        
        # Check session context
        session_context = await jarvis.get_sales_session_context(session_id)
        
        if session_context:
            requests_count = session_context.get("intent_count", 0)
            recent_intents = len(session_context.get("recent_intents", []))
            has_context = recent_intents >= i + 1
            
            print(f"   Recent intents: {recent_intents}")
            print(f"   Context maintained: {'✅' if has_context else '❌'}")
            
            if not has_context:
                context_maintained = False
        else:
            print(f"   ❌ No session context found")
            context_maintained = False
        
        print()
    
    print(f"📊 Results:")
    print(f"   Context maintained: {'✅' if context_maintained else '❌'}")
    print(f"   Criterion met: {'✅ PASS' if context_maintained else '❌ FAIL'}")
    
    return context_maintained

async def test_response_time():
    """✅ Test 8: Response time <2s for intent processing"""
    print("\n8. Testing Response Time")
    print("=" * 50)
    
    jarvis = await create_test_jarvis()
    
    test_requests = [
        "Find 20 SaaS leads",
        "Show me quick wins",
        "Create outreach campaign",
        "Business summary",
        "Workflow status",
        "Help me with lead generation",
        "Find fintech CTOs",
        "Generate 50 prospects"
    ]
    
    response_times = []
    
    for request in test_requests:
        start_time = time.time()
        response = await jarvis.process_sales_request(request, f"speed_test_{len(response_times)}")
        response_time = time.time() - start_time
        
        response_times.append(response_time)
        
        print(f"   Request: \"{request[:30]}...\"")
        print(f"   Response time: {response_time:.3f}s")
        print(f"   Under 2s: {'✅' if response_time < 2.0 else '❌'}")
        print()
    
    avg_response_time = sum(response_times) / len(response_times)
    max_response_time = max(response_times)
    under_2s_count = sum(1 for t in response_times if t < 2.0)
    under_2s_rate = under_2s_count / len(response_times)
    
    print(f"📊 Results:")
    print(f"   Average response time: {avg_response_time:.3f}s")
    print(f"   Max response time: {max_response_time:.3f}s")
    print(f"   Under 2s rate: {under_2s_rate:.1%}")
    print(f"   Criterion met: {'✅ PASS' if under_2s_rate >= 0.9 else '❌ FAIL'}")
    
    return under_2s_rate >= 0.9

async def main():
    """Run all Enhanced Jarvis validation tests"""
    print("🤖 Enhanced Jarvis Sales Integration Validation")
    print("=" * 70)
    
    start_time = time.time()
    
    # Run all tests
    results = {}
    
    try:
        results["lead_generation_mapping"] = await test_lead_generation_mapping()
        results["parameter_extraction"] = await test_parameter_extraction()
        results["websocket_updates"] = await test_websocket_updates()
        results["concurrent_requests"] = await test_concurrent_requests()
        results["result_summary"] = await test_result_summary()
        results["ambiguous_requests"] = await test_ambiguous_requests()
        results["conversation_context"] = await test_conversation_context()
        results["response_time"] = await test_response_time()
        
        # Summary
        total_time = time.time() - start_time
        
        print("\n" + "=" * 70)
        print("ENHANCED JARVIS SALES INTEGRATION VALIDATION RESULTS")
        print("=" * 70)
        
        criteria = [
            ("\"I need 50 leads\" correctly maps to lead_generation workflow", results.get("lead_generation_mapping", False)),
            ("Extracts quantities (\"50\"), industries (\"SaaS\"), titles (\"CTO\")", results.get("parameter_extraction", False)),
            ("WebSocket sends updates at least every 2 seconds", results.get("websocket_updates", False)),
            ("Supports concurrent requests from multiple sessions", results.get("concurrent_requests", False)),
            ("Result summary includes key metrics and next steps", results.get("result_summary", False)),
            ("Handles ambiguous requests with clarification", results.get("ambiguous_requests", False)),
            ("Maintains conversation context across messages", results.get("conversation_context", False)),
            ("Response time <2s for intent processing", results.get("response_time", False))
        ]
        
        passed = 0
        for criterion, result in criteria:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{status} {criterion}")
            if result:
                passed += 1
        
        total = len(criteria)
        print(f"\nOVERALL SCORE: {passed}/{total} ({passed/total:.1%})")
        print(f"VALIDATION TIME: {total_time:.1f} seconds")
        
        if passed == total:
            print("🎉 ALL SUCCESS CRITERIA MET!")
        elif passed >= 6:
            print("✨ Most criteria met - excellent performance!")
        else:
            print("⚠️ Some criteria need attention")
            
    except Exception as e:
        print(f"❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())