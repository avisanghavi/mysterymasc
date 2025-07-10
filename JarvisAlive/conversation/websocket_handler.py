"""WebSocket handler for real-time communication in HeyJarvis and Jarvis modes."""

import json
import logging
import asyncio
from enum import Enum
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timezone
import uuid
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """WebSocket message types for both agent builder and Jarvis modes."""
    # Existing agent builder types
    USER_MESSAGE = "user_message"
    AGENT_CREATED = "agent_created"
    AGENT_UPDATED = "agent_updated"
    AGENT_STATUS = "agent_status"
    ERROR = "error"
    PROGRESS = "progress"
    CLARIFICATION_REQUEST = "clarification_request"
    CLARIFICATION_RESPONSE = "clarification_response"
    
    # New Jarvis business-level types
    DEPARTMENT_ACTIVATED = "department_activated"
    WORKFLOW_PROGRESS = "workflow_progress"
    BUSINESS_METRIC_UPDATED = "business_metric_updated"
    OPTIMIZATION_SUGGESTION = "optimization_suggestion"
    AGENT_COORDINATION = "agent_coordination"
    BUSINESS_INSIGHT = "business_insight"
    DEPARTMENT_STATUS = "department_status"
    KPI_ALERT = "kpi_alert"


class OperatingMode(str, Enum):
    """Operating modes for message context."""
    AGENT_BUILDER = "agent_builder"
    JARVIS = "jarvis"
    HYBRID = "hybrid"  # For messages relevant to both modes


@dataclass
class WebSocketMessage:
    """Standard WebSocket message structure."""
    id: str
    type: MessageType
    mode: OperatingMode
    timestamp: str
    content: str
    details: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(asdict(self))
    
    @classmethod
    def from_json(cls, json_str: str) -> 'WebSocketMessage':
        """Create message from JSON string."""
        data = json.loads(json_str)
        data['type'] = MessageType(data['type'])
        data['mode'] = OperatingMode(data['mode'])
        return cls(**data)


class WebSocketHandler:
    """Handles WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.connections: Dict[str, Any] = {}  # connection_id -> websocket
        self.subscriptions: Dict[str, Set[str]] = {}  # session_id -> {connection_ids}
        self.connection_modes: Dict[str, OperatingMode] = {}  # connection_id -> mode
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.running = False
        
    async def start(self):
        """Start the WebSocket handler."""
        self.running = True
        logger.info("WebSocket handler started")
        
    async def stop(self):
        """Stop the WebSocket handler."""
        self.running = False
        # Close all connections
        for conn_id, websocket in self.connections.items():
            await websocket.close()
        self.connections.clear()
        self.subscriptions.clear()
        logger.info("WebSocket handler stopped")
    
    async def add_connection(self, websocket, connection_id: str = None, mode: OperatingMode = OperatingMode.AGENT_BUILDER, user_id: str = None) -> str:
        """Add a new WebSocket connection."""
        if not connection_id:
            connection_id = str(uuid.uuid4())
        
        self.connections[connection_id] = {
            'websocket': websocket,
            'user_id': user_id,
            'connected_at': datetime.now(timezone.utc),
            'last_activity': datetime.now(timezone.utc)
        }
        self.connection_modes[connection_id] = mode
        
        # Send welcome message
        welcome_msg = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.AGENT_STATUS,
            mode=mode,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"Connected to HeyJarvis WebSocket ({mode.value} mode)",
            details={
                "connection_id": connection_id,
                "mode": mode.value,
                "version": "1.0.0",
                "user_id": user_id,
                "authenticated": user_id is not None
            }
        )
        
        await self.send_to_connection(connection_id, welcome_msg)
        logger.info(f"WebSocket connection added: {connection_id} (mode: {mode.value}, user: {user_id})")
        
        return connection_id
    
    async def remove_connection(self, connection_id: str):
        """Remove a WebSocket connection."""
        if connection_id in self.connections:
            del self.connections[connection_id]
            
            # Remove from all subscriptions
            for session_id, conn_ids in self.subscriptions.items():
                conn_ids.discard(connection_id)
            
            # Clean up empty subscriptions
            self.subscriptions = {
                session_id: conn_ids 
                for session_id, conn_ids in self.subscriptions.items() 
                if conn_ids
            }
            
            if connection_id in self.connection_modes:
                del self.connection_modes[connection_id]
            
            logger.info(f"WebSocket connection removed: {connection_id}")
    
    async def subscribe_to_session(self, connection_id: str, session_id: str):
        """Subscribe a connection to a session for updates."""
        if connection_id not in self.connections:
            logger.warning(f"Connection {connection_id} not found")
            return
        
        if session_id not in self.subscriptions:
            self.subscriptions[session_id] = set()
        
        self.subscriptions[session_id].add(connection_id)
        logger.info(f"Connection {connection_id} subscribed to session {session_id}")
    
    async def unsubscribe_from_session(self, connection_id: str, session_id: str):
        """Unsubscribe a connection from a session."""
        if session_id in self.subscriptions:
            self.subscriptions[session_id].discard(connection_id)
            if not self.subscriptions[session_id]:
                del self.subscriptions[session_id]
        
        logger.info(f"Connection {connection_id} unsubscribed from session {session_id}")
    
    async def send_to_connection(self, connection_id: str, message: WebSocketMessage):
        """Send a message to a specific connection."""
        if connection_id in self.connections:
            connection = self.connections[connection_id]
            websocket = connection['websocket']
            try:
                await websocket.send(message.to_json())
                # Update last activity
                connection['last_activity'] = datetime.now(timezone.utc)
            except Exception as e:
                logger.error(f"Error sending to connection {connection_id}: {e}")
                await self.remove_connection(connection_id)
    
    async def broadcast_to_session(self, session_id: str, message: WebSocketMessage):
        """Broadcast a message to all connections in a session."""
        if session_id not in self.subscriptions:
            return
        
        # Send to all connections subscribed to this session
        for conn_id in list(self.subscriptions[session_id]):
            # Check if connection should receive this message based on mode
            conn_mode = self.connection_modes.get(conn_id, OperatingMode.AGENT_BUILDER)
            
            # Send if message mode matches connection mode or is hybrid
            if message.mode == conn_mode or message.mode == OperatingMode.HYBRID:
                await self.send_to_connection(conn_id, message)
    
    async def broadcast_all(self, message: WebSocketMessage):
        """Broadcast a message to all connections."""
        for conn_id in list(self.connections.keys()):
            # Check mode compatibility
            conn_mode = self.connection_modes.get(conn_id, OperatingMode.AGENT_BUILDER)
            if message.mode == conn_mode or message.mode == OperatingMode.HYBRID:
                await self.send_to_connection(conn_id, message)
    
    # Agent Builder specific messages (backward compatible)
    
    async def send_agent_created(self, session_id: str, agent_spec: Dict[str, Any]):
        """Send agent created notification."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.AGENT_CREATED,
            mode=OperatingMode.AGENT_BUILDER,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"Agent '{agent_spec.get('name', 'Unknown')}' created successfully",
            details=agent_spec
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_progress(self, session_id: str, progress: int, status: str):
        """Send progress update."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.PROGRESS,
            mode=OperatingMode.AGENT_BUILDER,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=status,
            details={
                "progress": progress,
                "status": status
            }
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_error(self, session_id: str, error_message: str, error_details: Optional[Dict] = None):
        """Send error notification."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.ERROR,
            mode=OperatingMode.AGENT_BUILDER,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=error_message,
            details=error_details or {}
        )
        await self.broadcast_to_session(session_id, message)
    
    # Jarvis specific messages (new functionality)
    
    async def send_department_activated(self, session_id: str, department_name: str, agent_count: int, details: Optional[Dict] = None):
        """Send department activation notification."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.DEPARTMENT_ACTIVATED,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"{department_name} department activated with {agent_count} agents",
            details={
                "department": department_name,
                "agents": agent_count,
                **(details or {})
            }
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_workflow_progress(self, session_id: str, workflow_name: str, progress: int, current_step: str):
        """Send workflow progress update."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.WORKFLOW_PROGRESS,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"{workflow_name}: {current_step} ({progress}%)",
            details={
                "workflow": workflow_name,
                "progress": progress,
                "current_step": current_step
            }
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_business_metric_updated(self, session_id: str, metric_name: str, value: Any, change: Optional[float] = None):
        """Send business metric update."""
        details = {
            "metric": metric_name,
            "value": value
        }
        
        if change is not None:
            details["change_percentage"] = change
            change_str = f" ({change:+.1f}%)" if change else ""
        else:
            change_str = ""
        
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.BUSINESS_METRIC_UPDATED,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"{metric_name}: {value}{change_str}",
            details=details
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_optimization_suggestion(self, session_id: str, suggestion: str, impact: str, priority: str = "medium"):
        """Send optimization suggestion."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.OPTIMIZATION_SUGGESTION,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=suggestion,
            details={
                "suggestion": suggestion,
                "impact": impact,
                "priority": priority
            }
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_agent_coordination(self, session_id: str, from_agent: str, to_agent: str, action: str, data: Optional[Dict] = None):
        """Send agent coordination message."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.AGENT_COORDINATION,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"{from_agent} → {to_agent}: {action}",
            details={
                "from_agent": from_agent,
                "to_agent": to_agent,
                "action": action,
                "data": data or {}
            }
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_business_insight(self, session_id: str, insight: str, category: str, confidence: float = 0.8):
        """Send business insight."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.BUSINESS_INSIGHT,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=insight,
            details={
                "insight": insight,
                "category": category,
                "confidence": confidence
            }
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_department_status(self, session_id: str, department: str, status: str, active_agents: int, metrics: Optional[Dict] = None):
        """Send department status update."""
        message = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.DEPARTMENT_STATUS,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"{department}: {status} ({active_agents} agents active)",
            details={
                "department": department,
                "status": status,
                "active_agents": active_agents,
                "metrics": metrics or {}
            }
        )
        await self.broadcast_to_session(session_id, message)
    
    async def send_kpi_alert(self, session_id: str, kpi: str, alert_type: str, message: str, threshold: Optional[float] = None):
        """Send KPI alert."""
        details = {
            "kpi": kpi,
            "alert_type": alert_type,
            "message": message
        }
        
        if threshold is not None:
            details["threshold"] = threshold
        
        alert_msg = WebSocketMessage(
            id=str(uuid.uuid4()),
            type=MessageType.KPI_ALERT,
            mode=OperatingMode.JARVIS,
            timestamp=datetime.now(timezone.utc).isoformat(),
            content=f"KPI Alert - {kpi}: {message}",
            details=details
        )
        await self.broadcast_to_session(session_id, alert_msg)
    
    # Example Jarvis-specific update handlers
    
    async def send_sales_updates(self, session_id: str, updates: Dict[str, Any]):
        """Send batch of sales-related updates."""
        # New leads found
        if "new_leads" in updates:
            await self.send_business_metric_updated(
                session_id, 
                "New Leads", 
                updates["new_leads"],
                change=updates.get("leads_change")
            )
        
        # Meetings scheduled
        if "meetings_scheduled" in updates:
            await self.send_business_insight(
                session_id,
                f"{updates['meetings_scheduled']} meetings scheduled for next week",
                "sales",
                confidence=0.95
            )
        
        # Pipeline value
        if "pipeline_increase" in updates:
            await self.send_business_metric_updated(
                session_id,
                "Pipeline Value",
                f"${updates['pipeline_increase']:,}",
                change=updates.get("pipeline_change_percentage")
            )
        
        # Agent coordination
        if "agent_actions" in updates:
            for action in updates["agent_actions"]:
                await self.send_agent_coordination(
                    session_id,
                    action["from"],
                    action["to"],
                    action["action"],
                    action.get("data")
                )


# Singleton instance
websocket_handler = WebSocketHandler()


# Helper functions for backward compatibility
async def send_agent_created(session_id: str, agent_spec: Dict[str, Any]):
    """Backward compatible helper for agent created notification."""
    await websocket_handler.send_agent_created(session_id, agent_spec)


async def send_progress_update(session_id: str, progress: int, status: str):
    """Backward compatible helper for progress updates."""
    await websocket_handler.send_progress(session_id, progress, status)


async def send_error_message(session_id: str, error: str, details: Optional[Dict] = None):
    """Backward compatible helper for error messages."""
    await websocket_handler.send_error(session_id, error, details)