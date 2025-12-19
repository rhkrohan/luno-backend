import os
import time
import threading
from datetime import datetime, timedelta

# Server start time for restart detection
SERVER_START_TIME = time.time()

class SessionManager:
    def __init__(self, firestore_service):
        """
        Initialize session manager

        Args:
            firestore_service: FirestoreService instance for database operations
        """
        self.fs = firestore_service
        self._lock = threading.Lock()  # Thread safety for ACTIVE_CONVERSATIONS
        self.INACTIVITY_TIMEOUT_SECONDS = int(os.getenv("SESSION_INACTIVITY_TIMEOUT", 120))  # Default 2 minutes (reasonable for conversations)
        self.ACTIVE_CONVERSATIONS = {}  # In-memory cache: session_id -> session_data

        print(f"[INFO] SessionManager initialized with {self.INACTIVITY_TIMEOUT_SECONDS}s inactivity timeout")

    def generate_session_id(self, device_id, user_id):
        """
        Generate unique session ID

        Args:
            device_id: Device/toy ID
            user_id: User ID

        Returns:
            session_id: Format {device_id}_{user_id}_{timestamp_ms}
        """
        timestamp_ms = int(time.time() * 1000)
        session_id = f"{device_id}_{user_id}_{timestamp_ms}"
        return session_id

    def get_or_create_session(self, device_id, user_id, child_id=None, toy_id=None):
        """
        Get existing active session or create new one

        This implements the full session lifecycle:
        1. Check in-memory cache
        2. Query Firestore for active session
        3. Validate session (not expired, not pre-restart)
        4. End old session if needed
        5. Create new session if needed

        Args:
            device_id: Device/toy ID
            user_id: User ID
            child_id: Optional child ID
            toy_id: Optional toy ID

        Returns:
            dict: {
                'session_id': str,
                'conversation_id': str,
                'user_id': str,
                'child_id': str,
                'toy_id': str,
                'start_time': float
            }
        """
        # Step 1: Check in-memory cache (thread-safe)
        # Look for any active session for this device-user pair in memory
        with self._lock:
            cached_session_id = None
            for sid, data in self.ACTIVE_CONVERSATIONS.items():
                if data.get('device_id') == device_id and data.get('user_id') == user_id:
                    cached_session_id = sid
                    break

        if cached_session_id:
            # BUGFIX: Check if cached session has expired
            cached_session = self.ACTIVE_CONVERSATIONS[cached_session_id]
            last_activity = cached_session.get('last_activity', cached_session.get('start_time'))
            time_since_activity = time.time() - last_activity

            if time_since_activity > self.INACTIVITY_TIMEOUT_SECONDS:
                print(f"[INFO] Cached session {cached_session_id} expired due to inactivity ({int(time_since_activity)}s)")
                self.end_session(cached_session_id, user_id, reason="inactivity_timeout")
                # Falls through to create new session
            else:
                print(f"[INFO] Using cached session: {cached_session_id} (active for {int(time_since_activity)}s)")
                return cached_session

        # Step 2: Query Firestore for active conversation (replaces session)
        firestore_session = self.fs.get_active_conversation_for_toy(user_id, device_id)

        if firestore_session:
            conversation_id = firestore_session.get('id')

            # Step 3: Validate conversation (replaces session validation)
            # Check if conversation created before server start (stale after restart)
            start_time = firestore_session.get('startTime')
            if start_time:
                # Convert Firestore timestamp to Python timestamp
                if hasattr(start_time, 'timestamp'):
                    created_timestamp = start_time.timestamp()
                else:
                    created_timestamp = start_time

                if created_timestamp < SERVER_START_TIME:
                    print(f"[INFO] Detected stale conversation after restart: {conversation_id}")
                    self.end_session(conversation_id, user_id, reason="server_restart")
                    # Falls through to create new conversation
                else:
                    # Check if conversation expired due to inactivity
                    last_activity = firestore_session.get('lastActivityAt')
                    if last_activity:
                        if hasattr(last_activity, 'timestamp'):
                            last_activity_timestamp = last_activity.timestamp()
                        else:
                            last_activity_timestamp = last_activity

                        time_since_activity = time.time() - last_activity_timestamp

                        if time_since_activity > self.INACTIVITY_TIMEOUT_SECONDS:
                            print(f"[INFO] Conversation {conversation_id} expired due to inactivity ({int(time_since_activity)}s)")
                            self.end_session(conversation_id, user_id, reason="inactivity_timeout")
                            # Falls through to create new conversation
                        else:
                            # Valid conversation, load into memory
                            print(f"[INFO] Loaded existing conversation from Firestore: {conversation_id}")
                            # Add user_id since it's not in conversation document
                            firestore_session['userId'] = user_id
                            return self._load_session_into_memory(firestore_session)

        # Step 4: No valid session exists, create new one
        return self._create_new_session(device_id, user_id, child_id, toy_id)

    def _load_session_into_memory(self, firestore_session):
        """
        Load conversation from Firestore into in-memory cache (unified schema)

        Args:
            firestore_session: Conversation document from Firestore

        Returns:
            dict: Session data
        """
        conversation_id = firestore_session.get('id')

        # Get timestamps
        start_time_ts = firestore_session.get('startTime')
        last_activity_ts = firestore_session.get('lastActivityAt')

        # Convert Firestore timestamps to Python timestamps
        start_time = start_time_ts.timestamp() if hasattr(start_time_ts, 'timestamp') else start_time_ts
        last_activity = last_activity_ts.timestamp() if hasattr(last_activity_ts, 'timestamp') else (start_time if last_activity_ts is None else last_activity_ts)

        session_data = {
            'session_id': conversation_id,  # session_id = conversation_id
            'conversation_id': conversation_id,
            'user_id': firestore_session.get('userId'),  # Not in new schema, need to get from parent
            'child_id': firestore_session.get('childId'),
            'toy_id': firestore_session.get('toyId'),
            'start_time': start_time,
            'last_activity': last_activity,
            'message_count': firestore_session.get('messageCount', 0),
        }

        self.ACTIVE_CONVERSATIONS[conversation_id] = session_data
        return session_data

    def _create_new_session(self, device_id, user_id, child_id=None, toy_id=None):
        """
        Create new session (now using unified conversation schema)

        Args:
            device_id: Device/toy ID (same as toy_id)
            user_id: User ID
            child_id: Optional child ID
            toy_id: Optional toy ID

        Returns:
            dict: New session data
        """
        # toyId and deviceId are the same - use toyId
        toy_id = toy_id or device_id

        # Create conversation in Firestore (unified schema - replaces both session + conversation)
        conversation_id = self.fs.create_conversation(
            user_id=user_id,
            child_id=child_id,
            toy_id=toy_id,
            conversation_type="conversation"
        )

        if not conversation_id:
            print(f"[ERROR] Failed to create conversation")
            return None

        # Store in memory (thread-safe)
        current_time = time.time()
        session_data = {
            'session_id': conversation_id,  # session_id = conversation_id now
            'conversation_id': conversation_id,
            'user_id': user_id,
            'child_id': child_id,
            'toy_id': toy_id,
            'start_time': current_time,
            'last_activity': current_time,
            'message_count': 0,
        }

        with self._lock:
            self.ACTIVE_CONVERSATIONS[conversation_id] = session_data

        print(f"[INFO] Created new conversation: {conversation_id} (status: active)")
        return session_data

    def update_session_activity(self, session_id, user_id):
        """
        Update conversation activity timestamp (replaces session activity update)

        Args:
            session_id: Session ID (conversation_id)
            user_id: User ID
        """
        # Update in-memory cache
        current_time = time.time()
        if session_id in self.ACTIVE_CONVERSATIONS:
            self.ACTIVE_CONVERSATIONS[session_id]['message_count'] += 1
            self.ACTIVE_CONVERSATIONS[session_id]['last_activity'] = current_time

        # Note: Firestore lastActivityAt is updated by batch writes in add_message_batch
        # So we don't need a separate update here anymore

    def end_session(self, session_id, user_id, reason="explicit"):
        """
        End conversation (replaces end_session)

        Args:
            session_id: Session ID (conversation_id)
            user_id: User ID
            reason: Reason for ending (explicit, inactivity_timeout, server_restart, etc.)
        """
        # Get session data for conversation cleanup
        session_data = self.ACTIVE_CONVERSATIONS.get(session_id)

        if session_data:
            conversation_id = session_data.get('conversation_id')
            start_time = session_data.get('start_time')

            # Calculate duration (in minutes, rounded)
            duration_seconds = time.time() - start_time
            duration_minutes = round(duration_seconds / 60)

            # End conversation in Firestore (unified schema)
            if conversation_id:
                self.fs.end_conversation(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    duration_minutes=duration_minutes
                )

            # Remove from memory (thread-safe)
            with self._lock:
                del self.ACTIVE_CONVERSATIONS[session_id]

            print(f"[INFO] Ended conversation {session_id}, duration: {duration_minutes}m, reason: {reason}")

        # Clear conversation history from gpt_reply.py
        try:
            from gpt_reply import clear_session_history
            clear_session_history(session_id)
        except Exception as e:
            print(f"[WARN] Could not clear session history: {e}")

    def is_session_expired(self, session_id, user_id):
        """
        Check if conversation has expired due to inactivity (replaces session expiration check)

        Args:
            session_id: Session ID (conversation_id)
            user_id: User ID

        Returns:
            bool: True if expired, False otherwise
        """
        # Get conversation from Firestore
        conversation = self.fs.get_conversation(user_id, session_id)

        if not conversation:
            return True  # Conversation doesn't exist, consider expired

        if conversation.get('status') != 'active':
            return True  # Not active, consider expired

        # Check last activity
        last_activity = conversation.get('lastActivityAt')
        if last_activity:
            if hasattr(last_activity, 'timestamp'):
                last_activity_timestamp = last_activity.timestamp()
            else:
                last_activity_timestamp = last_activity

            time_since_activity = time.time() - last_activity_timestamp

            if time_since_activity > self.INACTIVITY_TIMEOUT_SECONDS:
                return True

        return False

    def cleanup_expired_sessions(self):
        """
        Background task to cleanup expired sessions

        Queries Firestore for active sessions that have expired
        and marks them as expired.
        """
        print("[INFO] Running session cleanup task...")

        try:
            # Check in-memory sessions (thread-safe)
            expired_sessions = []

            with self._lock:
                for session_id, session_data in list(self.ACTIVE_CONVERSATIONS.items()):
                    user_id = session_data.get('user_id')
                    if self.is_session_expired(session_id, user_id):
                        expired_sessions.append((session_id, user_id))

            # End expired sessions
            for session_id, user_id in expired_sessions:
                print(f"[INFO] Cleanup: Ending expired session {session_id}")
                self.end_session(session_id, user_id, reason="cleanup_expired")

            if expired_sessions:
                print(f"[INFO] Cleaned up {len(expired_sessions)} expired session(s)")
            else:
                print("[INFO] No expired sessions found")

            # Also check for orphaned sessions in Firestore
            self.cleanup_firestore_orphans()

        except Exception as e:
            print(f"[ERROR] Session cleanup failed: {e}")

    def cleanup_firestore_orphans(self):
        """
        Find orphaned conversations in Firestore that aren't in memory

        Scans Firestore for expired active conversations that are not currently
        in the ACTIVE_CONVERSATIONS cache and ends them.
        """
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.INACTIVITY_TIMEOUT_SECONDS)

            # Query all expired active conversations across all users (unified schema)
            expired_conversations = self.fs.db.collection_group("conversations")\
                .where("status", "==", "active")\
                .where("lastActivityAt", "<", cutoff_time)\
                .stream()

            orphaned_count = 0
            for conv_doc in expired_conversations:
                conv_data = conv_doc.to_dict()
                conversation_id = conv_doc.id
                # Get user_id from parent document
                user_id = conv_doc.reference.parent.parent.id

                # Check if in memory (thread-safe)
                with self._lock:
                    in_memory = conversation_id in self.ACTIVE_CONVERSATIONS

                if not in_memory:
                    print(f"[CLEANUP] Found orphaned conversation: {conversation_id}")
                    self.end_session(conversation_id, user_id, reason="orphaned")
                    orphaned_count += 1

            if orphaned_count > 0:
                print(f"[CLEANUP] Cleaned up {orphaned_count} orphaned conversation(s)")

        except Exception as e:
            print(f"[ERROR] Orphan cleanup failed: {e}")

    def get_active_session_id(self, device_id, user_id):
        """
        Get active conversation ID for device-user pair (replaces session lookup)

        Args:
            device_id: Device ID (same as toy_id)
            user_id: User ID

        Returns:
            str: Conversation ID or None
        """
        # Check in-memory first
        for conversation_id, data in self.ACTIVE_CONVERSATIONS.items():
            if data.get('toy_id') == device_id and data.get('user_id') == user_id:
                return conversation_id

        # Check Firestore (unified schema)
        conversation = self.fs.get_active_conversation_for_toy(user_id, device_id)
        if conversation:
            return conversation.get('id')

        return None
