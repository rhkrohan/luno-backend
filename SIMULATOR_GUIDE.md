# ESP32 Simulator Guide

This guide explains how to use the ESP32 simulators to test the Luno backend locally without needing physical hardware.

---

## 📋 Overview

We provide **two simulators**:

1. **CLI Simulator** (`esp32_simulator.py`) - Terminal-based, full-featured
2. **Web Simulator** (`simulator.html`) - Browser-based, visual interface

Both simulators allow you to:
- Send text messages to the backend
- Record and send audio
- Manage conversation sessions
- View statistics
- Test all backend endpoints

---

## 🖥️ CLI Simulator

### Setup

#### 1. Install Dependencies

```bash
# Install PyAudio (required for audio recording)
# On macOS:
brew install portaudio
pip install pyaudio

# On Ubuntu/Debian:
sudo apt-get install portaudio19-dev
pip install pyaudio

# On Windows:
pip install pyaudio
```

#### 2. Make Script Executable

```bash
chmod +x esp32_simulator.py
```

### Running the CLI Simulator

```bash
python3 esp32_simulator.py
```

You'll see the main menu:

```
============================================================
   🤖 ESP32 Luno Toy Simulator
============================================================

Session ID: esp32_sim_1234567890_abc123
User ID: test_user_123
Child ID: test_child_456
Toy ID: test_toy_789
Backend: http://localhost:5005
Status: 🔴 Idle
Messages: 0

────────────────────────────────────────────────────────────
Main Menu:
  1. Send text message (text mode)
  2. Record and send audio (audio mode)
  3. Send pre-recorded audio file
  4. End conversation
  5. View conversation stats
  6. Configure settings
  7. Test backend connection
  8. New session (reset)
  9. Exit
────────────────────────────────────────────────────────────
```

### Usage Examples

#### Test Connection

```
Select option: 7
```

Output:
```
🔌 Testing connection to http://localhost:5005...
✓ Backend is running!
  Response: ESP32 Toy Backend is running. Broooo its workinggggggggggggg
```

#### Send Text Message

```
Select option: 1
Enter message: Hello Luna, what's the weather like today?
```

Output:
```
📤 Sending text: "Hello Luna, what's the weather like today?"
✓ Response received (3.45s)
  Total: 3.45s
  GPT: 1.20s
  TTS: 2.10s
Saved response: simulator_temp/response_20240115_103045.wav
🔊 Playing response...
✓ Playback complete
```

#### Record Audio

```
Select option: 2
Recording duration (seconds, default 5): 3
```

Output:
```
🎤 Recording... Speak now! (3 seconds)
Recording: ████████████████████ 100%
✓ Recording complete!
Saved to: simulator_temp/recorded_20240115_103045.wav
Send this recording? (y/n): y

📤 Uploading audio: simulator_temp/recorded_20240115_103045.wav
✓ Response received (5.20s)
  Total: 5.20s
  STT: 1.50s
  GPT: 1.60s
  TTS: 2.10s
🔊 Playing response...
```

#### End Conversation

```
Select option: 4
```

Output:
```
🛑 Ending conversation...
✓ Conversation ended successfully
  Messages sent: 5
New session ID: esp32_sim_1234567891_xyz456
```

#### View Stats

```
Select option: 5
```

Output:
```
📊 Fetching stats...

============================================================
User Statistics:
============================================================
  Total Conversations: 12
  Total Duration: 45 minutes
  Flagged Conversations: 1
  Last Activity: 2024-01-15T10:30:45Z
============================================================
```

#### Configure Settings

```
Select option: 6

Configuration:
  1. Change User ID (current: test_user_123)
  2. Change Child ID (current: test_child_456)
  3. Change Toy ID (current: test_toy_789)
  4. Change Backend URL (current: http://localhost:5005)
  5. Toggle auto-play (current: True)
  6. Back to main menu

Select option: 1
Enter new User ID: my_user_id
✓ Configuration saved to simulator_config.json
```

### Configuration File

The CLI simulator saves settings to `simulator_config.json`:

```json
{
  "user_id": "test_user_123",
  "child_id": "test_child_456",
  "toy_id": "test_toy_789",
  "backend_url": "http://localhost:5005",
  "auto_play_response": true,
  "save_conversations": true
}
```

You can edit this file directly to change default settings.

---

## 🌐 Web Simulator

### Setup

**No installation required!** The web simulator runs in your browser.

### Running the Web Simulator

1. **Start the backend**:

```bash
python app.py
```

2. **Open your browser** and navigate to:

```
http://localhost:5005/simulator
```

### Web Interface

The web simulator provides a beautiful, interactive interface:

#### Main Sections

1. **Status Bar** - Shows session ID, status, and message count
2. **Configuration** - Set User ID, Child ID, Toy ID, Backend URL
3. **Text Mode** - Send text messages
4. **Audio Mode** - Record and send audio
5. **Controls** - End conversation, view stats
6. **Logs** - Real-time activity log

### Usage Examples

#### Test Connection

1. Click **"🔌 Test Connection"** button
2. See status in logs

#### Send Text Message

1. Type message in the text input field
2. Click **"📤 Send"** or press Enter
3. Audio response plays automatically
4. See timing breakdown in logs

#### Record Audio

1. Click **"🎤 Start Recording"**
2. Allow microphone access when prompted
3. Speak your message
4. Click **"⏹️ Stop Recording"**
5. Preview the recording (plays automatically)
6. Click **"📤 Send Audio"** to upload
7. Receive and play response

#### End Conversation

1. Click **"🛑 End Conversation"**
2. Session resets automatically
3. New session ID generated

#### View Statistics

1. Click **"📊 Get Stats"**
2. Stats cards appear showing:
   - Total Conversations
   - Total Minutes
   - Flagged Conversations

### Features

✅ **Real-time Logs** - See all activity with timestamps
✅ **Audio Playback** - Automatic playback of responses
✅ **Visual Feedback** - Color-coded status indicators
✅ **Session Management** - Easy session reset
✅ **Timing Info** - See STT, GPT, and TTS performance
✅ **Microphone Access** - Browser-based audio recording
✅ **Responsive Design** - Works on desktop and tablets

---

## 🔧 Troubleshooting

### CLI Simulator Issues

#### "PyAudio not found"

```bash
# Install portaudio first
# macOS:
brew install portaudio

# Ubuntu/Debian:
sudo apt-get install portaudio19-dev python3-pyaudio

# Then:
pip install pyaudio
```

#### "Connection failed"

- Ensure backend is running: `python app.py`
- Check backend URL in configuration
- Verify firewall settings

#### "No audio output"

- Check system volume
- Ensure speakers/headphones are connected
- Try toggling auto-play: Option 6 → Option 5

### Web Simulator Issues

#### "Microphone access denied"

- Allow microphone permissions in browser
- Chrome: Settings → Privacy → Site Settings → Microphone
- Firefox: Preferences → Privacy → Permissions → Microphone

#### "CORS errors"

The backend already has CORS configured. If you see errors:

```python
# In app.py, add:
from flask_cors import CORS
CORS(app)
```

#### "Can't load page"

- Verify backend is running
- Check URL: `http://localhost:5005/simulator`
- Clear browser cache

---

## 📊 Testing Workflow

### Recommended Testing Flow

1. **Start Backend**
   ```bash
   python app.py
   ```

2. **Test Connection** (CLI or Web)
   - Verify backend is responding

3. **Configure IDs**
   - Set User ID to match Firestore user
   - Set Child ID to match Firestore child
   - Set Toy ID to match Firestore toy

4. **Send Text Messages**
   - Start with simple messages
   - Verify responses make sense
   - Check logs for timing

5. **Test Audio** (if available)
   - Record short audio clip
   - Verify transcription quality
   - Check response audio quality

6. **End Conversation**
   - End the session properly
   - Verify stats updated

7. **Check Firestore**
   - Open Firebase Console
   - Navigate to Firestore
   - Verify conversation and messages were saved

### Test Scenarios

#### Scenario 1: Basic Conversation

```
1. Send: "Hello Luna!"
2. Send: "What's your favorite color?"
3. Send: "Can you tell me a story?"
4. End conversation
5. Check stats
```

#### Scenario 2: Safety Testing

```
1. Send: "My phone number is 555-1234"
   → Should flag for personal info
2. Check Firestore for flagged conversation
3. Review flag in Safety Center
```

#### Scenario 3: Long Conversation

```
1. Send 10+ messages
2. Test context retention (does Luna remember earlier conversation?)
3. End conversation
4. Verify duration and message count in stats
```

#### Scenario 4: Multiple Sessions

```
1. Send messages in Session A
2. End conversation
3. Send messages in Session B (new session)
4. Verify both conversations saved separately in Firestore
```

---

## 🎯 Quick Start Checklist

- [ ] Backend is running (`python app.py`)
- [ ] Firebase credentials configured
- [ ] Firestore database created
- [ ] User document exists in Firestore
- [ ] Child document exists in Firestore
- [ ] Toy document exists (optional)
- [ ] Simulator IDs match Firestore documents
- [ ] Test connection successful
- [ ] First message sent successfully
- [ ] Audio response received
- [ ] Conversation ended properly
- [ ] Data visible in Firebase Console

---

## 📝 Simulator Comparison

| Feature | CLI Simulator | Web Simulator |
|---------|--------------|---------------|
| Text messages | ✅ | ✅ |
| Audio recording | ✅ | ✅ |
| Audio playback | ✅ | ✅ |
| Configuration | ✅ (config file) | ✅ (UI) |
| Stats viewing | ✅ | ✅ |
| Connection test | ✅ | ✅ |
| Real-time logs | ✅ | ✅ |
| Visual interface | ❌ | ✅ |
| Colored output | ✅ | ✅ |
| Session management | ✅ | ✅ |
| Timing breakdown | ✅ | ✅ |
| Pre-recorded audio | ✅ | ❌ |
| Cross-platform | Requires PyAudio | Any browser |

### When to Use Each

**Use CLI Simulator when:**
- You prefer terminal interfaces
- You want to automate testing with scripts
- You need to test pre-recorded audio files
- You're on a server without GUI

**Use Web Simulator when:**
- You prefer visual interfaces
- You want easier access (just open browser)
- You're testing from different devices
- You want to demo to others

---

## 🔍 Advanced Usage

### Automated Testing (CLI)

Create a test script:

```python
#!/usr/bin/env python3
import subprocess
import time

# Test messages
messages = [
    "Hello Luna!",
    "What's 5 plus 5?",
    "Tell me a joke",
    "Goodbye!"
]

for msg in messages:
    # Simulate sending text
    print(f"Testing: {msg}")
    # Add your test logic here
    time.sleep(2)
```

### Integration with CI/CD

```yaml
# .github/workflows/test.yml
name: Test Backend

on: [push]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Start backend
        run: python app.py &
      - name: Run simulator tests
        run: python test_simulator.py
```

---

## 📚 Additional Resources

- [Main README](./README.md) - Complete system documentation
- [Firestore Integration Guide](./FIRESTORE_INTEGRATION_GUIDE.md) - Database setup
- [ESP32 Integration Examples](./ESP32_INTEGRATION_EXAMPLE.md) - Hardware integration

---

## 💡 Tips & Tricks

### CLI Simulator

- Press **Ctrl+C** to interrupt at any time
- Use **Option 8** to quickly reset session
- Edit `simulator_config.json` to change defaults
- Check `simulator_temp/` for saved audio files

### Web Simulator

- Use **Enter key** to send text messages quickly
- Keep browser console open for debug info (F12)
- Test on different browsers for compatibility
- Bookmark `/simulator` for quick access

### General

- Start with text mode (easier to debug)
- Test audio after text is working
- Monitor backend logs in terminal
- Check Firestore console to verify data
- Use different user IDs for testing multiple accounts

---

## 🐛 Known Limitations

### CLI Simulator
- PyAudio installation can be tricky on some systems
- Audio quality depends on system microphone
- Terminal colors may not work on all systems

### Web Simulator
- Requires modern browser (Chrome, Firefox, Edge)
- Audio recording needs HTTPS in production
- Can't upload pre-recorded files (use CLI for this)

---

**Happy Testing! 🚀**

For issues or questions, check the backend logs and Firestore console for detailed debugging information.
