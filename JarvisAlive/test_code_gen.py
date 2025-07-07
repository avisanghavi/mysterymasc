#!/usr/bin/env python3
"""Test code generation and loading."""

import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add paths
current_dir = Path(__file__).parent
sys.path.append(str(current_dir))
sys.path.append(str(current_dir / "agent_builder"))
sys.path.append(str(current_dir / "agent_builder" / "docker"))

try:
    from agent_builder.agent_spec import create_monitor_agent
    from agent_builder.code_generator import AgentCodeGenerator
    from agent_builder.docker.base_agent import SandboxAgent
    print("✓ All imports successful")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

def test_generated_code(code: str) -> bool:
    """Test if generated code works."""
    print(f"\nTesting generated code ({len(code)} chars)...")
    
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_file = f.name
    
    try:
        # Try to import and instantiate
        import importlib.util
        spec = importlib.util.spec_from_file_location("test_agent", temp_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # Find the agent class
        agent_class = None
        for name in dir(module):
            obj = getattr(module, name)
            if (isinstance(obj, type) and 
                issubclass(obj, SandboxAgent) and 
                obj != SandboxAgent):
                agent_class = obj
                break
        
        if not agent_class:
            print("✗ No valid agent class found")
            return False
        
        print(f"✓ Found agent class: {agent_class.__name__}")
        
        # Try to instantiate
        agent = agent_class()
        print(f"✓ Created agent: {agent.name}")
        
        # Check required methods
        required_methods = ['initialize', 'execute', 'cleanup']
        for method in required_methods:
            if hasattr(agent, method):
                print(f"✓ Has {method} method")
            else:
                print(f"✗ Missing {method} method")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Error testing code: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        try:
            os.unlink(temp_file)
        except:
            pass

async def main():
    print("Testing HeyJarvis Code Generation\n")
    
    # Check for API key
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("✗ ANTHROPIC_API_KEY not found")
        print("Set the environment variable to test code generation")
        return
    
    print("✓ Found ANTHROPIC_API_KEY")
    
    # Create test agent spec
    try:
        spec = create_monitor_agent(
            target="email",
            frequency=5,
            created_by="test_session",
            name="Test Email Monitor"
        )
        print(f"✓ Created test spec: {spec.name}")
    except Exception as e:
        print(f"✗ Failed to create spec: {e}")
        return
    
    # Generate code
    try:
        generator = AgentCodeGenerator(api_key)
        print("✓ Created code generator")
        
        print("\nGenerating code...")
        code = await generator.generate_agent_code(spec)
        print(f"✓ Generated {len(code)} characters of code")
        
        # Show first few lines
        lines = code.split('\n')
        print("\nFirst 15 lines of generated code:")
        for i, line in enumerate(lines[:15], 1):
            print(f"{i:2}: {line}")
        
        # Test the code
        success = test_generated_code(code)
        print(f"\nCode test result: {'✓ PASS' if success else '✗ FAIL'}")
        
        if not success:
            print("\nFull generated code:")
            print("=" * 80)
            print(code)
            print("=" * 80)
        
    except Exception as e:
        print(f"✗ Code generation failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())