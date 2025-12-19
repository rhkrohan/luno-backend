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
        self.INACTIVITY_TIMEOUT_SECONDS = int(os.getenv("SESSION_INACTIVITY_TIMEOUT", 300))  # Default 2 min (for testing)
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
            print(f"[INFO] Using cached session: {cached_session_id}")
            return self.ACTIVE_CONVERSATIONS[cached_session_id]

        # Step 2: Query Firestore for active session
        firestore_session = self.fs.get_active_session(device_id, user_id)

        if firestore_session:
            session_id = firestore_session.get('id') or firestore_session.get('sessionId')

            # Step 3: Validate session
            # Check if session created before server start (stale after restart)
            created_at = firestore_session.get('createdAt')
            if created_at:
                # Convert Firestore timestamp to Python timestamp
                if hasattr(created_at, 'timestamp'):
                    created_timestamp = created_at.timestamp()
                else:
                    created_timestamp = created_at

                if created_timestamp < SERVER_START_TIME:
                    print(f"[INFO] Detected stale session after restart: {session_id}")
                    self.end_session(session_id, user_id, reason="server_restart")
                    # Falls through to create new session
                else:
                    # Check if session expired due to inactivity
                    last_activity = firestore_session.get('lastActivityAt')
                    if last_activity:
                        if hasattr(last_activity, 'timestamp'):
                            last_activity_timestamp = last_activity.timestamp()
                        else:
                            last_activity_timestamp = last_activity

                        time_since_activity = time.time() - last_activity_timestamp

                        if time_since_activity > self.INACTIVITY_TIMEOUT_SECONDS:
                            print(f"[INFO] Session {session_id} expired due to inactivity ({int(time_since_activity)}s)")
                            self.end_session(session_id, user_id, reason="inactivity_timeout")
                            # Falls through to create new session
                        else:
                            # Valid session, load into memory
                            print(f"[INFO] Loaded existing session from Firestore: {session_id}")
                            return self._load_session_into_memory(firestore_session)

        # Step 4: No valid session exists, create new one
        return self._create_new_session(device_id, user_id, child_id, toy_id)

    def _load_session_into_memory(self, firestore_session):
        """
        Load session from Firestore into in-memory cache

        Args:
            firestore_session: Session document from Firestore

        Returns:
            dict: Session data
        """
        session_id = firestore_session.get('id') or firestore_session.get('sessionId')

        session_data = {
            'session_id': session_id,
            'conversation_id': firestore_session.get('conversationId'),
            'user_id': firestore_session.get('userId'),
            'child_id': firestore_session.get('childId'),
            'toy_id': firestore_session.get('toyId'),
            'device_id': firestore_session.get('deviceId'),
            'start_time': firestore_session.get('createdAt').timestamp() if hasattr(firestore_session.get('createdAt'), 'timestamp') else firestore_session.get('createdAt'),
            'message_count': firestore_session.get('messageCount', 0),
        }

        self.ACTIVE_CONVERSATIONS[session_id] = session_data
        return session_data

    def _create_new_session(self, device_id, user_id, child_id=None, toy_id=None):
        """
        Create new session and conversation

        Args:
            device_id: Device/toy ID
            user_id: User ID
            child_id: Optional child ID
            toy_id: Optional toy ID

        Returns:
            dict: New session data
        """
        # Generate session ID
        session_id = self.generate_session_id(device_id, user_id)

        # Create conversation in Firestore
        conversation_id = self.fs.create_conversation(
            user_id=user_id,
            child_id=child_id,
            toy_id=toy_id or device_id,
            conversation_type="conversation"
        )

        if not conversation_id:
            print(f"[ERROR] Failed to create conversation for session {session_id}")
            return None

        # Create session in Firestore
        self.fs.create_session(
            session_id=session_id,
            user_id=user_id,
            device_id=device_id,
            child_id=child_id,
            toy_id=toy_id,
            conversation_id=conversation_id
        )

        # Store in memory (thread-safe)
        session_data = {
            'session_id': session_id,
            'conversation_id': conversation_id,
            'user_id': user_id,
            'child_id': child_id,
            'toy_id': toy_id,
            'device_id': device_id,
            'start_time': time.time(),
            'message_count': 0,
        }

        with self._lock:
            self.ACTIVE_CONVERSATIONS[session_id] = session_data

        print(f"[INFO] Created new session: {session_id} with conversation: {conversation_id}")
        return session_data

    def update_session_activity(self, session_id, user_id):
        """
        Update session activity timestamp

        Args:
            session_id: Session ID
            user_id: User ID
        """
        # Update in-memory cache
        if session_id in self.ACTIVE_CONVERSATIONS:
            self.ACTIVE_CONVERSATIONS[session_id]['message_count'] += 1
            message_count = self.ACTIVE_CONVERSATIONS[session_id]['message_count']
        else:
            message_count = None

        # Update Firestore
        self.fs.update_session_activity(user_id, session_id, message_count)

    def end_session(self, session_id, user_id, reason="explicit"):
        """
        End session and cleanup

        Args:
            session_id: Session ID
            user_id: User ID
            reason: Reason for ending (explicit, inactivity_timeout, server_restart, etc.)
        """
        # Get session data for conversation cleanup
        session_data = self.ACTIVE_CONVERSATIONS.get(session_id)

        if session_data:
            conversation_id = session_data.get('conversation_id')
            child_id = session_data.get('child_id')
            start_time = session_data.get('start_time')

            # Calculate duration (in minutes, rounded)
            duration_seconds = time.time() - start_time
            duration_minutes = round(duration_seconds / 60)

            # End conversation in Firestore
            if conversation_id:
                self.fs.end_conversation(
                    user_id=user_id,
                    child_id=child_id,
                    conversation_id=conversation_id,
                    duration_minutes=duration_minutes
                )

            # Remove from memory (thread-safe)
            with self._lock:
                del self.ACTIVE_CONVERSATIONS[session_id]

            print(f"[INFO] Ended session {session_id}, duration: {duration_minutes}m, reason: {reason}")

        # End session in Firestore
        self.fs.end_session(user_id, session_id, reason)

        # Clear conversation history from gpt_reply.py
        try:
            from gpt_reply import clear_session_history
            clear_session_history(session_id)
        except Exception as e:
            print(f"[WARN] Could not clear session history: {e}")

    def is_session_expired(self, session_id, user_id):
        """
        Check if session has expired due to inactivity

        Args:
            session_id: Session ID
            user_id: User ID

        Returns:
            bool: True if expired, False otherwise
        """
        # Get session from Firestore
        session = self.fs.get_session(user_id, session_id)

        if not session:
            return True  # Session doesn't exist, consider expired

        if session.get('status') != 'active':
            return True  # Not active, consider expired

        # Check last activity
        last_activity = session.get('lastActivityAt')
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
        Find orphaned sessions in Firestore that aren't in memory

        Scans Firestore for expired active sessions that are not currently
        in the ACTIVE_CONVERSATIONS cache and ends them.
        """
        try:
            cutoff_time = datetime.now() - timedelta(seconds=self.INACTIVITY_TIMEOUT_SECONDS)

            # Query all expired active sessions across all users
            expired_sessions = self.fs.db.collection_group("sessions")\
                .where("status", "==", "active")\
                .where("lastActivityAt", "<", cutoff_time)\
                .stream()

            orphaned_count = 0
            for session_doc in expired_sessions:
                session_data = session_doc.to_dict()
                session_id = session_data.get('sessionId')
                user_id = session_data.get('userId')

                # Check if in memory (thread-safe)
                with self._lock:
                    in_memory = session_id in self.ACTIVE_CONVERSATIONS

                if not in_memory:
                    print(f"[CLEANUP] Found orphaned session: {session_id}")
                    self.end_session(session_id, user_id, reason="orphaned")
                    orphaned_count += 1

            if orphaned_count > 0:
                print(f"[CLEANUP] Cleaned up {orphaned_count} orphaned session(s)")

        except Exception as e:
            print(f"[ERROR] Orphan cleanup failed: {e}")

    def get_active_session_id(self, device_id, user_id):
        """
        Get active session ID for device-user pair

        Args:
            device_id: Device ID
            user_id: User ID

        Returns:
            str: Session ID or None
        """
        # Check in-memory first
        for session_id, data in self.ACTIVE_CONVERSATIONS.items():
            if data.get('device_id') == device_id and data.get('user_id') == user_id:
                return session_id

        # Check Firestore
        session = self.fs.get_active_session(device_id, user_id)
        if session:
            return session.get('id') or session.get('sessionId')

        return None
