# 🔄 Session Management System

Complete guide to the backend-managed session system.

---

## Overview

As of the latest update, **session management is fully handled by the backend**. ESP32 devices no longer need to generate or track session IDs - the backend automatically creates and manages sessions based on device and user identifiers.

### Key Features

- ✅ **Backend-Generated Sessions** - Automatic session tracking via conversations
- ✅ **One Session Per Device-User** - New conversations auto-end previous ones
- ✅ **Firestore Persistence** - Sessions tracked via conversation `status` field
- ✅ **Automatic Cleanup** - 2-minute inactivity timeout (default)
- ✅ **Server Restart Handling** - Stale sessions automatically ended
- ✅ **No Separate Sessions Collection** - Sessions managed through active conversations

**IMPORTANT:** The current implementation does NOT use a separate `sessions` collection. Session state is tracked using the conversation document's `status` field ("active" or "ended").

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
         │ ├─ X-Device-ID: TOY123 (or X-Toy-ID)
         │ └─ X-User-ID: user456
         ▼
┌─────────────────┐
│ Session Manager │
│   (Backend)     │
└────────┬────────┘
         │
         ├─ 1. Check for active conversation (status="active")
         ├─ 2. If none, create new conversation
         ├─ 3. If exists and valid, reuse
         ├─ 4. If expired, end old & create new
         │
         ▼
┌─────────────────────────┐
│   Firestore             │
│ users/{userId}/         │
│  conversations/         │
│   {conversationId}      │
│     status: "active"    │
└─────────────────────────┘
```

**Note:** Sessions are NOT stored in a separate collection. The "active" conversation for a given toy/user is the session.

---

## Session Lifecycle

### 1. Session Creation

**Trigger:** First request from a device-user pair

**Process:**
```python
# Backend automatically:
1. Checks for existing active conversation for this toy+user
2. If none found, creates NEW conversation in Firestore:
   Path: users/{userId}/conversations/{conversationId}
   {
     "status": "active",
     "toyId": "TOY123",
     "userId": "user456",
     "childId": "child789",
     "startTime": timestamp,
     "lastActivityAt": timestamp,
     "messageCount": 0,
     "messages": []
   }
3. Stores conversation ID in memory for fast access
```

**ESP32 Action:** None required - just send audio/text as normal

**Note:** No separate session document is created. The conversation document itself serves as the session.

### 2. Session Reuse

**Trigger:** Subsequent requests within 2 minutes (default timeout)

**Process:**
```python
# Backend checks:
1. Is there an active conversation for this toy+user?
   Query: conversations.where("toyId", "==", toy_id)
                       .where("status", "==", "active")
2. If yes and not expired → reuse existing conversation
3. Update lastActivityAt timestamp using ArrayUnion for messages
4. Increment messageCount
```

**ESP32 Action:** None - backend handles automatically

### 3. Session Expiration

**Trigger:** 2 minutes of inactivity (default) OR explicit end request

**Process:**
```python
# Backend detects:
1. lastActivityAt + 2 minutes < now?
2. If expired:
   - Update conversation status to "ended"
   - Calculate and store duration
   - Clear from memory cache
3. Next request creates new conversation/session
```

**Cleanup Methods:**
- **On-demand**: Checked during session lookup
- **Background**: Automatic expiration checks
- **Manual**: Via `/api/conversations/end` endpoint

**Default Timeout:** 120 seconds (2 minutes) - configurable via `SESSION_INACTIVITY_TIMEOUT` env var

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

### Session Tracking (via Conversation Documents)

**Location:** `users/{userId}/conversations/{conversationId}`

**Note:** There is NO separate `sessions` collection. Sessions are tracked using the conversation's `status` field.

```javascript
{
  // Core Metadata
  "status": "active" | "ended",  // "active" = session in progress
  "type": "conversation" | "story" | "game",

  // Identity/Relationships
  "toyId": "TOY123",
  "userId": "user456",
  "childId": "child789",
  "childName": "Emma",
  "toyName": "Luna",

  // Timestamps
  "startTime": Timestamp,
  "lastActivityAt": Timestamp,
  "endTime": Timestamp | null,
  "durationMinutes": number,

  // Content
  "title": string,
  "messageCount": 12,
  "messages": [...]  // Array field, not subcollection

  // Safety
  "flagged": boolean,
  // ... other safety fields
}
```

### Queries

```python
# Get active conversation/session for a toy
conversations_ref.where("toyId", "==", "TOY123")\
                .where("status", "==", "active")\
                .limit(1)

# Find all active conversations (all sessions)
conversations_ref.where("status", "==", "active")

# Find expired conversations (check lastActivityAt)
conversations_ref.where("status", "==", "active")\
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
SESSION_INACTIVITY_TIMEOUT=120  # 2 minutes (default)
```

### Adjusting Timeout

```bash
# Change in .env file
SESSION_INACTIVITY_TIMEOUT=300   # 5 minutes
SESSION_INACTIVITY_TIMEOUT=600   # 10 minutes
SESSION_INACTIVITY_TIMEOUT=1800  # 30 minutes
```

**Important:** The default is 120 seconds (2 minutes), not 30 minutes as in earlier versions.

---

## Backend Implementation Details

### SessionManager Class

**Location:** `session_manager.py`

**Key Methods:**

```python
class SessionManager:
    def __init__(self, firestore_service):
        self.INACTIVITY_TIMEOUT_SECONDS = 120  # 2 min (default)

    def get_or_create_conversation(toy_id, user_id, child_id):
        """
        Main entry point - finds active conversation or creates new one
        Returns conversation_id for the active session
        """

    def update_conversation_activity(conversation_id, user_id):
        """Update lastActivityAt after each message"""

    def end_conversation(conversation_id, user_id, reason):
        """End conversation/session and cleanup"""

    def cleanup_expired_conversations():
        """Background task - finds and ends expired conversations"""
```

**Note:** Method names reflect that sessions are conversations, not separate entities.

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
# Query Firestore for active conversations (sessions)
firebase firestore:query \
  "users/{userId}/conversations" \
  --where status=active
```

Or using the backend API:

```bash
curl "http://localhost:5005/api/conversations/active?user_id=YOUR_USER_ID"
```

### View Session in Logs

```python
# Backend logs show:
[INFO] SessionManager initialized with 120s inactivity timeout
[INFO] Created new conversation: conv_abc (status: active) for toy TOY123
[INFO] Using active conversation: conv_abc
[INFO] Conversation conv_abc expired due to inactivity (125s)
[INFO] Ended conversation conv_abc, duration: 5m, reason: explicit
```

### Debug Session Issues

```python
# Check if active conversation exists for a toy
from firestore_service import firestore_service

# Query active conversation
conversations = firestore_service.db.collection('users')\
    .document(user_id)\
    .collection('conversations')\
    .where('toyId', '==', 'TOY123')\
    .where('status', '==', 'active')\
    .limit(1)\
    .get()

if conversations:
    conv = conversations[0].to_dict()
    print(f"Active conversation: {conversations[0].id}")
    print(f"Status: {conv['status']}")
    print(f"Last activity: {conv['lastActivityAt']}")
else:
    print("No active conversation/session found")
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

### Issue: Multiple conversations created for same device-user

**Symptom:** Each request creates a new conversation instead of reusing

**Cause:** Active conversation not being found

**Solution:**
- Check `toyId` (or `deviceId`) and `userId` are consistent across requests
- Verify conversation is being created with `status: "active"`
- Check backend logs for conversation lookup errors
- Ensure Firestore indexes are deployed

### Issue: Conversations not expiring

**Symptom:** Old conversations remain "active" indefinitely

**Cause:** Expiration checks not running or `lastActivityAt` still recent

**Solution:**
- Verify `SESSION_INACTIVITY_TIMEOUT` setting (default: 120 seconds)
- Confirm `lastActivityAt` is being updated on each message
- Check backend logs for expiration checks

### Issue: "No active conversation found" error

**Symptom:** Backend can't find active conversation for toy

**Cause:** Conversation already ended or toy ID mismatch

**Solution:**
- Verify `toyId` matches between requests
- Check if conversation expired (>2 min since last activity by default)
- Look in Firestore for conversation with `status: "ended"`
- Query: `conversations.where("toyId", "==", toy_id).where("status", "==", "active")`

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
