# 📁 Backend Directory Structure

## Organized Layout

```
backend/
├── app.py                         # 🚀 Main Flask application entry point
├── auth_middleware.py             # 🔐 Authentication middleware
├── firebase_config.py             # 🔥 Firebase initialization
├── firestore_service.py           # 🗄️  Firestore operations
├── gpt_reply.py                   # 🤖 GPT conversation logic
├── whisper_stt.py                 # 🎤 Speech-to-text service
├── tts_elevenlabs.py              # 🔊 Text-to-speech (ElevenLabs)
├── tts_speechify.py               # 🔊 Text-to-speech (Speechify)
│
├── simulators/                    # 🎮 Testing simulators
│   ├── esp32_simulator.py         #   CLI simulator
│   ├── simulator.html             #   Web simulator interface
│   └── simulator_config.json      #   Simulator configuration
│
├── scripts/                       # 🔧 Utility scripts
│   ├── setup_test_data.py         #   Create test Firestore data
│   ├── deploy.sh                  #   Deployment script
│   └── start.sh                   #   Start server script
│
├── tests/                         # 🧪 Test files
│   ├── test_auth_workflow.py      #   Auth workflow tests
│   └── test_auth.sh               #   Auth shell script tests
│
├── config/                        # ⚙️  Configuration files
│   ├── gunicorn.conf.py           #   Gunicorn production config
│   ├── nginx.conf                 #   Nginx configuration
│   ├── plushie-ai.service         #   Systemd service file
│   └── firebase_project_config.json  # Firebase project config
│
├── certs/                         # 🔒 SSL certificates
│   └── PlushieAI.pem              #   SSL certificate
│
├── docs/                          # 📚 Documentation
│   ├── README.md                  #   Documentation index
│   ├── QUICK_START.md             #   Quick start guide
│   ├── SETUP.md                   #   Setup instructions
│   ├── AUTHENTICATION.md          #   Auth system docs
│   ├── SIMULATOR_GUIDE.md         #   Simulator usage
│   ├── ESP32_INTEGRATION_EXAMPLE.md  # Hardware integration
│   └── DOCS_SUMMARY.md            #   Documentation summary
│
├── audio/                         # 🎵 Audio files
│   └── filler_audios/             #   Filler audio samples
│
├── temp/                          # 📂 Temporary files
│   └── (runtime generated files)
│
├── backups/                       # 💾 Backup files
│   └── (old/archived files)
│
├── .env                           # 🔑 Environment variables (not in git)
├── .gitignore                     # 🚫 Git ignore rules
├── firebase-credentials.json      # 🔥 Firebase service account key (not in git)
├── requirements.txt               # 📦 Python dependencies
└── README.md                      # 📖 Main documentation
```

## Core Application Files

Keep in root for easy imports:
- `app.py` - Main Flask application
- `auth_middleware.py` - Authentication logic
- `firebase_config.py` - Firebase setup
- `firestore_service.py` - Database operations
- `gpt_reply.py` - AI conversation handler
- `whisper_stt.py` - Speech-to-text
- `tts_*.py` - Text-to-speech services

## Directory Purposes

| Directory | Purpose |
|-----------|---------|
| `simulators/` | ESP32 simulators (CLI and web) for testing without hardware |
| `scripts/` | Utility scripts for deployment, setup, and management |
| `tests/` | All test files and test scripts |
| `config/` | Server configuration files (gunicorn, nginx, systemd) |
| `certs/` | SSL certificates and keys |
| `docs/` | Complete documentation |
| `audio/` | Audio files and samples |
| `temp/` | Temporary runtime files (git ignored) |
| `backups/` | Old files and backups (git ignored) |

## Files Not in Git

These files should be in `.gitignore`:
- `.env` - Environment variables
- `firebase-credentials.json` - Firebase service account key
- `firebase-key.json` - Alternative Firebase key
- `temp/` - Temporary files
- `backups/` - Backup files
- `__pycache__/` - Python cache
- `*.pyc` - Compiled Python files
- `simulator_temp/` - Simulator temporary files

## Running the Application

All commands still work from the backend root:

```bash
# Start development server
python app.py

# Start production server
gunicorn -c config/gunicorn.conf.py app:app

# Run simulators
python simulators/esp32_simulator.py
# or open: http://localhost:5005/simulators/web/simulator.html

# Setup test data
python scripts/setup_test_data.py

# Run tests
python tests/test_auth_workflow.py
bash tests/test_auth.sh
```

## Import Paths

All imports remain unchanged since core files are in root:

```python
from firebase_config import initialize_firebase
from firestore_service import firestore_service
from auth_middleware import require_device_auth
from gpt_reply import get_gpt_reply
# etc.
```
