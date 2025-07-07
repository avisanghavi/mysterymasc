import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

from base_agent import SandboxAgent

logger = logging.getLogger(__name__)

class SimpleTestAgent(SandboxAgent):
    def __init__(self) -> None:
        super().__init__()
        self.name = "Simple Test Agent"
        self.version = "1.0.0"
        self.capabilities = ["testing"]

    async def initialize(self) -> None:
        logger.info("Simple agent initialized")

    async def execute(self) -> Any:
        logger.info("Simple agent executing")
        return {"message": "Hello from simple agent", "status": "success"}

    async def cleanup(self) -> None:
        logger.info("Simple agent cleanup completed")