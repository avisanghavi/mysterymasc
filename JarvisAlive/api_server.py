"""FastAPI server for HeyJarvis orchestrator."""

import asyncio
import logging
import os
from typing import Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from orchestration.orchestrator import HeyJarvisOrchestrator, OrchestratorConfig

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global orchestrator instance
orchestrator = None


class AgentRequest(BaseModel):
    """Request model for agent creation."""
    user_request: str
    session_id: str


class AgentResponse(BaseModel):
    """Response model for agent creation."""
    status: str
    agent_spec: Dict[str, Any] = None
    error_message: str = None
    execution_context: Dict[str, Any] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage app lifecycle."""
    global orchestrator
    
    # Startup
    config = OrchestratorConfig(
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379"),
    )
    orchestrator = HeyJarvisOrchestrator(config)
    await orchestrator.initialize()
    logger.info("HeyJarvis orchestrator initialized")
    
    yield
    
    # Shutdown
    if orchestrator:
        await orchestrator.close()
    logger.info("HeyJarvis orchestrator shut down")


# Create FastAPI app
app = FastAPI(
    title="HeyJarvis API",
    description="AI Agent Orchestration System",
    version="0.1.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"message": "HeyJarvis API is running"}


@app.post("/agents/create", response_model=AgentResponse)
async def create_agent(request: AgentRequest):
    """Create a new agent."""
    try:
        result = await orchestrator.process_request(
            request.user_request, 
            request.session_id
        )
        
        return AgentResponse(
            status=result["deployment_status"].value,
            agent_spec=result.get("agent_spec"),
            error_message=result.get("error_message"),
            execution_context=result.get("execution_context", {})
        )
        
    except Exception as e:
        logger.error(f"Error creating agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/agents/session/{session_id}")
async def get_session_agents(session_id: str):
    """Get agents for a session."""
    try:
        state = await orchestrator.recover_session(session_id)
        if state:
            return {
                "session_id": session_id,
                "agents": state.get("existing_agents", [])
            }
        return {"session_id": session_id, "agents": []}
        
    except Exception as e:
        logger.error(f"Error getting session agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time agent creation."""
    await websocket.accept()
    
    try:
        while True:
            # Receive user request
            data = await websocket.receive_json()
            user_request = data.get("user_request")
            
            if not user_request:
                await websocket.send_json({
                    "error": "user_request is required"
                })
                continue
            
            # Process request
            result = await orchestrator.process_request(user_request, session_id)
            
            # Send response
            await websocket.send_json({
                "status": result["deployment_status"].value,
                "agent_spec": result.get("agent_spec"),
                "error_message": result.get("error_message"),
                "execution_context": result.get("execution_context", {})
            })
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)