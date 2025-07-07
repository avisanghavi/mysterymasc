import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from base_agent import SandboxAgent
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class DxFactorEmailMonitorAgent(SandboxAgent):
    def __init__(self) -> None:
        super().__init__()
        self.name = "DX Factor Email Monitor"
        self.version = "1.0.0"
        self.capabilities = ["alert_sending", "email_monitoring"]
        self.gmail_service: Optional[object] = None
        self.last_check_time: Optional[datetime] = None
        self.running: bool = True

    async def initialize(self) -> None:
        try:
            credentials = Credentials.from_authorized_user_info(
                self.config.get("gmail_credentials", {}),
                scopes=["https://www.googleapis.com/auth/gmail.readonly"]
            )
            self.gmail_service = build("gmail", "v1", credentials=credentials)
            self.last_check_time = datetime.utcnow() - timedelta(minutes=5)
            logger.info("Gmail service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gmail service: {str(e)}")
            raise

    @retry(
        wait=wait_exponential(multiplier=1, min=4, max=10),
        stop=stop_after_attempt(3)
    )
    async def check_emails(self) -> List[Dict]:
        try:
            query = f"after:{int(self.last_check_time.timestamp())}"
            results = self.gmail_service.users().messages().list(
                userId="me",
                q=query
            ).execute()

            messages = []
            if "messages" in results:
                for message in results["messages"]:
                    msg_detail = self.gmail_service.users().messages().get(
                        userId="me",
                        id=message["id"]
                    ).execute()
                    messages.append(msg_detail)

            return messages
        except HttpError as e:
            logger.error(f"HTTP error occurred while checking emails: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")
            raise

    async def process_messages(self, messages: List[Dict]) -> None:
        try:
            for message in messages:
                headers = {h["name"]: h["value"] for h in message["payload"]["headers"]}
                subject = headers.get("Subject", "")
                sender = headers.get("From", "")
                
                alert_data = {
                    "subject": subject,
                    "sender": sender,
                    "timestamp": datetime.utcnow().isoformat(),
                    "message_id": message["id"]
                }
                
                await self.send_alert("email_received", alert_data)
                logger.info(f"Processed email: {subject} from {sender}")
        except Exception as e:
            logger.error(f"Error processing messages: {str(e)}")
            raise

    async def execute(self) -> None:
        logger.info("Starting email monitoring loop")
        while self.running:
            try:
                async with asyncio.timeout(270):  # 4.5 minutes timeout
                    messages = await self.check_emails()
                    if messages:
                        await self.process_messages(messages)
                    self.last_check_time = datetime.utcnow()
                    logger.debug("Completed email check cycle")
                    
                await asyncio.sleep(180)  # Wait 3 minutes before next check
            except asyncio.TimeoutError:
                logger.error("Timeout occurred during execution cycle")
            except Exception as e:
                logger.error(f"Error in execution loop: {str(e)}")
                await asyncio.sleep(30)  # Brief pause before retry on error

    async def cleanup(self) -> None:
        try:
            self.running = False
            if self.gmail_service:
                self.gmail_service.close()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
            raise