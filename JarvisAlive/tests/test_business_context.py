"""Comprehensive tests for BusinessContext implementation."""

import pytest
import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from orchestration.business_context import BusinessContext, CompanyProfile, KeyMetrics, BusinessGoal, ResourceConstraints

class TestBusinessContext:
    """Test suite for BusinessContext functionality."""
    
    @pytest.fixture
    async def mock_redis(self):
        """Create a mock Redis client."""
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.setex = AsyncMock(return_value=True)
        return redis_client
    
    @pytest.fixture
    async def business_context(self, mock_redis):
        """Create a BusinessContext instance with mock Redis."""
        return BusinessContext(mock_redis, session_id="test_session")
    
    # Test 1: Verify all required components exist
    async def test_complete_structure(self, business_context):
        """Verify all required attributes and methods exist."""
        # Check attributes
        assert hasattr(business_context, 'company_profile')
        assert hasattr(business_context, 'key_metrics')
        assert hasattr(business_context, 'active_goals')
        assert hasattr(business_context, 'resource_constraints')
        
        # Check methods
        assert hasattr(business_context, 'update_metric')
        assert hasattr(business_context, 'check_goal_progress')
        assert hasattr(business_context, 'get_optimization_suggestions')
        
        # Check Redis integration
        assert business_context.redis_client is not None
        assert business_context.session_id == "test_session"
    
    # Test 2: Test metric updates and persistence
    async def test_update_metric(self, business_context, mock_redis):
        """Test metric updates work correctly."""
        # Update various metrics
        await business_context.update_metric('mrr', 50000)
        await business_context.update_metric('burn_rate', 100000)
        await business_context.update_metric('cac', 1500)
        
        # Verify updates
        assert business_context.key_metrics.mrr == 50000
        assert business_context.key_metrics.burn_rate == 100000
        assert business_context.key_metrics.cac == 1500
        
        # Verify Redis was called
        assert mock_redis.setex.called
        call_args = mock_redis.setex.call_args[0]
        assert call_args[0] == "business:test_session:metrics"
        assert call_args[1] == 86400  # 24-hour TTL
    
    # Test 3: Test derived metrics (runway calculation)
    async def test_derived_metrics(self, business_context):
        """Test automatic calculation of derived metrics."""
        # Set up metrics for runway calculation
        await business_context.update_metric('cash_balance', 1000000)
        await business_context.update_metric('burn_rate', 100000)
        
        # Runway should be automatically calculated
        assert business_context.key_metrics.runway == 10  # months
    
    # Test 4: Test goal progress tracking
    async def test_goal_progress(self, business_context):
        """Test goal progress checking."""
        # Add test goals
        goal1 = BusinessGoal(
            id="goal1",
            description="Reach $100k MRR",
            target_metric="mrr",
            target_value=100000,
            current_value=50000,
            deadline=datetime.now(timezone.utc).isoformat(),
            status="in_progress"
        )
        business_context.active_goals = [goal1]
        
        # Update metric
        await business_context.update_metric('mrr', 60000)
        
        # Check progress
        progress = await business_context.check_goal_progress()
        assert len(progress) == 1
        assert progress[0]['progress'] == 60.0  # 60% complete
    
    # Test 5: Test optimization suggestions
    async def test_optimization_suggestions(self, business_context):
        """Test getting optimization suggestions."""
        # Set up context
        business_context.company_profile.stage = "seed"
        business_context.company_profile.industry = "SaaS"
        await business_context.update_metric('burn_rate', 150000)
        await business_context.update_metric('runway', 6)
        
        # Get suggestions
        suggestions = await business_context.get_optimization_suggestions()
        
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        # Should suggest cost reduction due to short runway
        assert any('cost' in s['suggestion'].lower() for s in suggestions)
    
    # Test 6: Test Redis key format
    async def test_redis_key_format(self, business_context, mock_redis):
        """Test Redis keys follow the specified format."""
        await business_context.save_to_redis()
        
        # Check all Redis keys used
        calls = mock_redis.setex.call_args_list
        keys_used = [call[0][0] for call in calls]
        
        expected_keys = [
            "business:test_session:metrics",
            "business:test_session:company_profile",
            "business:test_session:goals",
            "business:test_session:constraints"
        ]
        
        for key in expected_keys:
            assert any(key in used for used in keys_used)
    
    # Test 7: Test loading from Redis
    async def test_load_from_redis(self, mock_redis):
        """Test loading existing business context from Redis."""
        # Mock Redis data
        mock_data = {
            "business:test_session:company_profile": json.dumps({
                "stage": "series_a",
                "industry": "FinTech"
            }),
            "business:test_session:metrics": json.dumps({
                "mrr": 200000,
                "burn_rate": 300000
            })
        }
        
        mock_redis.get = AsyncMock(side_effect=lambda key: mock_data.get(key))
        
        # Create new context that should load from Redis
        context = BusinessContext(mock_redis, session_id="test_session")
        await context.load_from_redis()
        
        assert context.company_profile.stage == "series_a"
        assert context.key_metrics.mrr == 200000

# Integration test with real Redis (optional)
class TestBusinessContextIntegration:
    """Integration tests with real Redis."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_full_workflow(self, real_redis_client):
        """Test complete workflow with real Redis."""
        context = BusinessContext(real_redis_client, session_id="integration_test")
        
        # Set company profile
        context.company_profile.stage = "seed"
        context.company_profile.industry = "SaaS"
        
        # Update metrics
        await context.update_metric('mrr', 75000)
        await context.update_metric('burn_rate', 150000)
        
        # Add goal
        goal = BusinessGoal(
            id="test_goal",
            description="Reach $150k MRR",
            target_metric="mrr",
            target_value=150000,
            current_value=75000,
            deadline="2024-12-31",
            status="in_progress"
        )
        context.active_goals.append(goal)
        
        # Save to Redis
        await context.save_to_redis()
        
        # Create new instance and load
        context2 = BusinessContext(real_redis_client, session_id="integration_test")
        await context2.load_from_redis()
        
        # Verify data persisted correctly
        assert context2.company_profile.stage == "seed"
        assert context2.key_metrics.mrr == 75000
        assert len(context2.active_goals) == 1
        assert context2.active_goals[0].description == "Reach $150k MRR"