#!/usr/bin/env python3
"""Docker sandbox system for safely executing HeyJarvis agent code."""

import asyncio
import docker
import json
import logging
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass

from .agent_spec import AgentSpec

logger = logging.getLogger(__name__)


@dataclass
class SandboxConfig:
    """Configuration for agent sandbox."""
    base_image: str = "heyjarvis-agent:latest"
    network_name: str = "heyjarvis-sandbox"
    max_cpu_cores: float = 2.0
    max_memory_mb: int = 1024
    default_timeout: int = 300  # 5 minutes
    allowed_networks: List[str] = None
    secrets_volume: str = "/app/secrets"
    logs_volume: str = "/app/logs"
    
    def __post_init__(self):
        if self.allowed_networks is None:
            self.allowed_networks = [
                "googleapis.com",
                "slack.com",
                "api.twitter.com",
                "graph.microsoft.com",
                "api.github.com",
                "webhook.site"  # For testing
            ]


class SandboxError(Exception):
    """Base exception for sandbox operations."""
    pass


class SandboxTimeoutError(SandboxError):
    """Raised when agent execution times out."""
    pass


class SandboxManager:
    """Manages Docker sandboxes for safe agent execution."""
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.docker_client = None
        self.active_containers: Dict[str, docker.models.containers.Container] = {}
        self.container_logs: Dict[str, List[str]] = {}
        
    async def initialize(self) -> None:
        """Initialize the sandbox manager."""
        try:
            self.docker_client = docker.from_env()
            
            # Build base image if it doesn't exist
            await self._ensure_base_image()
            
            # Create sandbox network if it doesn't exist
            await self._ensure_sandbox_network()
            
            logger.info("SandboxManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SandboxManager: {e}")
            raise SandboxError(f"Initialization failed: {e}")
    
    async def _ensure_base_image(self) -> None:
        """Ensure the base agent image exists."""
        try:
            # Check if image exists
            try:
                self.docker_client.images.get(self.config.base_image)
                logger.info(f"Base image {self.config.base_image} already exists")
                return
            except docker.errors.ImageNotFound:
                pass
            
            # Build the image
            logger.info(f"Building base image: {self.config.base_image}")
            dockerfile_dir = Path(__file__).parent / "docker"
            
            try:
                image, logs = self.docker_client.images.build(
                    path=str(dockerfile_dir),
                    dockerfile="Dockerfile.agent",
                    tag=self.config.base_image,
                    rm=True,
                    forcerm=True,
                    nocache=False  # Allow caching for faster rebuilds
                )
                
                # Log build output
                for log in logs:
                    if 'stream' in log:
                        logger.info(log['stream'].strip())
                    elif 'error' in log:
                        logger.error(log['error'])
                
                logger.info(f"Successfully built base image: {self.config.base_image}")
                
            except Exception as build_error:
                logger.error("Docker build failed. Full build logs:")
                
                # Try to get build logs even on failure
                try:
                    _, logs = self.docker_client.images.build(
                        path=str(dockerfile_dir),
                        dockerfile="Dockerfile.agent",
                        tag=self.config.base_image + "-debug",
                        rm=False,
                        forcerm=False
                    )
                    
                    for log in logs:
                        if 'stream' in log:
                            logger.error(f"BUILD: {log['stream'].strip()}")
                        elif 'error' in log:
                            logger.error(f"ERROR: {log['error']}")
                            
                except Exception as debug_error:
                    logger.error(f"Could not get debug logs: {debug_error}")
                
                raise build_error
            
        except Exception as e:
            logger.error(f"Failed to build base image: {e}")
            raise SandboxError(f"Image build failed: {e}")
    
    async def _ensure_sandbox_network(self) -> None:
        """Ensure the sandbox network exists."""
        try:
            # Check if network exists
            networks = self.docker_client.networks.list(names=[self.config.network_name])
            if networks:
                logger.info(f"Sandbox network {self.config.network_name} already exists")
                return
            
            # Create isolated network
            network = self.docker_client.networks.create(
                self.config.network_name,
                driver="bridge",
                options={
                    "com.docker.network.bridge.enable_icc": "false",
                    "com.docker.network.bridge.enable_ip_masquerade": "true"
                }
            )
            
            logger.info(f"Created sandbox network: {self.config.network_name}")
            
        except Exception as e:
            logger.error(f"Failed to create sandbox network: {e}")
            raise SandboxError(f"Network creation failed: {e}")
    
    async def create_sandbox(
        self,
        agent_id: str,
        agent_code: str,
        agent_spec: AgentSpec,
        requirements: Optional[List[str]] = None,
        secrets: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create a Docker sandbox for an agent.
        
        Args:
            agent_id: Unique identifier for the agent
            agent_code: Python code for the agent
            agent_spec: AgentSpec with resource limits and config
            requirements: Additional Python packages to install
            secrets: OAuth tokens and API keys
            
        Returns:
            Container ID
        """
        try:
            container_id = f"agent-{agent_id}-{uuid.uuid4().hex[:8]}"
            logger.info(f"Creating sandbox for agent {agent_id}: {container_id}")
            
            # Create temporary directory for agent files
            temp_dir = tempfile.mkdtemp(prefix=f"agent-{agent_id}-")
            temp_path = Path(temp_dir)
            
            # Write agent code to file
            agent_file = temp_path / "agent.py"
            with open(agent_file, 'w') as f:
                f.write(agent_code)
            
            # Create requirements file if additional packages needed
            if requirements:
                req_file = temp_path / "additional_requirements.txt"
                with open(req_file, 'w') as f:
                    f.write('\n'.join(requirements))
            
            # Create secrets directory and files
            secrets_dir = temp_path / "secrets"
            secrets_dir.mkdir(exist_ok=True)
            
            if secrets:
                for key, value in secrets.items():
                    secret_file = secrets_dir / f"{key}.txt"
                    with open(secret_file, 'w') as f:
                        f.write(value)
            
            # Create logs directory
            logs_dir = temp_path / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            # Prepare container configuration
            environment = {
                'SANDBOX_ID': container_id,
                'AGENT_TIMEOUT': str(agent_spec.resource_limits.timeout),
                'AGENT_MAX_MEMORY': str(agent_spec.resource_limits.memory),
                'AGENT_FILE': '/app/agent.py'
            }
            
            # Resource limits
            cpu_limit = min(agent_spec.resource_limits.cpu, self.config.max_cpu_cores)
            memory_limit = min(agent_spec.resource_limits.memory, self.config.max_memory_mb)
            
            # Volume mounts
            volumes = {
                str(agent_file): {'bind': '/app/agent.py', 'mode': 'ro'},
                str(secrets_dir): {'bind': '/app/secrets', 'mode': 'ro'},
                str(logs_dir): {'bind': '/app/logs', 'mode': 'rw'}
            }
            
            # Security settings
            security_opt = [
                'no-new-privileges:true'
            ]
            
            # Create container
            container = self.docker_client.containers.create(
                image=self.config.base_image,
                name=container_id,
                environment=environment,
                volumes=volumes,
                network=self.config.network_name,
                security_opt=security_opt,
                read_only=True,
                tmpfs={'/tmp': 'size=100m,noexec'},
                mem_limit=f"{memory_limit}m",
                cpu_period=100000,
                cpu_quota=int(cpu_limit * 100000),
                detach=True,
                remove=False,  # Keep container for log inspection
                user="agentuser",
                working_dir="/app",
                command=["python", "/app/base_agent.py"]
            )
            
            # Store container reference
            self.active_containers[container_id] = container
            self.container_logs[container_id] = []
            
            logger.info(f"Successfully created sandbox {container_id}")
            return container_id
            
        except Exception as e:
            logger.error(f"Failed to create sandbox for {agent_id}: {e}")
            raise SandboxError(f"Sandbox creation failed: {e}")
    
    async def execute_agent(self, container_id: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """
        Execute the agent in the sandbox.
        
        Args:
            container_id: Container ID returned from create_sandbox
            timeout: Execution timeout in seconds
            
        Returns:
            Execution results
        """
        if container_id not in self.active_containers:
            raise SandboxError(f"Container {container_id} not found")
        
        container = self.active_containers[container_id]
        timeout = timeout or self.config.default_timeout
        
        try:
            logger.info(f"Starting agent execution in {container_id}")
            
            # Start the container
            container.start()
            
            # Wait for completion with timeout
            try:
                exit_code = container.wait(timeout=timeout)
                
                # Get logs
                logs = container.logs(stdout=True, stderr=True).decode('utf-8')
                self.container_logs[container_id].append(logs)
                
                # Parse results from logs (should be JSON output)
                result = self._parse_execution_result(logs)
                result['exit_code'] = exit_code['StatusCode']
                result['container_id'] = container_id
                
                logger.info(f"Agent execution completed: {container_id}")
                return result
                
            except Exception as e:
                # Container didn't finish in time
                logger.warning(f"Agent execution timeout: {container_id}")
                container.stop(timeout=10)
                
                return {
                    'status': 'timeout',
                    'error': f'Execution timed out after {timeout} seconds',
                    'container_id': container_id,
                    'timeout': timeout
                }
                
        except Exception as e:
            logger.error(f"Failed to execute agent {container_id}: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'container_id': container_id
            }
    
    def _parse_execution_result(self, logs: str) -> Dict[str, Any]:
        """Parse execution results from container logs."""
        try:
            # Look for JSON output in the last few lines
            lines = logs.strip().split('\n')
            
            for line in reversed(lines):
                line = line.strip()
                if line.startswith('{') and line.endswith('}'):
                    try:
                        return json.loads(line)
                    except json.JSONDecodeError:
                        continue
            
            # If no JSON found, return basic info
            return {
                'status': 'completed',
                'result': 'No structured output found',
                'logs': logs
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Failed to parse results: {e}',
                'logs': logs
            }
    
    async def get_agent_logs(self, container_id: str) -> List[str]:
        """Get logs from a container."""
        if container_id not in self.active_containers:
            raise SandboxError(f"Container {container_id} not found")
        
        try:
            container = self.active_containers[container_id]
            logs = container.logs(stdout=True, stderr=True).decode('utf-8')
            return logs.split('\n')
            
        except Exception as e:
            logger.error(f"Failed to get logs for {container_id}: {e}")
            return [f"Error getting logs: {e}"]
    
    async def stop_agent(self, container_id: str, timeout: int = 10) -> bool:
        """Stop a running agent."""
        if container_id not in self.active_containers:
            raise SandboxError(f"Container {container_id} not found")
        
        try:
            container = self.active_containers[container_id]
            container.stop(timeout=timeout)
            logger.info(f"Stopped agent: {container_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop agent {container_id}: {e}")
            return False
    
    async def cleanup_sandbox(self, container_id: str) -> bool:
        """Remove a container and cleanup resources."""
        if container_id not in self.active_containers:
            logger.warning(f"Container {container_id} not found for cleanup")
            return True
        
        try:
            container = self.active_containers[container_id]
            
            # Stop container if running
            try:
                container.stop(timeout=5)
            except:
                pass
            
            # Remove container
            container.remove(force=True)
            
            # Cleanup references
            del self.active_containers[container_id]
            if container_id in self.container_logs:
                del self.container_logs[container_id]
            
            logger.info(f"Cleaned up sandbox: {container_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cleanup sandbox {container_id}: {e}")
            return False
    
    async def list_active_containers(self) -> List[Dict[str, Any]]:
        """List all active agent containers."""
        containers = []
        
        for container_id, container in self.active_containers.items():
            try:
                container.reload()
                status = container.status
                
                containers.append({
                    'container_id': container_id,
                    'status': status,
                    'created': container.attrs['Created'],
                    'image': container.attrs['Config']['Image'],
                    'labels': container.attrs['Config'].get('Labels', {})
                })
                
            except Exception as e:
                logger.error(f"Error getting info for container {container_id}: {e}")
        
        return containers
    
    async def cleanup_all(self) -> None:
        """Cleanup all managed containers."""
        logger.info("Cleaning up all sandbox containers...")
        
        container_ids = list(self.active_containers.keys())
        for container_id in container_ids:
            await self.cleanup_sandbox(container_id)
        
        logger.info(f"Cleaned up {len(container_ids)} containers")
    
    async def get_container_stats(self, container_id: str) -> Optional[Dict[str, Any]]:
        """Get real-time stats for a container."""
        if container_id not in self.active_containers:
            return None
        
        try:
            container = self.active_containers[container_id]
            stats = container.stats(stream=False)
            
            # Parse key metrics
            return {
                'cpu_usage': self._calculate_cpu_usage(stats),
                'memory_usage_mb': stats['memory']['usage'] / (1024 * 1024),
                'memory_limit_mb': stats['memory']['limit'] / (1024 * 1024),
                'network_io': stats.get('networks', {}),
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats for {container_id}: {e}")
            return None
    
    def _calculate_cpu_usage(self, stats: Dict[str, Any]) -> float:
        """Calculate CPU usage percentage from container stats."""
        try:
            cpu_stats = stats['cpu_stats']
            precpu_stats = stats['precpu_stats']
            
            cpu_delta = cpu_stats['cpu_usage']['total_usage'] - precpu_stats['cpu_usage']['total_usage']
            system_delta = cpu_stats['system_cpu_usage'] - precpu_stats['system_cpu_usage']
            
            if system_delta > 0:
                cpu_usage = (cpu_delta / system_delta) * len(cpu_stats['cpu_usage']['percpu_usage']) * 100.0
                return round(cpu_usage, 2)
            
            return 0.0
            
        except Exception:
            return 0.0