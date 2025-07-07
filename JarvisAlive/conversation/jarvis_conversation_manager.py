"""Jarvis-specific conversation manager extending ConversationContextManager."""

import re
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from collections import defaultdict

from .context_manager import ConversationContextManager, Message

logger = logging.getLogger(__name__)


class JarvisConversationManager(ConversationContextManager):
    """
    Extends ConversationContextManager with business-focused capabilities.
    
    Maintains technical context while adding business intelligence layer
    for department coordination, KPI tracking, and executive insights.
    """
    
    def __init__(self, max_tokens: int = 4096, session_id: str = "default"):
        super().__init__(max_tokens, session_id)
        
        # Business-specific context
        self.current_business_goals = []
        self.active_departments = []
        self.key_metrics_history = []
        self.department_needs_history = []
        
        # Business intelligence patterns
        self._metric_patterns = {
            'revenue': r'(?:revenue|sales|income|earnings)(?:\s+of)?\s*[\$€£]?([\d,]+\.?\d*)\s*(?:million|m|thousand|k|billion|b)?',
            'leads': r'(?:leads?|prospects?|contacts?)(?:\s+of)?\s*(\d+)',
            'conversion': r'(?:conversion|close|win)\s*rate\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*%?',
            'customers': r'(?:customers?|clients?|users?)(?:\s+of)?\s*(\d+)',
            'growth': r'(?:growth|increase|rise)(?:\s+of)?\s*(\d+(?:\.\d+)?)\s*%?',
            'pipeline': r'(?:pipeline|deals?)(?:\s+value)?\s*[\$€£]?([\d,]+\.?\d*)\s*(?:million|m|thousand|k|billion|b)?',
            'meetings': r'(?:meetings?|appointments?|calls?)(?:\s+scheduled)?\s*(\d+)',
            'emails': r'(?:emails?|messages?)(?:\s+sent)?\s*(\d+)',
            'response_rate': r'(?:response|reply)\s*rate\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*%?',
            'roi': r'(?:roi|return)\s*(?:on investment)?\s*(?:of)?\s*(\d+(?:\.\d+)?)\s*%?'
        }
        
        # Department keywords for need identification
        self._department_keywords = {
            'sales': ['sales', 'revenue', 'leads', 'prospects', 'pipeline', 'deals', 'conversion', 'crm'],
            'marketing': ['marketing', 'campaigns', 'brand', 'content', 'social media', 'ads', 'seo', 'website'],
            'customer_service': ['support', 'customer service', 'help desk', 'tickets', 'satisfaction', 'retention'],
            'hr': ['hr', 'human resources', 'recruitment', 'hiring', 'employees', 'onboarding', 'payroll'],
            'finance': ['finance', 'accounting', 'budget', 'expenses', 'invoices', 'cash flow', 'financial'],
            'operations': ['operations', 'logistics', 'supply chain', 'inventory', 'production', 'quality'],
            'it': ['it', 'technology', 'software', 'infrastructure', 'security', 'data', 'systems'],
            'legal': ['legal', 'compliance', 'contracts', 'regulatory', 'intellectual property', 'risk']
        }
        
        logger.info(f"JarvisConversationManager initialized for session: {session_id}")
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict] = None, priority: int = 1) -> None:
        """Override add_message to extract business data."""
        # Call parent method first
        super().add_message(role, content, metadata, priority)
        
        # Extract business intelligence from message
        metrics = self.extract_business_metrics(content)
        if metrics:
            self.key_metrics_history.extend(metrics)
            logger.debug(f"Extracted {len(metrics)} business metrics from message")
        
        # Identify department needs
        department_needs = self.identify_department_needs(content)
        if department_needs:
            self.department_needs_history.extend([{
                'departments': department_needs,
                'context': content[:200],  # First 200 chars for context
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'role': role
            }])
            logger.debug(f"Identified needs for departments: {department_needs}")
        
        # Track business goals from user messages
        if role == "user" and self._contains_business_goal(content):
            goal = self._extract_business_goal(content)
            if goal and goal not in self.current_business_goals:
                self.current_business_goals.append(goal)
                logger.debug(f"Added business goal: {goal}")
    
    def extract_business_metrics(self, message: str) -> List[Dict]:
        """Extract business metrics and KPIs from message text."""
        metrics = []
        message_lower = message.lower()
        
        for metric_type, pattern in self._metric_patterns.items():
            matches = re.finditer(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                try:
                    value = match.group(1).replace(',', '')
                    
                    # Parse numeric value
                    if '.' in value:
                        numeric_value = float(value)
                    else:
                        numeric_value = int(value)
                    
                    # Handle scale indicators (k, m, b)
                    full_match = match.group(0).lower()
                    if 'billion' in full_match or ' b' in full_match:
                        numeric_value *= 1_000_000_000
                    elif 'million' in full_match or ' m' in full_match:
                        numeric_value *= 1_000_000
                    elif 'thousand' in full_match or ' k' in full_match:
                        numeric_value *= 1_000
                    
                    metric = {
                        'type': metric_type,
                        'value': numeric_value,
                        'raw_text': match.group(0),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        'context': message[:100]  # First 100 chars for context
                    }
                    
                    metrics.append(metric)
                    
                except (ValueError, IndexError) as e:
                    logger.warning(f"Failed to parse metric value: {e}")
                    continue
        
        return metrics
    
    def identify_department_needs(self, message: str) -> List[str]:
        """Identify which departments should be activated based on message content."""
        needed_departments = []
        message_lower = message.lower()
        
        # Score departments based on keyword matches
        department_scores = defaultdict(int)
        
        for dept, keywords in self._department_keywords.items():
            for keyword in keywords:
                if keyword in message_lower:
                    # Weight longer keywords higher
                    weight = len(keyword.split())
                    department_scores[dept] += weight
        
        # Also check for explicit department activation requests
        activation_patterns = [
            r'activate\s+(\w+)\s+department',
            r'start\s+(\w+)\s+team',
            r'need\s+(\w+)\s+help',
            r'(\w+)\s+department\s+should',
            r'get\s+(\w+)\s+involved'
        ]
        
        for pattern in activation_patterns:
            matches = re.finditer(pattern, message_lower, re.IGNORECASE)
            for match in matches:
                dept_name = match.group(1)
                if dept_name in self._department_keywords:
                    department_scores[dept_name] += 5  # High weight for explicit requests
        
        # Return departments with score > 0, sorted by score
        for dept, score in sorted(department_scores.items(), key=lambda x: x[1], reverse=True):
            if score > 0:
                needed_departments.append(dept)
        
        return needed_departments
    
    def generate_executive_summary(self) -> str:
        """Generate a business-level executive summary of the conversation."""
        if not self.messages:
            return "No conversation data available for executive summary."
        
        # Analyze conversation for business context
        business_context = self._analyze_business_context()
        
        summary_parts = []
        
        # Business objectives
        if self.current_business_goals:
            summary_parts.append(f"**Business Objectives:** {', '.join(self.current_business_goals[:3])}")
        
        # Key metrics
        if self.key_metrics_history:
            latest_metrics = self._get_latest_metrics()
            if latest_metrics:
                metrics_str = ', '.join([f"{m['type']}: {m['value']}" for m in latest_metrics[:4]])
                summary_parts.append(f"**Key Metrics:** {metrics_str}")
        
        # Department recommendations
        if self.department_needs_history:
            recent_needs = self._get_recent_department_needs()
            if recent_needs:
                summary_parts.append(f"**Recommended Departments:** {', '.join(recent_needs)}")
        
        # Conversation insights
        insights = self._generate_conversation_insights()
        if insights:
            summary_parts.append(f"**Strategic Insights:** {insights}")
        
        # Business context from messages
        if business_context:
            summary_parts.append(f"**Business Context:** {business_context}")
        
        # Fallback to technical summary if no business context
        if not summary_parts:
            summary_parts.append("**Technical Summary:** " + (self.conversation_summary or "Technical discussion in progress"))
        
        return '\n\n'.join(summary_parts)
    
    def get_business_context_for_ai(self) -> Dict[str, Any]:
        """Get business context formatted for AI decision making."""
        return {
            'business_goals': self.current_business_goals,
            'active_departments': self.active_departments,
            'key_metrics': self._get_latest_metrics(),
            'department_needs': self._get_recent_department_needs(),
            'conversation_summary': self.generate_executive_summary(),
            'business_intelligence': {
                'total_metrics_tracked': len(self.key_metrics_history),
                'departments_identified': len(set(
                    dept for needs in self.department_needs_history 
                    for dept in needs.get('departments', [])
                )),
                'business_goals_count': len(self.current_business_goals)
            }
        }
    
    def add_department_activation(self, department: str, agents: List[str], goals: List[str] = None) -> None:
        """Track department activation for business context."""
        if department not in self.active_departments:
            self.active_departments.append(department)
        
        # Add as a business message
        activation_msg = f"Activated {department} department with {len(agents)} agents: {', '.join(agents)}"
        if goals:
            activation_msg += f". Goals: {', '.join(goals)}"
        
        self.add_message("system", activation_msg, {
            "type": "department_activation",
            "department": department,
            "agents": agents,
            "goals": goals or []
        }, priority=2)
    
    def track_business_outcome(self, outcome_type: str, details: Dict[str, Any]) -> None:
        """Track business outcomes and results."""
        outcome_msg = f"Business outcome: {outcome_type}"
        if details:
            outcome_msg += f" - {json.dumps(details, indent=2)}"
        
        self.add_message("system", outcome_msg, {
            "type": "business_outcome",
            "outcome_type": outcome_type,
            "details": details
        }, priority=2)
    
    def _contains_business_goal(self, content: str) -> bool:
        """Check if content contains a business goal."""
        goal_indicators = [
            'goal', 'objective', 'target', 'aim', 'increase', 'improve', 'grow',
            'achieve', 'want to', 'need to', 'looking to', 'trying to'
        ]
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in goal_indicators)
    
    def _extract_business_goal(self, content: str) -> Optional[str]:
        """Extract business goal from content."""
        # Look for goal patterns
        goal_patterns = [
            r'(?:goal|objective|target|aim)(?:\s+is)?\s+to\s+([^.!?]+)',
            r'(?:want|need|looking|trying)\s+to\s+([^.!?]+)',
            r'(?:increase|improve|grow|achieve)\s+([^.!?]+)'
        ]
        
        for pattern in goal_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                goal = match.group(1).strip()
                if len(goal) > 10 and len(goal) < 200:  # Reasonable goal length
                    return goal
        
        return None
    
    def _analyze_business_context(self) -> str:
        """Analyze conversation for business context."""
        business_keywords = [
            'business', 'company', 'revenue', 'sales', 'customers', 'growth',
            'market', 'strategy', 'profit', 'roi', 'kpi', 'metrics'
        ]
        
        business_messages = []
        for msg in self.messages[-10:]:  # Last 10 messages
            if msg.role == "user":
                msg_lower = msg.content.lower()
                if any(keyword in msg_lower for keyword in business_keywords):
                    business_messages.append(msg.content[:100])
        
        if business_messages:
            return "Focus on " + "; ".join(business_messages[:2])
        
        return ""
    
    def _get_latest_metrics(self) -> List[Dict]:
        """Get the most recent metrics by type."""
        latest_metrics = {}
        
        # Get the most recent metric of each type
        for metric in reversed(self.key_metrics_history):
            metric_type = metric['type']
            if metric_type not in latest_metrics:
                latest_metrics[metric_type] = metric
        
        return list(latest_metrics.values())
    
    def _get_recent_department_needs(self) -> List[str]:
        """Get recently identified department needs."""
        if not self.department_needs_history:
            return []
        
        # Get unique departments from recent needs
        recent_departments = set()
        for need in self.department_needs_history[-5:]:  # Last 5 identifications
            recent_departments.update(need['departments'])
        
        return sorted(list(recent_departments))
    
    def _generate_conversation_insights(self) -> str:
        """Generate business insights from conversation patterns."""
        insights = []
        
        # Metric trend analysis
        if len(self.key_metrics_history) >= 2:
            insights.append("Multiple KPIs being tracked and optimized")
        
        # Department coordination analysis
        if len(self.active_departments) > 1:
            insights.append(f"Cross-department coordination across {len(self.active_departments)} teams")
        
        # Business goal alignment
        if self.current_business_goals:
            insights.append(f"Clear business objectives defined ({len(self.current_business_goals)} goals)")
        
        return "; ".join(insights) if insights else ""
    
    def get_conversation_state(self) -> Dict[str, Any]:
        """Extend parent method to include business context."""
        state = super().get_conversation_state()
        
        # Add business-specific state
        state.update({
            'business_goals': self.current_business_goals,
            'active_departments': self.active_departments,
            'key_metrics_history': self.key_metrics_history,
            'department_needs_history': self.department_needs_history
        })
        
        return state
    
    def load_conversation_state(self, state: Dict[str, Any]) -> None:
        """Extend parent method to load business context."""
        super().load_conversation_state(state)
        
        # Load business-specific state
        self.current_business_goals = state.get('business_goals', [])
        self.active_departments = state.get('active_departments', [])
        self.key_metrics_history = state.get('key_metrics_history', [])
        self.department_needs_history = state.get('department_needs_history', [])
        
        logger.info(f"Loaded business context: {len(self.current_business_goals)} goals, "
                   f"{len(self.active_departments)} departments, "
                   f"{len(self.key_metrics_history)} metrics")