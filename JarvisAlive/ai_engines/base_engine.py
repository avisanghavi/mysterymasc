"""
Base AI Engine - Abstract base class and core models for AI engine abstraction layer
"""
import asyncio
import json
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import hashlib
import logging

# Configure logging
logger = logging.getLogger(__name__)

class AIResponse(BaseModel):
    """Standard response model for all AI engines"""
    content: str = Field(..., description="The generated content")
    model: str = Field(..., description="Model used for generation")
    usage: Dict[str, int] = Field(default_factory=dict, description="Token usage statistics")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional response metadata")
    cached: bool = Field(default=False, description="Whether response came from cache")
    timestamp: datetime = Field(default_factory=datetime.now, description="Response timestamp")
    engine_type: str = Field(..., description="Type of AI engine used")
    request_id: str = Field(..., description="Unique request identifier")

class AIEngineConfig(BaseModel):
    """Configuration for AI engines"""
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    base_url: Optional[str] = Field(default=None, description="Base URL for API calls")
    model: str = Field(..., description="Default model to use")
    max_tokens: int = Field(default=4000, description="Maximum tokens per request")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    
    # Rate limiting
    requests_per_minute: int = Field(default=60, description="Max requests per minute")
    requests_per_hour: int = Field(default=3600, description="Max requests per hour")
    
    # Budget management
    max_budget_usd: Optional[float] = Field(default=None, description="Maximum budget in USD")
    cost_per_1k_input_tokens: float = Field(default=0.003, description="Cost per 1K input tokens")
    cost_per_1k_output_tokens: float = Field(default=0.015, description="Cost per 1K output tokens")
    
    # Caching
    enable_cache: bool = Field(default=True, description="Enable response caching")
    cache_ttl_seconds: int = Field(default=3600, description="Cache time-to-live in seconds")
    
    # Retry configuration
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    retry_delay_base: float = Field(default=1.0, description="Base delay for exponential backoff")
    retry_delay_max: float = Field(default=60.0, description="Maximum retry delay")
    
    # Timeout
    timeout_seconds: int = Field(default=30, description="Request timeout in seconds")

class RateLimitInfo(BaseModel):
    """Rate limiting information"""
    requests_made: int = 0
    last_request_time: Optional[datetime] = None
    window_start: datetime = Field(default_factory=datetime.now)
    
class BudgetInfo(BaseModel):
    """Budget tracking information"""
    total_spent_usd: float = 0.0
    requests_made: int = 0
    input_tokens_used: int = 0
    output_tokens_used: int = 0
    last_updated: datetime = Field(default_factory=datetime.now)

class CacheEntry(BaseModel):
    """Cache entry model"""
    response: AIResponse
    created_at: datetime = Field(default_factory=datetime.now)
    ttl_seconds: int = 3600
    
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        return datetime.now() > self.created_at + timedelta(seconds=self.ttl_seconds)

class BaseAIEngine(ABC):
    """
    Abstract base class for all AI engines providing:
    - Standardized interface for AI interactions
    - Built-in caching with Redis support
    - Rate limiting and retry logic
    - Budget management and cost tracking
    - Comprehensive error handling
    """
    
    def __init__(self, config: AIEngineConfig, redis_client=None):
        self.config = config
        self.redis_client = redis_client
        self.rate_limit_info = RateLimitInfo()
        self.budget_info = BudgetInfo()
        self._cache: Dict[str, CacheEntry] = {}  # In-memory fallback cache
        
    @abstractmethod
    async def _make_api_call(self, prompt: str, **kwargs) -> AIResponse:
        """
        Make the actual API call to the AI service.
        Must be implemented by each engine.
        """
        pass
    
    @abstractmethod
    def get_engine_type(self) -> str:
        """Return the engine type identifier"""
        pass
    
    def _generate_cache_key(self, prompt: str, **kwargs) -> str:
        """Generate a cache key for the request"""
        # Create deterministic hash from prompt and parameters
        content = f"{prompt}:{json.dumps(kwargs, sort_keys=True)}"
        return hashlib.md5(content.encode()).hexdigest()
    
    async def _get_from_cache(self, cache_key: str) -> Optional[AIResponse]:
        """Get response from cache (Redis or in-memory)"""
        if not self.config.enable_cache:
            return None
            
        try:
            # Try Redis first if available
            if self.redis_client:
                cached_data = await self.redis_client.get(f"ai_cache:{cache_key}")
                if cached_data:
                    cache_entry = CacheEntry.parse_raw(cached_data)
                    if not cache_entry.is_expired():
                        response = cache_entry.response
                        response.cached = True
                        logger.debug(f"Cache hit from Redis: {cache_key[:8]}...")
                        return response
                    else:
                        # Remove expired entry
                        await self.redis_client.delete(f"ai_cache:{cache_key}")
            
            # Fallback to in-memory cache
            elif cache_key in self._cache:
                cache_entry = self._cache[cache_key]
                if not cache_entry.is_expired():
                    response = cache_entry.response
                    response.cached = True
                    logger.debug(f"Cache hit from memory: {cache_key[:8]}...")
                    return response
                else:
                    # Remove expired entry
                    del self._cache[cache_key]
                    
        except Exception as e:
            logger.warning(f"Cache retrieval error: {e}")
            
        return None
    
    async def _save_to_cache(self, cache_key: str, response: AIResponse):
        """Save response to cache (Redis or in-memory)"""
        if not self.config.enable_cache:
            return
            
        try:
            cache_entry = CacheEntry(
                response=response,
                ttl_seconds=self.config.cache_ttl_seconds
            )
            
            # Try Redis first if available
            if self.redis_client:
                await self.redis_client.setex(
                    f"ai_cache:{cache_key}",
                    self.config.cache_ttl_seconds,
                    cache_entry.json()
                )
                logger.debug(f"Cached to Redis: {cache_key[:8]}...")
            else:
                # Fallback to in-memory cache
                self._cache[cache_key] = cache_entry
                logger.debug(f"Cached to memory: {cache_key[:8]}...")
                
        except Exception as e:
            logger.warning(f"Cache save error: {e}")
    
    async def _check_rate_limit(self) -> bool:
        """Check if request is within rate limits"""
        now = datetime.now()
        
        # Reset window if needed (per minute)
        if (now - self.rate_limit_info.window_start).total_seconds() >= 60:
            self.rate_limit_info.requests_made = 0
            self.rate_limit_info.window_start = now
        
        # Check per-minute limit
        if self.rate_limit_info.requests_made >= self.config.requests_per_minute:
            logger.warning("Rate limit exceeded (per minute)")
            return False
            
        return True
    
    async def _wait_for_rate_limit(self):
        """Wait until rate limit window resets"""
        now = datetime.now()
        seconds_until_reset = 60 - (now - self.rate_limit_info.window_start).total_seconds()
        if seconds_until_reset > 0:
            logger.info(f"Rate limited, waiting {seconds_until_reset:.1f}s")
            await asyncio.sleep(seconds_until_reset)
    
    def _check_budget(self, estimated_input_tokens: int, estimated_output_tokens: int) -> bool:
        """Check if request would exceed budget"""
        if not self.config.max_budget_usd:
            return True
            
        estimated_cost = (
            estimated_input_tokens / 1000 * self.config.cost_per_1k_input_tokens +
            estimated_output_tokens / 1000 * self.config.cost_per_1k_output_tokens
        )
        
        if self.budget_info.total_spent_usd + estimated_cost > self.config.max_budget_usd:
            logger.warning(f"Budget would be exceeded. Current: ${self.budget_info.total_spent_usd:.4f}, Estimated cost: ${estimated_cost:.4f}")
            return False
            
        return True
    
    def _update_budget(self, input_tokens: int, output_tokens: int):
        """Update budget tracking with actual usage"""
        cost = (
            input_tokens / 1000 * self.config.cost_per_1k_input_tokens +
            output_tokens / 1000 * self.config.cost_per_1k_output_tokens
        )
        
        self.budget_info.total_spent_usd += cost
        self.budget_info.input_tokens_used += input_tokens
        self.budget_info.output_tokens_used += output_tokens
        self.budget_info.requests_made += 1
        self.budget_info.last_updated = datetime.now()
        
        logger.debug(f"Budget updated: +${cost:.4f}, total: ${self.budget_info.total_spent_usd:.4f}")
    
    async def _execute_with_retries(self, prompt: str, **kwargs) -> AIResponse:
        """Execute API call with retry logic"""
        last_exception = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                # Check rate limit
                if not await self._check_rate_limit():
                    await self._wait_for_rate_limit()
                
                # Make the API call
                response = await self._make_api_call(prompt, **kwargs)
                
                # Update rate limit tracking
                self.rate_limit_info.requests_made += 1
                self.rate_limit_info.last_request_time = datetime.now()
                
                # Update budget tracking
                input_tokens = response.usage.get('input_tokens', 0)
                output_tokens = response.usage.get('output_tokens', 0)
                self._update_budget(input_tokens, output_tokens)
                
                return response
                
            except Exception as e:
                last_exception = e
                
                if attempt < self.config.max_retries:
                    # Calculate exponential backoff delay
                    delay = min(
                        self.config.retry_delay_base * (2 ** attempt),
                        self.config.retry_delay_max
                    )
                    logger.warning(f"Attempt {attempt + 1} failed: {e}, retrying in {delay}s")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"All {self.config.max_retries + 1} attempts failed")
        
        raise last_exception
    
    async def generate(self, prompt: str, **kwargs) -> AIResponse:
        """
        Main method to generate AI response with full feature set:
        - Caching
        - Rate limiting
        - Budget management
        - Retry logic
        - Error handling
        """
        # Generate cache key
        cache_key = self._generate_cache_key(prompt, **kwargs)
        
        # Try cache first
        cached_response = await self._get_from_cache(cache_key)
        if cached_response:
            return cached_response
        
        # Estimate token usage for budget check
        estimated_input_tokens = len(prompt.split()) * 1.3  # Rough estimation
        estimated_output_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        
        # Check budget
        if not self._check_budget(estimated_input_tokens, estimated_output_tokens):
            raise ValueError("Request would exceed budget limit")
        
        # Execute with retries
        response = await self._execute_with_retries(prompt, **kwargs)
        
        # Cache the response
        await self._save_to_cache(cache_key, response)
        
        return response
    
    def get_budget_info(self) -> BudgetInfo:
        """Get current budget information"""
        return self.budget_info.copy()
    
    def get_rate_limit_info(self) -> RateLimitInfo:
        """Get current rate limit information"""
        return self.rate_limit_info.copy()
    
    async def clear_cache(self):
        """Clear all cached responses"""
        try:
            if self.redis_client:
                # Clear Redis cache entries
                keys = await self.redis_client.keys("ai_cache:*")
                if keys:
                    await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} entries from Redis cache")
            
            # Clear in-memory cache
            self._cache.clear()
            logger.info("Cleared in-memory cache")
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
    
    def reset_budget(self):
        """Reset budget tracking"""
        self.budget_info = BudgetInfo()
        logger.info("Budget tracking reset")
    
    def reset_rate_limits(self):
        """Reset rate limit tracking"""
        self.rate_limit_info = RateLimitInfo()
        logger.info("Rate limits reset")