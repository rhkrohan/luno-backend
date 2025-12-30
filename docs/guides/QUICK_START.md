# 🚀 Quick Start Guide

Get your Luno backend up and running in 5 minutes!

---

## 📋 Prerequisites Checklist

Before you begin, make sure you have:

- [ ] Python 3.12+ installed (`python3 --version`)
- [ ] pip installed (`pip3 --version`)
- [ ] Firebase project created (console.firebase.google.com)
- [ ] Firebase service account key downloaded
- [ ] OpenAI API key
- [ ] ElevenLabs API key (for TTS)

---

## ⚡ 5-Minute Setup

### Step 1: Install Dependencies (1 min)

```bash
cd backend
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables (2 min)

Create a `.env` file in the backend directory:

```bash
# Firebase Configuration
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-credentials.json

# API Keys
OPENAI_API_KEY=sk-proj-your_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here
SPEECHIFY_API_KEY=your_speechify_key_here
ELEVENLABS_VOICE_ID=5oDR2Spw4ffxVYWXiJC2

# Flask Configuration
PORT=5005
```

**Get your Firebase Service Account Key:**
1. Go to [Firebase Console](https://console.firebase.google.com/project/luno-companion-app-dev/settings/serviceaccounts/adminsdk)
2. Click "Generate New Private Key"
3. Save as `firebase-credentials.json` in the backend directory

### Step 3: Start the Backend (1 min)

```bash
python app.py
```

You should see:

```
[INFO] Firebase initialized with service account: /path/to/key.json
[INFO] Firestore client initialized successfully
 * Running on http://0.0.0.0:5005
```

### Step 4: Create Test Data (1 min)

In a new terminal:

```bash
python setup_test_data.py
```

This will:
- Create a test user in Firestore
- Create a test child profile
- Create a test toy
- Configure the simulators automatically

You'll see output like:

```
============================================================
   🚀 Luno Backend - Test Data Setup
============================================================

✓ Connected to Firestore

Creating test data with IDs:
  User:  test_user_1705334456
  Child: test_child_1705334456
  Toy:   test_toy_1705334456

✓ Created user: test_user_1705334456
✓ Created child: test_child_1705334456
✓ Created toy: test_toy_1705334456
✓ Updated simulator_config.json

============================================================
   ✅ Setup Complete!
============================================================
```

### Step 5: Test with Simulator (< 1 min)

**Option A: Web Simulator** (Easiest)

Open your browser and go to:
```
http://localhost:5005/simulator
```

**Option B: CLI Simulator**

```bash
python esp32_simulator.py
```

Send a test message:
```
Select option: 1
Enter message: Hello Luna!
```

---

## 🎯 Your First Conversation

### Using Web Simulator

1. Open `http://localhost:5005/simulator`
2. Configuration is already set from `setup_test_data.py`
3. Type a message in the text box: **"Hello Luna, how are you?"**
4. Click **"Send"** or press Enter
5. Audio response will play automatically
6. Check the logs for timing breakdown

### Using CLI Simulator

```bash
python esp32_simulator.py

# Select option 1 (Text Mode)
Select option: 1
Enter message: Hello Luna, how are you?

# Luna will respond with audio!
```

---

## ✅ Verification Steps

### Check Backend is Working

```bash
curl http://localhost:5005
```

Should return:
```
ESP32 Toy Backend is running. Broooo its workinggggggggggggg
```

### Check Firestore Data

1. Go to [Firestore Console](https://console.firebase.google.com/project/luno-companion-app-dev/firestore)
2. Navigate to: `users → {your_test_user} → children → {your_test_child} → conversations`
3. You should see your test conversation!

### Check Stats API

```bash
curl "http://localhost:5005/api/users/{your_user_id}/stats"
```

Should return your conversation stats!

---

## 🔍 Project Structure

```
backend/
├── app.py                          # Main Flask application
├── firebase_config.py              # Firebase initialization
├── firestore_service.py            # Firestore operations
├── gpt_reply.py                    # GPT conversation logic
├── whisper_stt.py                  # Speech-to-text
├── tts_elevenlabs.py               # Text-to-speech
├── esp32_simulator.py              # CLI simulator
├── simulator.html                  # Web simulator
├── setup_test_data.py              # Test data creation script
├── simulator_config.json           # Simulator configuration (auto-generated)
├── firebase_project_config.json    # Firebase project info
├── requirements.txt                # Python dependencies
├── README.md                       # Full documentation
├── QUICK_START.md                  # This file
├── SIMULATOR_GUIDE.md              # Simulator usage guide
├── FIRESTORE_INTEGRATION_GUIDE.md  # Firestore setup details
└── ESP32_INTEGRATION_EXAMPLE.md    # Hardware integration examples
```

---

## 🎮 Common Commands

### Start Backend
```bash
python app.py
```

### Create Test Data
```bash
python setup_test_data.py
```

### Run CLI Simulator
```bash
python esp32_simulator.py
```

### Open Web Simulator
```
http://localhost:5005/simulator
```

### Test Connection
```bash
curl http://localhost:5005
```

### Get User Stats
```bash
curl "http://localhost:5005/api/users/{user_id}/stats"
```

### End Conversation
```bash
curl -X POST http://localhost:5005/api/conversations/end \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your_session_id"}'
```

---

## 📊 Your Firebase Project

**Project ID:** `luno-companion-app-dev`

**Firebase Console:**
https://console.firebase.google.com/project/luno-companion-app-dev

**Frontend Config:**
```javascript
const firebaseConfig = {
  apiKey: "AIzaSyA3Lf7ydukXAo0UWdXwSo4mVVWB8r4DNGs",
  authDomain: "luno-companion-app-dev.firebaseapp.com",
  projectId: "luno-companion-app-dev",
  storageBucket: "luno-companion-app-dev.firebasestorage.app",
  messagingSenderId: "1045141937894",
  appId: "1:1045141937894:web:1548a3ef0e419815ad6527",
};
```

---

## 🔧 Troubleshooting

### "Firebase initialization failed"

```bash
# Verify .env file exists
cat .env

# Verify firebase-credentials.json exists
ls -la firebase-credentials.json

# Test Firebase connection
python3 -c "from dotenv import load_dotenv; load_dotenv(); from firebase_config import initialize_firebase; db = initialize_firebase(); print('✅ OK' if db else '❌ Failed')"
```

### "OpenAI API error"

```bash
# Verify API key is set in .env
grep OPENAI_API_KEY .env

# Test OpenAI connection
python3 -c "from dotenv import load_dotenv; load_dotenv(); from openai import OpenAI; client = OpenAI(); print('✅ OK')"
```

### "Connection refused"

- Is backend running? (`python app.py`)
- Check port 5005 is not in use
- Try accessing `http://127.0.0.1:5005` instead of `localhost`

### "No audio output" (CLI Simulator)

```bash
# Install PyAudio
# macOS:
brew install portaudio
pip install pyaudio

# Ubuntu:
sudo apt-get install portaudio19-dev
pip install pyaudio
```

---

## 🎯 What's Next?

### For Development

1. **Test Different Messages** - Try various conversation flows
2. **Test Safety Flags** - Send messages with personal info to test flagging
3. **Check Firestore Data** - Verify all data is being saved correctly
4. **Test Multiple Sessions** - Create and end multiple conversations
5. **Review Stats** - Check user statistics are updating

### For Production

1. **Deploy Backend** - See [README.md](../README.md#deployment)
2. **Configure Frontend** - Connect React app to backend
3. **Set up Monitoring** - Firebase Console + Sentry
4. **Configure Firestore Rules** - Production security rules
5. **Set Rate Limits** - Protect API endpoints

### For ESP32 Integration

1. **Read ESP32 Guide** - See [ESP32_INTEGRATION_EXAMPLE.md](./ESP32_INTEGRATION_EXAMPLE.md)
2. **Update ESP32 Firmware** - Add required headers
3. **Test with Hardware** - Connect real ESP32 toy
4. **Monitor Performance** - Check response times

---

## 📚 Documentation Links

| Document | Purpose |
|----------|---------|
| [README.md](../README.md) | Complete system documentation |
| [SETUP.md](./SETUP.md) | Detailed setup and configuration |
| [AUTHENTICATION.md](./AUTHENTICATION.md) | Authentication system guide |
| [SIMULATOR_GUIDE.md](./SIMULATOR_GUIDE.md) | How to use CLI and Web simulators |
| [ESP32_INTEGRATION_EXAMPLE.md](./ESP32_INTEGRATION_EXAMPLE.md) | Hardware integration code |

---

## 💡 Pro Tips

### Faster Testing

- Use **Web Simulator** for quick tests (no setup needed)
- Use **Text Mode** before testing audio (faster)
- Keep **browser console open** for debugging (F12)
- Monitor **backend terminal** for real-time logs

### Better Audio Quality

- Use a **good microphone** for recording
- Test in a **quiet environment**
- Adjust **recording duration** for longer messages
- Check **system volume** for playback

### Efficient Workflow

1. Start backend once → Keep running
2. Use web simulator for quick iteration
3. Check Firestore after each test
4. End conversations properly to update stats
5. Use CLI simulator for audio file testing

---

## 🎉 Success!

If you've followed all steps, you now have:

✅ Backend running locally
✅ Firebase/Firestore configured
✅ Test user, child, and toy created
✅ Simulators ready to use
✅ Your first conversation tested
✅ Data saved in Firestore

**You're ready to start developing!**

---

## 🆘 Need Help?

1. **Check logs** - Backend terminal shows detailed info
2. **Check Firestore** - Verify data in Firebase Console
3. **Re-run setup** - `python setup_test_data.py` creates fresh data
4. **Test connection** - Use simulator's "Test Connection" feature
5. **Read docs** - Each guide has troubleshooting sections

---

**Happy Building! 🚀**

For questions or issues, check the backend logs and Firebase Console for detailed debugging information.
