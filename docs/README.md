# 📚 Luno Backend Documentation

Complete documentation for the Luno interactive toy backend system.

---

## 🚀 Getting Started

New to the project? Start here:

1. **[QUICK_START.md](./QUICK_START.md)** - Get up and running in 5 minutes
   - Install dependencies
   - Configure environment
   - Create test data
   - Test with simulator

---

## 📖 Documentation Index

### Setup & Configuration

- **[SETUP.md](./SETUP.md)** - Complete setup guide
  - Virtual environment setup
  - Environment variables (`.env` file)
  - Firebase service account configuration
  - Firestore database structure
  - Troubleshooting common setup issues

### Authentication

- **[AUTHENTICATION.md](./AUTHENTICATION.md)** - Authentication system guide
  - How authentication works
  - Required headers for ESP32/devices
  - Firestore validation process
  - In-memory caching strategy
  - ESP32 implementation examples
  - Testing authentication
  - Security considerations
  - Troubleshooting auth errors

### Testing & Development

- **[SIMULATOR_GUIDE.md](./SIMULATOR_GUIDE.md)** - Testing without hardware
  - CLI simulator usage
  - Web simulator interface
  - Testing endpoints
  - Recording audio
  - Managing conversation sessions

### Hardware Integration

- **[ESP32_INTEGRATION_EXAMPLE.md](./ESP32_INTEGRATION_EXAMPLE.md)** - ESP32 hardware code
  - Arduino/C++ code examples
  - Required headers
  - Audio upload implementation
  - Text upload implementation
  - Session management
  - Error handling

### Navigation & Reference

- **[DOCS_SUMMARY.md](./DOCS_SUMMARY.md)** - Documentation quick reference
  - Authentication system overview
  - File organization
  - Where to find specific information
  - Recent updates
  - Quick command reference

---

## 🎯 Find What You Need

| I want to... | Read this... |
|--------------|--------------|
| Get started quickly | [QUICK_START.md](./QUICK_START.md) |
| Do a complete setup | [SETUP.md](./SETUP.md) |
| Understand authentication | [AUTHENTICATION.md](./AUTHENTICATION.md) |
| Test without hardware | [SIMULATOR_GUIDE.md](./SIMULATOR_GUIDE.md) |
| Write ESP32 code | [ESP32_INTEGRATION_EXAMPLE.md](./ESP32_INTEGRATION_EXAMPLE.md) |
| Find specific info | [DOCS_SUMMARY.md](./DOCS_SUMMARY.md) |
| See the big picture | [../README.md](../README.md) |

---

## 🔐 Authentication Quick Reference

Your backend uses **custom header-based authentication**:

**Required Headers:**
- `X-Email` - User's email address
- `X-User-ID` - Firebase user ID
- `X-Device-ID` - Device/toy identifier
- `X-Session-ID` - Session identifier (optional)
- `X-Child-ID` - Child ID (optional, for conversations)
- `X-Toy-ID` - Toy ID (optional, for conversations)

**How it works:**
1. Device sends headers with request
2. Middleware validates against Firestore
3. In-memory cache (5-min TTL) improves performance
4. Request proceeds with `request.auth_context` available

See [AUTHENTICATION.md](./AUTHENTICATION.md) for complete details.

---

## 🛠️ Quick Commands

### Start Backend
```bash
source venv/bin/activate
python app.py
```

### Test Authentication
```bash
curl -X GET http://localhost:5005/auth/test \
  -H "X-User-ID: test_user_1763434576" \
  -H "X-Device-ID: test_toy_1763434576" \
  -H "X-Email: test@lunotoys.com"
```

### Create Test Data
```bash
python setup_test_data.py
```

### Open Web Simulator
```
http://localhost:5005/simulator
```

---

## 📁 File Organization

### Configuration Files
```
backend/
├── .env                          # Environment variables
├── .gitignore                    # Git ignore rules
├── firebase-credentials.json     # Firebase service account key
└── simulator_config.json         # Simulator configuration
```

### Core Backend Files
```
backend/
├── app.py                        # Main Flask application
├── auth_middleware.py            # Authentication middleware
├── firebase_config.py            # Firebase initialization
├── firestore_service.py          # Firestore operations
├── gpt_reply.py                  # GPT conversation logic
├── whisper_stt.py                # Speech-to-text
├── tts_elevenlabs.py             # Text-to-speech
└── requirements.txt              # Python dependencies
```

### Testing/Development
```
backend/
├── esp32_simulator.py            # CLI simulator
├── simulator.html                # Web simulator
└── setup_test_data.py            # Test data creation
```

---

## 🔍 Common Tasks

### Setting Up Environment

1. Create `.env` file:
```bash
FIREBASE_SERVICE_ACCOUNT_PATH=firebase-credentials.json
OPENAI_API_KEY=sk-proj-...
ELEVENLABS_API_KEY=...
PORT=5005
```

2. Download Firebase credentials
3. Install dependencies: `pip install -r requirements.txt`
4. Start server: `python app.py`

See [SETUP.md](./SETUP.md) for details.

### Testing Authentication

1. Create test account: `python setup_test_data.py`
2. Test auth endpoint:
```bash
curl http://localhost:5005/auth/test \
  -H "X-User-ID: test_user_1763434576" \
  -H "X-Device-ID: test_toy_1763434576" \
  -H "X-Email: test@lunotoys.com"
```

See [AUTHENTICATION.md](./AUTHENTICATION.md) for details.

### Using Simulators

**Web Simulator:**
- Open: `http://localhost:5005/simulator`
- Configure settings
- Send text or record audio
- View responses

**CLI Simulator:**
```bash
python esp32_simulator.py
# Press 1 for text mode
# Press 2 for audio recording
# Press 7 to test authentication
```

See [SIMULATOR_GUIDE.md](./SIMULATOR_GUIDE.md) for details.

---

## 🐛 Troubleshooting

### Quick Fixes

| Issue | Solution | Doc Reference |
|-------|----------|---------------|
| Firebase not initializing | Check `.env` file and `firebase-credentials.json` | [SETUP.md](./SETUP.md) |
| Authentication failing | Verify headers and Firestore data | [AUTHENTICATION.md](./AUTHENTICATION.md) |
| Can't start server | Check port 5005 availability, verify venv | [SETUP.md](./SETUP.md) |
| Simulator not working | Check backend is running, verify config | [SIMULATOR_GUIDE.md](./SIMULATOR_GUIDE.md) |

---

## 📚 External Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [ElevenLabs API Docs](https://elevenlabs.io/docs)

---

## 🆘 Need Help?

1. Check the relevant documentation file above
2. Look in the "Troubleshooting" section
3. Verify your `.env` file configuration
4. Check backend logs for error messages
5. Test with the provided curl commands

---

**Happy Building! 🚀**

For complete system documentation, see [../README.md](../README.md)
