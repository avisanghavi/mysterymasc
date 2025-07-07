#!/usr/bin/env python3
import sys
sys.path.append('agent_builder/docker')
sys.path.append('agent_builder')

import importlib.util
from agent_builder.docker.base_agent import SandboxAgent

# Test loading the simple agent
spec = importlib.util.spec_from_file_location('simple_test_agent', 'simple_test_agent.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

print("=== Debugging class detection ===")
print(f"SandboxAgent from base_agent: {SandboxAgent}")
print(f"SandboxAgent id: {id(SandboxAgent)}")

for name in dir(module):
    obj = getattr(module, name)
    if isinstance(obj, type):
        print(f"\nClass: {name}")
        print(f"  Object: {obj}")
        print(f"  Is type?: {isinstance(obj, type)}")
        
        if name == 'SandboxAgent':
            print(f"  Module SandboxAgent id: {id(obj)}")
            print(f"  Same as imported?: {obj is SandboxAgent}")
        
        if name == 'SimpleTestAgent':
            print(f"  Is subclass of SandboxAgent?: {issubclass(obj, SandboxAgent)}")
            print(f"  Is not SandboxAgent?: {obj != SandboxAgent}")
            print(f"  Is not SandboxAgent (is)?: {obj is not SandboxAgent}")
            print(f"  MRO: {obj.__mro__}")
            
            # Test the full condition
            condition1 = isinstance(obj, type)
            condition2 = issubclass(obj, SandboxAgent)
            condition3 = obj != SandboxAgent
            
            print(f"  Condition 1 (isinstance): {condition1}")
            print(f"  Condition 2 (issubclass): {condition2}")  
            print(f"  Condition 3 (not SandboxAgent): {condition3}")
            print(f"  All conditions: {condition1 and condition2 and condition3}")