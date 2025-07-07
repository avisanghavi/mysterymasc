#!/usr/bin/env python3
"""Test the template system integration."""

import asyncio
import logging
from templates.template_engine import TemplateEngine
from templates.parameter_extractor import ParameterExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_template_system():
    """Test template system with various user requests."""
    
    # Initialize components
    template_engine = TemplateEngine()
    parameter_extractor = ParameterExtractor()
    
    # Test cases
    test_requests = [
        "Monitor my Gmail for emails from support@example.com",
        "Send Slack notifications to #alerts channel",
        "Scrape https://example.com every hour",
        "Analyze data from /path/to/data.csv",
        "Copy files from /source to /backup",
        "This is a random request that shouldn't match any template"
    ]
    
    print("🧪 Testing HeyJarvis Template System\n")
    
    # List available templates
    templates = template_engine.list_templates()
    print(f"📋 Available Templates ({len(templates)}):")
    for name, info in templates.items():
        print(f"  • {name}: {info.description}")
    print()
    
    # Test each request
    for i, request in enumerate(test_requests, 1):
        print(f"🔍 Test {i}: '{request}'")
        
        try:
            # Extract parameters
            result = parameter_extractor.extract_parameters(request)
            
            print(f"  Template: {result.template_match}")
            print(f"  Confidence: {result.confidence:.3f}")
            print(f"  Parameters: {result.extracted_parameters}")
            print(f"  Missing: {result.missing_required}")
            
            # Try to render if confidence is high enough
            if result.template_match and result.confidence >= 0.7 and not result.missing_required:
                try:
                    # Add default agent name if missing
                    params = result.extracted_parameters.copy()
                    if "agent_name" not in params:
                        template_info = template_engine.get_template_info(result.template_match)
                        params["agent_name"] = f"{template_info.description.split(' ')[0]} Agent"
                    
                    code = template_engine.render_template(
                        result.template_match,
                        params,
                        validate=True
                    )
                    print(f"  ✅ Generated {len(code)} characters of code")
                    
                except Exception as e:
                    print(f"  ❌ Template rendering failed: {e}")
            else:
                reasons = []
                if not result.template_match:
                    reasons.append("no template match")
                if result.confidence < 0.7:
                    reasons.append(f"low confidence ({result.confidence:.3f})")
                if result.missing_required:
                    reasons.append(f"missing params: {result.missing_required}")
                
                print(f"  ⚠️  Would fallback to LLM: {', '.join(reasons)}")
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
        
        print()
    
    # Test template rendering directly
    print("🛠️  Testing Direct Template Rendering:")
    
    test_params = {
        "gmail_monitor": {
            "email_filter": "from:support@example.com",
            "check_interval": "300",
            "agent_name": "Support Email Monitor"
        },
        "slack_notifier": {
            "slack_token": "xoxb-test-token",
            "channel": "#alerts",
            "agent_name": "Alert Notifier"
        }
    }
    
    for template_name, params in test_params.items():
        try:
            code = template_engine.render_template(template_name, params, validate=True)
            print(f"  ✅ {template_name}: {len(code)} characters")
        except Exception as e:
            print(f"  ❌ {template_name}: {e}")
    
    print("\n🎉 Template system test completed!")


if __name__ == "__main__":
    asyncio.run(test_template_system())