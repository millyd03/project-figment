"""
Push notification helper for Disney nudges and updates.
Supports Web Push API (standard) and Firebase Cloud Messaging.
"""

import json
import logging
from typing import Dict, Optional, List
from database import SessionLocal, UserSubscription

logger = logging.getLogger(__name__)

# For Web Push API - requires pywebpush
try:
    from pywebpush import webpush, WebPushException
    WEBPUSH_AVAILABLE = True
except ImportError:
    WEBPUSH_AVAILABLE = False
    logger.warning("pywebpush not available - Web Push notifications disabled")

# Firebase Cloud Messaging (optional)
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    logger.info("Firebase Admin SDK not available - using Web Push API")


class NotificationManager:
    """Handles sending push notifications to subscribed devices."""
    
    def __init__(self):
        self.webpush_available = WEBPUSH_AVAILABLE
        self.firebase_available = FIREBASE_AVAILABLE
        self.vapid_private_key = None
        self.vapid_public_key = None
        
        # Load VAPID keys for Web Push (required for webpush)
        # These should be generated once and stored in config/env
        # Generate with: python -c "from pywebpush import generate_vapid_keys; print(generate_vapid_keys())"
        # Then set as environment variables
        import os
        self.vapid_public_key = os.getenv("VAPID_PUBLIC_KEY")
        self.vapid_private_key = os.getenv("VAPID_PRIVATE_KEY")
    
    def send_nudge_notification(self, nudge: Dict, user_id: str = "default_user") -> bool:
        """
        Send a push notification for a Disney nudge (low wait time or must-do drop).
        
        nudge: Dict with keys like:
        {
            "type": "low_wait" | "must_do_drop",
            "ride": "Ride Name",
            "wait_time": 15,
            "drop_percent": 45 (optional)
        }
        """
        db = SessionLocal()
        try:
            # Get all active subscriptions for this user
            subscriptions = db.query(UserSubscription).filter(
                UserSubscription.user_id == user_id,
                UserSubscription.is_active == True
            ).all()
            
            if not subscriptions:
                logger.info(f"No active subscriptions found for user {user_id}")
                return False
            
            # Prepare notification payload
            if nudge["type"] == "low_wait":
                title = "Short Wait!"
                body = f"{nudge['ride']} - {nudge['wait_time']} min wait 🎢"
            else:  # must_do_drop
                title = "Must-Do Alert!"
                body = f"{nudge['ride']} dropped {nudge.get('drop_percent', 30):.0f}% - {nudge['wait_time']} mins 🎉"
            
            payload = {
                "title": title,
                "body": body,
                "tag": f"nudge-{nudge['ride'].replace(' ', '-')}",
                "badge": "/icons/badge-192x192.png",
                "icon": "/icons/icon-192x192.png",
            }
            
            success_count = 0
            for subscription in subscriptions:
                try:
                    if self._send_to_subscription(subscription, payload):
                        success_count += 1
                except Exception as e:
                    logger.error(f"Failed to send notification to subscription {subscription.id}: {e}")
            
            logger.info(f"Successfully sent {success_count}/{len(subscriptions)} nudge notifications")
            return success_count > 0
        finally:
            db.close()
    
    def _send_to_subscription(self, subscription: UserSubscription, payload: Dict) -> bool:
        """Send a push notification to a specific subscription."""
        try:
            subscription_data = json.loads(subscription.subscription_data)
            
            # Try Web Push API first (standard)
            if self.webpush_available and self.vapid_private_key:
                try:
                    webpush(
                        subscription_info=subscription_data,
                        data=json.dumps(payload),
                        vapid_private_key=self.vapid_private_key,
                        vapid_claims={"sub": "mailto:noreply@figment.local"}
                    )
                    logger.debug(f"Sent Web Push notification to {subscription_data['endpoint'][:50]}...")
                    return True
                except WebPushException as e:
                    # Handle subscription no longer valid
                    if 410 in str(e):
                        logger.info(f"Subscription expired, removing: {subscription.id}")
                        db = SessionLocal()
                        try:
                            sub = db.query(UserSubscription).get(subscription.id)
                            if sub:
                                sub.is_active = False
                                db.commit()
                        finally:
                            db.close()
                    return False
            else:
                logger.warning("Web Push unavailable - VAPID keys not configured")
                return False
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
            return False


# Global notification manager instance
notification_manager = NotificationManager()


def send_nudge(nudge: Dict, user_id: str = "default_user") -> bool:
    """Helper function to send a nudge notification."""
    return notification_manager.send_nudge_notification(nudge, user_id)
