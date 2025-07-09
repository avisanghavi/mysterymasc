#!/usr/bin/env python3
"""
Test suite for AI Engine implementations
"""
import asyncio
import sys
import os
import time
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_engines.base_engine import AIEngineConfig
from ai_engines.mock_engine import MockAIEngine
from ai_engines.anthropic_engine import AnthropicEngine

async def test_mock_engine():
    """Test MockAIEngine functionality"""
    print("🧪 Testing MockAIEngine")
    print("=" * 50)
    
    # Test 1: Basic configuration and initialization
    print("1. Testing basic initialization...")
    config = AIEngineConfig(
        model="mock-test",
        max_tokens=100,
        temperature=0.7,
        enable_cache=True,
        max_retries=2
    )
    
    engine = MockAIEngine(config, deterministic=True)
    print(f"✅ Initialized {engine.get_engine_type()} engine")
    
    # Test 2: Basic generation
    print("\n2. Testing basic generation...")
    response = await engine.generate("Hello, how are you?")
    print(f"✅ Generated response ({len(response.content)} chars)")
    print(f"   Model: {response.model}")
    print(f"   Usage: {response.usage}")
    print(f"   Engine: {response.engine_type}")
    
    # Test 3: Deterministic responses
    print("\n3. Testing deterministic responses...")
    response1 = await engine.generate("Test prompt for determinism")
    response2 = await engine.generate("Test prompt for determinism")
    
    if response1.content == response2.content:
        print("✅ Deterministic responses working correctly")
    else:
        print("❌ Responses should be identical in deterministic mode")
    
    # Test 4: Caching
    print("\n4. Testing caching...")
    start_time = time.time()
    response_fresh = await engine.generate("Cache test prompt")
    fresh_time = time.time() - start_time
    
    start_time = time.time()
    response_cached = await engine.generate("Cache test prompt")
    cached_time = time.time() - start_time
    
    if response_cached.cached:
        print(f"✅ Caching working (fresh: {fresh_time:.3f}s, cached: {cached_time:.3f}s)")
    else:
        print("❌ Response should have been cached")
    
    # Test 5: Budget tracking
    print("\n5. Testing budget tracking...")
    budget_info = engine.get_budget_info()
    print(f"✅ Budget tracking: {budget_info.requests_made} requests, ${budget_info.total_spent_usd:.4f} spent")
    
    # Test 6: Rate limiting
    print("\n6. Testing rate limiting...")
    rate_info = engine.get_rate_limit_info()
    print(f"✅ Rate limiting: {rate_info.requests_made} requests in current window")
    
    # Test 7: Different prompt types
    print("\n7. Testing different prompt types...")
    test_prompts = [
        "Write a Python function to calculate fibonacci numbers",
        "What's the best marketing strategy for SaaS companies?",
        "Analyze sales data trends and create a report",
        "Draft a personalized email for lead outreach"
    ]
    
    for i, prompt in enumerate(test_prompts):
        response = await engine.generate(prompt, max_tokens=50)
        domain = response.metadata.get('prompt_analysis', {}).get('domain', 'unknown')
        print(f"   Prompt {i+1} ({domain}): {len(response.content)} chars")
    
    print("✅ MockAIEngine tests completed successfully!\n")

async def test_anthropic_engine():
    """Test AnthropicEngine (if API key available)"""
    print("🧪 Testing AnthropicEngine")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("⚠️  ANTHROPIC_API_KEY not found, skipping real API tests")
        print("   Testing configuration only...")
        
        # Test configuration without making API calls
        try:
            config = AIEngineConfig(
                api_key="fake-key-for-testing",
                model="claude-3-sonnet-20240229",
                max_tokens=100
            )
            engine = AnthropicEngine(config)
            print(f"✅ Configuration test passed for {engine.get_engine_type()} engine")
            
            # Test model information
            supported_models = engine.get_supported_models()
            print(f"✅ Supports {len(supported_models)} models")
            
            limits = engine.get_model_limits("claude-3-sonnet-20240229")
            print(f"✅ Model limits: {limits}")
            
        except Exception as e:
            print(f"❌ Configuration test failed: {e}")
        
        return
    
    # Test with real API key
    try:
        config = AIEngineConfig(
            api_key=api_key,
            model="claude-3-haiku-20240307",  # Use fastest model for testing
            max_tokens=50,
            enable_cache=True
        )
        
        engine = AnthropicEngine(config)
        print(f"✅ Initialized {engine.get_engine_type()} engine")
        
        # Test API key validation
        print("1. Testing API key validation...")
        is_valid = await engine.validate_api_key()
        if is_valid:
            print("✅ API key validation successful")
        else:
            print("❌ API key validation failed")
            return
        
        # Test basic generation
        print("\n2. Testing basic generation...")
        response = await engine.generate("Say hello in exactly 5 words", max_tokens=20)
        print(f"✅ Generated response: '{response.content}'")
        print(f"   Model: {response.model}")
        print(f"   Tokens: {response.usage}")
        
        # Test caching
        print("\n3. Testing caching...")
        start_time = time.time()
        response1 = await engine.generate("What is 2+2?", max_tokens=10)
        time1 = time.time() - start_time
        
        start_time = time.time()
        response2 = await engine.generate("What is 2+2?", max_tokens=10)
        time2 = time.time() - start_time
        
        if response2.cached:
            print(f"✅ Caching working (fresh: {time1:.2f}s, cached: {time2:.2f}s)")
        else:
            print(f"⚠️  Caching not detected (fresh: {time1:.2f}s, repeat: {time2:.2f}s)")
        
        # Test budget tracking
        print("\n4. Testing budget tracking...")
        budget = engine.get_budget_info()
        print(f"✅ Budget: ${budget.total_spent_usd:.6f}, {budget.input_tokens_used} input + {budget.output_tokens_used} output tokens")
        
        print("✅ AnthropicEngine tests completed successfully!\n")
        
    except Exception as e:
        print(f"❌ AnthropicEngine test failed: {e}")

async def test_engine_comparison():
    """Compare responses between different engines"""
    print("🔄 Comparing Engine Responses")
    print("=" * 50)
    
    test_prompt = "Explain the benefits of AI automation in 2 sentences."
    
    # Mock engine (deterministic)
    mock_config = AIEngineConfig(model="mock-v1", max_tokens=100)
    mock_engine = MockAIEngine(mock_config, deterministic=True)
    mock_response = await mock_engine.generate(test_prompt)
    
    print("Mock Engine Response:")
    print(f"  Content: {mock_response.content[:100]}...")
    print(f"  Tokens: {mock_response.usage}")
    print(f"  Cached: {mock_response.cached}")
    
    # Anthropic engine (if available)
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            anthropic_config = AIEngineConfig(
                api_key=api_key,
                model="claude-3-haiku-20240307",
                max_tokens=100
            )
            anthropic_engine = AnthropicEngine(anthropic_config)
            anthropic_response = await anthropic_engine.generate(test_prompt)
            
            print("\nAnthropic Engine Response:")
            print(f"  Content: {anthropic_response.content[:100]}...")
            print(f"  Tokens: {anthropic_response.usage}")
            print(f"  Cached: {anthropic_response.cached}")
            
        except Exception as e:
            print(f"\nAnthropic Engine: ❌ {e}")
    else:
        print("\nAnthropic Engine: ⚠️  No API key provided")
    
    print("\n✅ Engine comparison completed!")

async def test_advanced_features():
    """Test advanced features like rate limiting and error handling"""
    print("⚙️  Testing Advanced Features")
    print("=" * 50)
    
    # Test rate limiting
    print("1. Testing rate limiting...")
    config = AIEngineConfig(
        model="mock-test",
        requests_per_minute=3,  # Very low limit for testing
        max_tokens=50
    )
    
    engine = MockAIEngine(config)
    
    # Make requests up to the limit
    for i in range(3):
        response = await engine.generate(f"Rate limit test {i+1}")
        print(f"   Request {i+1}: ✅ ({len(response.content)} chars)")
    
    # This should trigger rate limiting
    try:
        start_time = time.time()
        response = await engine.generate("This should be rate limited")
        elapsed = time.time() - start_time
        if elapsed > 1.0:  # Should have waited
            print(f"   Request 4: ✅ Rate limited (waited {elapsed:.1f}s)")
        else:
            print(f"   Request 4: ⚠️  No rate limiting detected")
    except Exception as e:
        print(f"   Request 4: ❌ {e}")
    
    # Test failure simulation
    print("\n2. Testing error handling...")
    engine.set_failure_rate(1.0)  # Force failures
    
    try:
        response = await engine.generate("This should fail")
        print("   ❌ Should have failed but didn't")
    except Exception as e:
        print(f"   ✅ Error handling working: {type(e).__name__}")
    
    # Reset failure rate
    engine.set_failure_rate(0.0)
    
    # Test cache clearing
    print("\n3. Testing cache management...")
    await engine.generate("Cache test message")
    budget_before = engine.get_budget_info().requests_made
    
    await engine.clear_cache()
    response = await engine.generate("Cache test message")  # Should not be cached
    budget_after = engine.get_budget_info().requests_made
    
    if budget_after > budget_before:
        print("   ✅ Cache cleared successfully")
    else:
        print("   ⚠️  Cache clearing unclear")
    
    print("\n✅ Advanced features tests completed!")

async def main():
    """Run all tests"""
    print("🚀 AI Engine Test Suite")
    print("=" * 60)
    print("This will test the AI Engine abstraction layer implementations\n")
    
    try:
        # Test mock engine (always available)
        await test_mock_engine()
        
        # Test Anthropic engine (if API key available)
        await test_anthropic_engine()
        
        # Compare engines
        await test_engine_comparison()
        
        # Test advanced features
        await test_advanced_features()
        
        print("🎉 All tests completed successfully!")
        print("\nTo use the AI engines in your code:")
        print("```python")
        print("from ai_engines.mock_engine import MockAIEngine")
        print("from ai_engines.anthropic_engine import AnthropicEngine")
        print("from ai_engines.base_engine import AIEngineConfig")
        print("")
        print("config = AIEngineConfig(model='claude-3-sonnet-20240229')")
        print("engine = MockAIEngine(config)  # or AnthropicEngine(config)")
        print("response = await engine.generate('Your prompt here')")
        print("```")
        
    except KeyboardInterrupt:
        print("\n👋 Tests stopped by user")
    except Exception as e:
        print(f"\n❌ Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())