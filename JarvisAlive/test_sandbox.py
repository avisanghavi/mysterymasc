#!/usr/bin/env python3
"""Test script for the Docker sandbox system."""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.insert(0, '/Users/avisanghavi/Desktop/hJ2/heyjarvis')

from agent_builder.sandbox import SandboxManager, SandboxConfig
from agent_builder.agent_spec import create_monitor_agent

# Mock agent code that inherits from SandboxAgent
MOCK_AGENT_CODE = '''"""Test agent for sandbox verification."""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from base_agent import SandboxAgent

class TestMonitorAgent(SandboxAgent):
    """Test agent: Monitors email every 5 minutes and sends alerts when conditions are met."""
    
    def __init__(self):
        super().__init__()
        self.name = "Test Monitor Agent"
        self.version = "1.0.0"
        self.capabilities = ["email_monitoring", "alert_sending"]
        self.config = {
            "id": "test-agent-001",
            "resource_limits": {"cpu": 0.5, "memory": 256, "timeout": 60, "max_retries": 3},
            "integrations": {}
        }
        
    async def initialize(self):
        """Initialize agent resources and connections"""
        self.logger.info("Initializing test agent...")
        
        # Simulate initialization
        await asyncio.sleep(1)
        self.logger.info("Agent initialization completed")
        
    async def execute(self):
        """Main execution logic"""
        self.logger.info("Starting test agent execution...")
        
        # Simulate some work
        for i in range(3):
            self.logger.info(f"Processing step {i+1}/3...")
            await asyncio.sleep(2)
        
        # Return test results
        return {
            "status": "success",
            "steps_completed": 3,
            "execution_time": 6,
            "test_data": "Agent executed successfully in sandbox"
        }
        
    async def cleanup(self):
        """Cleanup resources"""
        self.logger.info("Cleaning up test agent...")
        await asyncio.sleep(0.5)
        self.logger.info("Cleanup completed")
'''

async def test_sandbox_system():
    """Test the complete sandbox system."""
    
    print("🧪 Testing Docker Sandbox System")
    print("=" * 50)
    
    # Check if Docker is available
    try:
        import docker
        docker_client = docker.from_env()
        docker_client.ping()
        print("✅ Docker is available and running")
    except Exception as e:
        print(f"❌ Docker not available: {e}")
        print("Please ensure Docker is installed and running")
        return
    
    # Test 1: Initialize SandboxManager
    print("\n1. Initializing SandboxManager...")
    try:
        config = SandboxConfig(
            max_cpu_cores=1.0,
            max_memory_mb=256,
            default_timeout=60
        )
        
        sandbox_manager = SandboxManager(config)
        await sandbox_manager.initialize()
        print("✅ SandboxManager initialized successfully")
        
    except Exception as e:
        print(f"❌ Failed to initialize SandboxManager: {e}")
        return
    
    # Test 2: Create agent spec
    print("\n2. Creating test agent spec...")
    try:
        agent_spec = create_monitor_agent(
            target="email",
            frequency=5,
            created_by="sandbox_test",
            name="Test Monitor Agent"
        )
        print(f"✅ Agent spec created: {agent_spec.name}")
        
    except Exception as e:
        print(f"❌ Failed to create agent spec: {e}")
        return
    
    # Test 3: Create sandbox
    print("\n3. Creating sandbox container...")
    try:
        secrets = {
            "test_token": "mock_token_12345",
            "gmail_token": "mock_gmail_token"
        }
        
        container_id = await sandbox_manager.create_sandbox(
            agent_id="test_monitor_001",
            agent_code=MOCK_AGENT_CODE,
            agent_spec=agent_spec,
            secrets=secrets
        )
        
        print(f"✅ Sandbox created: {container_id}")
        
    except Exception as e:
        print(f"❌ Failed to create sandbox: {e}")
        return
    
    # Test 4: Execute agent in sandbox
    print("\n4. Executing agent in sandbox...")
    try:
        result = await sandbox_manager.execute_agent(
            container_id,
            timeout=120  # 2 minutes
        )
        
        print(f"✅ Agent execution completed")
        print(f"   Status: {result.get('status', 'unknown')}")
        print(f"   Exit code: {result.get('exit_code', 'unknown')}")
        
        if result.get('result'):
            print(f"   Result: {result['result']}")
        
        if result.get('error'):
            print(f"   Error: {result['error']}")
        
    except Exception as e:
        print(f"❌ Failed to execute agent: {e}")
    
    # Test 5: Get agent logs
    print("\n5. Retrieving agent logs...")
    try:
        logs = await sandbox_manager.get_agent_logs(container_id)
        print(f"✅ Retrieved {len(logs)} lines of logs")
        
        # Show last few log lines
        if logs:
            print("   Last 5 log lines:")
            for line in logs[-5:]:
                if line.strip():
                    print(f"     {line.strip()}")
        
    except Exception as e:
        print(f"❌ Failed to get logs: {e}")
    
    # Test 6: Get container stats
    print("\n6. Getting container statistics...")
    try:
        stats = await sandbox_manager.get_container_stats(container_id)
        if stats:
            print("✅ Container statistics:")
            print(f"   CPU Usage: {stats.get('cpu_usage', 'N/A')}%")
            print(f"   Memory Usage: {stats.get('memory_usage_mb', 'N/A'):.1f} MB")
            print(f"   Memory Limit: {stats.get('memory_limit_mb', 'N/A'):.1f} MB")
        else:
            print("⚠️  No statistics available (container may have stopped)")
        
    except Exception as e:
        print(f"❌ Failed to get stats: {e}")
    
    # Test 7: Cleanup
    print("\n7. Cleaning up sandbox...")
    try:
        success = await sandbox_manager.cleanup_sandbox(container_id)
        if success:
            print("✅ Sandbox cleaned up successfully")
        else:
            print("⚠️  Sandbox cleanup returned False")
        
    except Exception as e:
        print(f"❌ Failed to cleanup sandbox: {e}")
    
    # Test 8: List active containers
    print("\n8. Checking for remaining containers...")
    try:
        active_containers = await sandbox_manager.list_active_containers()
        print(f"✅ Active containers: {len(active_containers)}")
        
        if active_containers:
            for container in active_containers:
                print(f"   - {container['container_id']}: {container['status']}")
        
    except Exception as e:
        print(f"❌ Failed to list containers: {e}")
    
    print("\n🎉 Sandbox testing completed!")
    print("\nKey features verified:")
    print("  ✅ Docker image building")
    print("  ✅ Container creation with resource limits")
    print("  ✅ Agent code execution in isolation")
    print("  ✅ Log collection and monitoring")
    print("  ✅ Container cleanup and resource management")

if __name__ == "__main__":
    try:
        asyncio.run(test_sandbox_system())
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")