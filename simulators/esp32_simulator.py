#!/usr/bin/env python3
"""
ESP32 Virtual Simulator
Simulates an ESP32 Luno toy for testing the backend locally
"""

import os
import sys
import time
import wave
import json
import requests
import pyaudio
import uuid
from datetime import datetime
from pathlib import Path

# Configuration
CONFIG_FILE = "simulators/simulator_config.json"
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:5005")
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5
TEMP_DIR = "simulator_temp"

# Colors for CLI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'

class ESP32Simulator:
    def __init__(self):
        self.config = self.load_config()
        self.session_id = self.generate_session_id()
        self.conversation_active = False
        self.message_count = 0
        os.makedirs(TEMP_DIR, exist_ok=True)

        # Audio setup
        self.audio = pyaudio.PyAudio()

    def load_config(self):
        """Load simulator configuration"""
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        else:
            # Default configuration
            default_config = {
                "user_id": "test_user_123",
                "child_id": "test_child_456",
                "toy_id": "test_toy_789",
                "email": "test@lunotoys.com",
                "backend_url": BACKEND_URL,
                "auto_play_response": True,
                "save_conversations": True
            }
            self.save_config(default_config)
            return default_config

    def save_config(self, config):
        """Save configuration to file"""
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
        print(f"{Colors.GREEN}✓ Configuration saved to {CONFIG_FILE}{Colors.END}")

    def generate_session_id(self):
        """Generate unique session ID"""
        timestamp = int(time.time())
        unique_id = str(uuid.uuid4())[:8]
        return f"esp32_sim_{timestamp}_{unique_id}"

    def print_header(self):
        """Print simulator header"""
        print(f"\n{Colors.HEADER}{'='*60}{Colors.END}")
        print(f"{Colors.HEADER}{Colors.BOLD}   🤖 ESP32 Luno Toy Simulator{Colors.END}")
        print(f"{Colors.HEADER}{'='*60}{Colors.END}\n")
        print(f"{Colors.CYAN}Session ID:{Colors.END} {self.session_id}")
        print(f"{Colors.CYAN}User ID:{Colors.END} {self.config['user_id']}")
        print(f"{Colors.CYAN}Email:{Colors.END} {self.config.get('email', 'N/A')}")
        print(f"{Colors.CYAN}Child ID:{Colors.END} {self.config['child_id']}")
        print(f"{Colors.CYAN}Toy ID:{Colors.END} {self.config['toy_id']}")
        print(f"{Colors.CYAN}Backend:{Colors.END} {self.config['backend_url']}")
        print(f"{Colors.CYAN}Status:{Colors.END} {'🟢 Active' if self.conversation_active else '🔴 Idle'}")
        print(f"{Colors.CYAN}Messages:{Colors.END} {self.message_count}\n")

    def print_menu(self):
        """Print main menu"""
        print(f"{Colors.BLUE}{'─'*60}{Colors.END}")
        print(f"{Colors.BOLD}Main Menu:{Colors.END}")
        print(f"  {Colors.GREEN}1.{Colors.END} Send text message (text mode)")
        print(f"  {Colors.GREEN}2.{Colors.END} Record and send audio (audio mode)")
        print(f"  {Colors.GREEN}3.{Colors.END} Send pre-recorded audio file")
        print(f"  {Colors.GREEN}4.{Colors.END} End conversation")
        print(f"  {Colors.GREEN}5.{Colors.END} View conversation stats")
        print(f"  {Colors.GREEN}6.{Colors.END} Configure settings")
        print(f"  {Colors.GREEN}7.{Colors.END} Test authentication")
        print(f"  {Colors.GREEN}8.{Colors.END} Test backend connection")
        print(f"  {Colors.GREEN}9.{Colors.END} New session (reset)")
        print(f"  {Colors.GREEN}0.{Colors.END} Exit")
        print(f"{Colors.BLUE}{'─'*60}{Colors.END}\n")

    def record_audio(self, duration=RECORD_SECONDS):
        """Record audio from microphone"""
        print(f"\n{Colors.WARNING}🎤 Recording... Speak now! ({duration} seconds){Colors.END}")

        stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=RATE,
            input=True,
            frames_per_buffer=CHUNK
        )

        frames = []
        for i in range(0, int(RATE / CHUNK * duration)):
            data = stream.read(CHUNK)
            frames.append(data)

            # Progress indicator
            if i % 10 == 0:
                progress = (i / (RATE / CHUNK * duration)) * 100
                print(f"\rRecording: {'█' * int(progress/5)}{' ' * (20-int(progress/5))} {progress:.0f}%", end='')

        print(f"\r{Colors.GREEN}✓ Recording complete!{Colors.END}" + " " * 30)

        stream.stop_stream()
        stream.close()

        # Save to WAV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(TEMP_DIR, f"recorded_{timestamp}.wav")

        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(self.audio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        print(f"{Colors.CYAN}Saved to: {filename}{Colors.END}")
        return filename

    def play_audio(self, filename):
        """Play audio file"""
        if not os.path.exists(filename):
            print(f"{Colors.FAIL}❌ Audio file not found: {filename}{Colors.END}")
            return

        print(f"\n{Colors.GREEN}🔊 Playing response...{Colors.END}")

        wf = wave.open(filename, 'rb')

        stream = self.audio.open(
            format=self.audio.get_format_from_width(wf.getsampwidth()),
            channels=wf.getnchannels(),
            rate=wf.getframerate(),
            output=True
        )

        data = wf.readframes(CHUNK)
        while data:
            stream.write(data)
            data = wf.readframes(CHUNK)

        stream.stop_stream()
        stream.close()
        wf.close()

        print(f"{Colors.GREEN}✓ Playback complete{Colors.END}")

    def send_text_message(self, text):
        """Send text message to backend (simulates local STT)"""
        print(f"\n{Colors.CYAN}📤 Sending text: \"{text}\"{Colors.END}")

        url = f"{self.config['backend_url']}/text_upload"

        headers = {
            "Content-Type": "application/json",
            "X-Session-ID": self.session_id,
            "X-User-ID": self.config['user_id'],
            "X-Child-ID": self.config['child_id'],
            "X-Device-ID": self.config['toy_id'],
            "X-Email": self.config.get('email', ''),
        }

        payload = {
            "text": text,
            "session_id": self.session_id,
            "user_id": self.config['user_id'],
            "child_id": self.config['child_id'],
            "toy_id": self.config['toy_id']
        }

        try:
            start_time = time.time()
            response = requests.post(url, json=payload, headers=headers)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                print(f"{Colors.GREEN}✓ Response received ({elapsed:.2f}s){Colors.END}")

                # Show timing breakdown
                if 'X-Response-Time' in response.headers:
                    print(f"  Total: {response.headers.get('X-Response-Time')}s")
                    print(f"  GPT: {response.headers.get('X-GPT-Time', 'N/A')}s")
                    print(f"  TTS: {response.headers.get('X-TTS-Time', 'N/A')}s")

                # Save response audio
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                audio_filename = os.path.join(TEMP_DIR, f"response_{timestamp}.wav")

                with open(audio_filename, 'wb') as f:
                    f.write(response.content)

                print(f"{Colors.CYAN}Saved response: {audio_filename}{Colors.END}")

                # Auto-play if enabled
                if self.config.get('auto_play_response', True):
                    self.play_audio(audio_filename)

                self.conversation_active = True
                self.message_count += 1

                return True
            else:
                print(f"{Colors.FAIL}❌ Error {response.status_code}: {response.text}{Colors.END}")
                return False

        except requests.exceptions.ConnectionError:
            print(f"{Colors.FAIL}❌ Connection failed. Is the backend running at {self.config['backend_url']}?{Colors.END}")
            return False
        except Exception as e:
            print(f"{Colors.FAIL}❌ Error: {e}{Colors.END}")
            return False

    def send_audio_file(self, audio_filename):
        """Send audio file to backend (simulates ESP32 audio upload)"""
        if not os.path.exists(audio_filename):
            print(f"{Colors.FAIL}❌ Audio file not found: {audio_filename}{Colors.END}")
            return False

        print(f"\n{Colors.CYAN}📤 Uploading audio: {audio_filename}{Colors.END}")

        url = f"{self.config['backend_url']}/upload"

        headers = {
            "Content-Type": "audio/wav",
            "X-Session-ID": self.session_id,
            "X-User-ID": self.config['user_id'],
            "X-Child-ID": self.config['child_id'],
            "X-Device-ID": self.config['toy_id'],
            "X-Email": self.config.get('email', ''),
        }

        try:
            with open(audio_filename, 'rb') as f:
                audio_data = f.read()

            start_time = time.time()
            response = requests.post(url, data=audio_data, headers=headers)
            elapsed = time.time() - start_time

            if response.status_code == 200:
                print(f"{Colors.GREEN}✓ Response received ({elapsed:.2f}s){Colors.END}")

                # Show timing breakdown
                if 'X-Response-Time' in response.headers:
                    print(f"  Total: {response.headers.get('X-Response-Time')}s")
                    print(f"  STT: {response.headers.get('X-STT-Time', 'N/A')}s")
                    print(f"  GPT: {response.headers.get('X-GPT-Time', 'N/A')}s")
                    print(f"  TTS: {response.headers.get('X-TTS-Time', 'N/A')}s")

                # Save response audio
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                response_filename = os.path.join(TEMP_DIR, f"response_{timestamp}.wav")

                with open(response_filename, 'wb') as f:
                    f.write(response.content)

                print(f"{Colors.CYAN}Saved response: {response_filename}{Colors.END}")

                # Auto-play if enabled
                if self.config.get('auto_play_response', True):
                    self.play_audio(response_filename)

                self.conversation_active = True
                self.message_count += 1

                return True
            else:
                print(f"{Colors.FAIL}❌ Error {response.status_code}: {response.text}{Colors.END}")
                return False

        except Exception as e:
            print(f"{Colors.FAIL}❌ Error: {e}{Colors.END}")
            return False

    def end_conversation(self):
        """End the current conversation"""
        if not self.conversation_active:
            print(f"{Colors.WARNING}⚠ No active conversation{Colors.END}")
            return

        print(f"\n{Colors.CYAN}🛑 Ending conversation...{Colors.END}")

        url = f"{self.config['backend_url']}/api/conversations/end"

        payload = {
            "session_id": self.session_id
        }

        try:
            response = requests.post(url, json=payload)

            if response.status_code == 200:
                print(f"{Colors.GREEN}✓ Conversation ended successfully{Colors.END}")
                print(f"  Messages sent: {self.message_count}")
                self.conversation_active = False

                # Generate new session ID for next conversation
                self.session_id = self.generate_session_id()
                print(f"{Colors.CYAN}New session ID: {self.session_id}{Colors.END}")

                return True
            else:
                print(f"{Colors.FAIL}❌ Error ending conversation: {response.text}{Colors.END}")
                return False

        except Exception as e:
            print(f"{Colors.FAIL}❌ Error: {e}{Colors.END}")
            return False

    def get_conversation_stats(self):
        """Get conversation statistics from backend"""
        print(f"\n{Colors.CYAN}📊 Fetching stats...{Colors.END}")

        url = f"{self.config['backend_url']}/api/users/{self.config['user_id']}/stats"

        try:
            response = requests.get(url)

            if response.status_code == 200:
                data = response.json()
                stats = data.get('stats', {})

                print(f"\n{Colors.GREEN}{'='*60}{Colors.END}")
                print(f"{Colors.BOLD}User Statistics:{Colors.END}")
                print(f"{Colors.GREEN}{'='*60}{Colors.END}")
                print(f"  Total Conversations: {stats.get('totalConversations', 0)}")
                print(f"  Total Duration: {stats.get('totalConversationDurationSec', 0) // 60} minutes")
                print(f"  Flagged Conversations: {stats.get('flaggedConversations', 0)}")
                print(f"  Last Activity: {stats.get('lastConversationAt', 'N/A')}")
                print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")

                return True
            else:
                print(f"{Colors.FAIL}❌ Error fetching stats: {response.text}{Colors.END}")
                return False

        except Exception as e:
            print(f"{Colors.FAIL}❌ Error: {e}{Colors.END}")
            return False

    def configure_settings(self):
        """Configure simulator settings"""
        print(f"\n{Colors.BOLD}Configuration:{Colors.END}")
        print(f"  1. Change User ID (current: {self.config['user_id']})")
        print(f"  2. Change Email (current: {self.config.get('email', 'NOT SET')})")
        print(f"  3. Change Child ID (current: {self.config['child_id']})")
        print(f"  4. Change Toy ID (current: {self.config['toy_id']})")
        print(f"  5. Change Backend URL (current: {self.config['backend_url']})")
        print(f"  6. Toggle auto-play (current: {self.config.get('auto_play_response', True)})")
        print(f"  7. Back to main menu")

        choice = input(f"\n{Colors.CYAN}Select option: {Colors.END}").strip()

        if choice == "1":
            new_value = input(f"{Colors.CYAN}Enter new User ID: {Colors.END}").strip()
            if new_value:
                self.config['user_id'] = new_value
                self.save_config(self.config)
        elif choice == "2":
            new_value = input(f"{Colors.CYAN}Enter new Email: {Colors.END}").strip()
            if new_value:
                self.config['email'] = new_value
                self.save_config(self.config)
        elif choice == "3":
            new_value = input(f"{Colors.CYAN}Enter new Child ID: {Colors.END}").strip()
            if new_value:
                self.config['child_id'] = new_value
                self.save_config(self.config)
        elif choice == "4":
            new_value = input(f"{Colors.CYAN}Enter new Toy ID: {Colors.END}").strip()
            if new_value:
                self.config['toy_id'] = new_value
                self.save_config(self.config)
        elif choice == "5":
            new_value = input(f"{Colors.CYAN}Enter new Backend URL: {Colors.END}").strip()
            if new_value:
                self.config['backend_url'] = new_value
                self.save_config(self.config)
        elif choice == "6":
            self.config['auto_play_response'] = not self.config.get('auto_play_response', True)
            self.save_config(self.config)
            print(f"{Colors.GREEN}✓ Auto-play: {self.config['auto_play_response']}{Colors.END}")

    def test_authentication(self):
        """Test device authentication with backend"""
        print(f"\n{Colors.CYAN}🔐 Testing authentication...{Colors.END}")
        print(f"{Colors.CYAN}{'─'*60}{Colors.END}")
        print(f"  User ID:   {self.config['user_id']}")
        print(f"  Email:     {self.config.get('email', 'NOT SET')}")
        print(f"  Toy ID:    {self.config['toy_id']}")
        print(f"  Session:   {self.session_id}")
        print(f"{Colors.CYAN}{'─'*60}{Colors.END}\n")

        url = f"{self.config['backend_url']}/auth/test"

        headers = {
            "X-Session-ID": self.session_id,
            "X-User-ID": self.config['user_id'],
            "X-Device-ID": self.config['toy_id'],
            "X-Email": self.config.get('email', ''),
        }

        try:
            print(f"{Colors.CYAN}Sending authentication request...{Colors.END}")
            response = requests.get(url, headers=headers, timeout=5)

            if response.status_code == 200:
                data = response.json()
                print(f"\n{Colors.GREEN}✓ AUTHENTICATION SUCCESSFUL!{Colors.END}")
                print(f"{Colors.GREEN}{'='*60}{Colors.END}")
                print(f"  {Colors.BOLD}User ID:{Colors.END} {data.get('user_id')}")
                print(f"  {Colors.BOLD}Email:{Colors.END} {data.get('email')}")
                print(f"  {Colors.BOLD}Toy ID:{Colors.END} {data.get('toy_id')}")
                print(f"  {Colors.BOLD}Device Name:{Colors.END} {data.get('device_name', 'N/A')}")
                print(f"  {Colors.BOLD}Assigned Child:{Colors.END} {data.get('assigned_child', 'N/A')}")
                print(f"  {Colors.BOLD}Device Status:{Colors.END} {data.get('device_status', 'N/A')}")
                print(f"{Colors.GREEN}{'='*60}{Colors.END}\n")
                return True
            elif response.status_code == 400:
                error_data = response.json()
                print(f"\n{Colors.FAIL}✗ AUTHENTICATION FAILED - Missing Headers{Colors.END}")
                print(f"  Error: {error_data.get('error', 'Unknown error')}")
                print(f"  {Colors.WARNING}Tip: Check your configuration settings{Colors.END}\n")
                return False
            elif response.status_code == 403:
                error_data = response.json()
                print(f"\n{Colors.FAIL}✗ AUTHENTICATION FAILED - Forbidden{Colors.END}")
                print(f"  Error: {error_data.get('error', 'Unknown error')}")
                print(f"  {Colors.WARNING}Tip: Email or device not associated with user account{Colors.END}\n")
                return False
            elif response.status_code == 404:
                error_data = response.json()
                print(f"\n{Colors.FAIL}✗ AUTHENTICATION FAILED - Not Found{Colors.END}")
                print(f"  Error: {error_data.get('error', 'Unknown error')}")
                print(f"  {Colors.WARNING}Tip: User ID not found in database{Colors.END}\n")
                return False
            else:
                print(f"\n{Colors.FAIL}✗ AUTHENTICATION FAILED - Status {response.status_code}{Colors.END}")
                print(f"  Response: {response.text}\n")
                return False

        except requests.exceptions.ConnectionError:
            print(f"\n{Colors.FAIL}❌ Connection failed. Is the backend running at {self.config['backend_url']}?{Colors.END}\n")
            return False
        except Exception as e:
            print(f"\n{Colors.FAIL}❌ Error: {e}{Colors.END}\n")
            return False

    def test_connection(self):
        """Test backend connection"""
        print(f"\n{Colors.CYAN}🔌 Testing connection to {self.config['backend_url']}...{Colors.END}")

        try:
            response = requests.get(self.config['backend_url'], timeout=5)
            if response.status_code == 200:
                print(f"{Colors.GREEN}✓ Backend is running!{Colors.END}")
                print(f"  Response: {response.text}")
                return True
            else:
                print(f"{Colors.WARNING}⚠ Backend responded with status {response.status_code}{Colors.END}")
                return False
        except requests.exceptions.ConnectionError:
            print(f"{Colors.FAIL}❌ Connection failed. Is the backend running?{Colors.END}")
            return False
        except Exception as e:
            print(f"{Colors.FAIL}❌ Error: {e}{Colors.END}")
            return False

    def reset_session(self):
        """Reset to new session"""
        self.session_id = self.generate_session_id()
        self.conversation_active = False
        self.message_count = 0
        print(f"{Colors.GREEN}✓ New session started: {self.session_id}{Colors.END}")

    def run(self):
        """Main simulator loop"""
        try:
            while True:
                self.print_header()
                self.print_menu()

                choice = input(f"{Colors.CYAN}Select option: {Colors.END}").strip()

                if choice == "1":
                    # Text mode
                    text = input(f"\n{Colors.CYAN}Enter message: {Colors.END}").strip()
                    if text:
                        self.send_text_message(text)
                    else:
                        print(f"{Colors.WARNING}⚠ Empty message{Colors.END}")

                elif choice == "2":
                    # Audio recording mode
                    duration = input(f"\n{Colors.CYAN}Recording duration (seconds, default 5): {Colors.END}").strip()
                    duration = int(duration) if duration else 5

                    audio_file = self.record_audio(duration)

                    confirm = input(f"{Colors.CYAN}Send this recording? (y/n): {Colors.END}").strip().lower()
                    if confirm == 'y':
                        self.send_audio_file(audio_file)

                elif choice == "3":
                    # Send pre-recorded file
                    filename = input(f"\n{Colors.CYAN}Enter audio file path: {Colors.END}").strip()
                    if filename:
                        self.send_audio_file(filename)

                elif choice == "4":
                    # End conversation
                    self.end_conversation()

                elif choice == "5":
                    # View stats
                    self.get_conversation_stats()

                elif choice == "6":
                    # Configure
                    self.configure_settings()

                elif choice == "7":
                    # Test authentication
                    self.test_authentication()

                elif choice == "8":
                    # Test connection
                    self.test_connection()

                elif choice == "9":
                    # Reset session
                    self.reset_session()

                elif choice == "0":
                    # Exit
                    print(f"\n{Colors.GREEN}👋 Goodbye!{Colors.END}\n")
                    break

                else:
                    print(f"{Colors.WARNING}⚠ Invalid option{Colors.END}")

                input(f"\n{Colors.CYAN}Press Enter to continue...{Colors.END}")
                print("\n" * 2)

        except KeyboardInterrupt:
            print(f"\n\n{Colors.WARNING}Interrupted by user{Colors.END}")

        finally:
            self.audio.terminate()
            print(f"{Colors.GREEN}Simulator terminated{Colors.END}\n")


if __name__ == "__main__":
    simulator = ESP32Simulator()
    simulator.run()
