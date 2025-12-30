"""
Firestore Service Layer
Handles all Firestore operations for conversations, messages, and stats
"""

from datetime import datetime
from firebase_admin import firestore
from firebase_config import get_firestore_client
from logging_config import get_logger
import re
import time

logger = get_logger(__name__)

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
        Create a new conversation in Firestore (UNIFIED SCHEMA with ARRAY-BASED MESSAGES)

        NEW LOCATION: users/{userId}/conversations/{conversationId}
        Messages stored as array field, not subcollection

        Args:
            user_id: Parent user ID
            child_id: Child ID
            toy_id: Toy/Device ID (same thing)
            conversation_type: Type of conversation (conversation, story, game, learning)

        Returns:
            conversation_id: The ID of the created conversation
        """
        if not self.is_available():
            logger.warning("Firestore not available, skipping conversation creation")
            return None

        try:
            # Get denormalized names for quick display
            child_name = self._get_child_name(user_id, child_id)
            toy_name = self._get_toy_name(user_id, toy_id) if toy_id else None

            conversation_data = {
                # Core Metadata
                "status": "active",
                "type": conversation_type,
                "createdAt": firestore.SERVER_TIMESTAMP,

                # Relationships - IDs
                "childId": child_id,
                "toyId": toy_id or None,

                # Relationships - Denormalized names
                "childName": child_name,
                "toyName": toy_name,

                # Timing
                "startTime": firestore.SERVER_TIMESTAMP,
                "lastActivityAt": firestore.SERVER_TIMESTAMP,
                "endTime": None,
                "duration": 0,  # Legacy field for compatibility
                "durationMinutes": 0,

                # Content Summary
                "title": "Untitled",  # Will be AI-generated on end
                "titleGeneratedAt": None,
                "messageCount": 0,
                "firstMessagePreview": None,

                # Safety & Moderation
                "flagged": False,
                "flagType": None,
                "flagReason": None,
                "severity": None,
                "flagStatus": "unreviewed",

                # Messages Array (COMPACT STRUCTURE)
                "messages": [],
            }

            # Generate custom conversation ID: {child_id}_{toy_id}_{timestamp}
            timestamp = int(time.time())
            date_str = datetime.now().strftime("%Y%m%d")

            toy_part = toy_id if toy_id else "notoy"
            conversation_id = f"{child_id}_{toy_part}_{date_str}_{timestamp}"

            # NEW LOCATION: Direct under user (not nested in children)
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id)

            conversation_ref.set(conversation_data)

            # Update toy status if toy_id is provided
            if toy_id:
                self._update_toy_status(user_id, toy_id, status="online")

            logger.info(f"Created conversation with array-based messages: {conversation_id}")
            return conversation_id

        except Exception as e:
            logger.error(f"Failed to create conversation for user {user_id} | Error: {str(e)}", exc_info=True)
            return None

    def add_message(self, user_id, conversation_id, sender, content):
        """
        Add a single message to a conversation using ARRAY-BASED storage with cap
        NOTE: Prefer using add_message_batch() for better performance

        Args:
            user_id: Parent user ID
            conversation_id: Conversation ID
            sender: 'child' or 'toy'
            content: Message content

        Returns:
            bool: Success status
        """
        if not self.is_available():
            logger.warning("Firestore not available, skipping message save")
            return False

        try:
            # Get conversation ref
            conv_ref = self.db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id)

            # Check for safety issues
            safety_result = self._check_message_safety(content)

            # Create message object with timestamp
            # NOTE: Use datetime instead of SERVER_TIMESTAMP for arrays in transactions
            from datetime import datetime as dt_now
            timestamp_now = dt_now.utcnow()

            message = {
                "sender": sender,
                "content": content,
                "timestamp": timestamp_now,
                "flagged": safety_result["flagged"],
                "flagReason": safety_result.get("flagReason"),
            }

            # Use transaction for atomic read-modify-write with array cap
            @firestore.transactional
            def update_in_transaction(transaction, conv_ref):
                snapshot = conv_ref.get(transaction=transaction)

                # Check if conversation exists
                if not snapshot.exists:
                    raise ValueError(f"Conversation {conversation_id} does not exist for user {user_id}. Please create the conversation first.")

                snapshot_data = snapshot.to_dict()
                current_messages = snapshot_data.get('messages', [])
                message_count = snapshot_data.get('messageCount', 0)

                # Array cap: Keep last 149 messages, add 1 new = 150 max
                if len(current_messages) >= 150:
                    new_messages = current_messages[-149:] + [message]
                else:
                    new_messages = current_messages + [message]

                # Prepare update data
                update_data = {
                    "messages": new_messages,
                    "messageCount": message_count + 1,
                    "lastActivityAt": firestore.SERVER_TIMESTAMP
                }

                # Add flag data if message flagged
                if safety_result["flagged"]:
                    update_data.update({
                        "flagged": True,
                        "flagType": safety_result.get("flagType"),
                        "flagReason": safety_result.get("flagReason"),
                        "severity": safety_result.get("severity")
                    })

                # Update conversation document
                transaction.update(conv_ref, update_data)

            # Execute transaction
            transaction = self.db.transaction()
            update_in_transaction(transaction, conv_ref)

            logger.info(f"Added {sender} message to conversation {conversation_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id} | Error: {str(e)}", exc_info=True)
            return False

    def add_message_batch(self, user_id, conversation_id, child_message, toy_message):
        """
        Add both child and toy messages in a single transaction (ARRAY-BASED VERSION)
        Messages are stored as an array field in the conversation document with a 150 message cap

        Args:
            user_id: Parent user ID
            conversation_id: Conversation ID
            child_message: Child's message content
            toy_message: Toy's response content

        Returns:
            tuple: (child_message_id, toy_message_id) - synthetic IDs for compatibility
        """
        if not self.is_available():
            logger.warning("Firestore not available, skipping batch message save")
            return None, None

        try:
            # Get conversation ref
            conv_ref = self.db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id)

            # Check safety for child message
            child_safety = self._check_message_safety(child_message)

            # Create message objects with timestamps
            # NOTE: Use datetime instead of SERVER_TIMESTAMP for arrays in transactions
            from datetime import datetime as dt_now
            timestamp_now = dt_now.utcnow()

            child_msg = {
                "sender": "child",
                "content": child_message,
                "timestamp": timestamp_now,
                "flagged": child_safety["flagged"],
                "flagReason": child_safety.get("flagReason")
            }

            toy_msg = {
                "sender": "toy",
                "content": toy_message,
                "timestamp": timestamp_now,
                "flagged": False,
                "flagReason": None
            }

            # Use transaction for atomic read-modify-write
            @firestore.transactional
            def update_in_transaction(transaction, conv_ref):
                snapshot = conv_ref.get(transaction=transaction)
                snapshot_data = snapshot.to_dict()
                current_messages = snapshot_data.get('messages', [])
                message_count = snapshot_data.get('messageCount', 0)

                # Array cap: Keep last 148 messages, add 2 new = 150 max
                if len(current_messages) >= 149:
                    new_messages = current_messages[-(149-1):] + [child_msg, toy_msg]
                else:
                    new_messages = current_messages + [child_msg, toy_msg]

                # Build update data
                update_data = {
                    "messages": new_messages,
                    "messageCount": message_count + 2,
                    "lastActivityAt": firestore.SERVER_TIMESTAMP
                }

                # Add flag data if message flagged
                if child_safety["flagged"]:
                    update_data.update({
                        "flagged": True,
                        "flagType": child_safety.get("flagType"),
                        "flagReason": child_safety.get("flagReason"),
                        "severity": child_safety.get("severity")
                    })

                # Store first message preview if this is the first exchange
                if message_count == 0:
                    update_data["firstMessagePreview"] = child_message[:50]

                # Update conversation document
                transaction.update(conv_ref, update_data)

                return message_count

            # Execute transaction
            transaction = self.db.transaction()
            message_count = update_in_transaction(transaction, conv_ref)

            # Generate synthetic message IDs for compatibility
            child_msg_count = (message_count // 2) + 1
            toy_msg_count = (message_count // 2) + 1
            child_message_id = f"child_{child_msg_count}"
            toy_message_id = f"toy_{toy_msg_count}"

            logger.info(f"Batch saved messages to conversation {conversation_id} array (1 transaction)")
            return child_message_id, toy_message_id

        except Exception as e:
            logger.error(f"Failed to batch save messages to conversation {conversation_id} | Error: {str(e)}", exc_info=True)
            return None, None

    def end_conversation(self, user_id, conversation_id, duration_minutes):
        """
        End a conversation and update stats (ARRAY-BASED SCHEMA)

        Args:
            user_id: Parent user ID
            conversation_id: Conversation ID
            duration_minutes: Duration in minutes
        """
        if not self.is_available():
            print("[WARNING] Firestore not available, skipping conversation end")
            return

        try:
            # Get conversation ref
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id)

            # Get conversation data
            conv_doc = conversation_ref.get()
            if not conv_doc.exists:
                print(f"[ERROR] Conversation {conversation_id} not found")
                return

            conv_data = conv_doc.to_dict()
            child_id = conv_data.get("childId")

            # Get messages from array
            messages = conv_data.get("messages", [])

            # Use messageCount from conversation document (already accurate)
            total_message_count = conv_data.get("messageCount", len(messages))

            # Update conversation status with both duration fields
            conversation_ref.update({
                "status": "ended",
                "endTime": firestore.SERVER_TIMESTAMP,
                "duration": duration_minutes,  # Legacy field
                "durationMinutes": duration_minutes,
                "messageCount": total_message_count,
            })

            # Trigger AI title generation asynchronously
            import threading
            threading.Thread(
                target=self._generate_ai_title,
                args=(user_id, conversation_id, messages),
                daemon=True
            ).start()

            # Trigger knowledge graph extraction asynchronously
            if total_message_count >= 4:  # Only extract if meaningful conversation
                threading.Thread(
                    target=self._extract_knowledge_graph,
                    args=(user_id, conversation_id, child_id, messages),
                    daemon=True
                ).start()

            # Update user stats
            self._update_user_stats(user_id, child_id, conversation_id, duration_minutes)

            print(f"[INFO] Ended conversation {conversation_id}, duration: {duration_minutes}m, {total_message_count} messages")

        except Exception as e:
            print(f"[ERROR] Failed to end conversation: {e}")

    # ==================== STATS OPERATIONS ====================

    def _update_user_stats(self, user_id, child_id, conversation_id, duration_minutes):
        """Update user statistics after conversation ends (ARRAY-BASED SCHEMA)"""
        try:
            user_ref = self.db.collection("users").document(user_id)

            # NEW PATH: conversations directly under user
            conversation_ref = user_ref.collection("conversations").document(conversation_id)

            # Get conversation to check if flagged
            conv_doc = conversation_ref.get()
            if not conv_doc.exists:
                print(f"[WARNING] Conversation {conversation_id} not found for stats update")
                return

            conversation = conv_doc.to_dict()
            is_flagged = conversation.get("flagged", False)

            # Increment stats
            user_ref.update({
                "stats.totalConversations": firestore.Increment(1),
                "stats.totalConversationDurationSec": firestore.Increment(duration_minutes * 60),
                "stats.lastConversationAt": firestore.SERVER_TIMESTAMP,
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

    def _generate_ai_title(self, user_id, conversation_id, messages):
        """
        Generate AI-powered conversation title using GPT-4o-mini

        Args:
            user_id: Parent user ID
            conversation_id: Conversation ID
            messages: List of message dicts from array

        Returns:
            str: Generated title
        """
        try:
            from openai import OpenAI
            import os

            if not messages:
                title = "Empty Conversation"
            else:
                # Build context from first 10 messages
                message_context = "\n".join([
                    f"{msg.get('sender', 'unknown')}: {msg.get('content', '')}"
                    for msg in messages[:10]
                ])

                # Call GPT for title generation
                client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                prompt = f"""Generate a brief 2-4 word title for this conversation between a child and Luna (AI toy).

Conversation:
{message_context}

Requirements:
- 2-4 words maximum
- Capture main topic or theme
- Use title case
- Be specific and descriptive
- Examples: "Dinosaur Adventure", "Bedtime Story", "Math Practice"

Title:"""

                response = client.chat.completions.create(
                    model="gpt-4o-mini",  # Cheaper, faster model for titles
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=20,
                    temperature=0.7
                )

                title = response.choices[0].message.content.strip()

            # Update conversation with AI title
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id)

            conversation_ref.update({
                "title": title,
                "titleGeneratedAt": firestore.SERVER_TIMESTAMP
            })

            print(f"[INFO] AI title generated for {conversation_id}: '{title}'")
            return title

        except Exception as e:
            print(f"[ERROR] AI title generation failed: {e}")
            # Fallback to simple title extraction
            return self._generate_simple_title(messages)

    def _generate_simple_title(self, messages):
        """
        Fallback: Generate simple title from first child message

        Args:
            messages: List of message dicts from array

        Returns:
            str: Generated title (2 words max)
        """
        if not messages:
            return "Empty Chat"

        # Get first child message (skip toy responses)
        first_child_message = None
        for msg in messages:
            if msg.get('sender') == 'child':
                first_child_message = msg.get('content', '')
                break

        if not first_child_message:
            return "Quick Chat"

        # Clean the message
        title = first_child_message.strip()

        # Remove common filler words at the start
        filler_words = ['um', 'uh', 'well', 'so', 'like', 'hey', 'hi', 'hello']
        words = title.split()

        # Filter out filler words
        words = [w for w in words if w.lower() not in filler_words]

        if not words:
            return "Luno Chat"

        # Take only first 2 meaningful words
        words = words[:2]
        title = ' '.join(words)

        # Capitalize each word
        title = ' '.join(word.capitalize() for word in title.split())

        return title

    def _extract_knowledge_graph(self, user_id, conversation_id, child_id, messages):
        """
        Extract knowledge graph from conversation (background thread)

        Args:
            user_id: Parent user ID
            conversation_id: Conversation ID
            child_id: Child ID
            messages: List of message dicts from conversation
        """
        try:
            # Avoid circular import by importing here
            from knowledge_graph_service import knowledge_graph_service

            logger.info(f"[KG] Starting knowledge extraction for conversation {conversation_id}")

            knowledge_graph_service.extract_and_store(
                user_id=user_id,
                conversation_id=conversation_id,
                child_id=child_id,
                messages=messages
            )

            logger.info(f"[KG] Knowledge extraction completed for conversation {conversation_id}")

        except Exception as e:
            logger.error(f"[KG] Knowledge extraction failed for {conversation_id}: {e}", exc_info=True)
            # Don't crash - extraction is non-critical, conversation already ended successfully

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
                    "deviceId": toy_id,  # Same as document ID
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
                    "wifiNetwork": "Simulator-Network",
                    "wifiSSID": "Simulator-Network",  # Duplicate of wifiNetwork per schema
                    "wifiConnected": True
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

    # ==================== QUERY OPERATIONS ====================

    def get_conversation(self, user_id, conversation_id):
        """Get a specific conversation (UNIFIED SCHEMA)"""
        if not self.is_available():
            return None

        try:
            # NEW LOCATION: conversations directly under user
            conversation_ref = self.db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id)

            conversation_doc = conversation_ref.get()
            if conversation_doc.exists:
                return conversation_doc.to_dict()
            return None

        except Exception as e:
            print(f"[ERROR] Failed to get conversation: {e}")
            return None

    def get_conversation_messages(self, user_id, conversation_id, limit=100):
        """
        Get messages for a conversation (ARRAY-BASED SCHEMA)

        Args:
            user_id: Parent user ID
            conversation_id: Conversation ID
            limit: Maximum number of messages to return (default: 100)

        Returns:
            List of message dicts from the messages array
        """
        if not self.is_available():
            return []

        try:
            # Get conversation document
            conv_ref = self.db.collection("users").document(user_id)\
                .collection("conversations").document(conversation_id)

            conv_doc = conv_ref.get()
            if not conv_doc.exists:
                print(f"[ERROR] Conversation {conversation_id} not found")
                return []

            conv_data = conv_doc.to_dict()
            messages = conv_data.get("messages", [])

            # Apply limit (keep most recent messages)
            if len(messages) > limit:
                messages = messages[-limit:]

            # Add index as ID for compatibility
            for idx, msg in enumerate(messages):
                if "id" not in msg:
                    msg["id"] = f"msg_{idx}"

            return messages

        except Exception as e:
            print(f"[ERROR] Failed to get conversation messages: {e}")
            return []

    def get_child_conversations(self, user_id, child_id, limit=50):
        """Get recent conversations for a child (UNIFIED SCHEMA)"""
        if not self.is_available():
            return []

        try:
            # NEW QUERY: Filter by childId at user level
            conversations_ref = self.db.collection("users").document(user_id)\
                .collection("conversations")\
                .where("childId", "==", child_id)\
                .order_by("startTime", direction=firestore.Query.DESCENDING)\
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

    def get_active_conversations(self, user_id, limit=20):
        """Get all active conversations across all children (NEW METHOD)"""
        if not self.is_available():
            return []

        try:
            # Collection-group query for active conversations
            conversations_ref = self.db.collection_group("conversations")\
                .where("status", "==", "active")\
                .order_by("lastActivityAt", direction=firestore.Query.DESCENDING)\
                .limit(limit)

            conversations = []
            for doc in conversations_ref.stream():
                conv_data = doc.to_dict()
                conv_data["id"] = doc.id
                # Filter to only this user's conversations
                if doc.reference.parent.parent.id == user_id:
                    conversations.append(conv_data)

            return conversations

        except Exception as e:
            print(f"[ERROR] Failed to get active conversations: {e}")
            return []

    def get_flagged_conversations(self, user_id, limit=50):
        """Get all flagged conversations (NEW METHOD)"""
        if not self.is_available():
            return []

        try:
            # Collection-group query for flagged conversations
            conversations_ref = self.db.collection_group("conversations")\
                .where("flagged", "==", True)\
                .where("flagStatus", "==", "unreviewed")\
                .order_by("startTime", direction=firestore.Query.DESCENDING)\
                .limit(limit)

            conversations = []
            for doc in conversations_ref.stream():
                conv_data = doc.to_dict()
                conv_data["id"] = doc.id
                # Filter to only this user's conversations
                if doc.reference.parent.parent.id == user_id:
                    conversations.append(conv_data)

            return conversations

        except Exception as e:
            print(f"[ERROR] Failed to get flagged conversations: {e}")
            return []

    def get_active_conversation_for_toy(self, user_id, toy_id):
        """Get active conversation for a specific toy/device (NEW METHOD - replaces session lookup)"""
        if not self.is_available():
            return None

        try:
            # Query for active conversation with this toyId
            conversations_ref = self.db.collection("users").document(user_id)\
                .collection("conversations")\
                .where("toyId", "==", toy_id)\
                .where("status", "==", "active")\
                .limit(1)

            conversations = list(conversations_ref.stream())
            if conversations:
                conv_data = conversations[0].to_dict()
                conv_data["id"] = conversations[0].id
                return conv_data

            return None

        except Exception as e:
            print(f"[ERROR] Failed to get active conversation for toy: {e}")
            return None

    def get_active_conversation_for_child(self, user_id, child_id):
        """Get active conversation for a specific child (one conversation per child at a time)"""
        if not self.is_available():
            return None

        try:
            # Query for active conversation with this childId
            conversations_ref = self.db.collection("users").document(user_id)\
                .collection("conversations")\
                .where("childId", "==", child_id)\
                .where("status", "==", "active")\
                .limit(1)

            conversations = list(conversations_ref.stream())
            if conversations:
                conv_data = conversations[0].to_dict()
                conv_data["id"] = conversations[0].id
                return conv_data

            return None

        except Exception as e:
            print(f"[ERROR] Failed to get active conversation for child: {e}")
            return None

    # ==================== SESSION OPERATIONS (REMOVED - NOW USING UNIFIED CONVERSATIONS) ====================
    # All session methods removed - conversations collection now handles both session + conversation data


# Global service instance
firestore_service = FirestoreService()
