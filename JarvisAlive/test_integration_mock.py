#!/usr/bin/env python3
"""Test integration with mock code generation."""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agent_builder.code_generator import AgentCodeGenerator
from departments.sales.lead_scanner_agent import create_lead_scanner_spec


def test_template_type_detection():
    """Test that sales agent template types are correctly detected."""
    print("Testing template type detection...")
    
    # Create a mock code generator (no API key needed for template detection)
    class MockCodeGenerator(AgentCodeGenerator):
        def __init__(self):
            # Skip LLM initialization
            self.approved_libraries = set()
            self.forbidden_patterns = []
    
    generator = MockCodeGenerator()
    
    # Test lead scanner agent
    session_id = "test_session"
    lead_scanner_spec = create_lead_scanner_spec(session_id)
    
    template_type = generator._determine_template_type(lead_scanner_spec)
    print(f"Lead Scanner template type: {template_type}")
    
    assert template_type == "sales_lead_scanner", f"Expected 'sales_lead_scanner', got '{template_type}'"
    
    # Test requirements generation
    requirements = generator._get_template_specific_requirements(template_type, lead_scanner_spec)
    print(f"Requirements length: {len(requirements)} characters")
    
    assert "LinkedIn" in requirements, "LinkedIn should be mentioned in requirements"
    assert "lead scoring" in requirements.lower(), "Lead scoring should be mentioned"
    
    print("✓ Template type detection working correctly!")


def test_class_name_generation():
    """Test class name generation from agent names."""
    print("\nTesting class name generation...")
    
    class MockCodeGenerator(AgentCodeGenerator):
        def __init__(self):
            pass
    
    generator = MockCodeGenerator()
    
    test_cases = [
        ("Lead Scanner Agent", "LeadScannerAgent"),
        ("Outreach Composer Agent", "OutreachComposerAgent"), 
        ("Meeting Scheduler Agent", "MeetingSchedulerAgent"),
        ("Pipeline Tracker Agent", "PipelineTrackerAgent")
    ]
    
    for agent_name, expected_class in test_cases:
        result = generator._generate_class_name(agent_name)
        print(f"'{agent_name}' -> '{result}'")
        assert result == expected_class, f"Expected '{expected_class}', got '{result}'"
    
    print("✓ Class name generation working correctly!")


def test_config_generation():
    """Test configuration dictionary generation."""
    print("\nTesting config generation...")
    
    class MockCodeGenerator(AgentCodeGenerator):
        def __init__(self):
            pass
    
    generator = MockCodeGenerator()
    session_id = "test_session"
    lead_scanner_spec = create_lead_scanner_spec(session_id)
    
    config = generator._generate_config_dict(lead_scanner_spec)
    
    print(f"Generated config keys: {list(config.keys())}")
    
    assert "id" in config
    assert "resource_limits" in config
    assert "integrations" in config
    
    # Check resource limits
    resource_limits = config["resource_limits"]
    assert "cpu" in resource_limits
    assert "memory" in resource_limits
    assert "timeout" in resource_limits
    
    # Check integrations
    integrations = config["integrations"]
    assert len(integrations) > 0, "Should have at least one integration"
    
    print("✓ Config generation working correctly!")


def main():
    """Run all integration tests."""
    print("Running sales agent integration tests...")
    print("=" * 50)
    
    try:
        test_template_type_detection()
        test_class_name_generation()
        test_config_generation()
        
        print("\n" + "=" * 50)
        print("🎉 All integration tests passed!")
        print("Sales agents are ready for code generation!")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)