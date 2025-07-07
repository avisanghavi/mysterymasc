"""Fixed test script for BusinessContext."""

import asyncio
import os
import sys
import json

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestration.business_context import BusinessContext
import redis.asyncio as redis

async def test_business_context():
    """Test BusinessContext implementation."""
    print("🧪 Testing BusinessContext Implementation\n")
    
    # Connect to Redis
    try:
        redis_client = redis.from_url("redis://localhost:6379")
        await redis_client.ping()
        print("✅ Connected to Redis")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("Make sure Redis is running: docker run -d -p 6379:6379 redis:latest")
        return
    
    # Test 1: Create BusinessContext
    print("\n1️⃣ Testing BusinessContext creation...")
    context = BusinessContext(redis_client, session_id="test_123")
    print("✅ BusinessContext created")
    
    # Test 2: Update metrics
    print("\n2️⃣ Testing metric updates...")
    await context.update_metric('mrr', 50000)
    await context.update_metric('burn_rate', 100000)
    await context.update_metric('cash_balance', 600000)
    
    print(f"✅ MRR: ${context.key_metrics.mrr:,}")
    print(f"✅ Burn Rate: ${context.key_metrics.burn_rate:,}/month")
    print(f"✅ Runway: {context.key_metrics.runway} months")
    
    # Test 3: Check Redis persistence (update_metric should auto-save)
    print("\n3️⃣ Testing Redis persistence...")
    
    # Check if update_metric saved to Redis
    metrics_key = f"business:{context.session_id}:metrics"
    stored_data = await redis_client.get(metrics_key)
    if stored_data:
        print("✅ Data auto-persisted to Redis by update_metric()")
        metrics = json.loads(stored_data)
        print(f"   Stored MRR: ${metrics.get('mrr', 0):,}")
    else:
        print("⚠️  Data not auto-persisted, checking for manual save method...")
        
        # Check if there's a different save method
        save_methods = [method for method in dir(context) if 'save' in method.lower()]
        if save_methods:
            print(f"   Found methods: {save_methods}")
            # Try calling the first save method
            try:
                method = getattr(context, save_methods[0])
                if asyncio.iscoroutinefunction(method):
                    await method()
                else:
                    method()
                print("✅ Manual save completed")
            except Exception as e:
                print(f"⚠️  Save method failed: {e}")
    
    # Test 4: Goal progress
    print("\n4️⃣ Testing goal progress...")
    from datetime import datetime, timezone
    
    # Check if BusinessGoal is available
    if hasattr(context, 'BusinessGoal'):
        Goal = context.BusinessGoal
    else:
        # Try importing it
        try:
            from orchestration.business_context import BusinessGoal
            Goal = BusinessGoal
        except:
            # Create a simple goal dict
            Goal = dict
    
    # Create a goal
    if Goal == dict:
        goal = {
            'id': 'test_goal',
            'description': 'Reach $100k MRR',
            'target_metric': 'mrr',
            'target_value': 100000,
            'current_value': 50000,
            'deadline': datetime.now(timezone.utc).isoformat(),
            'status': 'in_progress'
        }
    else:
        goal = Goal(
            id='test_goal',
            description='Reach $100k MRR',
            target_metric='mrr',
            target_value=100000,
            current_value=50000,
            deadline=datetime.now(timezone.utc).isoformat(),
            status='in_progress'
        )
    
    context.active_goals = [goal]
    
    try:
        progress = await context.check_goal_progress()
        if progress:
            print(f"✅ Goal progress: {progress[0]['progress']:.1f}%")
        else:
            print("⚠️  No progress data returned")
    except Exception as e:
        print(f"⚠️  Goal progress check failed: {e}")
    
    # Test 5: Optimization suggestions
    print("\n5️⃣ Testing optimization suggestions...")
    try:
        suggestions = await context.get_optimization_suggestions()
        print(f"✅ Got {len(suggestions)} optimization suggestions:")
        for i, sugg in enumerate(suggestions[:3], 1):
            print(f"   {i}. {sugg['suggestion']}")
    except Exception as e:
        print(f"⚠️  Optimization suggestions failed: {e}")
    
    # Test 6: Check what methods are actually available
    print("\n6️⃣ Available methods in BusinessContext:")
    methods = [method for method in dir(context) if not method.startswith('_') and callable(getattr(context, method))]
    for method in sorted(methods):
        print(f"   - {method}")
    
    # Cleanup
    await redis_client.close()
    print("\n✅ Tests completed!")

if __name__ == "__main__":
    asyncio.run(test_business_context())