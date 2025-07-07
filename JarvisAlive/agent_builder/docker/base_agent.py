#!/usr/bin/env python3
"""Base agent class for all HeyJarvis agents running in sandbox."""

import asyncio
import logging
import json
import os
import signal
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pathlib import Path


class SandboxAgent(ABC):
    """Base class for all HeyJarvis agents running in sandbox environment."""
    
    def __init__(self):
        self.name: str = "SandboxAgent"
        self.version: str = "1.0.0"
        self.capabilities: List[str] = []
        self.config: Dict[str, Any] = {}
        self.is_running: bool = False
        self.start_time: Optional[datetime] = None
        self.execution_results: Dict[str, Any] = {}
        
        # Sandbox-specific attributes (must be set before logging setup)
        self.sandbox_id = os.environ.get('SANDBOX_ID', 'unknown')
        self.timeout = int(os.environ.get('AGENT_TIMEOUT', '300'))  # 5 minutes default
        self.max_memory = int(os.environ.get('AGENT_MAX_MEMORY', '512'))  # 512MB default
        
        # Setup logging after sandbox_id is available
        self.logger: logging.Logger = self._setup_logging()
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
        
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for the sandbox environment."""
        # Ensure logs directory exists
        log_dir = Path('/app/logs')
        try:
            log_dir.mkdir(exist_ok=True)
            use_file_logging = True
        except (PermissionError, FileNotFoundError):
            # Fallback - no file logging if directory can't be created
            use_file_logging = False
        
        # Configure logging
        handlers = [logging.StreamHandler(sys.stdout)]
        if use_file_logging:
            handlers.append(logging.FileHandler(log_dir / f'{self.sandbox_id}.log'))
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=handlers
        )
        
        return logging.getLogger(f"agent.{self.sandbox_id}")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.is_running = False
        asyncio.create_task(self.cleanup())
        sys.exit(0)
    
    @abstractmethod
    async def initialize(self) -> None:
        """Initialize agent resources and connections."""
        pass
    
    @abstractmethod
    async def execute(self) -> Any:
        """Main execution logic."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources."""
        pass
    
    async def run(self) -> Dict[str, Any]:
        """Main entry point for sandbox execution."""
        self.logger.info(f"Starting agent: {self.name} (sandbox: {self.sandbox_id})")
        
        try:
            # Check if we're within timeout
            if self.timeout > 0:
                return await asyncio.wait_for(self._run_with_monitoring(), timeout=self.timeout)
            else:
                return await self._run_with_monitoring()
                
        except asyncio.TimeoutError:
            self.logger.error(f"Agent execution timed out after {self.timeout} seconds")
            self.execution_results['error'] = f"Execution timeout ({self.timeout}s)"
            self.execution_results['status'] = 'timeout'
            return self.execution_results
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            self.execution_results['error'] = str(e)
            self.execution_results['status'] = 'error'
            return self.execution_results
            
        finally:
            await self.cleanup()
    
    async def _run_with_monitoring(self) -> Dict[str, Any]:
        """Run agent with resource monitoring."""
        self.start_time = datetime.now(timezone.utc)
        self.is_running = True
        
        try:
            # Initialize agent
            self.logger.info("Initializing agent...")
            await self.initialize()
            
            # Execute main logic
            self.logger.info("Executing agent logic...")
            result = await self.execute()
            
            # Record successful execution
            self.execution_results = {
                'status': 'completed',
                'result': result,
                'start_time': self.start_time.isoformat(),
                'end_time': datetime.now(timezone.utc).isoformat(),
                'sandbox_id': self.sandbox_id,
                'agent_name': self.name,
                'version': self.version
            }
            
            self.logger.info(f"Agent execution completed successfully")
            return self.execution_results
            
        except Exception as e:
            self.logger.error(f"Agent execution failed: {e}")
            self.execution_results = {
                'status': 'failed',
                'error': str(e),
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': datetime.now(timezone.utc).isoformat(),
                'sandbox_id': self.sandbox_id,
                'agent_name': self.name,
                'version': self.version
            }
            raise
            
        finally:
            self.is_running = False
    
    def save_state(self, state: Dict[str, Any]) -> None:
        """Save agent state to file."""
        try:
            state_file = Path('/tmp/agent') / f'{self.sandbox_id}_state.json'
            state_file.parent.mkdir(exist_ok=True)
            
            with open(state_file, 'w') as f:
                json.dump(state, f, indent=2, default=str)
                
            self.logger.info(f"State saved to {state_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save state: {e}")
    
    def load_state(self) -> Optional[Dict[str, Any]]:
        """Load agent state from file."""
        try:
            state_file = Path('/tmp/agent') / f'{self.sandbox_id}_state.json'
            
            if state_file.exists():
                with open(state_file, 'r') as f:
                    state = json.load(f)
                    
                self.logger.info(f"State loaded from {state_file}")
                return state
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to load state: {e}")
            return None
    
    def get_secrets(self) -> Dict[str, str]:
        """Load secrets from mounted volume."""
        secrets = {}
        secrets_dir = Path('/app/secrets')
        
        if secrets_dir.exists():
            for secret_file in secrets_dir.glob('*.txt'):
                try:
                    with open(secret_file, 'r') as f:
                        secrets[secret_file.stem] = f.read().strip()
                except Exception as e:
                    self.logger.error(f"Failed to load secret {secret_file}: {e}")
        
        return secrets
    
    def check_network_access(self, host: str, port: int = 443) -> bool:
        """Check if network access to a host is allowed."""
        import socket
        
        try:
            # Only check connection, don't send data
            with socket.create_connection((host, port), timeout=5):
                return True
        except Exception:
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        uptime = None
        if self.start_time:
            uptime = (datetime.now(timezone.utc) - self.start_time).total_seconds()
        
        return {
            "name": self.name,
            "version": self.version,
            "sandbox_id": self.sandbox_id,
            "is_running": self.is_running,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime,
            "capabilities": self.capabilities,
            "config": self.config
        }


# Main execution when run as script
if __name__ == "__main__":
    import importlib.util
    
    # Load the specific agent implementation
    agent_file = os.environ.get('AGENT_FILE', '/app/agent.py')
    
    if os.path.exists(agent_file):
        try:
            # Dynamically import the agent
            spec = importlib.util.spec_from_file_location("agent_module", agent_file)
            agent_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(agent_module)
            
            # Find the agent class (should inherit from SandboxAgent)
            agent_class = None
            for name in dir(agent_module):
                obj = getattr(agent_module, name)
                if (isinstance(obj, type) and 
                    name != 'SandboxAgent' and
                    hasattr(obj, '__mro__') and
                    any(cls.__name__ == 'SandboxAgent' for cls in obj.__mro__)):
                    agent_class = obj
                    break
            
            if agent_class:
                # Create and run the agent
                agent = agent_class()
                result = asyncio.run(agent.run())
                
                # Output results for the sandbox manager
                print(json.dumps(result, indent=2, default=str))
                
                # Exit with appropriate code
                if result.get('status') == 'completed':
                    sys.exit(0)
                else:
                    sys.exit(1)
            else:
                print(json.dumps({
                    'status': 'failed',
                    'error': 'No valid agent class found in agent file'
                }))
                sys.exit(1)
                
        except Exception as e:
            print(json.dumps({
                'status': 'failed',
                'error': f'Failed to load agent: {str(e)}'
            }))
            sys.exit(1)
    else:
        print(json.dumps({
            'status': 'failed',
            'error': f'Agent file not found: {agent_file}'
        }))
        sys.exit(1)