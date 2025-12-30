# Luno Backend Documentation

Complete documentation for the Luno interactive toy backend system.

---

## Getting Started

New to the project? Start here:

1. **[Quick Start Guide](./guides/QUICK_START.md)** - Get up and running in 5 minutes
2. **[Setup Guide](./guides/SETUP.md)** - Complete setup instructions
3. **[DOCS_SUMMARY.md](./DOCS_SUMMARY.md)** - Documentation quick reference

---

## Documentation Structure

### Deployment
Production deployment and infrastructure guides.

- **[AWS EC2 Deployment](./deployment/AWS_EC2_DEPLOYMENT.md)** - Complete AWS EC2 deployment guide
- **[AWS Deployment Summary](./deployment/AWS_DEPLOYMENT_SUMMARY.md)** - Deployment summary and overview
- **[Deployment Quickstart](./deployment/DEPLOYMENT_QUICKSTART.md)** - Quick deployment instructions

### Guides
Getting started, setup, and testing guides.

- **[Quick Start](./guides/QUICK_START.md)** - Get up and running quickly
- **[Setup Guide](./guides/SETUP.md)** - Complete setup instructions
- **[Simulator Guide](./guides/SIMULATOR_GUIDE.md)** - Testing with CLI simulator
- **[Simulator Setup Guide](./guides/SIMULATOR_SETUP_GUIDE.md)** - Simulator configuration

### API Documentation
Authentication, sessions, and API reference.

- **[Authentication](./api/AUTHENTICATION.md)** - Authentication system guide
- **[Session Management](./api/SESSION_MANAGEMENT.md)** - Session management documentation

### Architecture
System design, structure, and implementation details.

- **[Knowledge Graph](./architecture/KNOWLEDGE_GRAPH.md)** - Knowledge graph overview
- **[Knowledge Graph Implementation](./architecture/KNOWLEDGE_GRAPH_IMPLEMENTATION.md)** - Implementation details
- **[Firestore Restructure Summary](./architecture/FIRESTORE_RESTRUCTURE_SUMMARY.md)** - Database structure
- **[Directory Structure](./architecture/DIRECTORY_STRUCTURE.md)** - Project organization
- **[Organization Summary](./architecture/ORGANIZATION_SUMMARY.md)** - Overall system organization

### Examples
Hardware integration and code examples.

- **[ESP32 Integration Example](./examples/ESP32_INTEGRATION_EXAMPLE.md)** - ESP32 hardware code examples

---

## Quick Navigation

| I want to... | Read this... |
|--------------|--------------|
| Get started quickly | [Quick Start](./guides/QUICK_START.md) |
| Set up the backend | [Setup Guide](./guides/SETUP.md) |
| Deploy to production | [AWS EC2 Deployment](./deployment/AWS_EC2_DEPLOYMENT.md) |
| Understand authentication | [Authentication](./api/AUTHENTICATION.md) |
| Test without hardware | [Simulator Guide](./guides/SIMULATOR_GUIDE.md) |
| Write ESP32 code | [ESP32 Integration](./examples/ESP32_INTEGRATION_EXAMPLE.md) |
| Understand the architecture | [Directory Structure](./architecture/DIRECTORY_STRUCTURE.md) |
| Learn about knowledge graphs | [Knowledge Graph](./architecture/KNOWLEDGE_GRAPH.md) |

---

## Authentication Quick Reference

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

See [Authentication Documentation](./api/AUTHENTICATION.md) for complete details.

---

## Quick Commands

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

## File Organization

### Configuration Files
```
backend/
├── .env                          # Environment variables (DO NOT COMMIT)
├── .env.example                  # Environment template
├── .gitignore                    # Git ignore rules
├── firebase-credentials.json     # Firebase service account key (DO NOT COMMIT)
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
├── knowledge_graph_service.py    # Knowledge graph functionality
├── graph_query_service.py        # Graph query operations
├── session_manager.py            # Session management
├── whisper_stt.py                # Speech-to-text
├── tts_elevenlabs.py             # Text-to-speech
└── requirements.txt              # Python dependencies
```

### Documentation Structure
```
backend/docs/
├── README.md                     # This file
├── DOCS_SUMMARY.md               # Quick reference
├── deployment/                   # Deployment guides
├── guides/                       # Setup and testing guides
├── api/                          # API documentation
├── architecture/                 # System architecture docs
└── examples/                     # Code examples
```

---

## Troubleshooting

### Quick Fixes

| Issue | Solution | Doc Reference |
|-------|----------|---------------|
| Firebase not initializing | Check `.env` file and `firebase-credentials.json` | [Setup Guide](./guides/SETUP.md) |
| Authentication failing | Verify headers and Firestore data | [Authentication](./api/AUTHENTICATION.md) |
| Can't start server | Check port 5005 availability, verify venv | [Setup Guide](./guides/SETUP.md) |
| Simulator not working | Check backend is running, verify config | [Simulator Guide](./guides/SIMULATOR_GUIDE.md) |
| Deployment issues | Review AWS configuration | [AWS Deployment](./deployment/AWS_EC2_DEPLOYMENT.md) |

---

## Security Notes

**Never commit these files to version control:**
- `.env` - Contains API keys and secrets
- `firebase-credentials.json` - Firebase service account credentials
- `*.pem`, `*.key` - SSL certificates and private keys
- Any files in `certs/` directory

The `.gitignore` file is configured to protect these files automatically.

---

## External Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [ElevenLabs API Docs](https://elevenlabs.io/docs)

---

## Need Help?

1. Check the relevant documentation file above
2. Look in the "Troubleshooting" section
3. Verify your `.env` file configuration
4. Check backend logs for error messages
5. Test with the provided curl commands

---

**Happy Building!**

For complete system documentation, see [../README.md](../README.md)
