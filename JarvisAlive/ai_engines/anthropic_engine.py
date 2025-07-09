"""
Anthropic AI Engine - Implementation for Anthropic's Claude API
"""
import asyncio
import aiohttp
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
import logging

from .base_engine import BaseAIEngine, AIResponse, AIEngineConfig

logger = logging.getLogger(__name__)

class AnthropicEngine(BaseAIEngine):
    """
    Anthropic Claude API implementation with:
    - Full Claude API support (Messages API)
    - Proper authentication and headers
    - Response parsing and token counting
    - Error handling for Anthropic-specific errors
    """
    
    def __init__(self, config: AIEngineConfig, redis_client=None):
        super().__init__(config, redis_client)
        
        # Anthropic-specific settings
        self.api_version = "2023-06-01"
        self.base_url = config.base_url or "https://api.anthropic.com"
        
        # Validate required config
        if not config.api_key:
            raise ValueError("Anthropic API key is required")
            
        # Default models for Anthropic
        if not config.model:
            config.model = "claude-3-sonnet-20240229"
    
    def get_engine_type(self) -> str:
        """Return the engine type identifier"""
        return "anthropic"
    
    def _prepare_headers(self) -> Dict[str, str]:
        """Prepare headers for Anthropic API requests"""
        return {
            "Content-Type": "application/json",
            "x-api-key": self.config.api_key,
            "anthropic-version": self.api_version,
            "User-Agent": "HeyJarvis-AI-Engine/1.0"
        }
    
    def _prepare_payload(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """Prepare request payload for Anthropic Messages API"""
        # Extract parameters with defaults
        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        temperature = kwargs.get('temperature', self.config.temperature)
        model = kwargs.get('model', self.config.model)
        
        # Build messages array (Anthropic Messages API format)
        messages = [
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        # Add system message if provided
        system_message = kwargs.get('system_message')
        payload = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system_message:
            payload["system"] = system_message
            
        # Add optional parameters
        if 'top_p' in kwargs:
            payload["top_p"] = kwargs['top_p']
        if 'top_k' in kwargs:
            payload["top_k"] = kwargs['top_k']
        if 'stop_sequences' in kwargs:
            payload["stop_sequences"] = kwargs['stop_sequences']
        
        return payload
    
    def _parse_response(self, response_data: Dict[str, Any], model: str) -> AIResponse:
        """Parse Anthropic API response into standardized format"""
        # Extract content
        content = ""
        if response_data.get("content"):
            # Handle both single content block and multiple blocks
            content_blocks = response_data["content"]
            if isinstance(content_blocks, list):
                content = "".join(
                    block.get("text", "") for block in content_blocks 
                    if block.get("type") == "text"
                )
            else:
                content = content_blocks.get("text", "")
        
        # Extract usage information
        usage = {}
        if "usage" in response_data:
            usage_data = response_data["usage"]
            usage = {
                "input_tokens": usage_data.get("input_tokens", 0),
                "output_tokens": usage_data.get("output_tokens", 0),
                "total_tokens": usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0)
            }
        
        # Extract metadata
        metadata = {
            "id": response_data.get("id"),
            "type": response_data.get("type"),
            "role": response_data.get("role"),
            "stop_reason": response_data.get("stop_reason"),
            "stop_sequence": response_data.get("stop_sequence")
        }
        
        return AIResponse(
            content=content,
            model=model,
            usage=usage,
            metadata=metadata,
            cached=False,
            timestamp=datetime.now(),
            engine_type=self.get_engine_type(),
            request_id=str(uuid.uuid4())
        )
    
    async def _make_api_call(self, prompt: str, **kwargs) -> AIResponse:
        """Make the actual API call to Anthropic"""
        url = f"{self.base_url}/v1/messages"
        headers = self._prepare_headers()
        payload = self._prepare_payload(prompt, **kwargs)
        
        logger.debug(f"Making Anthropic API call to {url}")
        
        timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
        
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    response_data = await response.json()
                    
                    # Handle API errors
                    if response.status != 200:
                        error_msg = response_data.get("error", {}).get("message", "Unknown error")
                        error_type = response_data.get("error", {}).get("type", "api_error")
                        
                        logger.error(f"Anthropic API error {response.status}: {error_msg}")
                        
                        # Handle specific error types
                        if response.status == 401:
                            raise ValueError(f"Authentication failed: {error_msg}")
                        elif response.status == 429:
                            raise ValueError(f"Rate limit exceeded: {error_msg}")
                        elif response.status == 400:
                            raise ValueError(f"Invalid request: {error_msg}")
                        elif response.status >= 500:
                            raise ConnectionError(f"Server error: {error_msg}")
                        else:
                            raise ValueError(f"API error ({error_type}): {error_msg}")
                    
                    # Parse successful response
                    return self._parse_response(response_data, payload["model"])
                    
        except aiohttp.ClientTimeout:
            logger.error(f"Request timeout after {self.config.timeout_seconds}s")
            raise ConnectionError("Request timeout")
        except aiohttp.ClientError as e:
            logger.error(f"HTTP client error: {e}")
            raise ConnectionError(f"Network error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            raise ValueError("Invalid JSON response from API")
        except Exception as e:
            logger.error(f"Unexpected error in API call: {e}")
            raise
    
    async def generate_streaming(self, prompt: str, callback=None, **kwargs):
        """
        Generate streaming response (for future implementation)
        Note: This is a placeholder for streaming functionality
        """
        # For now, fall back to regular generation
        # TODO: Implement actual streaming using Anthropic's streaming API
        response = await self.generate(prompt, **kwargs)
        
        if callback:
            # Simulate streaming by calling callback with chunks
            words = response.content.split()
            current_content = ""
            
            for word in words:
                current_content += word + " "
                await callback(current_content.strip())
                await asyncio.sleep(0.05)  # Simulate streaming delay
        
        return response
    
    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text (rough approximation)
        Anthropic uses a similar tokenization to GPT models
        """
        # Rough estimation: ~0.75 tokens per word, ~4 characters per token
        word_count = len(text.split())
        char_count = len(text)
        
        # Use the higher of the two estimates for safety
        word_estimate = word_count * 0.75
        char_estimate = char_count / 4
        
        return int(max(word_estimate, char_estimate))
    
    def get_supported_models(self) -> list[str]:
        """Get list of supported Anthropic models"""
        return [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229", 
            "claude-3-haiku-20240307",
            "claude-2.1",
            "claude-2.0",
            "claude-instant-1.2"
        ]
    
    def get_model_limits(self, model: str) -> Dict[str, int]:
        """Get token limits for specific models"""
        limits = {
            "claude-3-opus-20240229": {"max_tokens": 4096, "context_window": 200000},
            "claude-3-sonnet-20240229": {"max_tokens": 4096, "context_window": 200000},
            "claude-3-haiku-20240307": {"max_tokens": 4096, "context_window": 200000},
            "claude-2.1": {"max_tokens": 4096, "context_window": 200000},
            "claude-2.0": {"max_tokens": 4096, "context_window": 100000},
            "claude-instant-1.2": {"max_tokens": 4096, "context_window": 100000}
        }
        
        return limits.get(model, {"max_tokens": 4096, "context_window": 100000})
    
    async def validate_api_key(self) -> bool:
        """Validate the API key by making a test request"""
        try:
            # Make a minimal test request
            await self.generate("Hello", max_tokens=1)
            return True
        except Exception as e:
            logger.error(f"API key validation failed: {e}")
            return False