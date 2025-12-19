# Simulator Setup Guide

The simulator now fetches real data from Firestore instead of using hardcoded values.

## What Was Fixed

### Backend Changes
Added 3 new API endpoints to `app.py`:

1. **`GET /api/users`** - Lists all users from Firestore
2. **`GET /api/users/<user_id>/children`** - Lists children for a user
3. **`GET /api/users/<user_id>/toys`** - Lists toys for a user

### Simulator Changes
Updated `simulators/esp32_test_simulator.html`:

- Removed ngrok URL (changed to `http://localhost:5005`)
- Updated `loadUsers()` to fetch from `/api/users`
- Updated `loadChildren()` to fetch from `/api/users/{userId}/children`
- Updated `loadToys()` to fetch from `/api/users/{userId}/toys`
- Added helpful error messages when no data is found

## How to Use

### Step 1: Create Test Data in Firestore

If you don't have users in Firestore yet, run the setup script:

```bash
cd /Users/rohankhan/Desktop/Luno/backend
python3 scripts/setup_test_data.py
```

This will create:
- ✅ A test user (`test@lunotoys.com`)
- ✅ A test child
- ✅ A test toy (assigned to the child)

### Step 2: Start Your Backend

```bash
cd /Users/rohankhan/Desktop/Luno/backend
python app.py
```

You should see:
```
[INFO] Background session cleanup task started
 * Running on http://0.0.0.0:5005
```

### Step 3: Open the Simulator

In your browser, go to:
```
http://localhost:5005/test
```

### Step 4: Use the Simulator

1. **The simulator will automatically load users from Firestore**
   - You should see users in the "Select User" dropdown
   - If empty, it means no users exist in Firestore (run Step 1)

2. **Select a user**
   - Children and toys will automatically load

3. **Test authentication**
   - Click "🔐 Test Authentication" button

4. **Send test messages**
   - Type a message in the text box
   - Click "📤 Send Text"
   - Wait for the audio response

## Troubleshooting

### "No users found in Firestore"

**Problem:** The dropdown is empty

**Solutions:**
1. Run the setup script: `python3 scripts/setup_test_data.py`
2. Check Firebase Console to verify users exist
3. Make sure Firebase credentials are configured correctly

### "Failed to load users: Failed to fetch"

**Problem:** Can't connect to backend

**Solutions:**
1. Make sure backend is running: `python app.py`
2. Check backend URL is correct: `http://localhost:5005`
3. Check browser console for CORS errors

### "Firestore not available"

**Problem:** Backend can't connect to Firestore

**Solutions:**
1. Check `firebase-credentials.json` exists
2. Check `.env` has `GOOGLE_APPLICATION_CREDENTIALS` set correctly
3. Verify Firebase project ID is correct

### Backend is running but simulator shows errors

**Check these:**
```bash
# 1. Test backend is running
curl http://localhost:5005/

# 2. Test users endpoint
curl http://localhost:5005/api/users

# 3. Check backend logs for errors
# Look for any error messages in the terminal where app.py is running
```

## Simulator Features

### Request Headers Configuration
- **X-Device-ID**: Device/toy identifier (auto-filled from selected toy)
- **X-User-Email**: User's email (auto-filled from selected user)
- **X-User-ID**: User ID (auto-filled from selected user)
- **X-Child-ID**: Child ID (optional, auto-filled from selected child)
- **X-Toy-ID**: Toy ID (optional, auto-filled from selected toy)

### Text Upload Test
Simulates ESP32 sending text after local STT processing:
- Type a message
- Click "Send Text"
- Receives audio response

### Audio Upload Test
Simulates ESP32 sending audio for server-side STT:
- Click "Start Recording"
- Speak into your microphone
- Click "Stop Recording"
- Click "Send Audio"
- Receives audio response with transcription

### Response Time Analysis
The simulator shows timing breakdown:
- **STT Time**: Speech-to-text processing
- **GPT Time**: AI response generation
- **TTS Time**: Text-to-speech synthesis
- **Total Time**: End-to-end response time

## Data Flow

```
┌─────────────────┐
│   Simulator     │
│  (Browser)      │
└────────┬────────┘
         │
         │ 1. Load users
         ▼
┌─────────────────┐
│  GET /api/users │
└────────┬────────┘
         │
         │ 2. Return user list
         ▼
┌─────────────────┐
│   Firestore     │
│   users/        │
└─────────────────┘

When user selected:
         │
         │ 3. Load children
         ▼
┌──────────────────────────┐
│ GET /api/users/{id}/     │
│        children          │
└──────────┬───────────────┘
           │
           │ 4. Return children
           ▼
┌──────────────────────────┐
│   Firestore              │
│   users/{id}/children/   │
└──────────────────────────┘

And similarly for toys...
```

## Test Endpoints Directly

You can test the new API endpoints with curl:

```bash
# List all users
curl http://localhost:5005/api/users

# List children for a user (replace USER_ID)
curl http://localhost:5005/api/users/test_user_1763434576/children

# List toys for a user (replace USER_ID)
curl http://localhost:5005/api/users/test_user_1763434576/toys

# Test authentication
curl -X GET http://localhost:5005/auth/test \
  -H "X-Device-ID: test_toy_1763434576" \
  -H "X-User-Email: test@lunotoys.com"
```

## Next Steps

After the simulator is working:

1. **Test full conversation flow**
   - Send multiple messages
   - Verify session management
   - Check Firestore for conversation history

2. **Deploy to EC2**
   - Follow `DEPLOYMENT_QUICKSTART.md`
   - Update simulator backend URL to EC2 IP/domain

3. **Test with real ESP32 device**
   - Use the same endpoints
   - Implement authentication headers
   - Handle audio encoding/decoding

## Files Modified

- ✅ `app.py` - Added 3 API endpoints (lines 990-1080)
- ✅ `simulators/esp32_test_simulator.html` - Updated to fetch from API
- ✅ Backend URL changed from ngrok to `http://localhost:5005`

---

For more information:
- [Main README](README.md)
- [Authentication Guide](docs/AUTHENTICATION.md)
- [Session Management](docs/SESSION_MANAGEMENT.md)
- [AWS Deployment](docs/AWS_EC2_DEPLOYMENT.md)
