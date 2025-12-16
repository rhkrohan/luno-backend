"""
Firestore Service Layer
Handles all Firestore operations for conversations, messages, and stats
"""

from datetime import datetime
from firebase_admin import firestore
from firebase_config import get_firestore_client
import re
import time

# Safety check keywords for content moderation
SAFETY_KEYWORDS = {
    'personal_info': [
        r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b',  # Phone numbers
        r'\b\d{3}[-]?\d{2}[-]?\d{4}\b',    # SSN
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{1,5}\s+\w+\s+(street|st|avenue|ave|road|rd|lane|ln|drive|dr|court|ct)\b',  # Addresses
    ],
    'inappropriate_content': [
        r'\b(kill|hurt|violence|weapon|gun|knife|blood)\b',
        r'\b(hate|stupid|dumb|idiot)\b',
    ],
    'emotional_distress': [
        r'\b(scared|afraid|terrified|nightmare|crying|sad|depressed)\b',
    ],
}


class FirestoreService:
    """Main service class for Firestore operations"""

    def __init__(self):
        self.db = get_firestore_client()

    def is_available(self):
        """Check if Firestore is available"""
        return self.db is not None

    # ==================== CONVERSATION OPERATIONS ====================

    def create_conversation(self, user_id, child_id, toy_id=None, conversation_type="conversation"):
        """
        Create a new conversation in Firestore

        Args:
            user_id: Parent user ID
            child_id: Child ID
            toy_id: Optional toy ID
            conversation_type: Type of conversation (conversation, story, game, learning)

        Returns:
            conversation_id: The ID of the created conversation
        """
        if not self.is_available():
            print("[WARNING] Firestore not available, skipping conversation creation")
            return None

        try:
            # Get child and toy names for denormalization
            child_name = self._get_child_name(user_id, child_id)
            toy_name = self._get_toy_name(user_id, toy_id) if toy_id else None

            conversation_data = {
                "startTime": firestore.SERVER_TIMESTAMP,
                "endTime": None,
                "duration": 0,
                "type": conversation_type,
                "title": "New Conversation",  # Will be updated based on content
                "messageCount": 0,
                "createdAt": firestore.SERVER_TIMESTAMP,

                # Denormalized fields
                "childId": child_id,
                "childName": child_name,
                "toyId": toy_id,  # Add toyId field
                "toyName": toy_name,

                # Safety fields
                "flagged": False,
                "flagReason": None,
                "flagType": None,
                "severity": None,
                "flagStatus": "unreviewed",
                "messagePreview": None,
            }

            # Generate custom conversation ID: {child_id}_{toy_id}_{timestamp}
            timestamp = int(time.time())
            date_str = datetime.now().strftime("%Y%m%d")

            # Format: childId_toyId_date
            # Use 'notoy' if toy_id is None
            toy_part = toy_id if toy_id else "notoy"
            conversation_id = f"{child_id}_{toy_part}_{date_str}_{timestamp}"

            # Create conversation document with custom ID
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("conversations").document(conversation_id)

            conversation_ref.set(conversation_data)

            # Update toy status if toy_id is provided
            if toy_id:
                self._update_toy_status(user_id, toy_id, status="online")

            print(f"[INFO] Created conversation: {conversation_id} for child: {child_id}")
            return conversation_id

        except Exception as e:
            print(f"[ERROR] Failed to create conversation: {e}")
            return None

    def add_message(self, user_id, child_id, conversation_id, sender, content):
        """
        Add a message to a conversation

        Args:
            user_id: Parent user ID
            child_id: Child ID
            conversation_id: Conversation ID
            sender: 'child' or 'toy'
            content: Message content

        Returns:
            message_id: The ID of the created message
        """
        if not self.is_available():
            print("[WARNING] Firestore not available, skipping message save")
            return None

        try:
            # Check for safety issues
            safety_result = self._check_message_safety(content)

            message_data = {
                "sender": sender,
                "content": content,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "flagged": safety_result["flagged"],
                "flagReason": safety_result.get("flagReason"),
            }

            # Get current message count for this sender to create sequential ID
            messages_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("conversations").document(conversation_id)\
                .collection("messages")

            # Count existing messages from this sender
            sender_messages = messages_ref.where("sender", "==", sender).stream()
            sender_count = sum(1 for _ in sender_messages) + 1

            # Create message ID: child_1, toy_1, child_2, toy_2, etc.
            message_id = f"{sender}_{sender_count}"

            # Add message with custom ID
            message_ref = messages_ref.document(message_id)
            message_ref.set(message_data)

            # Update conversation metadata
            self._update_conversation_after_message(
                user_id, child_id, conversation_id, content, safety_result
            )

            print(f"[INFO] Added {sender} message ({message_id}) to conversation {conversation_id}")
            return message_id

        except Exception as e:
            print(f"[ERROR] Failed to add message: {e}")
            return None

    def end_conversation(self, user_id, child_id, conversation_id, duration_minutes):
        """
        End a conversation and update stats

        Args:
            user_id: Parent user ID
            child_id: Child ID
            conversation_id: Conversation ID
            duration_minutes: Duration in minutes
        """
        if not self.is_available():
            print("[WARNING] Firestore not available, skipping conversation end")
            return

        try:
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("conversations").document(conversation_id)

            # Get current message count
            messages = conversation_ref.collection("messages").stream()
            message_count = sum(1 for _ in messages)

            # Update conversation
            conversation_ref.update({
                "endTime": firestore.SERVER_TIMESTAMP,
                "duration": duration_minutes,
                "messageCount": message_count,
            })

            # Update user stats
            self._update_user_stats(user_id, child_id, conversation_id, duration_minutes)

            print(f"[INFO] Ended conversation {conversation_id}, duration: {duration_minutes}m")

        except Exception as e:
            print(f"[ERROR] Failed to end conversation: {e}")

    # ==================== STATS OPERATIONS ====================

    def _update_user_stats(self, user_id, child_id, conversation_id, duration_minutes):
        """Update user statistics after conversation ends"""
        try:
            user_ref = self.db.collection("users").document(user_id)
            conversation_ref = user_ref.collection("children").document(child_id)\
                .collection("conversations").document(conversation_id)

            # Get conversation to check if flagged
            conversation = conversation_ref.get().to_dict()
            is_flagged = conversation.get("flagged", False)

            # Increment stats
            user_ref.update({
                "stats.totalConversations": firestore.Increment(1),
                "stats.totalConversationDurationSec": firestore.Increment(duration_minutes * 60),
                "stats.lastConversationAt": firestore.SERVER_TIMESTAMP,
                "lastActivityAt": firestore.SERVER_TIMESTAMP,
            })

            # If flagged, update flagged stats
            if is_flagged:
                user_ref.update({
                    "stats.flaggedConversations": firestore.Increment(1),
                    "stats.lastFlaggedAt": firestore.SERVER_TIMESTAMP,
                })

            print(f"[INFO] Updated user stats for user: {user_id}")

        except Exception as e:
            print(f"[ERROR] Failed to update user stats: {e}")

    # ==================== HELPER METHODS ====================

    def _get_child_name(self, user_id, child_id):
        """Get child name from Firestore"""
        try:
            child_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)
            child_doc = child_ref.get()
            if child_doc.exists:
                return child_doc.to_dict().get("name")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to get child name: {e}")
            return None

    def _get_toy_name(self, user_id, toy_id):
        """Get toy name from Firestore"""
        try:
            toy_ref = self.db.collection("users").document(user_id)\
                .collection("toys").document(toy_id)
            toy_doc = toy_ref.get()
            if toy_doc.exists:
                return toy_doc.to_dict().get("name")
            return None
        except Exception as e:
            print(f"[ERROR] Failed to get toy name: {e}")
            return None

    def _update_toy_status(self, user_id, toy_id, status="online"):
        """Update toy status and last connected time"""
        try:
            toy_ref = self.db.collection("users").document(user_id)\
                .collection("toys").document(toy_id)

            # Check if toy exists
            toy_doc = toy_ref.get()
            if toy_doc.exists:
                # Update existing toy
                toy_ref.update({
                    "status": status,
                    "lastConnected": firestore.SERVER_TIMESTAMP
                })
                print(f"[INFO] Updated toy {toy_id} status to {status}")
            else:
                # Toy doesn't exist - create a basic toy document
                print(f"[WARNING] Toy {toy_id} not found, creating basic toy document")
                toy_data = {
                    "name": f"Toy {toy_id[-6:]}",  # Use last 6 chars of ID
                    "emoji": "🦄",
                    "assignedChildId": None,
                    "pairedAt": firestore.SERVER_TIMESTAMP,
                    "status": status,
                    "batteryLevel": 100,
                    "lastConnected": firestore.SERVER_TIMESTAMP,
                    "model": "Luno Simulator",
                    "serialNumber": f"SIM-{toy_id}",
                    "firmwareVersion": "v1.0.0-simulator",
                    "volume": 70,
                    "ledBrightness": "Medium",
                    "soundEffects": True,
                    "voiceType": "Female, Child-friendly",
                    "autoUpdate": True,
                    "connectionType": "Wi-Fi",
                    "wifiNetwork": "Simulator-Network"
                }
                toy_ref.set(toy_data)
                print(f"[INFO] Created basic toy document for {toy_id}")

        except Exception as e:
            print(f"[ERROR] Failed to update toy status: {e}")

    def _check_message_safety(self, content):
        """
        Check message content for safety issues

        Returns:
            dict with 'flagged', 'flagType', 'flagReason', 'severity'
        """
        content_lower = content.lower()

        for flag_type, patterns in SAFETY_KEYWORDS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    severity = self._determine_severity(flag_type)
                    return {
                        "flagged": True,
                        "flagType": flag_type,
                        "flagReason": f"Detected {flag_type.replace('_', ' ')}",
                        "severity": severity,
                    }

        return {"flagged": False}

    def _determine_severity(self, flag_type):
        """Determine severity based on flag type"""
        if flag_type == "personal_info":
            return "critical"
        elif flag_type == "inappropriate_content":
            return "high"
        elif flag_type == "emotional_distress":
            return "medium"
        else:
            return "low"

    def _update_conversation_after_message(self, user_id, child_id, conversation_id, content, safety_result):
        """Update conversation metadata after adding a message"""
        try:
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("conversations").document(conversation_id)

            update_data = {
                "messageCount": firestore.Increment(1),
            }

            # If message is flagged, flag the conversation
            if safety_result.get("flagged"):
                update_data.update({
                    "flagged": True,
                    "flagType": safety_result.get("flagType"),
                    "flagReason": safety_result.get("flagReason"),
                    "severity": safety_result.get("severity"),
                    "messagePreview": content[:100] + "..." if len(content) > 100 else content,
                })

            conversation_ref.update(update_data)

        except Exception as e:
            print(f"[ERROR] Failed to update conversation after message: {e}")

    # ==================== QUERY OPERATIONS ====================

    def get_conversation(self, user_id, child_id, conversation_id):
        """Get a specific conversation"""
        if not self.is_available():
            return None

        try:
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("conversations").document(conversation_id)

            conversation_doc = conversation_ref.get()
            if conversation_doc.exists:
                return conversation_doc.to_dict()
            return None

        except Exception as e:
            print(f"[ERROR] Failed to get conversation: {e}")
            return None

    def get_conversation_messages(self, user_id, child_id, conversation_id, limit=100):
        """Get messages for a conversation"""
        if not self.is_available():
            return []

        try:
            messages_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("conversations").document(conversation_id)\
                .collection("messages")\
                .order_by("timestamp")\
                .limit(limit)

            messages = []
            for doc in messages_ref.stream():
                message_data = doc.to_dict()
                message_data["id"] = doc.id
                messages.append(message_data)

            return messages

        except Exception as e:
            print(f"[ERROR] Failed to get conversation messages: {e}")
            return []

    def get_child_conversations(self, user_id, child_id, limit=50):
        """Get recent conversations for a child"""
        if not self.is_available():
            return []

        try:
            conversations_ref = self.db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("conversations")\
                .order_by("createdAt", direction=firestore.Query.DESCENDING)\
                .limit(limit)

            conversations = []
            for doc in conversations_ref.stream():
                conv_data = doc.to_dict()
                conv_data["id"] = doc.id
                conversations.append(conv_data)

            return conversations

        except Exception as e:
            print(f"[ERROR] Failed to get child conversations: {e}")
            return []


# Global service instance
firestore_service = FirestoreService()
