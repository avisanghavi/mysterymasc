#!/usr/bin/env python3
"""
Validate Jarvis Integration Success Criteria
Tests all 8 success criteria for the enhanced Jarvis system
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

from orchestration.jarvis import Jarvis, SalesIntentType, SalesIntent, SalesResponse, JarvisConfig
from orchestration.orchestrator import OrchestratorConfig

# Mock Redis for testing
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
    
    async def subscribe(self, channel, callback):
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)

async def create_test_jarvis():
    """Create a Jarvis instance for testing"""
    # Create mock config
    orchestrator_config = OrchestratorConfig(
        anthropic_api_key="test_key",
        redis_url="redis://localhost:6379",
        redis_password=None
    )
    
    jarvis_config = JarvisConfig(
        orchestrator_config=orchestrator_config,
        max_concurrent_departments=5,
        business_context_refresh_interval=300,
        enable_autonomous_department_creation=True
    )
    
    # Create Jarvis instance
    jarvis = Jarvis(jarvis_config)
    
    # Mock Redis client
    jarvis.redis_client = MockRedis()
    
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
        "I want to find new leads"
    ]
    
    results = []
    
    for request in test_requests:
        start_time = time.time()
        response = await jarvis.process_sales_request(request, "test_session_1")
        processing_time = time.time() - start_time
        
        # Check if intent was correctly identified
        session_context = await jarvis.get_sales_session_context("test_session_1")
        last_intent = session_context["recent_intents"][0] if session_context and session_context["recent_intents"] else None
        
        is_lead_generation = last_intent and last_intent["intent_type"] == SalesIntentType.LEAD_GENERATION.value
        
        print(f"   Request: \"{request}\"")
        print(f"   Intent: {last_intent['intent_type'] if last_intent else 'None'}")
        print(f"   Confidence: {last_intent['confidence']:.2f if last_intent else 'N/A'}")
        print(f"   Processing time: {processing_time:.3f}s")
        print(f"   Correct mapping: {'✅' if is_lead_generation else '❌'}")
        print()
        
        results.append({
            "request": request,
            "intent": last_intent['intent_type'] if last_intent else 'unknown',
            "confidence": last_intent['confidence'] if last_intent else 0.0,
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
            "expected_params": {"max_results": 50}
        },
        {
            "request": "Find me 25 SaaS CTOs",
            "expected_params": {"max_results": 25, "industries": ["SaaS"], "titles": ["CTO"]}
        },
        {
            "request": "Target fintech VPs and directors",
            "expected_params": {"industries": ["FinTech"], "titles": ["VP", "Director"]}
        },
        {
            "request": "Get 100 healthcare CEOs",
            "expected_params": {"max_results": 100, "industries": ["Healthcare"], "titles": ["CEO"]}
        },
        {
            "request": "Find manufacturing managers",
            "expected_params": {"industries": ["Manufacturing"], "titles": ["Manager"]}
        }
    ]
    
    extraction_results = []
    
    for case in test_cases:
        response = await jarvis.process_sales_request(case["request"], "test_session_2")
        
        # Get the last intent with parameters
        session_context = await jarvis.get_sales_session_context("test_session_2")
        last_intent = session_context["recent_intents"][0] if session_context and session_context["recent_intents"] else None
        extracted_params = last_intent["parameters"] if last_intent else {}
        
        print(f"   Request: \"{case['request']}\"")
        print(f"   Expected: {case['expected_params']}")
        print(f"   Extracted: {extracted_params}")
        
        # Check parameter accuracy
        matches = 0
        total_expected = len(case["expected_params"])
        
        for key, expected_value in case["expected_params"].items():
            if key in extracted_params:
                if isinstance(expected_value, list):
                    # For lists, check if all expected items are present
                    extracted_list = extracted_params[key]
                    if all(item in extracted_list for item in expected_value):
                        matches += 1
                        print(f"   ✅ {key}: {extracted_list}")
                    else:
                        print(f"   ❌ {key}: {extracted_list} (expected {expected_value})")
                else:
                    # For scalars, exact match
                    if extracted_params[key] == expected_value:
                        matches += 1
                        print(f"   ✅ {key}: {extracted_params[key]}")
                    else:
                        print(f"   ❌ {key}: {extracted_params[key]} (expected {expected_value})")
            else:
                print(f"   ❌ {key}: Missing (expected {expected_value})")
        
        accuracy = matches / total_expected if total_expected > 0 else 0
        extraction_results.append(accuracy)
        print(f"   Accuracy: {accuracy:.1%}")
        print()
    
    overall_accuracy = sum(extraction_results) / len(extraction_results)
    print(f"📊 Results:")
    print(f"   Overall accuracy: {overall_accuracy:.1%}")
    print(f"   Criterion met: {'✅ PASS' if overall_accuracy >= 0.7 else '❌ FAIL'}")
    
    return overall_accuracy >= 0.7

async def test_websocket_updates():
    """✅ Test 3: WebSocket sends updates at least every 2 seconds"""
    print("\n3. Testing WebSocket Progress Updates")
    print("=" * 50)
    
    jarvis = JarvisEnhanced()
    
    # Track progress updates
    progress_updates = []
    update_times = []
    
    async def progress_callback(message):
        """Callback to capture progress updates"""
        update_data = json.loads(message)
        progress_updates.append(update_data)
        update_times.append(time.time())
        print(f"   Progress: {update_data['progress']}% - {update_data['message']}")
    
    # Subscribe to progress updates
    session_id = "websocket_test_session"
    await jarvis.get_progress_updates(session_id, progress_callback)
    
    # Start lead generation (which sends progress updates)
    start_time = time.time()
    response = await jarvis.process_request("Find 20 SaaS leads", session_id)
    total_time = time.time() - start_time
    
    print(f"   Total execution time: {total_time:.2f}s")
    print(f"   Progress updates received: {len(progress_updates)}")
    
    # Check update frequency
    if len(update_times) >= 2:
        # Calculate intervals between updates
        intervals = []
        for i in range(1, len(update_times)):
            interval = update_times[i] - update_times[i-1]
            intervals.append(interval)
        
        avg_interval = sum(intervals) / len(intervals)
        max_interval = max(intervals)
        
        print(f"   Average interval: {avg_interval:.2f}s")
        print(f"   Max interval: {max_interval:.2f}s")
        
        # Check if updates are frequent enough (at least every 2 seconds)
        frequent_enough = max_interval <= 2.0
        
        print(f"   Updates frequent enough: {'✅' if frequent_enough else '❌'}")
        print(f"   Criterion met: {'✅ PASS' if frequent_enough and len(progress_updates) >= 2 else '❌ FAIL'}")
        
        return frequent_enough and len(progress_updates) >= 2
    else:
        print(f"   ❌ Not enough updates received")
        print(f"   Criterion met: ❌ FAIL")
        return False

async def test_concurrent_requests():
    """✅ Test 4: Supports concurrent requests from multiple sessions"""
    print("\n4. Testing Concurrent Requests")
    print("=" * 50)
    
    jarvis = JarvisEnhanced()
    
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
        task = jarvis.process_request(request, session_id)
        tasks.append(task)
    
    responses = await asyncio.gather(*tasks)
    
    concurrent_time = time.time() - start_time
    
    print(f"   Concurrent execution time: {concurrent_time:.2f}s")
    print(f"   Requests processed: {len(responses)}")
    
    # Verify all requests succeeded
    all_successful = all(response.response_text for response in responses)
    
    # Check session isolation
    session_contexts = []
    for _, session_id in requests:
        context = jarvis.get_session_context(session_id)
        session_contexts.append(context)
    
    sessions_isolated = len(set(id(ctx) for ctx in session_contexts)) == len(session_contexts)
    
    print(f"   All requests successful: {'✅' if all_successful else '❌'}")
    print(f"   Sessions properly isolated: {'✅' if sessions_isolated else '❌'}")
    print(f"   Performance acceptable: {'✅' if concurrent_time < 10 else '❌'}")
    
    criterion_met = all_successful and sessions_isolated and concurrent_time < 10
    print(f"   Criterion met: {'✅ PASS' if criterion_met else '❌ FAIL'}")
    
    return criterion_met

async def test_result_summary():
    """✅ Test 5: Result summary includes key metrics and next steps"""
    print("\n5. Testing Result Summary")
    print("=" * 50)
    
    jarvis = JarvisEnhanced()
    
    test_requests = [
        "Find 15 SaaS CTOs",
        "Show me 5 quick wins",
        "Business summary"
    ]
    
    summary_results = []
    
    for request in test_requests:
        response = await jarvis.process_request(request, "summary_test_session")
        
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
        
        if has_metrics:
            key_count = len(response.data.keys())
            print(f"   Data keys: {key_count}")
        
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
    
    jarvis = JarvisEnhanced()
    
    ambiguous_requests = [
        "I need help with something",
        "Can you do stuff for me?",
        "Generate some things",
        "What about those companies?",
        "Make it happen"
    ]
    
    clarification_results = []
    
    for request in ambiguous_requests:
        response = await jarvis.process_request(request, "ambiguous_test_session")
        
        print(f"   Request: \"{request}\"")
        
        # Check for clarification indicators
        clarification_phrases = [
            "not sure how to help",
            "can you be more specific",
            "let me suggest",
            "try asking",
            "help me understand",
            "suggest some things"
        ]
        
        has_clarification = any(phrase in response.response_text.lower() for phrase in clarification_phrases)
        
        # Check for helpful suggestions
        has_suggestions = response.next_suggestions is not None or "suggest" in response.response_text.lower()
        
        # Check for examples or alternatives
        has_examples = "example" in response.response_text.lower() or "try" in response.response_text.lower()
        
        print(f"   Has clarification: {'✅' if has_clarification else '❌'}")
        print(f"   Has suggestions: {'✅' if has_suggestions else '❌'}")
        print(f"   Has examples: {'✅' if has_examples else '❌'}")
        
        good_handling = has_clarification and (has_suggestions or has_examples)
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
    
    jarvis = JarvisEnhanced()
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
        response = await jarvis.process_request(request, session_id)
        
        print(f"   Message {i+1}: \"{request}\"")
        
        # Check session context
        session_context = jarvis.get_session_context(session_id)
        
        if session_context:
            requests_count = len(session_context["requests"])
            has_context = requests_count == i + 1
            
            print(f"   Requests in session: {requests_count}")
            print(f"   Context maintained: {'✅' if has_context else '❌'}")
            
            if not has_context:
                context_maintained = False
        else:
            print(f"   ❌ No session context found")
            context_maintained = False
        
        print()
    
    # Check final context state
    final_context = jarvis.get_session_context(session_id)
    if final_context:
        total_requests = len(final_context["requests"])
        has_history = total_requests == len(conversation)
        
        print(f"   Final context check:")
        print(f"   Total requests tracked: {total_requests}")
        print(f"   Expected requests: {len(conversation)}")
        print(f"   Complete history: {'✅' if has_history else '❌'}")
        
        context_maintained = context_maintained and has_history
    
    print(f"📊 Results:")
    print(f"   Context maintained: {'✅' if context_maintained else '❌'}")
    print(f"   Criterion met: {'✅ PASS' if context_maintained else '❌ FAIL'}")
    
    return context_maintained

async def test_response_time():
    """✅ Test 8: Response time <2s for intent processing"""
    print("\n8. Testing Response Time")
    print("=" * 50)
    
    jarvis = JarvisEnhanced()
    
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
        response = await jarvis.process_request(request, f"speed_test_{len(response_times)}")
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
    """Run all Jarvis Integration validation tests"""
    print("🤖 Jarvis Integration Success Criteria Validation")
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
        print("JARVIS INTEGRATION SUCCESS CRITERIA VALIDATION RESULTS")
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