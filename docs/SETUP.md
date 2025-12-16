# 🔧 Luno Backend Setup Guide

Complete setup instructions for the Luno backend system.

---

## 📋 Prerequisites

- **Python 3.9+** installed (`python3 --version`)
- **pip** package manager
- **Firebase project** created at console.firebase.google.com
- **OpenAI API key** from platform.openai.com
- **ElevenLabs API key** from elevenlabs.io (for TTS)
- **Speechify API key** (optional, for alternative TTS)

---

## 🚀 Installation

### 1. Create Virtual Environment

```bash
cd /Users/rohankhan/Desktop/Luno/backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- Flask (web framework)
- Firebase Admin SDK (Firestore database)
- OpenAI Python SDK (GPT-4 and Whisper)
- python-dotenv (environment variables)
- And other required packages

---

## 🔑 Environment Configuration

### Create `.env` File

Create a `.env` file in the backend directory:

```bash
# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-credentials.json

# API Keys
OPENAI_API_KEY=sk-proj-your_openai_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
SPEECHIFY_API_KEY=your_speechify_key_here
ELEVENLABS_VOICE_ID=5oDR2Spw4ffxVYWXiJC2

# Flask Configuration
PORT=5005
```

### Get Firebase Service Account Key

#### Step 1: Go to Firebase Console

Visit: https://console.firebase.google.com/project/luno-companion-app-dev/settings/serviceaccounts/adminsdk

Or manually:
1. Go to https://console.firebase.google.com/
2. Select **luno-companion-app-dev** project
3. Click **⚙️ gear icon** → **Project settings**
4. Go to **Service accounts** tab

#### Step 2: Generate Private Key

1. Click **"Generate new private key"**
2. Click **"Generate key"** to confirm
3. A JSON file downloads (e.g., `luno-companion-app-dev-xxxxx.json`)

#### Step 3: Save the File

Save it as `firebase-credentials.json` in the backend directory:

```bash
mv ~/Downloads/luno-companion-app-dev-*.json firebase-credentials.json
```

**IMPORTANT:** This file is already in `.gitignore` - never commit it to git!

### Get API Keys

#### OpenAI API Key

1. Go to https://platform.openai.com/api-keys
2. Click **"Create new secret key"**
3. Copy the key (starts with `sk-proj-...`)
4. Add to `.env` file

#### ElevenLabs API Key

1. Go to https://elevenlabs.io/
2. Sign up/login
3. Go to Profile → API Keys
4. Copy your key
5. Add to `.env` file

---

## 📁 Project Structure

```
backend/
├── .env                          # Environment variables (create this)
├── .gitignore                    # Git ignore rules
├── firebase-credentials.json     # Firebase key (download from console)
│
├── app.py                        # Main Flask application
├── auth_middleware.py            # Device authentication
├── firebase_config.py            # Firebase initialization
├── firestore_service.py          # Firestore operations
├── gpt_reply.py                  # GPT conversation logic
├── whisper_stt.py                # Speech-to-text
├── tts_elevenlabs.py             # Text-to-speech
│
├── requirements.txt              # Python dependencies
├── gunicorn.conf.py              # Production server config
│
├── esp32_simulator.py            # CLI simulator
├── simulator.html                # Web simulator
├── simulator_config.json         # Simulator configuration
│
└── docs/
    ├── README.md                 # Main documentation
    ├── QUICK_START.md            # 5-minute quick start
    ├── SETUP.md                  # This file
    ├── AUTHENTICATION.md         # Auth system guide
    ├── SIMULATOR_GUIDE.md        # Simulator usage
    └── ESP32_INTEGRATION_EXAMPLE.md  # Hardware integration
```

---

## 🗄️ Firebase/Firestore Setup

### Firestore Database Structure

The backend expects this structure in Firestore:

```
users/
└── {userId}/                     # Parent user document
    ├── children/
    │   └── {childId}/            # Child profile
    │       └── conversations/
    │           └── {conversationId}/
    │               └── messages/
    │                   └── {messageId}
    └── toys/
        └── {toyId}/              # Toy/device document
```

### Firestore Security Rules

**Important:** The backend uses Firebase Admin SDK which bypasses security rules. These rules are for frontend client access:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can only access their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;

      match /children/{childId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;

        match /conversations/{conversationId} {
          allow read, write: if request.auth != null && request.auth.uid == userId;

          match /messages/{messageId} {
            allow read, write: if request.auth != null && request.auth.uid == userId;
          }
        }
      }

      match /toys/{toyId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
  }
}
```

---

## 🧪 Create Test Data

### Using the Setup Script

```bash
# Activate virtual environment
source venv/bin/activate

# Run test data creation
python setup_test_data.py
```

This creates:
- Test user in Firestore
- Test child profile
- Test toy/device
- Updates `simulator_config.json` automatically

### Manual Account Creation (via API)

```bash
curl -X POST http://localhost:5005/api/setup/create_account \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test_user_123",
    "email": "test@example.com",
    "display_name": "Test User",
    "child_id": "test_child_123",
    "child_name": "Test Child",
    "toy_id": "test_toy_123",
    "toy_name": "Test Toy"
  }'
```

---

## 🏃 Running the Backend

### Development Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Start Flask development server
python app.py
```

Server runs on: `http://localhost:5005`

You should see:
```
[INFO] Firebase initialized with service account: firebase-credentials.json
[INFO] Firestore client initialized successfully
[INFO] Connected to project: luno-companion-app-dev
 * Running on http://0.0.0.0:5005
```

### Production Mode

```bash
# Activate virtual environment
source venv/bin/activate

# Run with Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

---

## ✅ Verify Installation

### 1. Test Backend is Running

```bash
curl http://localhost:5005/
```

Expected response:
```
ESP32 Toy Backend is running. Broooo its workinggggggggggggg
```

### 2. Test Firebase Connection

```bash
python3 -c "
from dotenv import load_dotenv
load_dotenv()
from firebase_config import initialize_firebase
db = initialize_firebase()
print('✅ Firebase connected!' if db else '❌ Failed')
"
```

### 3. Test Authentication

```bash
curl -X GET http://localhost:5005/auth/test \
  -H "X-User-ID: test_user_1763434576" \
  -H "X-Device-ID: test_toy_1763434576" \
  -H "X-Email: test@lunotoys.com" \
  -H "X-Session-ID: test_session"
```

Expected: Authentication successful response

### 4. Open Web Simulator

Go to: `http://localhost:5005/simulator`

---

## 🐛 Troubleshooting

### "ModuleNotFoundError: No module named 'dotenv'"

```bash
pip install python-dotenv
```

### "Failed to initialize Firebase"

**Check 1:** Verify `.env` file exists
```bash
ls -la .env
```

**Check 2:** Verify firebase-credentials.json exists
```bash
ls -la firebase-credentials.json
```

**Check 3:** Check environment variable is set
```bash
python3 -c "
from dotenv import load_dotenv
import os
load_dotenv()
print(os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH'))
"
```

### "Permission denied" Firestore Errors

**Solution:** Ensure Firebase service account key has correct permissions:
1. Go to Firebase Console → IAM & Admin
2. Find service account email
3. Ensure it has "Firebase Admin SDK Administrator Service Agent" role

### "Port 5005 already in use"

**Find and kill the process:**
```bash
lsof -i :5005
kill -9 <PID>
```

Or use a different port in `.env`:
```bash
PORT=5006
```

### Virtual Environment Issues

**Recreate virtual environment:**
```bash
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🔒 Security Best Practices

- ✅ Never commit `.env` file to git
- ✅ Never commit `firebase-credentials.json` to git
- ✅ Rotate API keys regularly
- ✅ Use environment-specific Firebase projects (dev/staging/prod)
- ✅ Enable Firebase security rules for frontend access
- ✅ Use HTTPS in production
- ✅ Monitor API usage and set billing alerts

---

## 📈 Next Steps

After setup is complete:

1. **Test with Simulators** - See [SIMULATOR_GUIDE.md](./SIMULATOR_GUIDE.md)
2. **Understand Authentication** - See [AUTHENTICATION.md](./AUTHENTICATION.md)
3. **Deploy to Production** - See [README.md](../README.md#deployment)
4. **Integrate ESP32 Hardware** - See [ESP32_INTEGRATION_EXAMPLE.md](./ESP32_INTEGRATION_EXAMPLE.md)

---

## 📞 Support

If you encounter issues:
1. Check backend logs for error messages
2. Verify all environment variables are set correctly
3. Ensure Firebase project exists and credentials are valid
4. Test with curl commands above
5. Check Firestore console for data

---

**Setup Complete! 🎉**

You're ready to start developing with the Luno backend.
