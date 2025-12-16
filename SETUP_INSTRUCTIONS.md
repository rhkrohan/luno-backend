# 🚀 Backend Setup Instructions

## Current Status: Firebase Credentials Needed ⚠️

Your backend is almost ready! You just need to configure Firebase credentials.

---

## Step 1: Get Firebase Service Account Key

### Option A: Download from Firebase Console (Recommended)

1. **Go to Firebase Console:**
   - Visit: https://console.firebase.google.com/project/luno-companion-app-dev/settings/serviceaccounts

2. **Generate Key:**
   - Click on **"Service accounts"** tab
   - Click **"Generate new private key"**
   - Click **"Generate key"** in the popup
   - A JSON file will be downloaded (e.g., `luno-companion-app-dev-firebase-adminsdk-xxxxx.json`)

3. **Save the File:**
   ```bash
   # Move it to your backend directory
   mv ~/Downloads/luno-companion-app-dev-*.json /Users/rohankhan/Desktop/Luno/backend/firebase-key.json
   ```

4. **Set Environment Variable:**
   ```bash
   export FIREBASE_SERVICE_ACCOUNT_PATH="/Users/rohankhan/Desktop/Luno/backend/firebase-key.json"
   ```

### Option B: Use Application Default Credentials (Development)

If you have Google Cloud SDK installed:

```bash
gcloud auth application-default login
```

---

## Step 2: Set API Keys

```bash
# OpenAI API Key (required for GPT and Whisper)
export OPENAI_API_KEY="sk-proj-YOUR_OPENAI_KEY_HERE"

# ElevenLabs API Key (required for TTS)
export ELEVENLABS_API_KEY="YOUR_ELEVENLABS_KEY_HERE"
```

---

## Step 3: Run the Backend

```bash
python app.py
```

You should see:

```
[INFO] Firebase initialized with service account: /path/to/firebase-key.json
[INFO] Firestore client initialized successfully
 * Running on http://0.0.0.0:5005
```

---

## Quick Setup Script

Create a file called `start.sh`:

```bash
#!/bin/bash

# Set your API keys here
export OPENAI_API_KEY="sk-proj-YOUR_KEY"
export ELEVENLABS_API_KEY="YOUR_KEY"
export FIREBASE_SERVICE_ACCOUNT_PATH="/Users/rohankhan/Desktop/Luno/backend/firebase-key.json"

# Start the backend
python app.py
```

Then run:

```bash
chmod +x start.sh
./start.sh
```

---

## Alternative: .env File

Create a `.env` file in the backend directory:

```bash
OPENAI_API_KEY=sk-proj-YOUR_KEY
ELEVENLABS_API_KEY=YOUR_KEY
FIREBASE_SERVICE_ACCOUNT_PATH=/Users/rohankhan/Desktop/Luno/backend/firebase-key.json
```

Then load it before running:

```bash
# Install python-dotenv if needed
pip install python-dotenv

# Load .env and run
source .env  # or use python-dotenv in app.py
python app.py
```

---

## Verification

### Test Backend:
```bash
curl http://localhost:5005
```

Should return:
```
ESP32 Toy Backend is running. Broooo its workinggggggggggggg
```

### Test Firestore Connection:
```bash
python setup_test_data.py
```

This will create test data and verify Firestore is working!

---

## Your Firebase Project Info

**Project ID:** `luno-companion-app-dev`

**Firebase Console:**
https://console.firebase.google.com/project/luno-companion-app-dev

**Firestore Database:**
https://console.firebase.google.com/project/luno-companion-app-dev/firestore

**Service Accounts:**
https://console.firebase.google.com/project/luno-companion-app-dev/settings/serviceaccounts

---

## Troubleshooting

### "Your default credentials were not found"
→ You need to download the service account key (see Step 1 above)

### "Permission denied" when reading firebase-key.json
```bash
chmod 600 /Users/rohankhan/Desktop/Luno/backend/firebase-key.json
```

### "Module not found" errors
```bash
pip install -r requirements.txt
```

### "Port 5005 already in use"
```bash
# Find and kill the process
lsof -ti:5005 | xargs kill -9

# Or use a different port
PORT=5006 python app.py
```

---

## What's Next?

Once the backend is running:

1. ✅ **Create test data:** `python setup_test_data.py`
2. ✅ **Open web simulator:** http://localhost:5005/simulator
3. ✅ **Send your first message!**

---

**Need help?** Check the full [README.md](./README.md) or [QUICK_START.md](./QUICK_START.md)
