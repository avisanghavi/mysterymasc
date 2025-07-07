"""Agent communication infrastructure for micro-agent coordination within departments."""

import json
import time
import logging
from typing import Dict, Any, List, Optional, Union, Literal
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

import redis.asyncio as redis
from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """Types of messages that can be sent between agents."""
    DATA_SHARE = "DataShareMessage"
    TASK_ASSIGNMENT = "TaskAssignmentMessage"
    STATUS_UPDATE = "StatusUpdateMessage"
    COORDINATION = "CoordinationMessage"
    ALERT = "AlertMessage"
    HANDOFF = "HandoffMessage"


class MessagePriority(str, Enum):
    """Message priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MessageStatus(str, Enum):
    """Message processing status."""
    PENDING = "pending"
    DELIVERED = "delivered"
    READ = "read"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"


# Pydantic Message Models
class BaseMessage(BaseModel):
    """Base message model with common fields."""
    message_id: str = Field(..., description="Unique message identifier")
    from_agent_id: str = Field(..., description="Sender agent ID")
    to_agent_id: Optional[str] = Field(None, description="Recipient agent ID (None for broadcasts)")
    message_type: MessageType = Field(..., description="Type of message")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    priority: MessagePriority = Field(default=MessagePriority.MEDIUM, description="Message priority")
    department_id: Optional[str] = Field(None, description="Department context")
    expires_at: Optional[datetime] = Field(None, description="Message expiration time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataShareMessage(BaseMessage):
    """Message for sharing data between agents."""
    message_type: Literal[MessageType.DATA_SHARE] = Field(default=MessageType.DATA_SHARE, description="Message type")
    data_type: str = Field(..., description="Type of data being shared")
    data_content: Dict[str, Any] = Field(..., description="The actual data content")
    schema_version: str = Field(default="1.0", description="Data schema version")
    data_size: Optional[int] = Field(None, description="Size of data in bytes")
    
    @field_validator('data_content')
    @classmethod
    def validate_data_content(cls, v):
        if not isinstance(v, dict):
            raise ValueError("data_content must be a dictionary")
        return v


class TaskAssignmentMessage(BaseMessage):
    """Message for delegating tasks between agents."""
    message_type: Literal[MessageType.TASK_ASSIGNMENT] = Field(default=MessageType.TASK_ASSIGNMENT, description="Message type")
    task_id: str = Field(..., description="Unique task identifier")
    task_spec: Dict[str, Any] = Field(..., description="Task specification and requirements")
    deadline: Optional[datetime] = Field(None, description="Task deadline")
    estimated_duration: Optional[int] = Field(None, description="Estimated duration in minutes")
    required_capabilities: List[str] = Field(default_factory=list, description="Required agent capabilities")
    dependencies: List[str] = Field(default_factory=list, description="Task dependencies")
    
    @field_validator('task_spec')
    @classmethod
    def validate_task_spec(cls, v):
        required_fields = ['action', 'description']
        for field in required_fields:
            if field not in v:
                raise ValueError(f"task_spec must contain '{field}' field")
        return v


class StatusUpdateMessage(BaseMessage):
    """Message for reporting agent progress and status."""
    message_type: Literal[MessageType.STATUS_UPDATE] = Field(default=MessageType.STATUS_UPDATE, description="Message type")
    status: str = Field(..., description="Current agent status")
    progress_percentage: float = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    details: Dict[str, Any] = Field(default_factory=dict, description="Status details")
    task_id: Optional[str] = Field(None, description="Related task ID")
    error_info: Optional[Dict[str, Any]] = Field(None, description="Error information if status is error")
    next_action: Optional[str] = Field(None, description="Next planned action")
    
    @field_validator('progress_percentage')
    @classmethod
    def validate_progress(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("progress_percentage must be between 0 and 100")
        return v


class CoordinationMessage(BaseMessage):
    """Message for coordination between agents."""
    message_type: Literal[MessageType.COORDINATION] = Field(default=MessageType.COORDINATION, description="Message type")
    coordination_type: str = Field(..., description="Type of coordination needed")
    context: Dict[str, Any] = Field(default_factory=dict, description="Coordination context")
    proposed_action: Optional[str] = Field(None, description="Proposed action")
    requires_response: bool = Field(default=False, description="Whether response is required")
    response_deadline: Optional[datetime] = Field(None, description="Response deadline")


class AlertMessage(BaseMessage):
    """Message for alerts and notifications."""
    message_type: Literal[MessageType.ALERT] = Field(default=MessageType.ALERT, description="Message type")
    alert_type: str = Field(..., description="Type of alert")
    alert_level: str = Field(..., description="Alert severity level")
    alert_content: str = Field(..., description="Alert message content")
    action_required: bool = Field(default=False, description="Whether action is required")
    escalation_path: Optional[List[str]] = Field(None, description="Escalation path if no response")


@dataclass
class MessageDeliveryResult:
    """Result of message delivery attempt."""
    message_id: str
    success: bool
    error_message: Optional[str] = None
    delivery_time: Optional[datetime] = None
    retry_count: int = 0


class AgentMessageBus:
    """Message bus for agent communication using Redis Streams."""
    
    def __init__(self, redis_client: redis.Redis):
        """Initialize the message bus with Redis client."""
        self.redis_client = redis_client
        self.rate_limit_window = 60  # 1 minute
        self.rate_limit_max = 100  # 100 messages per minute
        self.message_ttl = 604800  # 7 days in seconds
        self.dead_letter_ttl = 2592000  # 30 days for dead letters
        
    async def publish_message(
        self, 
        from_agent_id: str, 
        to_agent_id: str, 
        message_type: str, 
        payload: dict,
        priority: MessagePriority = MessagePriority.MEDIUM
    ) -> str:
        """
        Publish a message from one agent to another.
        
        Args:
            from_agent_id: ID of the sending agent
            to_agent_id: ID of the receiving agent
            message_type: Type of message (must match MessageType enum)
            payload: Message payload data
            priority: Message priority level
            
        Returns:
            message_id: Unique identifier for the sent message
            
        Raises:
            ValueError: If message type is invalid or rate limit exceeded
            redis.RedisError: If Redis operation fails
        """
        try:
            # Validate message type
            if message_type not in [mt.value for mt in MessageType]:
                raise ValueError(f"Invalid message type: {message_type}")
            
            # Check rate limit
            if not await self._check_rate_limit(from_agent_id):
                raise ValueError(f"Rate limit exceeded for agent {from_agent_id}")
            
            # Generate message ID
            message_id = f"{from_agent_id}:{to_agent_id}:{int(time.time() * 1000)}"
            
            # Create message
            message_data = {
                "message_id": message_id,
                "from_agent_id": from_agent_id,
                "to_agent_id": to_agent_id,
                "message_type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
                "priority": priority.value,
                "payload": payload,
                "status": MessageStatus.PENDING.value
            }
            
            # Publish to recipient's stream
            stream_key = f"agent:{to_agent_id}:messages"
            await self.redis_client.xadd(stream_key, message_data)
            
            # Set TTL on the stream
            await self.redis_client.expire(stream_key, self.message_ttl)
            
            # Store message in sender's outbox for tracking
            outbox_key = f"agent:{from_agent_id}:outbox"
            await self.redis_client.xadd(outbox_key, {
                "message_id": message_id,
                "to_agent_id": to_agent_id,
                "message_type": message_type,
                "timestamp": datetime.utcnow().isoformat(),
                "status": MessageStatus.DELIVERED.value
            })
            await self.redis_client.expire(outbox_key, self.message_ttl)
            
            # Update rate limit counter
            await self._update_rate_limit(from_agent_id)
            
            logger.info(f"Message {message_id} sent from {from_agent_id} to {to_agent_id}")
            return message_id
            
        except Exception as e:
            logger.error(f"Error publishing message: {e}")
            # Add to dead letter queue
            await self._add_to_dead_letter_queue(from_agent_id, to_agent_id, message_type, payload, str(e))
            raise
    
    async def broadcast_to_department(
        self, 
        dept_id: str, 
        message: dict,
        from_agent_id: Optional[str] = None
    ) -> List[str]:
        """
        Broadcast a message to all agents in a department.
        
        Args:
            dept_id: Department ID
            message: Message to broadcast
            from_agent_id: Optional sender agent ID
            
        Returns:
            List of message IDs for each recipient
            
        Raises:
            redis.RedisError: If Redis operation fails
        """
        try:
            message_ids = []
            
            # Generate broadcast message ID
            broadcast_id = f"dept:{dept_id}:broadcast:{int(time.time() * 1000)}"
            
            # Prepare broadcast message
            broadcast_data = {
                "broadcast_id": broadcast_id,
                "department_id": dept_id,
                "from_agent_id": from_agent_id or "system",
                "timestamp": datetime.utcnow().isoformat(),
                "message": json.dumps(message),
                "message_type": "broadcast"
            }
            
            # Add to department broadcast stream
            dept_stream_key = f"dept:{dept_id}:broadcast"
            await self.redis_client.xadd(dept_stream_key, broadcast_data)
            await self.redis_client.expire(dept_stream_key, self.message_ttl)
            
            # Get all agents in the department
            dept_agents = await self._get_department_agents(dept_id)
            
            # Send to each agent's individual stream
            for agent_id in dept_agents:
                try:
                    individual_message_id = f"{broadcast_id}:{agent_id}"
                    
                    agent_message_data = {
                        "message_id": individual_message_id,
                        "from_agent_id": from_agent_id or "system",
                        "to_agent_id": agent_id,
                        "message_type": "broadcast",
                        "timestamp": datetime.utcnow().isoformat(),
                        "priority": MessagePriority.MEDIUM.value,
                        "department_id": dept_id,
                        "broadcast_id": broadcast_id,
                        "payload": message,
                        "status": MessageStatus.PENDING.value
                    }
                    
                    # Add to agent's message stream
                    agent_stream_key = f"agent:{agent_id}:messages"
                    await self.redis_client.xadd(agent_stream_key, agent_message_data)
                    await self.redis_client.expire(agent_stream_key, self.message_ttl)
                    
                    message_ids.append(individual_message_id)
                    
                except Exception as e:
                    logger.error(f"Error sending broadcast to agent {agent_id}: {e}")
                    continue
            
            logger.info(f"Broadcast {broadcast_id} sent to {len(message_ids)} agents in department {dept_id}")
            return message_ids
            
        except Exception as e:
            logger.error(f"Error broadcasting to department {dept_id}: {e}")
            raise
    
    async def subscribe_to_topics(self, agent_id: str, topics: List[str]) -> bool:
        """
        Subscribe an agent to specific message topics.
        
        Args:
            agent_id: Agent ID
            topics: List of topics to subscribe to
            
        Returns:
            True if subscription successful, False otherwise
        """
        try:
            subscription_key = f"agent:{agent_id}:subscriptions"
            
            # Store subscriptions as a Redis set
            for topic in topics:
                await self.redis_client.sadd(subscription_key, topic)
            
            # Set TTL on subscriptions
            await self.redis_client.expire(subscription_key, self.message_ttl)
            
            logger.info(f"Agent {agent_id} subscribed to topics: {topics}")
            return True
            
        except Exception as e:
            logger.error(f"Error subscribing agent {agent_id} to topics: {e}")
            return False
    
    async def get_pending_messages(self, agent_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get pending messages for an agent.
        
        Args:
            agent_id: Agent ID
            limit: Maximum number of messages to retrieve
            
        Returns:
            List of pending messages
        """
        try:
            stream_key = f"agent:{agent_id}:messages"
            
            # Get messages from the stream
            messages = await self.redis_client.xread({stream_key: '0'}, count=limit)
            
            pending_messages = []
            
            for stream, msgs in messages:
                for msg_id, fields in msgs:
                    try:
                        # Decode message fields
                        decoded_fields = {k.decode(): v.decode() for k, v in fields.items()}
                        
                        # Parse JSON fields
                        if 'payload' in decoded_fields:
                            decoded_fields['payload'] = json.loads(decoded_fields['payload'])
                        
                        # Add stream message ID
                        decoded_fields['stream_message_id'] = msg_id.decode()
                        
                        pending_messages.append(decoded_fields)
                        
                    except Exception as e:
                        logger.error(f"Error decoding message {msg_id}: {e}")
                        continue
            
            logger.info(f"Retrieved {len(pending_messages)} pending messages for agent {agent_id}")
            return pending_messages
            
        except Exception as e:
            logger.error(f"Error getting pending messages for agent {agent_id}: {e}")
            return []
    
    async def mark_message_read(self, agent_id: str, message_id: str) -> bool:
        """
        Mark a message as read by an agent.
        
        Args:
            agent_id: Agent ID
            message_id: Message ID or stream message ID
            
        Returns:
            True if message marked as read, False otherwise
        """
        try:
            # Update message status in agent's stream
            read_key = f"agent:{agent_id}:read_messages"
            read_data = {
                "message_id": message_id,
                "read_at": datetime.utcnow().isoformat(),
                "agent_id": agent_id
            }
            
            await self.redis_client.xadd(read_key, read_data)
            await self.redis_client.expire(read_key, self.message_ttl)
            
            # Create consumer group for the agent's message stream if it doesn't exist
            stream_key = f"agent:{agent_id}:messages"
            try:
                await self.redis_client.xgroup_create(stream_key, agent_id, '0', mkstream=True)
            except redis.RedisError:
                # Group already exists, ignore
                pass
            
            # Acknowledge the message
            if message_id.startswith('agent:'):
                # If it's a stream message ID, acknowledge it
                await self.redis_client.xack(stream_key, agent_id, message_id)
            
            logger.info(f"Message {message_id} marked as read by agent {agent_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error marking message {message_id} as read by agent {agent_id}: {e}")
            return False
    
    async def get_agent_subscriptions(self, agent_id: str) -> List[str]:
        """Get list of topics an agent is subscribed to."""
        try:
            subscription_key = f"agent:{agent_id}:subscriptions"
            subscriptions = await self.redis_client.smembers(subscription_key)
            return [sub.decode() for sub in subscriptions]
        except Exception as e:
            logger.error(f"Error getting subscriptions for agent {agent_id}: {e}")
            return []
    
    async def get_message_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get message statistics for an agent."""
        try:
            stats = {
                "pending_messages": 0,
                "read_messages": 0,
                "sent_messages": 0,
                "subscriptions": 0
            }
            
            # Count pending messages
            stream_key = f"agent:{agent_id}:messages"
            stream_info = await self.redis_client.xinfo_stream(stream_key)
            stats["pending_messages"] = stream_info.get('length', 0)
            
            # Count read messages
            read_key = f"agent:{agent_id}:read_messages"
            read_info = await self.redis_client.xinfo_stream(read_key)
            stats["read_messages"] = read_info.get('length', 0)
            
            # Count sent messages
            outbox_key = f"agent:{agent_id}:outbox"
            outbox_info = await self.redis_client.xinfo_stream(outbox_key)
            stats["sent_messages"] = outbox_info.get('length', 0)
            
            # Count subscriptions
            subscription_key = f"agent:{agent_id}:subscriptions"
            stats["subscriptions"] = await self.redis_client.scard(subscription_key)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting message stats for agent {agent_id}: {e}")
            return {"error": str(e)}
    
    async def cleanup_expired_messages(self) -> int:
        """Clean up expired messages and return count of cleaned messages."""
        try:
            cleaned_count = 0
            
            # Get all agent message streams
            agent_streams = await self.redis_client.keys("agent:*:messages")
            
            for stream_key in agent_streams:
                try:
                    # Use XTRIM to remove old messages
                    trimmed = await self.redis_client.xtrim(stream_key, maxlen=1000, approximate=True)
                    cleaned_count += trimmed
                except Exception as e:
                    logger.error(f"Error trimming stream {stream_key}: {e}")
                    continue
            
            logger.info(f"Cleaned up {cleaned_count} expired messages")
            return cleaned_count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired messages: {e}")
            return 0
    
    # Private helper methods
    async def _check_rate_limit(self, agent_id: str) -> bool:
        """Check if agent has exceeded rate limit."""
        try:
            rate_key = f"rate_limit:{agent_id}"
            current_count = await self.redis_client.get(rate_key)
            
            if current_count is None:
                return True
            
            return int(current_count) < self.rate_limit_max
            
        except Exception as e:
            logger.error(f"Error checking rate limit for agent {agent_id}: {e}")
            return True  # Allow on error
    
    async def _update_rate_limit(self, agent_id: str) -> None:
        """Update rate limit counter for agent."""
        try:
            rate_key = f"rate_limit:{agent_id}"
            
            # Use pipeline for atomic operations
            pipe = self.redis_client.pipeline()
            pipe.incr(rate_key)
            pipe.expire(rate_key, self.rate_limit_window)
            await pipe.execute()
            
        except Exception as e:
            logger.error(f"Error updating rate limit for agent {agent_id}: {e}")
    
    async def _get_department_agents(self, dept_id: str) -> List[str]:
        """Get list of agents in a department."""
        try:
            # This would typically query the department state
            # For now, return from a Redis set
            dept_agents_key = f"dept:{dept_id}:agents"
            agents = await self.redis_client.smembers(dept_agents_key)
            return [agent.decode() for agent in agents]
        except Exception as e:
            logger.error(f"Error getting agents for department {dept_id}: {e}")
            return []
    
    async def _add_to_dead_letter_queue(
        self, 
        from_agent_id: str, 
        to_agent_id: str, 
        message_type: str, 
        payload: dict, 
        error_message: str
    ) -> None:
        """Add failed message to dead letter queue."""
        try:
            dead_letter_data = {
                "from_agent_id": from_agent_id,
                "to_agent_id": to_agent_id,
                "message_type": message_type,
                "payload": json.dumps(payload),
                "error_message": error_message,
                "failed_at": datetime.utcnow().isoformat(),
                "retry_count": 0
            }
            
            dead_letter_key = "failed:messages"
            await self.redis_client.xadd(dead_letter_key, dead_letter_data)
            await self.redis_client.expire(dead_letter_key, self.dead_letter_ttl)
            
        except Exception as e:
            logger.error(f"Error adding to dead letter queue: {e}")


# Utility functions for message handling
def create_data_share_message(
    from_agent_id: str,
    to_agent_id: str,
    data_type: str,
    data_content: Dict[str, Any],
    department_id: Optional[str] = None
) -> DataShareMessage:
    """Create a data share message."""
    return DataShareMessage(
        message_id=f"data:{from_agent_id}:{to_agent_id}:{int(time.time() * 1000)}",
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        data_type=data_type,
        data_content=data_content,
        department_id=department_id
    )


def create_task_assignment_message(
    from_agent_id: str,
    to_agent_id: str,
    task_id: str,
    task_spec: Dict[str, Any],
    deadline: Optional[datetime] = None,
    department_id: Optional[str] = None
) -> TaskAssignmentMessage:
    """Create a task assignment message."""
    return TaskAssignmentMessage(
        message_id=f"task:{from_agent_id}:{to_agent_id}:{int(time.time() * 1000)}",
        from_agent_id=from_agent_id,
        to_agent_id=to_agent_id,
        task_id=task_id,
        task_spec=task_spec,
        deadline=deadline,
        department_id=department_id
    )


def create_status_update_message(
    from_agent_id: str,
    status: str,
    progress_percentage: float,
    details: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    department_id: Optional[str] = None
) -> StatusUpdateMessage:
    """Create a status update message."""
    return StatusUpdateMessage(
        message_id=f"status:{from_agent_id}:{int(time.time() * 1000)}",
        from_agent_id=from_agent_id,
        status=status,
        progress_percentage=progress_percentage,
        details=details or {},
        task_id=task_id,
        department_id=department_id
    )