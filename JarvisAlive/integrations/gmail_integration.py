#!/usr/bin/env python3
"""
Gmail Integration for HeyJarvis
Real-time email sending with tracking, queue management, and safety features
"""

import os
import json
import asyncio
import logging
import base64
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formataddr, formatdate
import re

# Gmail API imports
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
import google.auth.exceptions

import redis.asyncio as redis
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EmailRecipient:
    """Email recipient information"""
    email: str
    name: Optional[str] = None
    lead_id: Optional[str] = None
    tracking_id: Optional[str] = None


@dataclass
class EmailMessage:
    """Email message data structure"""
    id: str
    to: List[EmailRecipient]
    subject: str
    text_body: str
    cc: Optional[List[EmailRecipient]] = None
    bcc: Optional[List[EmailRecipient]] = None
    html_body: Optional[str] = None
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
    tracking_enabled: bool = True
    unsubscribe_url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class EmailTrackingEvent:
    """Email tracking event"""
    tracking_id: str
    event_type: str  # 'sent', 'delivered', 'opened', 'clicked', 'replied', 'bounced', 'unsubscribed'
    timestamp: datetime
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class SendingQuota:
    """Daily sending quota tracking"""
    user_id: str
    date: str
    emails_sent: int
    limit: int
    last_reset: datetime


class GmailIntegration:
    """
    Gmail API integration with tracking, queue management, and safety features
    
    Features:
    - Real-time email sending via Gmail API
    - HTML email formatting with tracking pixels
    - Thread management for follow-ups
    - Daily sending limits and safety checks
    - Redis-based queue management
    - Tracking pixel endpoint integration
    - SPF/DKIM compliance headers
    - Test mode for draft creation
    """
    
    def __init__(
        self,
        credentials: Optional[Credentials] = None,
        redis_client: Optional[redis.Redis] = None,
        test_mode: bool = False,
        daily_limit: int = 50,
        tracking_domain: str = "localhost:8000"
    ):
        """
        Initialize Gmail integration
        
        Args:
            credentials: Google OAuth credentials
            redis_client: Redis client for queue management
            test_mode: If True, creates drafts instead of sending
            daily_limit: Maximum emails per day per user
            tracking_domain: Domain for tracking pixel URLs
        """
        self.credentials = credentials
        self.redis_client = redis_client
        self.test_mode = test_mode
        self.daily_limit = daily_limit
        self.tracking_domain = tracking_domain
        
        # Gmail service
        self.service = None
        self.user_email = None
        
        # Queue settings
        self.queue_name = "gmail_outbound_queue"
        self.retry_queue_name = "gmail_retry_queue"
        self.dead_letter_queue = "gmail_dead_letter_queue"
        
        # Rate limiting (Gmail allows 250 quota units/user/second, 1 billion/day)
        self.rate_limiter = asyncio.Semaphore(10)  # Conservative rate limit
        self.last_request_time = datetime.utcnow()
        
        if self.credentials:
            self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Gmail API service"""
        try:
            if not self.credentials.valid:
                if self.credentials.expired and self.credentials.refresh_token:
                    self.credentials.refresh(Request())
                else:
                    raise Exception("Invalid credentials - reauthorization required")
            
            self.service = build('gmail', 'v1', credentials=self.credentials)
            
            # Get user's email address
            profile = self.service.users().getProfile(userId='me').execute()
            self.user_email = profile.get('emailAddress')
            
            logger.info(f"Gmail service initialized for {self.user_email}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {e}")
            raise
    
    async def _rate_limit(self):
        """Enforce rate limiting"""
        async with self.rate_limiter:
            # Ensure minimum 100ms between requests
            elapsed = (datetime.utcnow() - self.last_request_time).total_seconds()
            if elapsed < 0.1:
                await asyncio.sleep(0.1 - elapsed)
            self.last_request_time = datetime.utcnow()
    
    async def send_email(
        self,
        message: EmailMessage,
        user_id: str,
        bypass_limits: bool = False
    ) -> Dict[str, Any]:
        """
        Send email with safety checks and tracking
        
        Args:
            message: Email message to send
            user_id: User ID for quota tracking
            bypass_limits: Skip safety checks (admin only)
            
        Returns:
            Dictionary with send status and message details
        """
        try:
            # Safety checks
            if not bypass_limits:
                safety_check = await self._safety_checks(message, user_id)
                if not safety_check["allowed"]:
                    return {
                        "success": False,
                        "error": safety_check["reason"],
                        "message_id": message.id
                    }
            
            # Generate tracking IDs
            await self._generate_tracking_ids(message)
            
            # Create MIME message
            mime_message = await self._create_mime_message(message)
            
            await self._rate_limit()
            
            if self.test_mode:
                # Create draft instead of sending
                result = await self._create_draft(mime_message)
                result["test_mode"] = True
            else:
                # Send email
                result = await self._send_message(mime_message)
                
                # Update quota
                await self._update_sending_quota(user_id)
                
                # Store tracking data
                await self._store_tracking_data(message, result.get("id"))
            
            logger.info(f"Email {'drafted' if self.test_mode else 'sent'}: {message.id}")
            
            return {
                "success": True,
                "message_id": message.id,
                "gmail_id": result.get("id"),
                "thread_id": result.get("threadId"),
                "test_mode": self.test_mode
            }
            
        except Exception as e:
            logger.error(f"Failed to send email {message.id}: {e}")
            
            # Add to retry queue
            await self._add_to_retry_queue(message, user_id, str(e))
            
            return {
                "success": False,
                "error": str(e),
                "message_id": message.id,
                "queued_for_retry": True
            }
    
    async def create_draft(self, message: EmailMessage) -> Dict[str, Any]:
        """Create email draft"""
        try:
            await self._generate_tracking_ids(message)
            mime_message = await self._create_mime_message(message)
            
            await self._rate_limit()
            result = await self._create_draft(mime_message)
            
            return {
                "success": True,
                "draft_id": result.get("id"),
                "message_id": message.id
            }
            
        except Exception as e:
            logger.error(f"Failed to create draft: {e}")
            return {
                "success": False,
                "error": str(e),
                "message_id": message.id
            }
    
    async def add_to_queue(
        self,
        message: EmailMessage,
        user_id: str,
        priority: int = 5,
        delay_minutes: int = 0
    ) -> bool:
        """
        Add email to sending queue
        
        Args:
            message: Email message
            user_id: User ID
            priority: Queue priority (1-10, lower = higher priority)
            delay_minutes: Delay before sending
            
        Returns:
            True if successfully queued
        """
        if not self.redis_client:
            logger.warning("No Redis client - cannot queue message")
            return False
        
        try:
            queue_item = {
                "message": asdict(message),
                "user_id": user_id,
                "priority": priority,
                "queued_at": datetime.utcnow().isoformat(),
                "send_after": (datetime.utcnow() + timedelta(minutes=delay_minutes)).isoformat(),
                "retry_count": 0
            }
            
            # Add to Redis queue with priority
            score = priority + (datetime.utcnow().timestamp() / 1000000)  # Priority + timestamp for ordering
            
            await self.redis_client.zadd(
                self.queue_name,
                {json.dumps(queue_item): score}
            )
            
            logger.info(f"Queued email {message.id} for user {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue email: {e}")
            return False
    
    async def process_queue(self, batch_size: int = 10) -> Dict[str, Any]:
        """
        Process emails from queue
        
        Args:
            batch_size: Number of emails to process in batch
            
        Returns:
            Processing results
        """
        if not self.redis_client:
            return {"processed": 0, "errors": 0}
        
        processed = 0
        errors = 0
        
        try:
            # Get items from queue (lowest score first)
            items = await self.redis_client.zrange(
                self.queue_name, 0, batch_size - 1, withscores=True
            )
            
            for item_data, score in items:
                try:
                    queue_item = json.loads(item_data)
                    
                    # Check if it's time to send
                    send_after = datetime.fromisoformat(queue_item["send_after"])
                    if datetime.utcnow() < send_after:
                        continue
                    
                    # Reconstruct message
                    message_data = queue_item["message"]
                    message = EmailMessage(**message_data)
                    
                    # Send email
                    result = await self.send_email(
                        message, 
                        queue_item["user_id"], 
                        bypass_limits=False
                    )
                    
                    if result["success"]:
                        # Remove from queue
                        await self.redis_client.zrem(self.queue_name, item_data)
                        processed += 1
                    else:
                        # Move to retry queue or dead letter queue
                        retry_count = queue_item.get("retry_count", 0) + 1
                        if retry_count <= 3:
                            queue_item["retry_count"] = retry_count
                            queue_item["last_error"] = result.get("error")
                            queue_item["next_retry"] = (
                                datetime.utcnow() + timedelta(minutes=2 ** retry_count)
                            ).isoformat()
                            
                            await self.redis_client.zadd(
                                self.retry_queue_name,
                                {json.dumps(queue_item): datetime.utcnow().timestamp()}
                            )
                        else:
                            # Move to dead letter queue
                            await self.redis_client.zadd(
                                self.dead_letter_queue,
                                {json.dumps(queue_item): datetime.utcnow().timestamp()}
                            )
                        
                        await self.redis_client.zrem(self.queue_name, item_data)
                        errors += 1
                
                except Exception as e:
                    logger.error(f"Error processing queue item: {e}")
                    errors += 1
            
        except Exception as e:
            logger.error(f"Error processing queue: {e}")
            
        return {"processed": processed, "errors": errors}
    
    async def _safety_checks(self, message: EmailMessage, user_id: str) -> Dict[str, Any]:
        """Perform safety checks before sending"""
        
        # Check daily sending limit
        quota = await self._get_sending_quota(user_id)
        if quota.emails_sent >= quota.limit:
            return {
                "allowed": False,
                "reason": f"Daily sending limit reached ({quota.limit})"
            }
        
        # Check for duplicate emails (same recipient in last 24 hours)
        if await self._is_duplicate_email(message, user_id):
            return {
                "allowed": False,
                "reason": "Duplicate email detected (same recipient within 24 hours)"
            }
        
        # Validate email addresses
        for recipient in message.to:
            if not self._is_valid_email(recipient.email):
                return {
                    "allowed": False,
                    "reason": f"Invalid email address: {recipient.email}"
                }
        
        # Check for spam content
        spam_score = self._calculate_spam_score(message)
        if spam_score > 5.0:
            return {
                "allowed": False,
                "reason": f"Content appears spammy (score: {spam_score})"
            }
        
        # Check unsubscribe compliance
        if not self._has_unsubscribe_link(message):
            return {
                "allowed": False,
                "reason": "Missing unsubscribe link"
            }
        
        return {"allowed": True}
    
    async def _generate_tracking_ids(self, message: EmailMessage):
        """Generate unique tracking IDs for recipients"""
        for recipient in message.to:
            if not recipient.tracking_id:
                recipient.tracking_id = str(uuid.uuid4())
    
    async def _create_mime_message(self, message: EmailMessage) -> str:
        """Create MIME email message with tracking"""
        
        # Create multipart message
        mime_msg = MIMEMultipart('alternative')
        
        # Headers
        mime_msg['From'] = formataddr((self.user_email.split('@')[0], self.user_email))
        mime_msg['To'] = ', '.join([
            formataddr((r.name or r.email.split('@')[0], r.email)) 
            for r in message.to
        ])
        mime_msg['Subject'] = message.subject
        mime_msg['Date'] = formatdate(localtime=True)
        mime_msg['Message-ID'] = f"<{message.id}@{self.tracking_domain}>"
        
        if message.reply_to:
            mime_msg['Reply-To'] = message.reply_to
        
        if message.cc:
            mime_msg['Cc'] = ', '.join([r.email for r in message.cc])
        
        # List-Unsubscribe header for compliance
        if message.unsubscribe_url:
            mime_msg['List-Unsubscribe'] = f'<{message.unsubscribe_url}>'
            mime_msg['List-Unsubscribe-Post'] = 'List-Unsubscribe=One-Click'
        
        # Text version
        text_body = message.text_body
        if message.unsubscribe_url and message.unsubscribe_url not in text_body:
            text_body += f"\n\nTo unsubscribe: {message.unsubscribe_url}"
        
        text_part = MIMEText(text_body, 'plain', 'utf-8')
        mime_msg.attach(text_part)
        
        # HTML version with tracking
        if message.html_body:
            html_body = message.html_body
        else:
            # Convert text to HTML
            html_body = message.text_body.replace('\n', '<br>\n')
            html_body = f"""
            <html>
            <body>
            <div style="font-family: Arial, sans-serif; max-width: 600px;">
            {html_body}
            </div>
            </body>
            </html>
            """
        
        # Add tracking pixel and unsubscribe link
        html_body = await self._add_tracking_elements(html_body, message)
        
        html_part = MIMEText(html_body, 'html', 'utf-8')
        mime_msg.attach(html_part)
        
        return mime_msg.as_string()
    
    async def _add_tracking_elements(self, html_body: str, message: EmailMessage) -> str:
        """Add tracking pixel and unsubscribe link to HTML"""
        
        # Add tracking pixel for each recipient
        tracking_pixels = []
        for recipient in message.to:
            if recipient.tracking_id and message.tracking_enabled:
                pixel_url = f"https://{self.tracking_domain}/api/track/pixel/{recipient.tracking_id}.gif"
                tracking_pixels.append(
                    f'<img src="{pixel_url}" width="1" height="1" style="display:none;" alt="">'
                )
        
        # Add unsubscribe link
        unsubscribe_html = ""
        if message.unsubscribe_url:
            unsubscribe_html = f"""
            <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; 
                        text-align: center; font-size: 12px; color: #666;">
                <a href="{message.unsubscribe_url}" style="color: #666; text-decoration: underline;">
                    Unsubscribe from these emails
                </a>
            </div>
            """
        
        # Insert tracking elements before closing body tag
        if '</body>' in html_body:
            html_body = html_body.replace(
                '</body>',
                f"{''.join(tracking_pixels)}{unsubscribe_html}</body>"
            )
        else:
            html_body += f"{''.join(tracking_pixels)}{unsubscribe_html}"
        
        return html_body
    
    async def _send_message(self, mime_message: str) -> Dict[str, Any]:
        """Send email via Gmail API"""
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(mime_message.encode()).decode()
        
        # Send via Gmail API
        message = {
            'raw': raw_message
        }
        
        result = self.service.users().messages().send(
            userId='me',
            body=message
        ).execute()
        
        return result
    
    async def _create_draft(self, mime_message: str) -> Dict[str, Any]:
        """Create draft via Gmail API"""
        
        # Encode message
        raw_message = base64.urlsafe_b64encode(mime_message.encode()).decode()
        
        # Create draft
        draft = {
            'message': {
                'raw': raw_message
            }
        }
        
        result = self.service.users().drafts().create(
            userId='me',
            body=draft
        ).execute()
        
        return result
    
    async def _get_sending_quota(self, user_id: str) -> SendingQuota:
        """Get current sending quota for user"""
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        if self.redis_client:
            quota_key = f"gmail_quota:{user_id}:{today}"
            quota_data = await self.redis_client.get(quota_key)
            
            if quota_data:
                data = json.loads(quota_data)
                return SendingQuota(**data)
        
        # Return new quota
        return SendingQuota(
            user_id=user_id,
            date=today,
            emails_sent=0,
            limit=self.daily_limit,
            last_reset=datetime.utcnow()
        )
    
    async def _update_sending_quota(self, user_id: str):
        """Update sending quota after successful send"""
        if not self.redis_client:
            return
        
        quota = await self._get_sending_quota(user_id)
        quota.emails_sent += 1
        
        today = datetime.utcnow().strftime('%Y-%m-%d')
        quota_key = f"gmail_quota:{user_id}:{today}"
        
        await self.redis_client.setex(
            quota_key,
            timedelta(days=1),
            json.dumps(asdict(quota))
        )
    
    async def _is_duplicate_email(self, message: EmailMessage, user_id: str) -> bool:
        """Check if this is a duplicate email"""
        if not self.redis_client:
            return False
        
        for recipient in message.to:
            # Create hash of user + recipient + subject
            content_hash = hashlib.md5(
                f"{user_id}:{recipient.email}:{message.subject}".encode()
            ).hexdigest()
            
            duplicate_key = f"gmail_sent:{content_hash}"
            
            if await self.redis_client.exists(duplicate_key):
                return True
            
            # Store this email hash for 24 hours
            await self.redis_client.setex(
                duplicate_key,
                timedelta(hours=24),
                "1"
            )
        
        return False
    
    def _is_valid_email(self, email: str) -> bool:
        """Validate email address format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def _calculate_spam_score(self, message: EmailMessage) -> float:
        """Calculate spam score for message content"""
        score = 0.0
        
        # Check subject line
        subject_lower = message.subject.lower()
        spam_words = [
            'free', 'guarantee', 'urgent', 'act now', 'limited time',
            'click here', 'buy now', '!!!', 'winner', 'congratulations'
        ]
        
        for word in spam_words:
            if word in subject_lower:
                score += 0.5
        
        # Check body content
        body_lower = message.text_body.lower()
        
        # Excessive punctuation
        exclamation_count = body_lower.count('!')
        if exclamation_count > 3:
            score += exclamation_count * 0.2
        
        # ALL CAPS
        caps_ratio = sum(1 for c in message.text_body if c.isupper()) / max(1, len(message.text_body))
        if caps_ratio > 0.3:
            score += 2.0
        
        # Spam phrases
        for word in spam_words:
            if word in body_lower:
                score += 0.3
        
        return score
    
    def _has_unsubscribe_link(self, message: EmailMessage) -> bool:
        """Check if message has unsubscribe functionality"""
        return (
            message.unsubscribe_url is not None or
            'unsubscribe' in message.text_body.lower() or
            (message.html_body and 'unsubscribe' in message.html_body.lower())
        )
    
    async def _store_tracking_data(self, message: EmailMessage, gmail_id: str):
        """Store tracking data for sent message"""
        if not self.redis_client:
            return
        
        for recipient in message.to:
            if recipient.tracking_id:
                tracking_data = {
                    "tracking_id": recipient.tracking_id,
                    "message_id": message.id,
                    "gmail_id": gmail_id,
                    "recipient": recipient.email,
                    "lead_id": recipient.lead_id,
                    "sent_at": datetime.utcnow().isoformat(),
                    "subject": message.subject
                }
                
                tracking_key = f"gmail_tracking:{recipient.tracking_id}"
                await self.redis_client.setex(
                    tracking_key,
                    timedelta(days=30),  # Keep tracking data for 30 days
                    json.dumps(tracking_data)
                )
    
    async def _add_to_retry_queue(self, message: EmailMessage, user_id: str, error: str):
        """Add failed message to retry queue"""
        if not self.redis_client:
            return
        
        retry_item = {
            "message": asdict(message),
            "user_id": user_id,
            "error": error,
            "retry_count": 1,
            "first_attempt": datetime.utcnow().isoformat(),
            "next_retry": (datetime.utcnow() + timedelta(minutes=2)).isoformat()
        }
        
        await self.redis_client.zadd(
            self.retry_queue_name,
            {json.dumps(retry_item): datetime.utcnow().timestamp()}
        )
    
    async def track_event(
        self,
        tracking_id: str,
        event_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Track email event (open, click, etc.)
        
        Args:
            tracking_id: Unique tracking ID
            event_type: Type of event ('opened', 'clicked', 'replied', etc.)
            metadata: Additional event data
            
        Returns:
            True if event was tracked successfully
        """
        if not self.redis_client:
            return False
        
        try:
            # Get tracking data
            tracking_key = f"gmail_tracking:{tracking_id}"
            tracking_data = await self.redis_client.get(tracking_key)
            
            if not tracking_data:
                logger.warning(f"No tracking data found for ID: {tracking_id}")
                return False
            
            tracking_info = json.loads(tracking_data)
            
            # Create tracking event
            event = EmailTrackingEvent(
                tracking_id=tracking_id,
                event_type=event_type,
                timestamp=datetime.utcnow(),
                metadata=metadata or {}
            )
            
            # Store event
            event_key = f"gmail_events:{tracking_id}:{event_type}:{datetime.utcnow().timestamp()}"
            await self.redis_client.setex(
                event_key,
                timedelta(days=30),
                json.dumps(asdict(event))
            )
            
            # Update tracking summary
            summary_key = f"gmail_summary:{tracking_id}"
            summary = await self.redis_client.get(summary_key)
            
            if summary:
                summary_data = json.loads(summary)
            else:
                summary_data = {
                    "tracking_id": tracking_id,
                    "message_id": tracking_info.get("message_id"),
                    "recipient": tracking_info.get("recipient"),
                    "lead_id": tracking_info.get("lead_id"),
                    "events": {}
                }
            
            # Update event count
            if event_type not in summary_data["events"]:
                summary_data["events"][event_type] = 0
            summary_data["events"][event_type] += 1
            summary_data[f"last_{event_type}"] = datetime.utcnow().isoformat()
            
            await self.redis_client.setex(
                summary_key,
                timedelta(days=30),
                json.dumps(summary_data)
            )
            
            logger.info(f"Tracked {event_type} event for {tracking_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to track event: {e}")
            return False
    
    async def get_tracking_summary(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        """Get tracking summary for a specific email"""
        if not self.redis_client:
            return None
        
        try:
            summary_key = f"gmail_summary:{tracking_id}"
            summary = await self.redis_client.get(summary_key)
            
            if summary:
                return json.loads(summary)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get tracking summary: {e}")
            return None
    
    async def get_user_stats(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get email sending statistics for a user"""
        if not self.redis_client:
            return {}
        
        try:
            stats = {
                "total_sent": 0,
                "total_opened": 0,
                "total_clicked": 0,
                "total_replied": 0,
                "daily_breakdown": {},
                "open_rate": 0.0,
                "click_rate": 0.0,
                "reply_rate": 0.0
            }
            
            # Get daily quotas for the period
            for i in range(days):
                date = (datetime.utcnow() - timedelta(days=i)).strftime('%Y-%m-%d')
                quota_key = f"gmail_quota:{user_id}:{date}"
                quota_data = await self.redis_client.get(quota_key)
                
                if quota_data:
                    quota = json.loads(quota_data)
                    sent = quota.get("emails_sent", 0)
                    stats["total_sent"] += sent
                    stats["daily_breakdown"][date] = {"sent": sent}
            
            # Calculate rates (would need to scan tracking events for accurate numbers)
            # This is a simplified version
            if stats["total_sent"] > 0:
                stats["open_rate"] = stats["total_opened"] / stats["total_sent"]
                stats["click_rate"] = stats["total_clicked"] / stats["total_sent"]
                stats["reply_rate"] = stats["total_replied"] / stats["total_sent"]
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get user stats: {e}")
            return {}


# Example OAuth setup function
def create_oauth_flow(client_config: Dict[str, Any], redirect_uri: str) -> Flow:
    """Create OAuth flow for Gmail authentication"""
    
    scopes = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.compose',
        'https://www.googleapis.com/auth/gmail.modify'
    ]
    
    flow = Flow.from_client_config(
        client_config,
        scopes=scopes,
        redirect_uri=redirect_uri
    )
    
    return flow


# Example usage
async def main():
    """Example usage of Gmail integration"""
    
    # Initialize Redis
    redis_client = await redis.from_url("redis://localhost:6379")
    
    # Initialize Gmail integration (test mode)
    gmail = GmailIntegration(
        redis_client=redis_client,
        test_mode=True,  # Creates drafts instead of sending
        daily_limit=50,
        tracking_domain="localhost:8000"
    )
    
    try:
        # Create test email
        message = EmailMessage(
            id=str(uuid.uuid4()),
            to=[EmailRecipient(
                email="test@example.com",
                name="John Doe",
                lead_id="lead_123"
            )],
            subject="Test Email from HeyJarvis",
            text_body="Hello! This is a test email from HeyJarvis.",
            html_body="<h1>Hello!</h1><p>This is a test email from HeyJarvis.</p>",
            unsubscribe_url="https://localhost:8000/unsubscribe/test123"
        )
        
        # Add to queue
        queued = await gmail.add_to_queue(message, "user_123", priority=1)
        print(f"Queued: {queued}")
        
        # Process queue
        results = await gmail.process_queue()
        print(f"Processed: {results}")
        
        # Track events (simulated)
        if message.to[0].tracking_id:
            await gmail.track_event(message.to[0].tracking_id, "opened")
            await gmail.track_event(message.to[0].tracking_id, "clicked")
            
            # Get tracking summary
            summary = await gmail.get_tracking_summary(message.to[0].tracking_id)
            print(f"Tracking summary: {summary}")
        
    finally:
        await redis_client.close()


if __name__ == "__main__":
    asyncio.run(main())