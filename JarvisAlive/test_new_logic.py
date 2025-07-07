#!/usr/bin/env python3
import sys
sys.path.append('agent_builder/docker')
sys.path.append('agent_builder')

import importlib.util

# Test the new logic
spec = importlib.util.spec_from_file_location('simple_test_agent', 'simple_test_agent.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

print("=== Testing New Class Detection Logic ===")
agent_class = None
for name in dir(module):
    obj = getattr(module, name)
    if (isinstance(obj, type) and 
        name != 'SandboxAgent' and
        hasattr(obj, '__mro__') and
        any(cls.__name__ == 'SandboxAgent' for cls in obj.__mro__)):
        print(f"Found agent class: {name}")
        print(f"  MRO: {[cls.__name__ for cls in obj.__mro__]}")
        agent_class = obj
        break

if agent_class:
    print("✓ New logic successfully found agent class!")
    agent = agent_class()
    print(f"  Agent name: {agent.name}")
else:
    print("✗ New logic failed to find agent class")