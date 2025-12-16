# Firestore Integration Guide

## Overview

This backend now integrates with Firebase Firestore to store conversations, messages, and user statistics. The integration is designed to work seamlessly with your existing ESP32 toy communication system while maintaining backward compatibility.

## Architecture

```
┌──────────────┐
│   ESP32 Toy  │
└──────┬───────┘
       │ HTTP Request (with headers)
       ▼
┌──────────────────────────────────┐
│   Flask Backend (/upload)        │
│   - Extracts metadata            │
│   - Creates/gets conversation    │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│   GPT Reply Service              │
│   - Processes message            │
│   - Saves to Firestore           │
└──────┬───────────────────────────┘
       │
       ▼
┌──────────────────────────────────┐
│   Firestore Database             │
│   - Conversations                │
│   - Messages                     │
│   - User Stats                   │
└──────────────────────────────────┘
```

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install `firebase-admin` along with other dependencies.

### 2. Configure Firebase Credentials

You have **three options** for Firebase authentication:

#### Option 1: Service Account JSON File (Recommended for Production)

1. Download your Firebase service account key JSON file from Firebase Console
2. Set the environment variable:

```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/serviceAccountKey.json"
```

#### Option 2: Service Account JSON as Environment Variable

```bash
export FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project",...}'
```

#### Option 3: Application Default Credentials (Development Only)

For local development, you can use Google Cloud SDK:

```bash
gcloud auth application-default login
```

### 3. Run the Backend

```bash
python app.py
```

The backend will:
- Initialize Firebase on startup
- Connect to Firestore
- Start the Flask server on port 5005

## How It Works

### Conversation Lifecycle

#### 1. **Starting a Conversation**

When the ESP32 sends its first message, a new conversation is automatically created in Firestore.

**ESP32 Requirements:**
The ESP32 must send the following headers with each request:

```
X-Session-ID: esp32_session_123
X-User-ID: userId123
X-Child-ID: childId456
X-Toy-ID: toyId789  (optional)
```

**What happens:**
- Backend checks if a conversation exists for this session
- If not, creates a new conversation document in Firestore
- Conversation is tracked in `ACTIVE_CONVERSATIONS` dict

#### 2. **Sending Messages**

Each message exchange automatically saves to Firestore:

**Child Message → Toy Response:**
- Child's speech is transcribed
- Child message saved to Firestore
- GPT generates response
- Toy message saved to Firestore
- Both messages linked to the same conversation

**Safety Checks:**
- Each message is checked for safety issues
- Personal info, inappropriate content, or emotional distress is flagged
- Conversations are automatically flagged if issues detected

#### 3. **Ending a Conversation**

Call the `/api/conversations/end` endpoint:

```bash
POST /api/conversations/end
Content-Type: application/json

{
  "session_id": "esp32_session_123"
}
```

**What happens:**
- Calculates conversation duration
- Updates conversation end time and message count
- Updates user statistics
- Removes from active sessions

## API Endpoints

### ESP32 Communication Endpoints

#### `POST /upload`
Upload audio from ESP32 (with server-side STT)

**Headers:**
- `X-Session-ID`: Session identifier
- `X-User-ID`: Parent user ID
- `X-Child-ID`: Child ID
- `X-Toy-ID`: Toy ID (optional)

**Body:** Audio file (ADPCM or WAV)

**Response:** Audio response (WAV)

#### `POST /text_upload`
Send text from ESP32 (with local STT)

**Headers:** Same as `/upload`

**Body:**
```json
{
  "text": "Hello Luna!",
  "session_id": "esp32_session_123",
  "user_id": "userId123",
  "child_id": "childId456",
  "toy_id": "toyId789"
}
```

**Response:** Audio response (WAV)

### Conversation Management Endpoints

#### `POST /api/conversations/end`
End a conversation session

**Request:**
```json
{
  "session_id": "esp32_session_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Conversation ended for session esp32_session_123"
}
```

#### `GET /api/conversations/{conversation_id}`
Get conversation details

**Query Parameters:**
- `user_id`: Parent user ID (required)
- `child_id`: Child ID (required)

**Response:**
```json
{
  "success": true,
  "conversation": {
    "startTime": "2024-01-15T10:30:00Z",
    "endTime": "2024-01-15T10:45:00Z",
    "duration": 15,
    "type": "conversation",
    "messageCount": 12,
    "flagged": false,
    ...
  }
}
```

#### `GET /api/conversations/{conversation_id}/messages`
Get all messages for a conversation

**Query Parameters:**
- `user_id`: Parent user ID (required)
- `child_id`: Child ID (required)
- `limit`: Max messages to return (default: 100)

**Response:**
```json
{
  "success": true,
  "messages": [
    {
      "id": "msg123",
      "sender": "child",
      "content": "Hello Luna!",
      "timestamp": "2024-01-15T10:30:00Z",
      "flagged": false
    },
    {
      "id": "msg124",
      "sender": "toy",
      "content": "Hi there! How are you?",
      "timestamp": "2024-01-15T10:30:05Z",
      "flagged": false
    }
  ],
  "count": 2
}
```

#### `GET /api/children/{child_id}/conversations`
Get all conversations for a child

**Query Parameters:**
- `user_id`: Parent user ID (required)
- `limit`: Max conversations to return (default: 50)

**Response:**
```json
{
  "success": true,
  "conversations": [
    {
      "id": "conv123",
      "title": "Math Adventure",
      "startTime": "2024-01-15T10:30:00Z",
      "duration": 15,
      "messageCount": 12,
      ...
    }
  ],
  "count": 1
}
```

#### `PUT /api/conversations/{conversation_id}/flag`
Update conversation flag status

**Request:**
```json
{
  "user_id": "userId123",
  "child_id": "childId456",
  "flag_status": "reviewed"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Conversation flag status updated to reviewed"
}
```

#### `GET /api/users/{user_id}/stats`
Get user statistics

**Response:**
```json
{
  "success": true,
  "stats": {
    "totalConversations": 45,
    "totalConversationDurationSec": 2700,
    "flaggedConversations": 2,
    "lastConversationAt": "2024-01-15T10:45:00Z",
    "lastFlaggedAt": "2024-01-14T15:20:00Z"
  }
}
```

## Safety & Content Moderation

The backend automatically checks messages for:

### Safety Categories

1. **Personal Information** (Severity: Critical)
   - Phone numbers
   - Social Security Numbers
   - Email addresses
   - Physical addresses

2. **Inappropriate Content** (Severity: High)
   - Violence keywords
   - Harmful language

3. **Emotional Distress** (Severity: Medium)
   - Fear, anxiety keywords
   - Concerning emotional states

### Flagging Behavior

When unsafe content is detected:
- Message is flagged with `flagged: true`
- Conversation is flagged with details
- `flagType`, `flagReason`, and `severity` are set
- `messagePreview` is captured for parent review
- `flagStatus` defaults to "unreviewed"

## Data Flow Example

### Complete Conversation Flow

```
1. ESP32 sends first message
   Headers: X-User-ID, X-Child-ID, X-Toy-ID, X-Session-ID
   ↓
2. Backend creates conversation in Firestore
   Document: users/{userId}/children/{childId}/conversations/{convId}
   ↓
3. Child message transcribed and saved
   Collection: .../conversations/{convId}/messages/{msgId1}
   ↓
4. GPT generates response
   ↓
5. Toy message saved to Firestore
   Collection: .../conversations/{convId}/messages/{msgId2}
   ↓
6. Safety check runs on both messages
   ↓
7. Conversation metadata updated (messageCount++)
   ↓
8. Audio response sent to ESP32
   ↓
9. (Repeat steps 3-8 for each message)
   ↓
10. ESP32 calls /api/conversations/end
    ↓
11. Backend calculates duration and updates stats
    ↓
12. User stats incremented:
    - totalConversations++
    - totalConversationDurationSec += duration
    - flaggedConversations++ (if flagged)
```

## Firestore Structure

See `Firestore Database Structure.md` for the complete database schema.

## Error Handling

The integration uses **graceful degradation**:

- If Firestore is unavailable, conversations continue but aren't saved
- Errors are logged but don't block ESP32 responses
- In-memory conversation history (`CONVERSATIONS` dict) always works

## Testing

### Test with cURL

```bash
# Test text upload with metadata
curl -X POST http://localhost:5005/text_upload \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user123" \
  -H "X-Child-ID: child456" \
  -H "X-Toy-ID: toy789" \
  -d '{
    "text": "Hello Luna!",
    "session_id": "test_session_1"
  }'

# End the conversation
curl -X POST http://localhost:5005/api/conversations/end \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test_session_1"
  }'

# Get user stats
curl -X GET "http://localhost:5005/api/users/user123/stats"
```

## ESP32 Integration Checklist

To integrate with your ESP32 firmware:

- [ ] Add HTTP headers to all requests:
  - `X-Session-ID` (unique per conversation session)
  - `X-User-ID` (from paired user account)
  - `X-Child-ID` (active child using the toy)
  - `X-Toy-ID` (toy's unique identifier)

- [ ] Call `/api/conversations/end` when:
  - User stops talking for >30 seconds (timeout)
  - Toy is turned off
  - User manually ends session

- [ ] Handle responses:
  - Check for `X-Response-Time` header for latency monitoring
  - Log conversation IDs for debugging

## Frontend Integration

Your mobile app can:

1. **View conversations** for each child
2. **Review flagged content** via Safety Center
3. **See real-time stats** on dashboard
4. **Mark flags as reviewed** after parent review

Use the API endpoints listed above to build these features.

## Environment Variables Summary

```bash
# Required
OPENAI_API_KEY=sk-...

# Firebase (choose one method)
FIREBASE_SERVICE_ACCOUNT_PATH=/path/to/key.json
# OR
FIREBASE_SERVICE_ACCOUNT_JSON='{...}'
# OR use gcloud auth application-default login

# Optional
PORT=5005
```

## Troubleshooting

### "Firebase not initialized" errors
- Check that `FIREBASE_SERVICE_ACCOUNT_PATH` or credentials are set
- Verify the JSON file has correct permissions

### Messages not saving to Firestore
- Check that ESP32 sends all required headers
- Check backend logs for Firestore errors
- Verify Firestore rules allow writes from your service account

### Stats not updating
- Make sure `/api/conversations/end` is called
- Check that conversation has valid `user_id` and `child_id`

## Next Steps

1. **Add Redis** for distributed session storage (currently in-memory)
2. **Add background jobs** for periodic cleanup of old conversations
3. **Add webhooks** to notify mobile app of flagged content
4. **Add analytics** for conversation insights

## Support

For issues or questions, check:
- Backend logs: Look for `[INFO]`, `[WARNING]`, `[ERROR]` prefixes
- Firestore console: Verify data is being written
- API testing: Use the cURL examples above

---

**Happy Building! 🚀**
