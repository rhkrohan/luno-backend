# ESP32 Toy Backend 123
from dotenv import load_dotenv
from flask import Flask, request, send_file, jsonify
import os, datetime, time
import struct
import wave
from google.cloud import firestore

# Load environment variables from .env file
load_dotenv()

from whisper_stt import transcribe_audio
from gpt_reply import get_gpt_reply
from tts_elevenlabs import synthesize_speech
from firebase_config import initialize_firebase
from firestore_service import firestore_service
from auth_middleware import require_device_auth

app = Flask(__name__)
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# Initialize Firebase on startup
initialize_firebase()

# Track active conversations: session_id -> {conversation_id, user_id, child_id, start_time}
ACTIVE_CONVERSATIONS = {}


def get_or_create_conversation(session_id, user_id, child_id, toy_id=None):
    """
    Get existing conversation for session or create a new one

    Args:
        session_id: ESP32 session ID
        user_id: Parent user ID
        child_id: Child ID
        toy_id: Optional toy ID

    Returns:
        conversation_id: The active conversation ID
    """
    # Check if conversation already exists for this session
    if session_id in ACTIVE_CONVERSATIONS:
        conv_data = ACTIVE_CONVERSATIONS[session_id]
        print(f"[INFO] Using existing conversation {conv_data['conversation_id']} for session {session_id}")
        return conv_data['conversation_id']

    # Create new conversation in Firestore
    conversation_id = firestore_service.create_conversation(
        user_id=user_id,
        child_id=child_id,
        toy_id=toy_id,
        conversation_type="conversation"
    )

    if conversation_id:
        # Track active conversation
        ACTIVE_CONVERSATIONS[session_id] = {
            'conversation_id': conversation_id,
            'user_id': user_id,
            'child_id': child_id,
            'toy_id': toy_id,
            'start_time': time.time(),
            'message_count': 0,
        }
        print(f"[INFO] Created new conversation {conversation_id} for session {session_id}")
    else:
        print(f"[WARNING] Failed to create conversation in Firestore for session {session_id}")

    return conversation_id


def end_conversation_session(session_id):
    """
    End a conversation session and update Firestore

    Args:
        session_id: ESP32 session ID
    """
    if session_id not in ACTIVE_CONVERSATIONS:
        print(f"[WARNING] No active conversation found for session {session_id}")
        return

    conv_data = ACTIVE_CONVERSATIONS[session_id]

    # Calculate duration
    duration_seconds = time.time() - conv_data['start_time']
    duration_minutes = int(duration_seconds / 60)

    # End conversation in Firestore
    firestore_service.end_conversation(
        user_id=conv_data['user_id'],
        child_id=conv_data['child_id'],
        conversation_id=conv_data['conversation_id'],
        duration_minutes=duration_minutes
    )

    # Remove from active conversations
    del ACTIVE_CONVERSATIONS[session_id]

    print(f"[INFO] Ended conversation session {session_id}, duration: {duration_minutes}m")


def decompress_adpcm_to_wav(adpcm_data, output_path, sample_rate=16000):
    """
    Decompress ADPCM data to WAV format
    Assumes IMA ADPCM format commonly used by ESP32
    """
    try:
        # IMA ADPCM step size table
        step_table = [
            7, 8, 9, 10, 11, 12, 13, 14, 16, 17,
            19, 21, 23, 25, 28, 31, 34, 37, 41, 45,
            50, 55, 60, 66, 73, 80, 88, 97, 107, 118,
            130, 143, 157, 173, 190, 209, 230, 253, 279, 307,
            337, 371, 408, 449, 494, 544, 598, 658, 724, 796,
            876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066,
            2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
            5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899,
            15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767
        ]
        
        # Index table for IMA ADPCM (matches ESP32 implementation)
        index_table = [-1, -1, -1, -1, 2, 4, 6, 8, -1, -1, -1, -1, 2, 4, 6, 8]
        
        # Initialize decoder state
        predicted_sample = 0
        step_index = 0
        decoded_samples = []
        
        # Process ADPCM data
        for byte in adpcm_data:
            # Each byte contains two 4-bit ADPCM samples
            for nibble in [(byte & 0x0F), (byte >> 4)]:
                step = step_table[step_index]
                
                # Decode the nibble (matching ESP32 encoder logic)
                diffq = step >> 3
                if nibble & 4:
                    diffq += step
                if nibble & 2:
                    diffq += step >> 1
                if nibble & 1:
                    diffq += step >> 2
                
                if nibble & 8:
                    predicted_sample -= diffq
                else:
                    predicted_sample += diffq
                
                # Clamp to 16-bit range
                predicted_sample = max(-32768, min(32767, predicted_sample))
                decoded_samples.append(predicted_sample)
                
                # Update step index
                step_index += index_table[nibble]
                step_index = max(0, min(88, step_index))
        
        # Convert to bytes (16-bit PCM)
        pcm_data = struct.pack('<' + 'h' * len(decoded_samples), *decoded_samples)
        
        # Write WAV file
        with wave.open(output_path, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        
        print(f"[INFO] ADPCM decompressed: {len(adpcm_data)} bytes -> {len(decoded_samples)} samples")
        return True
        
    except Exception as e:
        print(f"[ERROR] ADPCM decompression failed: {str(e)}")
        return False

@app.route("/")
def index():
    return "ESP32 Toy Backend is running. Broooo its workinggggggggggggg"

@app.route("/simulator")
def simulator():
    """Serve the web-based ESP32 simulator"""
    return send_file("simulators/simulator.html")

@app.route("/simulator_config.json")
def simulator_config():
    """Serve the simulator configuration file"""
    return send_file("simulators/simulator_config.json")

@app.route("/upload", methods=["POST"])
@require_device_auth
def upload_audio():
    # Start timing measurements
    start_time = time.time()
    timing_log = {"start": start_time}
    
    # 1. Receive audio
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = os.path.join(TEMP_DIR, f"input_{timestamp}.wav")
    adpcm_path = os.path.join(TEMP_DIR, f"adpcm_{timestamp}.bin")

    # Get session ID and metadata from headers
    session_id = request.headers.get('X-Session-ID', 'esp32_audio_default')
    user_id = request.headers.get('X-User-ID')
    child_id = request.headers.get('X-Child-ID')
    toy_id = request.headers.get('X-Toy-ID')

    # Fallback: If child_id not provided, use toy's assigned child
    if not child_id and hasattr(request, 'auth_context'):
        child_id = request.auth_context.get('toy_data', {}).get('assignedChildId')
        if child_id:
            print(f"[INFO] Using toy's assigned child ID: {child_id}")

    # Get or create conversation if metadata is provided
    conversation_id = None
    if user_id and child_id:
        conversation_id = get_or_create_conversation(session_id, user_id, child_id, toy_id)
        print(f"[INFO] Conversation ID: {conversation_id}")
    else:
        print(f"[WARNING] Missing user/child metadata - Firestore tracking disabled for this request")

    if "audio" in request.files:               # multipart
        # Save the uploaded file temporarily
        request.files["audio"].save(adpcm_path)
        audio_data = request.files["audio"].read()
        request.files["audio"].seek(0)  # Reset file pointer for potential re-read
        request.files["audio"].save(adpcm_path)
    else:                                      # raw body
        audio_data = request.data
        with open(adpcm_path, "wb") as f:
            f.write(audio_data)

    # Detect format and handle accordingly
    content_type = request.content_type or request.headers.get('Content-Type', '')
    
    if content_type == "audio/adpcm" or request.headers.get('X-Audio-Format') == 'adpcm':
        # ADPCM format - decompress to WAV
        print(f"[INFO] Processing ADPCM audio ({len(audio_data)} bytes) (Session: {session_id})")
        
        if not decompress_adpcm_to_wav(audio_data, input_path):
            return jsonify({"error": "ADPCM decompression failed"}), 500
            
        print(f"[INFO] ADPCM decompressed => {input_path}")
        
    elif content_type == "audio/wav":
        # Already WAV format - save directly
        with open(input_path, "wb") as f:
            f.write(audio_data)
        print(f"[INFO] Saved WAV audio => {input_path} (Session: {session_id})")
        
    else:
        # Assume ADPCM by default for ESP32 compatibility
        print(f"[INFO] No format specified, assuming ADPCM ({len(audio_data)} bytes) (Session: {session_id})")
        
        if not decompress_adpcm_to_wav(audio_data, input_path):
            return jsonify({"error": "ADPCM decompression failed"}), 500
            
        print(f"[INFO] ADPCM decompressed => {input_path}")

    timing_log["audio_saved"] = time.time()

    # 2. STT (Server-side Whisper API)
    stt_start = time.time()
    print(f"[INFO] Starting server-side STT for session: {session_id}")
    user_text = transcribe_audio(input_path)
    if not user_text:
        print("[ERROR] Server STT failed - no transcription returned")
        return jsonify({"error": "Speech transcription failed"}), 500
    timing_log["stt_complete"] = time.time()
    stt_time = timing_log["stt_complete"] - stt_start
    print(f"[TRANSCRIPT] '{user_text}' (took {stt_time:.2f}s)")

    # 3. GPT with memory context (includes Firestore saving)
    gpt_start = time.time()
    gpt_reply = get_gpt_reply(
        user_text=user_text,
        session_id=session_id,
        user_id=user_id,
        child_id=child_id,
        conversation_id=conversation_id
    )
    timing_log["gpt_complete"] = time.time()
    print("[GPT]", gpt_reply)

    # 4. TTS
    tts_start = time.time()
    output_path = os.path.join(TEMP_DIR, f"reply_{timestamp}.wav")
    print(f"[DEBUG] Expected output path: {os.path.abspath(output_path)}")
    synthesize_speech(gpt_reply, output_path)

    # 5. Wait for TTS output file to be created (with retry)
    max_retries = 60
    retry_delay = 1.0
    for attempt in range(max_retries):
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            break
        print(f"[DEBUG] Attempt {attempt + 1}: File not ready, waiting {retry_delay}s...")
        time.sleep(retry_delay)
    else:
        print(f"[DEBUG] File still not found after {max_retries} attempts at: {os.path.abspath(output_path)}")
        print(f"[DEBUG] Current working directory: {os.getcwd()}")
        print(f"[DEBUG] Files in temp directory: {os.listdir('../temp') if os.path.exists('../temp') else 'temp dir not found'}")
        return jsonify({"error": "Speech synthesis failed"}), 500

    # 6. Send back WAV with proper headers
    timing_log["tts_complete"] = time.time()
    file_size = os.path.getsize(output_path)
    
    # Calculate timing breakdown
    total_time = timing_log["tts_complete"] - timing_log["start"]
    stt_time = timing_log["stt_complete"] - timing_log["audio_saved"]
    gpt_time = timing_log["gpt_complete"] - timing_log["stt_complete"]
    tts_time = timing_log["tts_complete"] - timing_log["gpt_complete"]
    
    print(f"\n=== RESPONSE TIME ANALYSIS ===")
    print(f"Total Response Time: {total_time:.2f}s")
    print(f"├─ STT Processing: {stt_time:.2f}s ({stt_time/total_time*100:.1f}%)")
    print(f"├─ GPT Generation: {gpt_time:.2f}s ({gpt_time/total_time*100:.1f}%)")
    print(f"└─ TTS Generation: {tts_time:.2f}s ({tts_time/total_time*100:.1f}%)")
    print(f"Audio file size: {file_size} bytes")
    print(f"=== END TIMING ANALYSIS ===\n")
    
    response = send_file(output_path, mimetype="audio/wav", as_attachment=False)
    response.headers["Content-Length"] = str(file_size)
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Response-Time"] = f"{total_time:.2f}"
    response.headers["X-STT-Time"] = f"{stt_time:.2f}"
    response.headers["X-GPT-Time"] = f"{gpt_time:.2f}"
    response.headers["X-TTS-Time"] = f"{tts_time:.2f}"
    return response

@app.route("/wakeup", methods=["GET"])
def wakeup():
    try:
        # Look for WAV files in the audio directory
        wav_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.wav')]
        
        if not wav_files:
            return jsonify({"error": "No audio files available"}), 404
        
        # Return the most recent WAV file
        wav_files.sort(key=lambda x: os.path.getmtime(os.path.join(AUDIO_DIR, x)), reverse=True)
        latest_file = wav_files[0]
        file_path = os.path.join(AUDIO_DIR, latest_file)
        
        # Verify file exists and has content
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            return jsonify({"error": "Audio file not found or empty"}), 404
        
        print(f"[INFO] Serving wakeup audio: {latest_file}")
        
        # Send the WAV file with proper headers
        response = send_file(file_path, mimetype="audio/wav", as_attachment=False)
        response.headers["Content-Length"] = str(os.path.getsize(file_path))
        response.headers["Connection"] = "keep-alive"
        return response
        
    except Exception as e:
        print(f"[ERROR] Wakeup route error: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@app.route("/audios")
def get_audios():
    """
    Returns a JSON list of available filler audio files for ESP32 discovery
    """
    try:
        filler_dir = os.path.join(AUDIO_DIR, "filler_audios")

        # Check if filler_audios directory exists
        if not os.path.exists(filler_dir):
            return jsonify({"audio_urls": []})

        # List all audio files in filler_audios subdirectory
        files = os.listdir(filler_dir)
        audio_files = [f for f in files if f.endswith(('.wav', '.mp3'))]

        # Build flattened URLs for the client
        urls = [f"/audio/{fname}" for fname in audio_files]

        print(f"[INFO] Filler audio discovery - found {len(audio_files)} files in filler_audios/")
        return jsonify({"audio_urls": urls})

    except Exception as e:
        print(f"[ERROR] Filler audio discovery failed: {str(e)}")
        return jsonify({"error": "Failed to list filler audio files"}), 500

@app.route("/audio/<filename>")
def serve_filler_audio(filename):
    """
    Serves individual filler audio files for ESP32 download
    """
    try:
        filler_dir = os.path.join(AUDIO_DIR, "filler_audios")
        file_path = os.path.join(filler_dir, filename)

        # Security check - ensure file exists and is valid audio
        if not os.path.exists(file_path) or not filename.endswith(('.wav', '.mp3')):
            return jsonify({"error": "Filler audio file not found"}), 404

        print(f"[INFO] Serving filler audio: {filename}")

        # Determine MIME type
        mimetype = "audio/wav" if filename.endswith('.wav') else "audio/mpeg"

        response = send_file(file_path, mimetype=mimetype, as_attachment=True)
        response.headers["Content-Length"] = str(os.path.getsize(file_path))
        return response

    except Exception as e:
        print(f"[ERROR] Filler audio serving failed for {filename}: {str(e)}")
        return jsonify({"error": "Failed to serve filler audio file"}), 500

@app.route("/text_upload", methods=["POST"])
@require_device_auth
def upload_text():
    # Start timing measurements  
    start_time = time.time()
    timing_log = {"start": start_time}
    
    # New route for receiving text directly from ESP32 with local STT
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "Expected JSON with 'text' field"}), 400

        user_text = data['text']
        session_id = data.get('session_id', 'esp32_default')  # ESP32 can send session ID

        # Get metadata for Firestore tracking
        user_id = data.get('user_id') or request.headers.get('X-User-ID')
        child_id = data.get('child_id') or request.headers.get('X-Child-ID')
        toy_id = data.get('toy_id') or request.headers.get('X-Toy-ID')

        # Fallback: If child_id not provided, use toy's assigned child
        if not child_id and hasattr(request, 'auth_context'):
            child_id = request.auth_context.get('toy_data', {}).get('assignedChildId')
            if child_id:
                print(f"[INFO] Using toy's assigned child ID: {child_id}")

        print(f"[INFO] Received text from local STT: {user_text} (Session: {session_id})")
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400

    # Get or create conversation if metadata is provided
    conversation_id = None
    if user_id and child_id:
        conversation_id = get_or_create_conversation(session_id, user_id, child_id, toy_id)
        print(f"[INFO] Conversation ID: {conversation_id}")
    else:
        print(f"[WARNING] Missing user/child metadata - Firestore tracking disabled for this request")

    timing_log["text_received"] = time.time()

    # Process with GPT with memory context (skip STT since we have text)
    gpt_start = time.time()
    gpt_reply = get_gpt_reply(
        user_text=user_text,
        session_id=session_id,
        user_id=user_id,
        child_id=child_id,
        conversation_id=conversation_id
    )
    timing_log["gpt_complete"] = time.time()
    if not gpt_reply:
        return jsonify({"error": "GPT processing failed"}), 500
    print("[GPT]", gpt_reply)

    # Generate TTS response
    tts_start = time.time()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = os.path.join(TEMP_DIR, f"reply_text_{timestamp}.wav")
    synthesize_speech(gpt_reply, output_path)

    # Wait for TTS output file
    max_retries = 60
    retry_delay = 1.0
    for attempt in range(max_retries):
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            break
        print(f"[DEBUG] Attempt {attempt + 1}: File not ready, waiting {retry_delay}s...")
        time.sleep(retry_delay)
    else:
        return jsonify({"error": "Speech synthesis failed"}), 500

    timing_log["tts_complete"] = time.time()
    file_size = os.path.getsize(output_path)
    
    # Calculate timing breakdown (Local STT version)
    total_time = timing_log["tts_complete"] - timing_log["start"]
    gpt_time = timing_log["gpt_complete"] - timing_log["text_received"]
    tts_time = timing_log["tts_complete"] - timing_log["gpt_complete"]
    
    print(f"\n=== LOCAL STT RESPONSE TIME ANALYSIS ===")
    print(f"Total Response Time: {total_time:.2f}s")
    print(f"├─ GPT Generation: {gpt_time:.2f}s ({gpt_time/total_time*100:.1f}%)")
    print(f"└─ TTS Generation: {tts_time:.2f}s ({tts_time/total_time*100:.1f}%)")
    print(f"Audio file size: {file_size} bytes")
    print(f"NOTE: STT was done locally on ESP32 (not measured here)")
    print(f"=== END TIMING ANALYSIS ===\n")
    
    response = send_file(output_path, mimetype="audio/wav", as_attachment=False)
    response.headers["Content-Length"] = str(file_size)
    response.headers["Connection"] = "keep-alive"
    response.headers["X-Response-Time"] = f"{total_time:.2f}"
    response.headers["X-GPT-Time"] = f"{gpt_time:.2f}"
    response.headers["X-TTS-Time"] = f"{tts_time:.2f}"
    return response

# ==================== AUTHENTICATION ROUTES ====================

@app.route("/auth/test", methods=["GET"])
@require_device_auth
def test_auth():
    """
    Test endpoint to verify authentication is working

    Headers required:
        X-User-ID: Parent user ID
        X-Device-ID: Device identifier
        X-Email: User email
        X-Session-ID: Session identifier (optional)

    Returns:
        JSON with authentication details if successful
        Error JSON with status code if failed
    """
    auth_context = request.auth_context
    return jsonify({
        "success": True,
        "message": "Authentication successful",
        "user_id": auth_context['user_id'],
        "device_id": auth_context['device_id'],
        "email": auth_context['email'],
        "device_name": auth_context['toy_data'].get('name'),
        "assigned_child": auth_context['toy_data'].get('assignedChildId'),
        "device_status": auth_context['toy_data'].get('status')
    }), 200


@app.route("/device/info", methods=["GET"])
@require_device_auth
def get_device_info():
    """
    Get device/toy information including assigned child

    ESP32 calls this endpoint:
    - During initial pairing (after WiFi connection)
    - On every boot (to check for assignment updates)

    Headers required:
        X-Device-ID: Device MAC address
        X-Email: Parent email (from pairing)
        X-User-ID: Parent user ID (optional, can be looked up from email)
        X-Session-ID: Session identifier (optional)

    Returns:
        - assignedChildId: Which child this toy is assigned to
        - childName: Name of the assigned child
        - toyName: Name of this toy
        - toySettings: Volume, LED brightness, etc.
    """
    auth_context = request.auth_context
    toy_data = auth_context.get('toy_data', {})
    user_id = auth_context.get('user_id')

    # Get assigned child ID
    assigned_child_id = toy_data.get('assignedChildId')

    # Build response
    response_data = {
        "success": True,
        "deviceId": auth_context['device_id'],
        "toyName": toy_data.get('name', 'Unknown Toy'),
        "assignedChildId": assigned_child_id,
        "toySettings": {
            "volume": toy_data.get('volume', 70),
            "ledBrightness": toy_data.get('ledBrightness', 'Medium'),
            "soundEffects": toy_data.get('soundEffects', True),
            "voiceType": toy_data.get('voiceType', 'Female, Child-friendly')
        },
        "status": {
            "batteryLevel": toy_data.get('batteryLevel', 100),
            "firmwareVersion": toy_data.get('firmwareVersion', 'v1.0.0'),
            "lastConnected": toy_data.get('lastConnected')
        }
    }

    # If toy is assigned to a child, fetch child details
    if assigned_child_id and user_id:
        try:
            child_doc = firestore_service.db.collection("users").document(user_id)\
                .collection("children").document(assigned_child_id).get()

            if child_doc.exists:
                child_data = child_doc.to_dict()
                response_data["childName"] = child_data.get('name', 'Unknown Child')
                response_data["childAvatar"] = child_data.get('avatar', '🧒')

                # Include parental control settings that ESP32 might need
                response_data["parentalControls"] = {
                    "dailyLimitHours": child_data.get('dailyLimitHours', 2),
                    "quietHoursEnabled": child_data.get('quietHoursEnabled', False),
                    "contentFilterEnabled": child_data.get('contentFilterEnabled', True)
                }
            else:
                response_data["childName"] = None
                response_data["warning"] = "Toy is assigned but child not found"

        except Exception as e:
            print(f"[ERROR] Failed to fetch child info: {str(e)}")
            response_data["childName"] = None
            response_data["warning"] = "Could not fetch child details"
    else:
        # Toy not assigned to any child yet
        response_data["childName"] = None
        response_data["assignedChildId"] = None
        response_data["warning"] = "Toy not assigned to any child yet"

    print(f"[INFO] Device info fetched for toy {auth_context['device_id']}, assigned to child: {assigned_child_id}")

    return jsonify(response_data), 200


# ==================== CONVERSATION MANAGEMENT ROUTES ====================

@app.route("/api/conversations/end", methods=["POST"])
def end_conversation():
    """
    End a conversation session

    Request body:
    {
        "session_id": "esp32_session_123"
    }
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if not session_id:
            return jsonify({"error": "session_id is required"}), 400

        end_conversation_session(session_id)

        return jsonify({
            "success": True,
            "message": f"Conversation ended for session {session_id}"
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to end conversation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>", methods=["GET"])
def get_conversation(conversation_id):
    """
    Get conversation details

    Query params:
        user_id: Parent user ID
        child_id: Child ID
    """
    try:
        user_id = request.args.get('user_id')
        child_id = request.args.get('child_id')

        if not user_id or not child_id:
            return jsonify({"error": "user_id and child_id are required"}), 400

        conversation = firestore_service.get_conversation(user_id, child_id, conversation_id)

        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404

        return jsonify({
            "success": True,
            "conversation": conversation
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get conversation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>/messages", methods=["GET"])
def get_conversation_messages(conversation_id):
    """
    Get messages for a conversation

    Query params:
        user_id: Parent user ID
        child_id: Child ID
        limit: Max number of messages (default: 100)
    """
    try:
        user_id = request.args.get('user_id')
        child_id = request.args.get('child_id')
        limit = int(request.args.get('limit', 100))

        if not user_id or not child_id:
            return jsonify({"error": "user_id and child_id are required"}), 400

        messages = firestore_service.get_conversation_messages(
            user_id, child_id, conversation_id, limit
        )

        return jsonify({
            "success": True,
            "messages": messages,
            "count": len(messages)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get conversation messages: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/children/<child_id>/conversations", methods=["GET"])
def get_child_conversations(child_id):
    """
    Get conversations for a child

    Query params:
        user_id: Parent user ID
        limit: Max number of conversations (default: 50)
    """
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 50))

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        conversations = firestore_service.get_child_conversations(user_id, child_id, limit)

        return jsonify({
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get child conversations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>/flag", methods=["PUT"])
def flag_conversation(conversation_id):
    """
    Flag or unflag a conversation

    Request body:
    {
        "user_id": "user123",
        "child_id": "child123",
        "flagged": true,
        "flag_status": "reviewed"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        child_id = data.get('child_id')
        flag_status = data.get('flag_status', 'reviewed')

        if not user_id or not child_id:
            return jsonify({"error": "user_id and child_id are required"}), 400

        conversation_ref = firestore_service.db.collection("users").document(user_id)\
            .collection("children").document(child_id)\
            .collection("conversations").document(conversation_id)

        conversation_ref.update({
            "flagStatus": flag_status,
        })

        return jsonify({
            "success": True,
            "message": f"Conversation flag status updated to {flag_status}"
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to update conversation flag: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/setup/create_account", methods=["POST"])
def create_account():
    """Create a complete test account (user + child + toy)"""
    try:
        data = request.get_json()

        user_id = data.get('user_id')
        email = data.get('email')
        display_name = data.get('display_name')
        child_id = data.get('child_id')
        child_name = data.get('child_name')
        toy_id = data.get('toy_id')
        toy_name = data.get('toy_name')

        if not all([user_id, email, display_name, child_id, child_name, toy_id, toy_name]):
            return jsonify({"error": "Missing required fields"}), 400

        if not firestore_service or not firestore_service.is_available():
            error_msg = "Firestore not initialized. Please set up Firebase credentials. See FIRESTORE_INTEGRATION_GUIDE.md for setup instructions."
            print(f"[ERROR] {error_msg}")
            return jsonify({
                "error": error_msg,
                "hint": "Run: python3 setup_test_data.py to initialize Firestore with test data"
            }), 503

        # Create user
        user_data = {
            "uid": user_id,
            "email": email,
            "displayName": display_name,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "onboardingCompleted": True,
            "preferences": {
                "notifications": True,
                "theme": "light"
            },
            "childrenCount": 1,
            "toys": [toy_id],
            "stats": {
                "totalConversations": 0,
                "totalConversationDurationSec": 0,
                "flaggedConversations": 0,
                "lastConversationAt": None,
                "lastFlaggedAt": None,
                "lastActivityAt": firestore.SERVER_TIMESTAMP
            }
        }

        firestore_service.db.collection("users").document(user_id).set(user_data)
        print(f"[SETUP] Created user: {user_id} ({email})")

        # Create child
        child_data = {
            "name": child_name,
            "birthDate": "01/01/2015",
            "avatar": "🧒",
            "ageLevel": "elementary",
            "dailyLimitHours": 2,
            "createdAt": firestore.SERVER_TIMESTAMP,
            "contentFilterEnabled": True,
            "quietHoursEnabled": False,
            "dailyLimitEnabled": True,
            "creativeModeEnabled": True,
            "recordConversations": True,
            "blockedTopics": {
                "violence": True,
                "matureContent": True,
                "politics": False,
                "religion": False,
                "personalInfo": True
            },
            "alertTypes": {
                "personalInfo": True,
                "inappropriateContent": True,
                "emotionalDistress": True,
                "unusualPatterns": True
            },
            "alertSensitivity": "Medium"
        }

        firestore_service.db.collection("users").document(user_id)\
            .collection("children").document(child_id).set(child_data)
        print(f"[SETUP] Created child: {child_id} ({child_name})")

        # Create toy
        toy_data = {
            "name": toy_name,
            "emoji": "🦄",
            "assignedChildId": child_id,
            "pairedAt": firestore.SERVER_TIMESTAMP,
            "status": "online",
            "batteryLevel": 100,
            "lastConnected": firestore.SERVER_TIMESTAMP,
            "model": "Luno Simulator",
            "serialNumber": f"SIM-{toy_id}",
            "firmwareVersion": "v1.0.0",
            "volume": 70,
            "ledBrightness": "Medium",
            "soundEffects": True,
            "voiceType": "Female, Child-friendly",
            "autoUpdate": True,
            "connectionType": "Wi-Fi",
            "wifiNetwork": "Simulator-Network"
        }

        firestore_service.db.collection("users").document(user_id)\
            .collection("toys").document(toy_id).set(toy_data)
        print(f"[SETUP] Created toy: {toy_id} ({toy_name})")

        return jsonify({
            "success": True,
            "message": "Account created successfully",
            "user_id": user_id,
            "child_id": child_id,
            "toy_id": toy_id
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to create account: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/setup/add_toy", methods=["POST"])
def add_toy():
    """Add a toy to an existing user account"""
    try:
        data = request.get_json()

        user_id = data.get('user_id')
        toy_id = data.get('toy_id')
        toy_name = data.get('toy_name')
        assigned_child_id = data.get('assigned_child_id')

        if not all([user_id, toy_id, toy_name]):
            return jsonify({"error": "Missing required fields (user_id, toy_id, toy_name)"}), 400

        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        # Verify user exists
        user_ref = firestore_service.db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({"error": f"User {user_id} not found"}), 404

        # Create toy
        toy_data = {
            "name": toy_name,
            "emoji": "🦄",
            "assignedChildId": assigned_child_id,
            "pairedAt": firestore.SERVER_TIMESTAMP,
            "status": "online",
            "batteryLevel": 100,
            "lastConnected": firestore.SERVER_TIMESTAMP,
            "model": "Luno Simulator",
            "serialNumber": f"SIM-{toy_id}",
            "firmwareVersion": "v1.0.0",
            "volume": 70,
            "ledBrightness": "Medium",
            "soundEffects": True,
            "voiceType": "Female, Child-friendly",
            "autoUpdate": True,
            "connectionType": "Wi-Fi",
            "wifiNetwork": "Simulator-Network"
        }

        firestore_service.db.collection("users").document(user_id)\
            .collection("toys").document(toy_id).set(toy_data)

        print(f"[SETUP] Added toy {toy_id} ({toy_name}) to user {user_id}")

        return jsonify({
            "success": True,
            "message": f"Toy {toy_id} added successfully",
            "toy_id": toy_id,
            "user_id": user_id
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to add toy: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<user_id>/stats", methods=["GET"])
def get_user_stats(user_id):
    """Get user statistics"""
    try:
        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        user_ref = firestore_service.db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user_doc.to_dict()
        stats = user_data.get('stats', {})

        return jsonify({
            "success": True,
            "stats": stats
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get user stats: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5005)), debug=True)
# To run this app, ensure you have the required environment variables set:
# - OPENAI_API_KEY for OpenAI API access
# - PORT for the Flask server port (default is 5005)
# Make sure to install the required packages:
# pip install Flask openai
# Also, ensure you have the whisper_stt.py and gpt_reply.py modules implemented as needed.
# You can run the app with: python app.py
# The app will listen for audio uploads at the /upload endpoint and respond with synthesized speech.    
