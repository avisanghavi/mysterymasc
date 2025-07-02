"""Conversation context management for HeyJarvis."""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# Try to import tiktoken, fallback to basic counting if not available
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False
    logger.warning("tiktoken not available, using approximate token counting")


@dataclass
class Message:
    """Represents a conversation message with metadata."""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None
    priority: int = 1  # 1=normal, 2=important, 3=critical
    token_count: int = 0


class ConversationContextManager:
    """Manages conversation context with intelligent token window management."""
    
    def __init__(self, max_tokens: int = 4096, session_id: str = "default"):
        self.max_tokens = max_tokens
        self.session_id = session_id
        self.messages: List[Message] = []
        self.key_decisions: Dict[str, Any] = {}
        self.conversation_summary = ""
        
        # Initialize tokenizer
        if TIKTOKEN_AVAILABLE:
            try:
                self.encoder = tiktoken.get_encoding("cl100k_base")
            except Exception as e:
                logger.warning(f"Failed to initialize tiktoken: {e}")
                self.encoder = None
        else:
            self.encoder = None
    
    def get_token_count(self, text: str) -> int:
        """Count tokens in text using tiktoken or approximation."""
        if self.encoder:
            try:
                return len(self.encoder.encode(text))
            except Exception as e:
                logger.warning(f"Token encoding failed: {e}")
                # Fallback to approximation
                return len(text.split()) * 1.3  # Rough approximation
        else:
            # Approximation: ~1.3 tokens per word on average
            return int(len(text.split()) * 1.3)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None, priority: int = 1) -> None:
        """Add a message to the conversation context."""
        if not content.strip():
            return
            
        token_count = self.get_token_count(content)
        
        message = Message(
            role=role,
            content=content.strip(),
            timestamp=datetime.now(timezone.utc).isoformat(),
            metadata=metadata or {},
            priority=priority,
            token_count=token_count
        )
        
        self.messages.append(message)
        logger.debug(f"Added {role} message with {token_count} tokens")
        
        # Trigger context window management if needed
        self._manage_context_window()
    
    def add_user_message(self, content: str, metadata: Optional[Dict] = None, priority: int = 2) -> None:
        """Add a user message with default priority 2 (important)."""
        self.add_message("user", content, metadata, priority=priority)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict] = None, priority: int = 1) -> None:
        """Add an assistant message with default priority 1."""
        self.add_message("assistant", content, metadata, priority=priority)
    
    def add_system_message(self, content: str, metadata: Optional[Dict] = None, priority: int = 3) -> None:
        """Add a system message with priority 3 (critical)."""
        self.add_message("system", content, metadata, priority=priority)
    
    def get_context_window(self, include_summary: bool = True) -> List[Dict[str, Any]]:
        """Return messages that fit in token window, prioritized by importance."""
        if not self.messages:
            return []
        
        # Calculate available tokens (reserve space for summary if needed)
        available_tokens = self.max_tokens
        if include_summary and self.conversation_summary:
            summary_tokens = self.get_token_count(self.conversation_summary)
            available_tokens -= (summary_tokens + 100)  # Buffer for summary formatting
        
        # Always include the most recent message
        context_messages = []
        used_tokens = 0
        
        # Start from the most recent messages and work backwards
        for message in reversed(self.messages):
            message_tokens = message.token_count + 20  # Buffer for formatting
            
            if used_tokens + message_tokens <= available_tokens:
                context_messages.insert(0, message)
                used_tokens += message_tokens
            else:
                # Check if we can fit this message by removing older, lower-priority ones
                if message.priority >= 2:  # Important messages
                    # Try to make room by removing lower priority messages
                    temp_messages = [m for m in context_messages if m.priority >= message.priority]
                    temp_tokens = sum(m.token_count + 20 for m in temp_messages) + message_tokens
                    
                    if temp_tokens <= available_tokens:
                        context_messages = temp_messages
                        context_messages.insert(0, message)
                        used_tokens = temp_tokens
                    else:
                        break
                else:
                    break
        
        # Convert to format expected by LLM
        formatted_messages = []
        
        # Add summary if available and we have room
        if include_summary and self.conversation_summary and context_messages:
            formatted_messages.append({
                "role": "system",
                "content": f"Previous conversation summary: {self.conversation_summary}"
            })
        
        # Add context messages
        for message in context_messages:
            formatted_messages.append({
                "role": message.role,
                "content": message.content
            })
        
        logger.debug(f"Context window: {len(formatted_messages)} messages, ~{used_tokens} tokens")
        return formatted_messages
    
    def _manage_context_window(self) -> None:
        """Manage context window size by summarizing old messages if needed."""
        total_tokens = sum(msg.token_count for msg in self.messages)
        
        if total_tokens > self.max_tokens * 1.5:  # 50% buffer before summarizing
            self._summarize_old_messages()
    
    def _summarize_old_messages(self) -> None:
        """Summarize messages that don't fit in the context window."""
        if len(self.messages) < 5:  # Don't summarize very short conversations
            return
        
        # Keep the last 30% of messages, summarize the rest
        keep_count = max(2, int(len(self.messages) * 0.3))
        messages_to_summarize = self.messages[:-keep_count]
        
        if not messages_to_summarize:
            return
        
        # Extract key information from messages to be summarized
        summary_parts = []
        user_requests = []
        assistant_responses = []
        key_decisions = []
        
        for msg in messages_to_summarize:
            if msg.role == "user":
                user_requests.append(msg.content)
            elif msg.role == "assistant":
                assistant_responses.append(msg.content)
            
            # Extract decisions from metadata
            if msg.metadata and msg.metadata.get("type") == "decision":
                key_decisions.append(msg.metadata.get("decision", ""))
        
        # Build summary
        if user_requests:
            summary_parts.append(f"User requests: {'; '.join(user_requests[:3])}")
        if assistant_responses:
            summary_parts.append(f"Key responses: {'; '.join(assistant_responses[:2])}")
        if key_decisions:
            summary_parts.append(f"Decisions made: {'; '.join(key_decisions)}")
        
        if summary_parts:
            new_summary = " | ".join(summary_parts)
            
            # Combine with existing summary
            if self.conversation_summary:
                self.conversation_summary = f"{self.conversation_summary} | {new_summary}"
            else:
                self.conversation_summary = new_summary
            
            # Truncate summary if it gets too long
            if self.get_token_count(self.conversation_summary) > 200:
                # Keep only the most recent part
                summary_tokens = self.conversation_summary.split(" | ")
                self.conversation_summary = " | ".join(summary_tokens[-2:])
        
        # Remove summarized messages
        self.messages = self.messages[-keep_count:]
        
        logger.info(f"Summarized {len(messages_to_summarize)} messages, kept {len(self.messages)}")
    
    def extract_key_decisions(self) -> Dict[str, Any]:
        """Extract important parameters and decisions from the conversation."""
        decisions = {
            "agent_requirements": {},
            "user_preferences": {},
            "clarifications_provided": {},
            "rejected_options": [],
            "confirmed_features": []
        }
        
        for message in self.messages:
            if not message.metadata:
                continue
            
            metadata = message.metadata
            
            # Extract agent requirements
            if metadata.get("type") == "agent_requirement":
                req_type = metadata.get("requirement_type")
                req_value = metadata.get("value")
                if req_type and req_value:
                    decisions["agent_requirements"][req_type] = req_value
            
            # Extract user preferences
            elif metadata.get("type") == "user_preference":
                pref_type = metadata.get("preference_type")
                pref_value = metadata.get("value")
                if pref_type and pref_value:
                    decisions["user_preferences"][pref_type] = pref_value
            
            # Extract clarifications
            elif metadata.get("type") == "clarification":
                question = metadata.get("question")
                answer = metadata.get("answer")
                if question and answer:
                    decisions["clarifications_provided"][question] = answer
            
            # Extract confirmations and rejections
            elif metadata.get("type") == "confirmation":
                feature = metadata.get("feature")
                confirmed = metadata.get("confirmed", True)
                if feature:
                    if confirmed:
                        decisions["confirmed_features"].append(feature)
                    else:
                        decisions["rejected_options"].append(feature)
        
        # Update stored decisions
        self.key_decisions.update(decisions)
        return decisions
    
    def get_conversation_state(self) -> Dict[str, Any]:
        """Get the current state of the conversation for persistence."""
        return {
            "session_id": self.session_id,
            "messages": [asdict(msg) for msg in self.messages],
            "key_decisions": self.key_decisions,
            "conversation_summary": self.conversation_summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    def load_conversation_state(self, state: Dict[str, Any]) -> None:
        """Load conversation state from persistence."""
        try:
            self.session_id = state.get("session_id", self.session_id)
            self.key_decisions = state.get("key_decisions", {})
            self.conversation_summary = state.get("conversation_summary", "")
            
            # Load messages
            messages_data = state.get("messages", [])
            self.messages = []
            
            for msg_data in messages_data:
                message = Message(
                    role=msg_data["role"],
                    content=msg_data["content"],
                    timestamp=msg_data["timestamp"],
                    metadata=msg_data.get("metadata"),
                    priority=msg_data.get("priority", 1),
                    token_count=msg_data.get("token_count", 0)
                )
                # Recalculate token count if not stored
                if message.token_count == 0:
                    message.token_count = self.get_token_count(message.content)
                
                self.messages.append(message)
            
            logger.info(f"Loaded conversation state with {len(self.messages)} messages")
            
        except Exception as e:
            logger.error(f"Failed to load conversation state: {e}")
    
    def clear_context(self) -> None:
        """Clear the conversation context."""
        self.messages.clear()
        self.key_decisions.clear()
        self.conversation_summary = ""
        logger.info("Conversation context cleared")
    
    def get_recent_user_messages(self, count: int = 3) -> List[str]:
        """Get the most recent user messages."""
        user_messages = [msg.content for msg in self.messages if msg.role == "user"]
        return user_messages[-count:] if user_messages else []
    
    def has_clarification_context(self, topic: str) -> bool:
        """Check if we have clarification context for a specific topic."""
        for message in self.messages:
            if (message.metadata and 
                message.metadata.get("type") == "clarification" and
                topic.lower() in message.metadata.get("question", "").lower()):
                return True
        return False
    
    def get_context_for_intent_parsing(self) -> Dict[str, Any]:
        """Get relevant context for intent parsing."""
        return {
            "recent_messages": self.get_recent_user_messages(),
            "key_decisions": self.extract_key_decisions(),
            "conversation_summary": self.conversation_summary,
            "session_id": self.session_id
        }