# 🔄 Session Management System

Complete guide to the backend-managed session system.

---

## Overview

As of the latest update, **session management is fully handled by the backend**. ESP32 devices no longer need to generate or track session IDs - the backend automatically creates and manages sessions based on device and user identifiers.

### Key Features

- ✅ **Backend-Generated Sessions** - Automatic session ID creation
- ✅ **One Session Per Device-User** - New conversations auto-end previous ones
- ✅ **Firestore Persistence** - All sessions stored in database
- ✅ **Automatic Cleanup** - 30-minute inactivity timeout
- ✅ **Server Restart Handling** - Stale sessions automatically ended
- ✅ **Backward Compatible** - Gracefully ignores ESP32-sent session IDs

---

## Architecture

### Session ID Format

```
{device_id}_{user_id}_{timestamp_ms}
```

**Example:** `TOY123_user456_1734345600000`

### Components

```
┌─────────────────┐
│   ESP32 Device  │
└────────┬────────┘
         │ HTTP Request (no session ID needed)
         │ Headers:
         │ ├─ X-Device-ID: TOY123
         │ └─ X-User-ID: user456
         ▼
┌─────────────────┐
│ Session Manager │
│   (Backend)     │
└────────┬────────┘
         │
         ├─ 1. Check for active session (device+user)
         ├─ 2. If none, create new session
         ├─ 3. If exists and valid, reuse
         ├─ 4. If expired, end old & create new
         │
         ▼
┌─────────────────┐
│   Firestore     │
│ users/{userId}/ │
│  sessions/      │
│   {sessionId}   │
└─────────────────┘
```

---

## Session Lifecycle

### 1. Session Creation

**Trigger:** First request from a device-user pair

**Process:**
```python
# Backend automatically:
1. Generates session_id = f"{device_id}_{user_id}_{timestamp_ms}"
2. Creates conversation in Firestore
3. Creates session document:
   {
     "sessionId": "TOY123_user456_1734345600000",
     "deviceId": "TOY123",
     "userId": "user456",
     "childId": "child789",
     "conversationId": "conv_abc123",
     "status": "active",
     "createdAt": timestamp,
     "lastActivityAt": timestamp,
     "messageCount": 0
   }
4. Stores in memory for fast access
```

**ESP32 Action:** None required - just send audio/text as normal

### 2. Session Reuse

**Trigger:** Subsequent requests within 30 minutes

**Process:**
```python
# Backend checks:
1. Is there an active session for this device+user?
2. If yes and not expired → reuse existing session
3. Update lastActivityAt timestamp
4. Increment messageCount
```

**ESP32 Action:** None - backend handles automatically

### 3. Session Expiration

**Trigger:** 30 minutes of inactivity OR explicit end request

**Process:**
```python
# Backend detects:
1. lastActivityAt + 30 minutes < now?
2. If expired:
   - Mark session as "expired"
   - End associated conversation
   - Clear from memory
3. Next request creates new session
```

**Cleanup Methods:**
- **On-demand**: Checked during `get_or_create_session()`
- **Background**: Thread runs every 10 minutes
- **Manual**: Via `/api/conversations/end` endpoint

### 4. Session End (Explicit)

**Trigger:** ESP32 calls `/api/conversations/end` or inactivity timeout

**Process:**
```python
# Backend:
1. Calculates conversation duration
2. Updates conversation with end time
3. Marks session as "ended"
4. Updates user stats
5. Clears in-memory history
```

**ESP32 Action:** Optional - can call endpoint when conversation ends

---

## Firestore Schema

### Session Document

**Location:** `users/{userId}/sessions/{sessionId}`

```javascript
{
  // Identity
  "sessionId": "TOY123_user456_1734345600000",
  "deviceId": "TOY123",
  "userId": "user456",
  "childId": "child789",
  "toyId": "TOY123",

  // Linking
  "conversationId": "conv_abc123",  // Links to conversation

  // Status
  "status": "active" | "ended" | "expired",

  // Timestamps
  "createdAt": Timestamp,
  "lastActivityAt": Timestamp,
  "endedAt": Timestamp | null,

  // Metrics
  "messageCount": 12,

  // Optional
  "endReason": "explicit" | "inactivity_timeout" | "server_restart"
}
```

### Queries

```python
# Get active session for device-user pair
sessions_ref.where("deviceId", "==", "TOY123")\
            .where("userId", "==", "user456")\
            .where("status", "==", "active")\
            .limit(1)

# Find expired sessions
sessions_ref.where("status", "==", "active")\
            .where("lastActivityAt", "<", threshold)
```

---

## ESP32 Integration

### What Changed

**Before (Old System):**
```cpp
// ESP32 had to generate and track session IDs
String sessionId = generateSessionId();

http.addHeader("X-Session-ID", sessionId);  // Required
```

**After (New System):**
```cpp
// No session ID needed - backend handles it!
http.addHeader("X-Device-ID", deviceId);
http.addHeader("X-User-ID", userId);
// Backend auto-creates/manages session
```

### Updated Code Example

```cpp
void sendAudioToBackend(uint8_t* audioData, size_t audioLength) {
  HTTPClient http;
  http.begin("http://your-server.com:5005/upload");

  // Required headers (NO session ID needed)
  http.addHeader("Content-Type", "audio/adpcm");
  http.addHeader("X-Audio-Format", "adpcm");
  http.addHeader("X-Device-ID", deviceId);        // Backend uses this
  http.addHeader("X-User-Email", userEmail);      // Or X-User-ID
  http.addHeader("X-Child-ID", activeChildId);
  http.addHeader("X-Toy-ID", toyId);

  int httpCode = http.POST(audioData, audioLength);

  if (httpCode == 200) {
    // Process response audio
  }

  http.end();
}
```

### Ending Conversations

**Option 1: Let backend handle it (Recommended)**
```cpp
// Do nothing - backend auto-expires after 30 min inactivity
```

**Option 2: Explicit end (Optional)**
```cpp
void endConversation() {
  HTTPClient http;
  http.begin("http://your-server.com:5005/api/conversations/end");
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> doc;
  doc["device_id"] = deviceId;  // Backend looks up session
  doc["user_id"] = userId;

  String payload;
  serializeJson(doc, payload);

  http.POST(payload);
  http.end();
}
```

---

## Configuration

### Environment Variables

Add to `.env`:

```bash
# Session inactivity timeout (seconds)
SESSION_INACTIVITY_TIMEOUT=1800  # 30 minutes (default)
```

### Adjusting Timeout

```python
# Change in .env file
SESSION_INACTIVITY_TIMEOUT=900   # 15 minutes
SESSION_INACTIVITY_TIMEOUT=3600  # 60 minutes
```

---

## Backend Implementation Details

### SessionManager Class

**Location:** `session_manager.py`

**Key Methods:**

```python
class SessionManager:
    def __init__(self, firestore_service):
        self.INACTIVITY_TIMEOUT_SECONDS = 1800  # 30 min

    def get_or_create_session(device_id, user_id, child_id, toy_id):
        """
        Main entry point - handles full session lifecycle
        Returns session data with session_id and conversation_id
        """

    def update_session_activity(session_id, user_id):
        """Update lastActivityAt after each message"""

    def end_session(session_id, user_id, reason):
        """End session and cleanup"""

    def cleanup_expired_sessions():
        """Background task - runs every 10 minutes"""
```

### Server Restart Handling

```python
SERVER_START_TIME = time.time()

# On session lookup:
if session.createdAt < SERVER_START_TIME:
    # Session created before restart - end it
    end_session(session_id, user_id, reason="server_restart")
    # Create new session
```

---

## Monitoring & Debugging

### Check Active Sessions

```bash
# Query Firestore
firebase firestore:query \
  "users/{userId}/sessions" \
  --where status=active
```

### View Session in Logs

```python
# Backend logs show:
[INFO] SessionManager initialized with 1800s inactivity timeout
[INFO] Created new session: TOY123_user456_1734345600000 with conversation: conv_abc
[INFO] Using cached session: TOY123_user456_1734345600000
[INFO] Session TOY123_user456_1734345600000 expired due to inactivity (1850s)
[INFO] Ended session TOY123_user456_1734345600000, duration: 15m, reason: explicit
```

### Debug Session Issues

```python
# Check if session exists
from session_manager import session_manager

session_id = session_manager.get_active_session_id("TOY123", "user456")
print(f"Active session: {session_id}")

# Check session details
session = firestore_service.get_session("user456", session_id)
print(f"Session status: {session['status']}")
print(f"Last activity: {session['lastActivityAt']}")
```

---

## Migration from Old System

### Backward Compatibility

The system **gracefully handles ESP32 devices still sending X-Session-ID**:

```python
# In auth_middleware.py:
session_id = request.headers.get("X-Session-ID")
if session_id:
    print(f"[INFO] Ignoring ESP32-provided session ID: {session_id}")
    # Backend generates its own session ID
```

### Migration Steps

1. **Deploy Backend Update** - New session management goes live
2. **ESP32 Continues Working** - Old firmware still functional
3. **Update ESP32 Firmware** - Remove session ID generation
4. **Clean Up** - Remove X-Session-ID header from requests

**Timeline:** No breaking changes - update at your convenience

---

## Performance Characteristics

### Session Lookup Performance

```
First Request (New Session):
├─ Check in-memory: <1ms (cache miss)
├─ Query Firestore: ~50-100ms
├─ Create session: ~30ms
└─ Total: ~100-150ms

Subsequent Requests (Existing Session):
├─ Check in-memory: <1ms (cache hit)
└─ Total: <1ms

Expected Cache Hit Rate: >95%
```

### Memory Usage

```
Per Session: ~1KB
100 Active Sessions: ~100KB
Cleanup: Every 10 minutes
```

---

## Testing

### Test Session Creation

```bash
# Send first message
curl -X POST http://localhost:5005/text_upload \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: TEST_TOY" \
  -H "X-User-ID: test_user" \
  -H "X-Child-ID: test_child" \
  -d '{"text": "Hello"}' \
  --output test1.wav

# Check logs for: "Created new session: TEST_TOY_test_user_..."
```

### Test Session Reuse

```bash
# Send second message immediately
curl -X POST http://localhost:5005/text_upload \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: TEST_TOY" \
  -H "X-User-ID: test_user" \
  -H "X-Child-ID: test_child" \
  -d '{"text": "How are you?"}' \
  --output test2.wav

# Check logs for: "Using cached session: TEST_TOY_test_user_..."
```

### Test Session Expiration

```bash
# Wait 31 minutes, then send message
sleep 1860
curl -X POST http://localhost:5005/text_upload \
  -H "Content-Type: application/json" \
  -H "X-Device-ID: TEST_TOY" \
  -H "X-User-ID: test_user" \
  -H "X-Child-ID: test_child" \
  -d '{"text": "Still there?"}' \
  --output test3.wav

# Check logs for: "Session ... expired due to inactivity"
# Then: "Created new session: ..."
```

### Test Explicit End

```bash
# End session manually
curl -X POST http://localhost:5005/api/conversations/end \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "TEST_TOY",
    "user_id": "test_user"
  }'

# Check logs for: "Ended session ..., duration: Xm, reason: explicit"
```

---

## Troubleshooting

### Issue: Multiple sessions created for same device-user

**Symptom:** Each request creates a new conversation

**Cause:** Session not being found/reused

**Solution:**
- Check device_id and user_id are consistent across requests
- Verify session is being stored in Firestore
- Check backend logs for session lookup errors

### Issue: Sessions not expiring

**Symptom:** Old sessions remain active indefinitely

**Cause:** Background cleanup not running or sessions still receiving activity

**Solution:**
- Verify background cleanup thread started (check logs)
- Confirm lastActivityAt is being updated
- Check `SESSION_INACTIVITY_TIMEOUT` setting

### Issue: "No active session found" error

**Symptom:** `/api/conversations/end` returns 404

**Cause:** Session already ended or device-user mismatch

**Solution:**
- Verify device_id and user_id match session creation
- Check if session expired (>30 min since last activity)
- Look in Firestore for session with status "ended"

---

## Best Practices

### For ESP32 Developers

✅ **DO:**
- Send consistent device_id and user_id in all requests
- Let backend handle session management automatically
- Optionally call `/api/conversations/end` when appropriate

❌ **DON'T:**
- Generate or track session IDs on ESP32
- Send X-Session-ID header (ignored by backend)
- Worry about session expiration - backend handles it

### For Backend Developers

✅ **DO:**
- Always call `session_manager.update_session_activity()` after processing
- Use session_manager methods instead of direct Firestore access
- Monitor session counts to detect leaks

❌ **DON'T:**
- Bypass session_manager and create sessions directly
- Forget to end sessions when explicitly requested
- Disable background cleanup thread

---

## Future Enhancements

Potential improvements:

1. **Redis Caching** - Store sessions in Redis for multi-server deployments
2. **Session Analytics** - Track session duration distribution, peak times
3. **Dynamic Timeouts** - Adjust timeout based on user behavior
4. **Session Recovery** - Restore sessions after server restart (if desired)
5. **Multi-Device Support** - Allow same user on multiple devices simultaneously

---

## Related Documentation

- [AUTHENTICATION.md](./AUTHENTICATION.md) - Authentication system
- [ESP32_INTEGRATION_EXAMPLE.md](./ESP32_INTEGRATION_EXAMPLE.md) - Hardware integration
- [README.md](../README.md) - Complete system documentation

---

**Backend Session Management Ready! 🔄**

Your sessions are now fully managed by the backend with automatic cleanup and persistence.
