#!/usr/bin/env python3
import sys
sys.path.append('agent_builder/docker')
sys.path.append('agent_builder')

import importlib.util
from agent_builder.docker.base_agent import SandboxAgent

# Test loading the simple agent
try:
    spec = importlib.util.spec_from_file_location('simple_test_agent', 'simple_test_agent.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Find agent class
    agent_class = None
    for name in dir(module):
        obj = getattr(module, name)
        if (isinstance(obj, type) and 
            issubclass(obj, SandboxAgent) and 
            obj != SandboxAgent):
            agent_class = obj
            break

    if agent_class:
        print(f'✓ Found agent class: {agent_class.__name__}')
        agent = agent_class()
        print(f'✓ Created agent: {agent.name}')
        print(f'✓ Base classes: {[cls.__name__ for cls in agent_class.__mro__]}')
        print('✓ Agent loads successfully')
    else:
        print('✗ No valid agent class found')
        print('Available classes in module:')
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type):
                print(f'  - {name}: {obj}')
                if hasattr(obj, '__mro__'):
                    print(f'    MRO: {[cls.__name__ for cls in obj.__mro__]}')

except Exception as e:
    print(f'✗ Error loading agent: {e}')
    import traceback
    traceback.print_exc()