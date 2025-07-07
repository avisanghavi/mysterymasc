#!/usr/bin/env python3
import sys
sys.path.append('agent_builder/docker')
sys.path.append('agent_builder')

import importlib.util
from agent_builder.docker.base_agent import SandboxAgent

# Test loading the debug agent
spec = importlib.util.spec_from_file_location('debug_agent', 'debug_agent.py')
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
    print(f'✓ Agent methods: {[m for m in dir(agent) if not m.startswith("_")]}')
else:
    print('✗ No valid agent class found')
    print('Available classes in module:')
    for name in dir(module):
        obj = getattr(module, name)
        if isinstance(obj, type):
            print(f'  - {name}: {obj}')