"""
Mock AI Engine - For testing and development without API calls
"""
import asyncio
import random
import uuid
from datetime import datetime
from typing import Dict, Any, List
import logging

from .base_engine import BaseAIEngine, AIResponse, AIEngineConfig

logger = logging.getLogger(__name__)

class MockAIEngine(BaseAIEngine):
    """
    Mock AI engine for testing and development that:
    - Simulates realistic response times
    - Generates deterministic or random responses
    - Tracks usage without making real API calls
    - Supports all base engine features (caching, rate limiting, etc.)
    - Useful for testing and development
    """
    
    def __init__(self, config: AIEngineConfig = None, redis_client=None, **kwargs):
        # Use default config if none provided
        if config is None:
            config = AIEngineConfig(
                model="mock-ai-v1",
                max_tokens=4000,
                temperature=0.7,
                cost_per_1k_input_tokens=0.0,  # Free for testing
                cost_per_1k_output_tokens=0.0
            )
        
        super().__init__(config, redis_client)
        
        # Mock-specific settings
        self.response_delay_min = kwargs.get('response_delay_min', 0.5)
        self.response_delay_max = kwargs.get('response_delay_max', 2.0)
        self.deterministic = kwargs.get('deterministic', False)
        self.failure_rate = kwargs.get('failure_rate', 0.0)  # 0.0 = never fail, 1.0 = always fail
        
        # Pre-defined response templates
        self.response_templates = kwargs.get('response_templates', self._get_default_templates())
        
        # Seed for deterministic responses
        if self.deterministic:
            random.seed(42)
    
    def get_engine_type(self) -> str:
        """Return the engine type identifier"""
        return "mock"
    
    def _get_default_templates(self) -> List[str]:
        """Get default response templates for various types of prompts"""
        return [
            "Based on your request, here's a comprehensive response that addresses the key points you've raised. {topic_response}",
            "I understand you're asking about {topic}. Let me provide you with a detailed analysis and practical recommendations.",
            "Thank you for your question regarding {topic}. This is an important topic that requires careful consideration of multiple factors.",
            "Here's my assessment of your request: {detailed_response} I hope this helps clarify the situation.",
            "To address your inquiry effectively, I'll break this down into several key components: {structured_response}",
            "I appreciate you bringing this question to my attention. Based on the information provided, here's my analysis: {analysis}",
            "This is an excellent question that touches on several important aspects. Let me provide a thorough response: {thorough_response}",
            "I can help you with that. Here's a step-by-step approach to address your needs: {step_by_step_response}",
            "Great question! This topic involves several considerations that I'd like to explore with you: {exploratory_response}",
            "I'm happy to assist with this request. Here's a comprehensive overview of the key points: {overview_response}"
        ]
    
    def _analyze_prompt(self, prompt: str) -> Dict[str, Any]:
        """Analyze the prompt to generate contextually appropriate responses"""
        prompt_lower = prompt.lower()
        
        # Determine response type and content based on prompt analysis
        analysis = {
            'length': 'short' if len(prompt) < 50 else 'medium' if len(prompt) < 200 else 'long',
            'type': 'question' if '?' in prompt else 'command' if any(word in prompt_lower for word in ['create', 'generate', 'write', 'make']) else 'general',
            'domain': self._identify_domain(prompt_lower),
            'complexity': 'simple' if len(prompt.split()) < 10 else 'complex',
            'key_terms': [word for word in prompt.split() if len(word) > 4][:5]
        }
        
        return analysis
    
    def _identify_domain(self, prompt: str) -> str:
        """Identify the domain/topic of the prompt"""
        domains = {
            'code': ['code', 'programming', 'function', 'algorithm', 'python', 'javascript', 'api'],
            'business': ['sales', 'marketing', 'customer', 'revenue', 'business', 'strategy'],
            'data': ['data', 'analysis', 'statistics', 'metrics', 'dashboard', 'report'],
            'email': ['email', 'outreach', 'template', 'personalization', 'campaign'],
            'technical': ['system', 'architecture', 'database', 'infrastructure', 'deployment'],
            'general': []
        }
        
        for domain, keywords in domains.items():
            if any(keyword in prompt for keyword in keywords):
                return domain
        
        return 'general'
    
    def _generate_response_content(self, prompt: str, analysis: Dict[str, Any], **kwargs) -> str:
        """Generate appropriate response content based on prompt analysis"""
        if self.deterministic:
            # Deterministic response based on prompt hash
            prompt_hash = hash(prompt) % len(self.response_templates)
            template = self.response_templates[prompt_hash]
        else:
            # Random template selection
            template = random.choice(self.response_templates)
        
        # Generate domain-specific content
        domain_content = self._generate_domain_content(analysis['domain'], analysis['key_terms'])
        
        # Determine response length based on max_tokens
        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        target_words = min(max_tokens // 4, 500)  # Rough token-to-word conversion
        
        # Build response with appropriate length
        response_parts = []
        
        # Main response
        main_response = template.format(
            topic=analysis['key_terms'][0] if analysis['key_terms'] else 'your request',
            topic_response=domain_content,
            detailed_response=domain_content,
            structured_response=domain_content,
            analysis=domain_content,
            thorough_response=domain_content,
            step_by_step_response=domain_content,
            exploratory_response=domain_content,
            overview_response=domain_content
        )
        response_parts.append(main_response)
        
        # Add additional content if needed for longer responses
        if target_words > 100 and analysis['complexity'] == 'complex':
            additional_content = self._generate_additional_content(analysis['domain'])
            response_parts.append(additional_content)
        
        # Combine and truncate to target length
        full_response = ' '.join(response_parts)
        words = full_response.split()
        
        if len(words) > target_words:
            words = words[:target_words]
            full_response = ' '.join(words) + "..."
        
        return full_response
    
    def _generate_domain_content(self, domain: str, key_terms: List[str]) -> str:
        """Generate domain-specific content"""
        content_maps = {
            'code': [
                "This involves implementing efficient algorithms and following best practices for code organization.",
                "Consider using modern programming patterns and ensuring proper error handling throughout the implementation.",
                "The solution should be scalable, maintainable, and well-documented for future development."
            ],
            'business': [
                "This requires strategic thinking about market positioning and customer value proposition.",
                "Focus on building strong relationships with stakeholders and measuring key performance indicators.",
                "Consider the competitive landscape and ensure alignment with overall business objectives."
            ],
            'data': [
                "The analysis should include comprehensive data validation and statistical significance testing.",
                "Implement robust data pipelines with proper monitoring and alerting mechanisms.",
                "Ensure data privacy compliance and establish clear governance policies."
            ],
            'email': [
                "Focus on personalization and segmentation to improve engagement rates.",
                "A/B test different subject lines and content variations to optimize performance.",
                "Monitor deliverability metrics and maintain healthy sender reputation."
            ],
            'technical': [
                "Design for scalability and reliability with appropriate monitoring and observability.",
                "Implement proper security measures and follow infrastructure best practices.",
                "Consider disaster recovery and backup strategies for business continuity."
            ],
            'general': [
                "This requires careful consideration of multiple factors and stakeholder perspectives.",
                "The approach should be systematic and evidence-based with clear success metrics.",
                "Regular monitoring and adjustment will be important for long-term success."
            ]
        }
        
        domain_content = content_maps.get(domain, content_maps['general'])
        
        if self.deterministic and key_terms:
            # Use first key term to select content deterministically
            index = hash(key_terms[0]) % len(domain_content)
            return domain_content[index]
        else:
            return random.choice(domain_content)
    
    def _generate_additional_content(self, domain: str) -> str:
        """Generate additional content for longer responses"""
        additional_content = {
            'code': "Additionally, consider implementing comprehensive unit tests and continuous integration to ensure code quality. Documentation should include API specifications and usage examples.",
            'business': "Furthermore, establish clear metrics for success and implement regular review processes. Stakeholder communication and change management will be crucial for successful implementation.",
            'data': "Moreover, implement data quality monitoring and establish clear data lineage documentation. Consider implementing automated reporting and alerting for key business metrics.",
            'email': "Also, implement progressive profiling to gather additional customer insights over time. Consider implementing dynamic content personalization based on customer behavior.",
            'technical': "Additionally, implement comprehensive logging and monitoring with appropriate alerting thresholds. Consider implementing automated deployment pipelines with proper testing gates.",
            'general': "Furthermore, it's important to establish clear communication channels and feedback loops. Regular evaluation and optimization will help ensure continued success."
        }
        
        return additional_content.get(domain, additional_content['general'])
    
    def _simulate_token_usage(self, prompt: str, response: str) -> Dict[str, int]:
        """Simulate realistic token usage"""
        # Rough token estimation (1 token ≈ 0.75 words or 4 characters)
        input_words = len(prompt.split())
        output_words = len(response.split())
        
        input_tokens = int(input_words * 1.3)  # Slightly higher than word count
        output_tokens = int(output_words * 1.3)
        
        return {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'total_tokens': input_tokens + output_tokens
        }
    
    async def _make_api_call(self, prompt: str, **kwargs) -> AIResponse:
        """Simulate an API call with realistic behavior"""
        # Simulate network delay
        if self.deterministic:
            delay = (self.response_delay_min + self.response_delay_max) / 2
        else:
            delay = random.uniform(self.response_delay_min, self.response_delay_max)
        
        await asyncio.sleep(delay)
        
        # Simulate occasional failures
        if not self.deterministic and random.random() < self.failure_rate:
            error_types = [
                "Simulated network timeout",
                "Simulated rate limit exceeded", 
                "Simulated service unavailable",
                "Simulated authentication error"
            ]
            raise ConnectionError(random.choice(error_types))
        
        # Analyze prompt and generate response
        analysis = self._analyze_prompt(prompt)
        response_content = self._generate_response_content(prompt, analysis, **kwargs)
        
        # Simulate token usage
        usage = self._simulate_token_usage(prompt, response_content)
        
        # Create metadata
        metadata = {
            'prompt_analysis': analysis,
            'simulated_delay': delay,
            'deterministic': self.deterministic,
            'template_used': 'deterministic' if self.deterministic else 'random'
        }
        
        return AIResponse(
            content=response_content,
            model=kwargs.get('model', self.config.model),
            usage=usage,
            metadata=metadata,
            cached=False,
            timestamp=datetime.now(),
            engine_type=self.get_engine_type(),
            request_id=str(uuid.uuid4())
        )
    
    def set_deterministic(self, deterministic: bool, seed: int = 42):
        """Set whether responses should be deterministic"""
        self.deterministic = deterministic
        if deterministic:
            random.seed(seed)
    
    def set_failure_rate(self, failure_rate: float):
        """Set the rate of simulated failures (0.0 to 1.0)"""
        self.failure_rate = max(0.0, min(1.0, failure_rate))
    
    def add_response_template(self, template: str):
        """Add a custom response template"""
        self.response_templates.append(template)
    
    def set_response_delay(self, min_delay: float, max_delay: float):
        """Set the range of simulated response delays"""
        self.response_delay_min = min_delay
        self.response_delay_max = max_delay
    
    def get_engine_stats(self) -> Dict[str, Any]:
        """Get mock engine statistics"""
        return {
            'engine_type': self.get_engine_type(),
            'deterministic': self.deterministic,
            'failure_rate': self.failure_rate,
            'response_delay_range': (self.response_delay_min, self.response_delay_max),
            'template_count': len(self.response_templates),
            'budget_info': self.get_budget_info().dict(),
            'rate_limit_info': self.get_rate_limit_info().dict()
        }