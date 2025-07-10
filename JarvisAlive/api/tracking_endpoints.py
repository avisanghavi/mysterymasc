#!/usr/bin/env python3
"""
Email Tracking Endpoints for HeyJarvis
Handles tracking pixels, click tracking, and unsubscribe functionality
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from fastapi import FastAPI, Request, Response, HTTPException, Depends
from fastapi.responses import StreamingResponse, RedirectResponse, HTMLResponse
import redis.asyncio as redis

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Gmail integration for tracking
try:
    from integrations.gmail_integration import GmailIntegration
except ImportError:
    GmailIntegration = None

class EmailTrackingService:
    """Service for handling email tracking events"""
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self.redis_client = redis_client
        self.gmail_integration = None
        
        if GmailIntegration and redis_client:
            self.gmail_integration = GmailIntegration(
                redis_client=redis_client,
                test_mode=True  # Default to test mode
            )
    
    async def track_pixel_view(
        self,
        tracking_id: str,
        request: Request
    ) -> Dict[str, Any]:
        """Track email open via tracking pixel"""
        
        try:
            # Extract request metadata
            user_agent = request.headers.get("user-agent", "")
            ip_address = request.client.host if request.client else ""
            
            metadata = {
                "user_agent": user_agent,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat(),
                "tracking_method": "pixel"
            }
            
            # Track the event
            if self.gmail_integration:
                success = await self.gmail_integration.track_event(
                    tracking_id=tracking_id,
                    event_type="opened",
                    metadata=metadata
                )
            else:
                # Fallback storage
                success = await self._fallback_track_event(tracking_id, "opened", metadata)
            
            logger.info(f"Tracked email open: {tracking_id} - Success: {success}")
            
            return {
                "success": success,
                "tracking_id": tracking_id,
                "event_type": "opened",
                "timestamp": metadata["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Error tracking pixel view: {e}")
            return {
                "success": False,
                "error": str(e),
                "tracking_id": tracking_id
            }
    
    async def track_link_click(
        self,
        tracking_id: str,
        target_url: str,
        request: Request
    ) -> Dict[str, Any]:
        """Track email link click"""
        
        try:
            # Extract request metadata
            user_agent = request.headers.get("user-agent", "")
            ip_address = request.client.host if request.client else ""
            referer = request.headers.get("referer", "")
            
            metadata = {
                "user_agent": user_agent,
                "ip_address": ip_address,
                "referer": referer,
                "target_url": target_url,
                "timestamp": datetime.utcnow().isoformat(),
                "tracking_method": "link_click"
            }
            
            # Track the event
            if self.gmail_integration:
                success = await self.gmail_integration.track_event(
                    tracking_id=tracking_id,
                    event_type="clicked",
                    metadata=metadata
                )
            else:
                # Fallback storage
                success = await self._fallback_track_event(tracking_id, "clicked", metadata)
            
            logger.info(f"Tracked link click: {tracking_id} -> {target_url}")
            
            return {
                "success": success,
                "tracking_id": tracking_id,
                "event_type": "clicked",
                "target_url": target_url,
                "timestamp": metadata["timestamp"]
            }
            
        except Exception as e:
            logger.error(f"Error tracking link click: {e}")
            return {
                "success": False,
                "error": str(e),
                "tracking_id": tracking_id
            }
    
    async def handle_unsubscribe(
        self,
        token: str,
        request: Request
    ) -> Dict[str, Any]:
        """Handle unsubscribe request"""
        
        try:
            # Decode unsubscribe token
            unsubscribe_data = await self._decode_unsubscribe_token(token)
            
            if not unsubscribe_data:
                return {
                    "success": False,
                    "error": "Invalid unsubscribe token"
                }
            
            # Extract request metadata
            user_agent = request.headers.get("user-agent", "")
            ip_address = request.client.host if request.client else ""
            
            metadata = {
                "user_agent": user_agent,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat(),
                "lead_id": unsubscribe_data.get("lead_id"),
                "email": unsubscribe_data.get("email"),
                "message_id": unsubscribe_data.get("message_id")
            }
            
            # Track unsubscribe event
            tracking_id = unsubscribe_data.get("tracking_id")
            if tracking_id and self.gmail_integration:
                await self.gmail_integration.track_event(
                    tracking_id=tracking_id,
                    event_type="unsubscribed",
                    metadata=metadata
                )
            
            # Store unsubscribe in Redis
            await self._store_unsubscribe(unsubscribe_data, metadata)
            
            logger.info(f"Processed unsubscribe: {unsubscribe_data.get('email')}")
            
            return {
                "success": True,
                "email": unsubscribe_data.get("email"),
                "message": "Successfully unsubscribed"
            }
            
        except Exception as e:
            logger.error(f"Error handling unsubscribe: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_tracking_stats(
        self,
        tracking_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get tracking statistics for an email"""
        
        if self.gmail_integration:
            return await self.gmail_integration.get_tracking_summary(tracking_id)
        else:
            # Fallback to direct Redis lookup
            return await self._fallback_get_stats(tracking_id)
    
    async def _fallback_track_event(
        self,
        tracking_id: str,
        event_type: str,
        metadata: Dict[str, Any]
    ) -> bool:
        """Fallback event tracking without Gmail integration"""
        
        if not self.redis_client:
            return False
        
        try:
            # Store event
            event_key = f"email_tracking:{tracking_id}:{event_type}:{datetime.utcnow().timestamp()}"
            await self.redis_client.setex(
                event_key,
                86400 * 30,  # 30 days
                json.dumps(metadata)
            )
            
            # Update summary
            summary_key = f"email_summary:{tracking_id}"
            summary = await self.redis_client.get(summary_key)
            
            if summary:
                summary_data = json.loads(summary)
            else:
                summary_data = {"tracking_id": tracking_id, "events": {}}
            
            if event_type not in summary_data["events"]:
                summary_data["events"][event_type] = 0
            summary_data["events"][event_type] += 1
            summary_data[f"last_{event_type}"] = metadata["timestamp"]
            
            await self.redis_client.setex(
                summary_key,
                86400 * 30,  # 30 days
                json.dumps(summary_data)
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Fallback tracking failed: {e}")
            return False
    
    async def _fallback_get_stats(self, tracking_id: str) -> Optional[Dict[str, Any]]:
        """Fallback stats retrieval"""
        
        if not self.redis_client:
            return None
        
        try:
            summary_key = f"email_summary:{tracking_id}"
            summary = await self.redis_client.get(summary_key)
            
            if summary:
                return json.loads(summary)
            
            return None
            
        except Exception as e:
            logger.error(f"Fallback stats retrieval failed: {e}")
            return None
    
    async def _decode_unsubscribe_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode unsubscribe token to get lead information"""
        
        if not self.redis_client:
            return None
        
        try:
            # Look up token in Redis (tokens are stored when emails are sent)
            token_key = f"unsubscribe_token:{token}"
            token_data = await self.redis_client.get(token_key)
            
            if token_data:
                return json.loads(token_data)
            
            # If not found, try to parse as simple hash
            # This is a fallback for tokens generated by _generate_unsubscribe_url
            # In a real implementation, you'd store the mapping when generating the URL
            return {
                "token": token,
                "email": "unknown@example.com",  # Would need to reverse lookup
                "lead_id": "unknown",
                "message_id": "unknown"
            }
            
        except Exception as e:
            logger.error(f"Error decoding unsubscribe token: {e}")
            return None
    
    async def _store_unsubscribe(
        self,
        unsubscribe_data: Dict[str, Any],
        metadata: Dict[str, Any]
    ):
        """Store unsubscribe information"""
        
        if not self.redis_client:
            return
        
        try:
            email = unsubscribe_data.get("email")
            if not email:
                return
            
            # Store unsubscribe record
            unsubscribe_key = f"unsubscribed:{email}"
            record = {
                "email": email,
                "unsubscribed_at": metadata["timestamp"],
                "ip_address": metadata.get("ip_address"),
                "user_agent": metadata.get("user_agent"),
                "lead_id": unsubscribe_data.get("lead_id"),
                "message_id": unsubscribe_data.get("message_id")
            }
            
            await self.redis_client.setex(
                unsubscribe_key,
                86400 * 365,  # Keep for 1 year
                json.dumps(record)
            )
            
            # Add to global unsubscribe list
            await self.redis_client.sadd("global_unsubscribed", email)
            
        except Exception as e:
            logger.error(f"Error storing unsubscribe: {e}")


# FastAPI app for tracking endpoints
app = FastAPI(title="HeyJarvis Email Tracking API", version="1.0.0")

# Initialize tracking service
tracking_service = None

@app.on_event("startup")
async def startup_event():
    """Initialize Redis connection on startup"""
    global tracking_service
    
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = await redis.from_url(redis_url)
        tracking_service = EmailTrackingService(redis_client)
        logger.info("Email tracking service initialized")
    except Exception as e:
        logger.error(f"Failed to initialize tracking service: {e}")
        tracking_service = EmailTrackingService()  # Initialize without Redis

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    if tracking_service and tracking_service.redis_client:
        await tracking_service.redis_client.close()

# Tracking pixel endpoint
@app.get("/api/track/pixel/{tracking_id}.gif")
async def tracking_pixel(tracking_id: str, request: Request):
    """
    Tracking pixel endpoint - returns 1x1 transparent GIF
    Tracks email opens
    """
    
    # Track the event
    if tracking_service:
        await tracking_service.track_pixel_view(tracking_id, request)
    
    # Return 1x1 transparent GIF
    gif_data = b'\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x01\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x04\x01\x00\x3b'
    
    return Response(
        content=gif_data,
        media_type="image/gif",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )

# Link click tracking endpoint
@app.get("/api/track/click/{tracking_id}")
async def track_click(tracking_id: str, url: str, request: Request):
    """
    Link click tracking endpoint
    Tracks clicks and redirects to target URL
    """
    
    # Track the event
    if tracking_service:
        await tracking_service.track_link_click(tracking_id, url, request)
    
    # Redirect to target URL
    return RedirectResponse(url=url, status_code=302)

# Unsubscribe endpoint
@app.get("/api/unsubscribe/{token}")
async def unsubscribe_get(token: str, request: Request):
    """
    Unsubscribe page (GET request)
    Shows unsubscribe confirmation form
    """
    
    # Simple HTML unsubscribe page
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Unsubscribe - HeyJarvis</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 600px;
                margin: 50px auto;
                padding: 20px;
                background-color: #f9f9f9;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .btn {{
                background-color: #dc3545;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 4px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px;
            }}
            .btn:hover {{
                background-color: #c82333;
            }}
            .btn-secondary {{
                background-color: #6c757d;
            }}
            .btn-secondary:hover {{
                background-color: #5a6268;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Unsubscribe from HeyJarvis Emails</h2>
            <p>Are you sure you want to unsubscribe from our email communications?</p>
            <p>You will no longer receive emails from us about sales opportunities and updates.</p>
            
            <form method="post" action="/api/unsubscribe/{token}">
                <button type="submit" class="btn">Yes, Unsubscribe</button>
                <button type="button" class="btn btn-secondary" onclick="window.close()">Cancel</button>
            </form>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=html_content)

@app.post("/api/unsubscribe/{token}")
async def unsubscribe_post(token: str, request: Request):
    """
    Unsubscribe endpoint (POST request)
    Processes unsubscribe request
    """
    
    result = {"success": False, "message": "Failed to process unsubscribe"}
    
    if tracking_service:
        result = await tracking_service.handle_unsubscribe(token, request)
    
    # Return confirmation page
    if result["success"]:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unsubscribed - HeyJarvis</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }
                .container {
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                }
                .success {
                    color: #28a745;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="success">✓ Successfully Unsubscribed</h2>
                <p>You have been unsubscribed from HeyJarvis emails.</p>
                <p>You will no longer receive marketing emails from us.</p>
                <p>Thank you for your time.</p>
            </div>
        </body>
        </html>
        """
    else:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Unsubscribe Error - HeyJarvis</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    max-width: 600px;
                    margin: 50px auto;
                    padding: 20px;
                    background-color: #f9f9f9;
                }}
                .container {{
                    background-color: white;
                    padding: 30px;
                    border-radius: 8px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    text-align: center;
                }}
                .error {{
                    color: #dc3545;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2 class="error">Unsubscribe Error</h2>
                <p>There was an error processing your unsubscribe request.</p>
                <p>Error: {result.get("error", "Unknown error")}</p>
                <p>Please contact support if this continues.</p>
            </div>
        </body>
        </html>
        """
    
    return HTMLResponse(content=html_content)

# Tracking stats endpoint
@app.get("/api/track/stats/{tracking_id}")
async def get_tracking_stats(tracking_id: str):
    """
    Get tracking statistics for an email
    """
    
    if not tracking_service:
        raise HTTPException(status_code=503, detail="Tracking service not available")
    
    stats = await tracking_service.get_tracking_stats(tracking_id)
    
    if not stats:
        raise HTTPException(status_code=404, detail="Tracking data not found")
    
    return stats

# Health check endpoint
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    
    redis_status = "connected" if tracking_service and tracking_service.redis_client else "disconnected"
    
    return {
        "status": "healthy",
        "redis": redis_status,
        "timestamp": datetime.utcnow().isoformat()
    }

# Example usage and testing
if __name__ == "__main__":
    import uvicorn
    
    # Run the tracking server
    uvicorn.run(
        "tracking_endpoints:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )