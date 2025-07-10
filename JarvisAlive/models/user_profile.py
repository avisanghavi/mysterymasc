"""User profile and session management models."""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum


class UserTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PREMIUM = "premium"
    ENTERPRISE = "enterprise"


class UserProfile(BaseModel):
    """User profile model for storing user preferences and limits."""
    id: str = Field(..., description="User ID from Supabase")
    email: str = Field(..., description="User email address")
    tier: UserTier = Field(default=UserTier.FREE, description="User subscription tier")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Preferences
    preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    enabled_features: List[str] = Field(default_factory=list, description="Enabled features")
    
    # Usage limits based on tier
    agent_limit: int = Field(default=5, description="Maximum number of agents")
    monthly_requests: int = Field(default=1000, description="Monthly request limit")
    storage_limit_mb: int = Field(default=100, description="Storage limit in MB")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    def get_tier_limits(self) -> Dict[str, int]:
        """Get limits based on user tier."""
        limits = {
            UserTier.FREE: {
                "agent_limit": 5,
                "monthly_requests": 1000,
                "storage_limit_mb": 100
            },
            UserTier.PREMIUM: {
                "agent_limit": 25,
                "monthly_requests": 10000,
                "storage_limit_mb": 1000
            },
            UserTier.ENTERPRISE: {
                "agent_limit": 100,
                "monthly_requests": 50000,
                "storage_limit_mb": 10000
            }
        }
        return limits.get(self.tier, limits[UserTier.FREE])
    
    def update_limits(self):
        """Update user limits based on tier."""
        limits = self.get_tier_limits()
        self.agent_limit = limits["agent_limit"]
        self.monthly_requests = limits["monthly_requests"]
        self.storage_limit_mb = limits["storage_limit_mb"]
    
    def can_create_agent(self, current_count: int) -> bool:
        """Check if user can create another agent."""
        return current_count < self.agent_limit
    
    def can_make_request(self, current_count: int) -> bool:
        """Check if user can make another request this month."""
        return current_count < self.monthly_requests


class UserSession(BaseModel):
    """User session model for tracking active sessions."""
    id: str = Field(..., description="Session ID")
    user_id: str = Field(..., description="User ID")
    original_session_id: Optional[str] = Field(None, description="Original anonymous session ID")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = Field(None, description="Session expiration time")
    
    # Session data
    context: Dict[str, Any] = Field(default_factory=dict, description="Session context")
    agent_count: int = Field(default=0, description="Number of agents in session")
    
    # Metadata
    ip_address: Optional[str] = Field(None, description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    
    def is_expired(self) -> bool:
        """Check if session is expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def update_activity(self):
        """Update last activity timestamp."""
        self.last_activity = datetime.now(timezone.utc)


class UserUsage(BaseModel):
    """User usage tracking model."""
    user_id: str = Field(..., description="User ID")
    month: str = Field(..., description="Month in YYYY-MM format")
    
    # Usage counters
    api_requests: int = Field(default=0, description="API requests made")
    agents_created: int = Field(default=0, description="Agents created")
    websocket_connections: int = Field(default=0, description="WebSocket connections")
    storage_used_mb: float = Field(default=0.0, description="Storage used in MB")
    
    # Detailed usage
    request_details: List[Dict[str, Any]] = Field(default_factory=list, description="Request details")
    agent_details: List[Dict[str, Any]] = Field(default_factory=list, description="Agent details")
    
    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    def add_request(self, endpoint: str, processing_time: float):
        """Add a request to usage tracking."""
        self.api_requests += 1
        self.request_details.append({
            "endpoint": endpoint,
            "processing_time": processing_time,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.updated_at = datetime.now(timezone.utc)
    
    def add_agent(self, agent_id: str, agent_type: str):
        """Add an agent to usage tracking."""
        self.agents_created += 1
        self.agent_details.append({
            "agent_id": agent_id,
            "agent_type": agent_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.updated_at = datetime.now(timezone.utc)
    
    def add_websocket_connection(self):
        """Add a WebSocket connection to usage tracking."""
        self.websocket_connections += 1
        self.updated_at = datetime.now(timezone.utc)


class UserQuota(BaseModel):
    """User quota management model."""
    user_id: str = Field(..., description="User ID")
    quota_type: str = Field(..., description="Type of quota (requests, agents, storage)")
    limit: int = Field(..., description="Quota limit")
    used: int = Field(default=0, description="Amount used")
    reset_date: datetime = Field(..., description="When quota resets")
    
    def is_exceeded(self) -> bool:
        """Check if quota is exceeded."""
        return self.used >= self.limit
    
    def remaining(self) -> int:
        """Get remaining quota."""
        return max(0, self.limit - self.used)
    
    def percentage_used(self) -> float:
        """Get percentage of quota used."""
        return (self.used / self.limit) * 100 if self.limit > 0 else 0
    
    def can_consume(self, amount: int = 1) -> bool:
        """Check if can consume specified amount."""
        return (self.used + amount) <= self.limit
    
    def consume(self, amount: int = 1) -> bool:
        """Consume quota amount, return success."""
        if self.can_consume(amount):
            self.used += amount
            return True
        return False