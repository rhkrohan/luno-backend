# ESP32 Toy Backend 123
from dotenv import load_dotenv
from flask import Flask, request, send_file, jsonify, g
from flask_cors import CORS
import os, datetime, time
import struct
import wave
import threading
import uuid
from google.cloud import firestore

# Load environment variables from .env file
load_dotenv()

from whisper_stt import transcribe_audio
from gemini_reply import get_gpt_reply  # Using Google Gemini for Google Cloud Hackathon
from tts_elevenlabs_streaming import synthesize_speech  # Using ElevenLabs Streaming TTS
from firebase_config import initialize_firebase
from firestore_service import firestore_service
from auth_middleware import require_device_auth
from session_manager import SessionManager

# Initialize logging configuration BEFORE creating Flask app
from logging_config import setup_logging, get_logger, log_execution_time

app = Flask(__name__)

# Setup logging (will integrate with Gunicorn if running under Gunicorn)
setup_logging(app)
logger = get_logger(__name__)
TEMP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "temp")
AUDIO_DIR = os.path.join(os.path.dirname(__file__), "audio")
os.makedirs(TEMP_DIR, exist_ok=True)
os.makedirs(AUDIO_DIR, exist_ok=True)

# ==================== CORS CONFIGURATION ====================
# Allowed origins - restrict to your domain only for security
ALLOWED_ORIGINS = [
    'https://myluno.space',
    'https://www.myluno.space',
    'https://api.myluno.space',
    # 'http://localhost:8080'  # Uncomment for local development
]

# Configure CORS with specific origins
CORS(app,
     origins=ALLOWED_ORIGINS,
     allow_headers=['Content-Type', 'X-Audio-Format', 'X-Device-ID', 'X-User-Email',
                    'X-User-ID', 'X-Session-ID', 'X-Child-ID', 'X-Sample-Rate',
                    'X-Channels', 'X-Bits-Per-Sample', 'User-Agent', 'X-Email'],
     methods=['GET', 'POST', 'PUT', 'OPTIONS'],
     supports_credentials=True,
     max_age=3600)  # Cache preflight requests for 1 hour

logger.info(f"CORS configured for origins: {ALLOWED_ORIGINS}")

# ==================== MIDDLEWARE AND ERROR HANDLERS ====================

@app.before_request
def before_request():
    """Generate request ID and log incoming requests"""
    g.request_id = str(uuid.uuid4())[:8]
    g.start_time = time.time()

    # Store auth context in g for logging
    if hasattr(request, 'auth_context'):
        g.user_id = request.auth_context.get('user_id', '-')
        g.device_id = request.auth_context.get('toy_id', '-')
    else:
        g.user_id = '-'
        g.device_id = '-'

    logger.info(
        f"Incoming request: {request.method} {request.path} | "
        f"Remote: {request.remote_addr} | "
        f"Content-Type: {request.content_type} | "
        f"Content-Length: {request.content_length or 0}"
    )


@app.after_request
def after_request(response):
    """Log request completion"""
    duration = time.time() - g.get('start_time', time.time())

    logger.info(
        f"Request completed: {request.method} {request.path} | "
        f"Status: {response.status_code} | "
        f"Duration: {duration:.3f}s | "
        f"Response-Size: {response.content_length or 0}"
    )

    # Add request ID to response headers for tracking
    response.headers['X-Request-ID'] = g.get('request_id', '-')

    return response


@app.errorhandler(400)
def bad_request_error(error):
    """Handle 400 Bad Request errors"""
    logger.warning(f"Bad request: {request.path} | Error: {str(error)}")
    return jsonify({"error": "Bad request", "message": str(error)}), 400


@app.errorhandler(403)
def forbidden_error(error):
    """Handle 403 Forbidden errors"""
    logger.warning(f"Forbidden access: {request.path} | Error: {str(error)}")
    return jsonify({"error": "Forbidden", "message": str(error)}), 403


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 Not Found errors"""
    logger.warning(f"Not found: {request.path}")
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(500)
def internal_server_error(error):
    """Handle 500 Internal Server errors"""
    logger.error(f"Internal server error: {request.path}", exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all uncaught exceptions"""
    logger.error(
        f"Unhandled exception in {request.method} {request.path}: {str(error)}",
        exc_info=True
    )
    return jsonify({"error": "Internal server error", "message": str(error)}), 500


# Initialize Firebase on startup
logger.info("Initializing Firebase...")
initialize_firebase()
logger.info("Firebase initialization completed")

# Initialize session manager (backend-managed sessions)
logger.info("Initializing session manager...")
session_manager = SessionManager(firestore_service)
logger.info("Session manager initialized successfully")

# Track active conversations: session_id -> {conversation_id, user_id, child_id, start_time}
# Note: This dict is now managed by session_manager (kept for backward compatibility)
ACTIVE_CONVERSATIONS = session_manager.ACTIVE_CONVERSATIONS

# Background session cleanup task
def run_cleanup_loop():
    """Background thread to cleanup expired sessions every 60 seconds"""
    while True:
        time.sleep(60)  # 1 minute - run more frequently to catch expired sessions quickly
        try:
            session_manager.cleanup_expired_sessions()
        except Exception as e:
            logger.error(f"Session cleanup failed: {str(e)}", exc_info=True)

# Start cleanup thread as daemon (will exit when main program exits)
cleanup_thread = threading.Thread(target=run_cleanup_loop, daemon=True)
cleanup_thread.start()
logger.info("Background session cleanup task started (60s interval)")

# Old get_or_create_conversation() and end_conversation_session() functions removed
# Session management now handled by session_manager


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

        logger.info(
            f"ADPCM decompression successful: {len(adpcm_data)} bytes -> "
            f"{len(decoded_samples)} samples | Output: {output_path}"
        )
        return True

    except Exception as e:
        logger.error(f"ADPCM decompression failed: {str(e)}", exc_info=True)
        return False

@app.route("/")
def index():
    return "ESP32 Toy Backend is running. Broooo its workinggggggggggggg"

@app.route("/simulator")
def simulator():
    """Serve the web-based ESP32 simulator"""
    return send_file("simulators/simulator.html")

@app.route("/test")
def test_simulator():
    """Serve the simplified ESP32 test simulator"""
    return send_file("simulators/esp32_test_simulator.html")

@app.route("/knowledge-graph")
def knowledge_graph_viewer():
    """Serve the knowledge graph visualization interface"""
    return send_file("simulators/knowledge_graph_viewer.html")

@app.route("/simulator_config.json")
def simulator_config():
    """Serve the simulator configuration file"""
    return send_file("simulators/simulator_config.json")

@app.route("/upload", methods=["POST"])
@require_device_auth
def upload_audio():
    """
    Main audio upload endpoint for ESP32 devices.
    Handles ADPCM audio, performs STT, generates GPT response, and returns TTS audio.
    """
    # Start timing measurements
    start_time = time.time()
    timing_log = {"start": start_time}

    # 1. Receive audio
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    input_path = os.path.join(TEMP_DIR, f"input_{timestamp}.wav")
    adpcm_path = os.path.join(TEMP_DIR, f"adpcm_{timestamp}.bin")

    # Get device and user from auth context (backend-managed sessions)
    toy_id = request.auth_context.get('toy_id')
    user_id = request.auth_context.get('user_id')
    child_id = request.headers.get('X-Child-ID')

    logger.info(
        f"Audio upload started | Toy: {toy_id} | User: {user_id} | "
        f"Child: {child_id or 'None'} | Timestamp: {timestamp}"
    )

    # Fallback: If child_id not provided, use toy's assigned child
    if not child_id and hasattr(request, 'auth_context'):
        child_id = request.auth_context.get('toy_data', {}).get('assignedChildId')
        if child_id:
            logger.info(f"Using toy's assigned child ID: {child_id}")

    # Get or create session (backend-managed)
    logger.debug(f"Getting or creating session for toy {toy_id}, user {user_id}, child {child_id}")
    session_data = session_manager.get_or_create_session(
        toy_id=toy_id,
        user_id=user_id,
        child_id=child_id
    )

    if not session_data:
        logger.error(f"Failed to create session for toy {toy_id}, user {user_id}")
        return jsonify({"error": "Session creation failed"}), 500

    session_id = session_data['session_id']
    conversation_id = session_data['conversation_id']
    logger.info(
        f"Session established | SessionID: {session_id} | "
        f"ConversationID: {conversation_id}"
    )

    # Store session info in g for logging context
    g.user_id = user_id
    g.device_id = toy_id

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
        logger.info(
            f"Processing ADPCM audio | Size: {len(audio_data)} bytes | "
            f"Session: {session_id}"
        )

        if not decompress_adpcm_to_wav(audio_data, input_path):
            logger.error(f"ADPCM decompression failed for session {session_id}")
            return jsonify({"error": "ADPCM decompression failed"}), 500

        logger.info(f"ADPCM decompressed successfully to {input_path}")

    elif content_type == "audio/wav":
        # Already WAV format - save directly
        with open(input_path, "wb") as f:
            f.write(audio_data)
        logger.info(
            f"Saved WAV audio directly | Size: {len(audio_data)} bytes | "
            f"Path: {input_path} | Session: {session_id}"
        )

    else:
        # Assume ADPCM by default for ESP32 compatibility
        logger.warning(
            f"No audio format specified, assuming ADPCM | Size: {len(audio_data)} bytes | "
            f"Session: {session_id}"
        )

        if not decompress_adpcm_to_wav(audio_data, input_path):
            logger.error(f"ADPCM decompression failed for session {session_id}")
            return jsonify({"error": "ADPCM decompression failed"}), 500

        logger.info(f"ADPCM decompressed successfully to {input_path}")

    timing_log["audio_saved"] = time.time()

    # 2. STT (Server-side Whisper API)
    stt_start = time.time()
    logger.info(f"Starting Whisper STT | Session: {session_id} | Input: {input_path}")

    try:
        user_text = transcribe_audio(input_path)
        if not user_text:
            logger.error(f"STT failed - no transcription returned | Session: {session_id}")
            return jsonify({"error": "Speech transcription failed"}), 500

        timing_log["stt_complete"] = time.time()
        stt_time = timing_log["stt_complete"] - stt_start
        logger.info(
            f"STT completed successfully | Duration: {stt_time:.2f}s | "
            f"Transcription: '{user_text}' | Session: {session_id}"
        )
    except Exception as e:
        logger.error(f"STT exception: {str(e)} | Session: {session_id}", exc_info=True)
        return jsonify({"error": "Speech transcription failed"}), 500

    # 3. GPT with memory context (includes Firestore batch saving - 3 writes instead of 6)
    gpt_start = time.time()
    logger.info(
        f"Starting GPT generation | Session: {session_id} | "
        f"UserText: '{user_text[:100]}{'...' if len(user_text) > 100 else ''}'"
    )

    try:
        gpt_reply = get_gpt_reply(
            user_text=user_text,
            session_id=session_id,
            user_id=user_id,
            conversation_id=conversation_id,
            child_id=child_id
        )

        timing_log["gpt_complete"] = time.time()
        gpt_time = timing_log["gpt_complete"] - gpt_start
        logger.info(
            f"GPT completed successfully | Duration: {gpt_time:.2f}s | "
            f"Reply: '{gpt_reply[:100]}{'...' if len(gpt_reply) > 100 else ''}' | "
            f"Session: {session_id}"
        )
    except Exception as e:
        logger.error(f"GPT generation exception: {str(e)} | Session: {session_id}", exc_info=True)
        return jsonify({"error": "GPT processing failed"}), 500

    # 4. TTS
    tts_start = time.time()
    output_path = os.path.join(TEMP_DIR, f"reply_{timestamp}.wav")
    logger.info(
        f"Starting TTS generation | Output: {output_path} | "
        f"Text length: {len(gpt_reply)} chars | Session: {session_id}"
    )

    try:
        synthesize_speech(gpt_reply, output_path)
    except Exception as e:
        logger.error(f"TTS synthesis exception: {str(e)} | Session: {session_id}", exc_info=True)
        return jsonify({"error": "Speech synthesis failed"}), 500

    # 5. Wait for TTS output file to be created (with retry)
    max_retries = 60
    retry_delay = 1.0
    logger.debug(f"Waiting for TTS output file: {output_path}")

    for attempt in range(max_retries):
        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            logger.info(f"TTS output file ready after {attempt + 1} attempts")
            break

        if attempt % 10 == 0:  # Log every 10 attempts to reduce noise
            logger.debug(
                f"TTS file not ready yet | Attempt {attempt + 1}/{max_retries} | "
                f"Waiting {retry_delay}s..."
            )
        time.sleep(retry_delay)
    else:
        logger.error(
            f"TTS output file not created after {max_retries} attempts | "
            f"Path: {os.path.abspath(output_path)} | "
            f"CWD: {os.getcwd()} | "
            f"Session: {session_id}"
        )
        if os.path.exists('../temp'):
            temp_files = os.listdir('../temp')
            logger.error(f"Files in temp directory: {temp_files}")
        return jsonify({"error": "Speech synthesis failed"}), 500

    # 6. Send back WAV with proper headers
    timing_log["tts_complete"] = time.time()
    file_size = os.path.getsize(output_path)

    # Calculate timing breakdown
    total_time = timing_log["tts_complete"] - timing_log["start"]
    stt_time = timing_log["stt_complete"] - timing_log["audio_saved"]
    gpt_time = timing_log["gpt_complete"] - timing_log["stt_complete"]
    tts_time = timing_log["tts_complete"] - timing_log["gpt_complete"]

    # Log comprehensive timing analysis
    logger.info(
        f"\n"
        f"=== RESPONSE TIME ANALYSIS ===\n"
        f"Session: {session_id} | Conversation: {conversation_id}\n"
        f"Total Response Time: {total_time:.2f}s\n"
        f"├─ STT Processing: {stt_time:.2f}s ({stt_time/total_time*100:.1f}%)\n"
        f"├─ GPT Generation: {gpt_time:.2f}s ({gpt_time/total_time*100:.1f}%)\n"
        f"└─ TTS Generation: {tts_time:.2f}s ({tts_time/total_time*100:.1f}%)\n"
        f"Audio file size: {file_size} bytes\n"
        f"=== END TIMING ANALYSIS ==="
    )

    # Update session activity
    try:
        session_manager.update_session_activity(session_id, user_id)
        logger.debug(f"Session activity updated | Session: {session_id}")
    except Exception as e:
        logger.warning(f"Failed to update session activity: {str(e)}", exc_info=True)

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
    """Serve the most recent wakeup audio file from the audio directory"""
    logger.info("Wakeup audio requested")

    try:
        # Look for WAV files in the audio directory
        wav_files = [f for f in os.listdir(AUDIO_DIR) if f.endswith('.wav')]

        if not wav_files:
            logger.warning("No wakeup audio files available in audio directory")
            return jsonify({"error": "No audio files available"}), 404

        # Return the most recent WAV file
        wav_files.sort(key=lambda x: os.path.getmtime(os.path.join(AUDIO_DIR, x)), reverse=True)
        latest_file = wav_files[0]
        file_path = os.path.join(AUDIO_DIR, latest_file)

        # Verify file exists and has content
        if not os.path.exists(file_path) or os.path.getsize(file_path) == 0:
            logger.error(f"Wakeup audio file not found or empty: {file_path}")
            return jsonify({"error": "Audio file not found or empty"}), 404

        file_size = os.path.getsize(file_path)
        logger.info(f"Serving wakeup audio: {latest_file} ({file_size} bytes)")

        # Send the WAV file with proper headers
        response = send_file(file_path, mimetype="audio/wav", as_attachment=False)
        response.headers["Content-Length"] = str(file_size)
        response.headers["Connection"] = "keep-alive"
        return response

    except Exception as e:
        logger.error(f"Wakeup route error: {str(e)}", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route("/audios")
def get_audios():
    """
    Returns a JSON list of available filler audio files for ESP32 discovery
    """
    logger.info("Filler audio discovery requested")

    try:
        filler_dir = os.path.join(AUDIO_DIR, "filler_audios")

        # Check if filler_audios directory exists
        if not os.path.exists(filler_dir):
            logger.warning(f"Filler audio directory does not exist: {filler_dir}")
            return jsonify({"audio_urls": []})

        # List all audio files in filler_audios subdirectory
        files = os.listdir(filler_dir)
        audio_files = [f for f in files if f.endswith(('.wav', '.mp3'))]

        # Build flattened URLs for the client
        urls = [f"/audio/{fname}" for fname in audio_files]

        logger.info(
            f"Filler audio discovery completed | Found {len(audio_files)} files | "
            f"Directory: {filler_dir}"
        )
        return jsonify({"audio_urls": urls})

    except Exception as e:
        logger.error(f"Filler audio discovery failed: {str(e)}", exc_info=True)
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

        # Get device and user from auth context (backend-managed sessions)
        toy_id = request.auth_context.get('toy_id')
        user_id = request.auth_context.get('user_id')
        child_id = data.get('child_id') or request.headers.get('X-Child-ID')

        # Fallback: If child_id not provided, use toy's assigned child
        if not child_id and hasattr(request, 'auth_context'):
            child_id = request.auth_context.get('toy_data', {}).get('assignedChildId')
            if child_id:
                print(f"[INFO] Using toy's assigned child ID: {child_id}")

        print(f"[INFO] Received text from local STT: {user_text}")
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400

    # Get or create session (backend-managed)
    session_data = session_manager.get_or_create_session(
        toy_id=toy_id,
        user_id=user_id,
        child_id=child_id
    )

    if not session_data:
        print(f"[ERROR] Failed to create session for toy {toy_id}")
        return jsonify({"error": "Session creation failed"}), 500

    session_id = session_data['session_id']
    conversation_id = session_data['conversation_id']
    print(f"[INFO] Session ID: {session_id}, Conversation ID: {conversation_id}")

    timing_log["text_received"] = time.time()

    # Process with GPT with memory context (skip STT since we have text - using batch writes)
    gpt_start = time.time()
    gpt_reply = get_gpt_reply(
        user_text=user_text,
        session_id=session_id,
        user_id=user_id,
        conversation_id=conversation_id,
        child_id=child_id
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

    # Update session activity
    session_manager.update_session_activity(session_id, user_id)

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
        X-Device-ID: Device identifier (required)
        X-User-Email: User email (required, or use X-Email for legacy support)
        OR
        X-User-ID: Parent user ID (alternative to X-User-Email)
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
        "toy_id": auth_context['toy_id'],
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
        X-Device-ID: Device MAC address (required)
        X-User-Email: Parent email from pairing (required, or use X-Email for legacy)
        X-User-ID: Parent user ID (optional alternative to X-User-Email)
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
        "toyId": auth_context['toy_id'],
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

    print(f"[INFO] Device info fetched for toy {auth_context['toy_id']}, assigned to child: {assigned_child_id}")

    return jsonify(response_data), 200


# ==================== CONVERSATION MANAGEMENT ROUTES ====================

@app.route("/api/conversations/end", methods=["POST"])
def end_conversation():
    """
    End a conversation session

    Request body can include:
    - session_id: Explicit session ID (for backward compatibility)
    - OR toy_id + user_id: To lookup active session
    """
    try:
        data = request.get_json()
        session_id = data.get('session_id')
        toy_id = data.get('toy_id')
        user_id = data.get('user_id')

        # Try to get session_id from toy+user if not explicitly provided
        if not session_id and toy_id and user_id:
            session_id = session_manager.get_active_session_id(toy_id, user_id)
            if not session_id:
                return jsonify({"error": "No active session found for toy-user pair"}), 404

        if not session_id:
            return jsonify({"error": "session_id (or toy_id + user_id) is required"}), 400

        # Get user_id for session if not provided
        if not user_id and session_id in ACTIVE_CONVERSATIONS:
            user_id = ACTIVE_CONVERSATIONS[session_id].get('user_id')

        if not user_id:
            return jsonify({"error": "Could not determine user_id for session"}), 400

        session_manager.end_session(session_id, user_id, reason="explicit")

        return jsonify({
            "success": True,
            "message": f"Conversation ended for session {session_id}"
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to end conversation: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>", methods=["GET"])
@require_device_auth
def get_conversation(conversation_id):
    """
    Get conversation details (UNIFIED SCHEMA) - requires authentication

    Query params:
        user_id: Parent user ID
    """
    try:
        user_id = request.args.get('user_id')

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Verify the authenticated user is requesting their own data
        auth_user_id = request.auth_context.get('user_id')
        if auth_user_id != user_id:
            return jsonify({"error": "Unauthorized - can only access your own conversations"}), 403

        conversation = firestore_service.get_conversation(user_id, conversation_id)

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
@require_device_auth
def get_conversation_messages(conversation_id):
    """
    Get messages for a conversation (UNIFIED SCHEMA) - requires authentication

    Query params:
        user_id: Parent user ID
        limit: Max number of messages (default: 100)
    """
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 100))

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Verify the authenticated user is requesting their own data
        auth_user_id = request.auth_context.get('user_id')
        if auth_user_id != user_id:
            return jsonify({"error": "Unauthorized - can only access your own conversations"}), 403

        messages = firestore_service.get_conversation_messages(
            user_id, conversation_id, limit
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
@require_device_auth
def get_child_conversations(child_id):
    """
    Get conversations for a child - requires authentication

    Query params:
        user_id: Parent user ID
        limit: Max number of conversations (default: 50)
    """
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 50))

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Verify the authenticated user is requesting their own data
        auth_user_id = request.auth_context.get('user_id')
        if auth_user_id != user_id:
            return jsonify({"error": "Unauthorized - can only access your own data"}), 403

        conversations = firestore_service.get_child_conversations(user_id, child_id, limit)

        return jsonify({
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get child conversations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/active", methods=["GET"])
@require_device_auth
def get_active_conversations():
    """
    Get all active conversations across all children - requires authentication

    Query params:
        user_id: Parent user ID
        limit: Max number of conversations (default: 20)
    """
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 20))

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Verify the authenticated user is requesting their own data
        auth_user_id = request.auth_context.get('user_id')
        if auth_user_id != user_id:
            return jsonify({"error": "Unauthorized - can only access your own data"}), 403

        conversations = firestore_service.get_active_conversations(user_id, limit)

        return jsonify({
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get active conversations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/flagged", methods=["GET"])
@require_device_auth
def get_flagged_conversations():
    """
    Get all flagged conversations - requires authentication

    Query params:
        user_id: Parent user ID
        limit: Max number of conversations (default: 50)
    """
    try:
        user_id = request.args.get('user_id')
        limit = int(request.args.get('limit', 50))

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Verify the authenticated user is requesting their own data
        auth_user_id = request.auth_context.get('user_id')
        if auth_user_id != user_id:
            return jsonify({"error": "Unauthorized - can only access your own data"}), 403

        conversations = firestore_service.get_flagged_conversations(user_id, limit)

        return jsonify({
            "success": True,
            "conversations": conversations,
            "count": len(conversations)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get flagged conversations: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/conversations/<conversation_id>/flag", methods=["PUT"])
@require_device_auth
def flag_conversation(conversation_id):
    """
    Flag or unflag a conversation - requires authentication

    Request body:
    {
        "user_id": "user123",
        "flag_status": "reviewed"
    }
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        flag_status = data.get('flag_status', 'reviewed')

        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Verify the authenticated user is modifying their own data
        auth_user_id = request.auth_context.get('user_id')
        if auth_user_id != user_id:
            return jsonify({"error": "Unauthorized - can only modify your own data"}), 403

        # NEW LOCATION: conversations directly under user
        conversation_ref = firestore_service.db.collection("users").document(user_id)\
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
            "stats": {
                "totalConversations": 0,
                "totalConversationDurationSec": 0,
                "flaggedConversations": 0,
                "lastConversationAt": None,
                "lastFlaggedAt": None
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
@require_device_auth
def get_user_stats(user_id):
    """Get user statistics - requires authentication"""
    # Verify the authenticated user is requesting their own data
    auth_user_id = request.auth_context.get('user_id')
    if auth_user_id != user_id:
        return jsonify({"error": "Unauthorized - can only access your own stats"}), 403

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


@app.route("/api/users", methods=["GET"])
@require_device_auth
def list_users():
    """Get authenticated user info (for simulator) - requires authentication"""
    try:
        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        # Only return the authenticated user's data
        auth_user_id = request.auth_context.get('user_id')
        user_ref = firestore_service.db.collection("users").document(auth_user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            return jsonify({"error": "User not found"}), 404

        user_data = user_doc.to_dict()
        users = [{
            "userId": auth_user_id,
            "email": user_data.get('email', 'N/A'),
            "displayName": user_data.get('displayName', 'N/A')
        }]

        return jsonify({
            "success": True,
            "users": users,
            "count": 1
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to get user: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<user_id>/children", methods=["GET"])
@require_device_auth
def list_children(user_id):
    """List children for a specific user - requires authentication"""
    # Verify the authenticated user is requesting their own data
    auth_user_id = request.auth_context.get('user_id')
    if auth_user_id != user_id:
        return jsonify({"error": "Unauthorized - can only access your own children"}), 403

    try:
        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        children_ref = firestore_service.db.collection("users").document(user_id).collection("children")
        children_docs = children_ref.stream()

        children = []
        for doc in children_docs:
            child_data = doc.to_dict()
            children.append({
                "childId": doc.id,
                "name": child_data.get('name', 'N/A'),
                "avatar": child_data.get('avatar', '🧒'),
                "ageLevel": child_data.get('ageLevel', 'N/A')
            })

        return jsonify({
            "success": True,
            "children": children,
            "count": len(children)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to list children: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/users/<user_id>/toys", methods=["GET"])
@require_device_auth
def list_toys(user_id):
    """List toys for a specific user - requires authentication"""
    # Verify the authenticated user is requesting their own data
    auth_user_id = request.auth_context.get('user_id')
    if auth_user_id != user_id:
        return jsonify({"error": "Unauthorized - can only access your own toys"}), 403

    try:
        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        toys_ref = firestore_service.db.collection("users").document(user_id).collection("toys")
        toys_docs = toys_ref.stream()

        toys = []
        for doc in toys_docs:
            toy_data = doc.to_dict()
            toys.append({
                "toyId": doc.id,
                "name": toy_data.get('name', 'N/A'),
                "emoji": toy_data.get('emoji', '🦄'),
                "assignedChildId": toy_data.get('assignedChildId'),
                "status": toy_data.get('status', 'offline')
            })

        return jsonify({
            "success": True,
            "toys": toys,
            "count": len(toys)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to list toys: {e}")
        return jsonify({"error": str(e)}), 500


# =============================================================================
# SIMULATOR-ONLY ENDPOINTS (No Authentication Required - For Testing Only)
# =============================================================================

@app.route("/api/simulator/users", methods=["GET"])
def simulator_list_users():
    """List all users from Firestore (SIMULATOR ONLY - No auth required)"""
    try:
        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        users_ref = firestore_service.db.collection("users")
        users_docs = users_ref.stream()

        users = []
        for doc in users_docs:
            user_data = doc.to_dict()
            users.append({
                "userId": doc.id,
                "email": user_data.get('email', 'N/A'),
                "displayName": user_data.get('displayName', 'N/A')
            })

        return jsonify({
            "success": True,
            "users": users,
            "count": len(users)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to list users: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulator/users/<user_id>/children", methods=["GET"])
def simulator_list_children(user_id):
    """List children for a specific user (SIMULATOR ONLY - No auth required)"""
    try:
        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        children_ref = firestore_service.db.collection("users").document(user_id).collection("children")
        children_docs = children_ref.stream()

        children = []
        for doc in children_docs:
            child_data = doc.to_dict()
            children.append({
                "childId": doc.id,
                "name": child_data.get('name', 'N/A'),
                "avatar": child_data.get('avatar', '🧒'),
                "ageLevel": child_data.get('ageLevel', 'N/A')
            })

        return jsonify({
            "success": True,
            "children": children,
            "count": len(children)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to list children: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulator/users/<user_id>/toys", methods=["GET"])
def simulator_list_toys(user_id):
    """List toys for a specific user (SIMULATOR ONLY - No auth required)"""
    try:
        if not firestore_service.is_available():
            return jsonify({"error": "Firestore not available"}), 503

        toys_ref = firestore_service.db.collection("users").document(user_id).collection("toys")
        toys_docs = toys_ref.stream()

        toys = []
        for doc in toys_docs:
            toy_data = doc.to_dict()
            toys.append({
                "toyId": doc.id,
                "name": toy_data.get('name', 'N/A'),
                "emoji": toy_data.get('emoji', '🦄'),
                "assignedChildId": toy_data.get('assignedChildId'),
                "status": toy_data.get('status', 'offline')
            })

        return jsonify({
            "success": True,
            "toys": toys,
            "count": len(toys)
        }), 200

    except Exception as e:
        print(f"[ERROR] Failed to list toys: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/simulator/children/<child_id>/knowledge/graph", methods=["GET"])
def simulator_get_knowledge_graph(child_id):
    """
    Get knowledge graph for simulator (SIMULATOR ONLY - No auth required)

    Query params:
    - user_id: Parent user ID (required)
    - timeRange: last_week | last_month | all_time (default: all_time)
    - entityTypes: comma-separated types (default: all)
    - edgeTypes: comma-separated edge types (default: all)
    - minWeight: 0.0-1.0 (default: 0.3)
    - limit: max nodes (default: 50)
    """
    try:
        from knowledge_graph_service import knowledge_graph_service
        from datetime import datetime, timedelta

        user_id = request.args.get('user_id')
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        # Parse query parameters
        time_range = request.args.get('timeRange', 'all_time')
        entity_types_param = request.args.get('entityTypes', '')
        edge_types_param = request.args.get('edgeTypes', '')
        min_weight = float(request.args.get('minWeight', 0.3))
        limit = int(request.args.get('limit', 50))

        entity_types = [t.strip() for t in entity_types_param.split(',') if t.strip()] if entity_types_param else None
        edge_types = [t.strip() for t in edge_types_param.split(',') if t.strip()] if edge_types_param else None

        # Get entities with filters
        query_filter = {"limit": limit}
        if entity_types and len(entity_types) == 1:
            query_filter["type"] = entity_types[0]

        entities = knowledge_graph_service.get_entities(user_id, child_id, query_filter)

        # Apply time filter if needed
        if time_range != 'all_time':
            cutoff_date = datetime.utcnow()
            if time_range == 'last_week':
                cutoff_date -= timedelta(days=7)
            elif time_range == 'last_month':
                cutoff_date -= timedelta(days=30)

            entities = [e for e in entities
                       if e.get('lastMentionedAt') and e['lastMentionedAt'] > cutoff_date]

        # Apply entity type filter (if multiple types)
        if entity_types:
            entities = [e for e in entities if e.get('type') in entity_types]

        entity_ids = {e['id'] for e in entities}

        # Get edges between these entities
        edges_ref = firestore_service.db.collection("users").document(user_id)\
            .collection("children").document(child_id)\
            .collection("edges")

        all_edges = []
        query = edges_ref.where("weight", ">=", min_weight)

        for edge_doc in query.stream():
            edge = edge_doc.to_dict()

            # Check if both entities are in our set
            if edge['sourceEntityId'] in entity_ids and edge['targetEntityId'] in entity_ids:
                # Apply edge type filter
                if not edge_types or edge['edgeType'] in edge_types:
                    all_edges.append(edge)

        # Convert to D3 format
        nodes = []
        for idx, entity in enumerate(entities):
            nodes.append({
                'id': entity['id'],
                'name': entity['name'],
                'type': entity['type'],
                'strength': entity.get('strength', 0),
                'mentionCount': entity.get('mentionCount', 0),
                'group': _get_node_group(entity['type']),
                'centrality': entity.get('centrality', 0),
                'cluster': entity.get('clusterId')
            })

        links = []
        for edge in all_edges:
            links.append({
                'source': edge['sourceEntityId'],
                'target': edge['targetEntityId'],
                'type': edge['edgeType'],
                'weight': edge['weight'],
                'value': edge['weight'] * 10
            })

        return jsonify({
            'success': True,
            'graph': {
                'nodes': nodes,
                'links': links,
                'stats': {
                    'nodeCount': len(nodes),
                    'linkCount': len(links),
                    'filters': {
                        'timeRange': time_range,
                        'entityTypes': entity_types,
                        'edgeTypes': edge_types,
                        'minWeight': min_weight
                    }
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Failed to get simulator graph visualization: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== KNOWLEDGE GRAPH API ENDPOINTS ====================

@app.route("/api/children/<child_id>/knowledge/summary", methods=["GET"])
@require_device_auth
def get_child_knowledge_summary(child_id):
    """
    Get aggregate knowledge graph summary for parent dashboard

    Returns: {success, summary: {stats, topTopics, topSkills, topInterests, learningProfile}}
    """
    try:
        user_id = get_current_user_id()
        from knowledge_graph_service import knowledge_graph_service

        summary = knowledge_graph_service.get_summary(user_id, child_id)

        if not summary:
            return jsonify({"success": True, "summary": None}), 200

        return jsonify({"success": True, "summary": summary}), 200

    except Exception as e:
        logger.error(f"Failed to get knowledge summary: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/children/<child_id>/knowledge/entities", methods=["GET"])
@require_device_auth
def get_child_entities(child_id):
    """
    Query entities with filters

    Query params:
    - type: Filter by entity type (topic, skill, interest, concept, personality_trait)
    - limit: Max results (default: 50)
    - orderBy: Sort field (mentionCount, lastMentionedAt, strength)

    Returns: {success, entities: [...]}
    """
    try:
        user_id = get_current_user_id()
        filters = {
            "type": request.args.get("type"),
            "limit": int(request.args.get("limit", 50)),
            "orderBy": request.args.get("orderBy", "strength")
        }

        from knowledge_graph_service import knowledge_graph_service
        entities = knowledge_graph_service.get_entities(user_id, child_id, filters)

        return jsonify({"success": True, "entities": entities, "count": len(entities)}), 200

    except Exception as e:
        logger.error(f"Failed to get entities: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/children/<child_id>/knowledge/observations", methods=["GET"])
@require_device_auth
def get_child_observations(child_id):
    """
    Get time-series observations for learning timeline

    Query params:
    - limit: Max results (default: 20)

    Returns: {success, observations: [...]}
    """
    try:
        user_id = get_current_user_id()
        limit = int(request.args.get("limit", 20))

        # Query observations collection
        observations_ref = firestore_service.db.collection("users").document(user_id)\
            .collection("children").document(child_id)\
            .collection("observations")

        observations_query = observations_ref.order_by("timestamp", direction=firestore.Query.DESCENDING)\
            .limit(limit)

        observations = []
        for doc in observations_query.stream():
            obs_data = doc.to_dict()
            observations.append(obs_data)

        return jsonify({"success": True, "observations": observations, "count": len(observations)}), 200

    except Exception as e:
        logger.error(f"Failed to get observations: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/children/<child_id>/knowledge/entities/<entity_id>", methods=["GET"])
@require_device_auth
def get_entity_details(child_id, entity_id):
    """
    Get full details of a specific entity including related entities

    Returns: {success, entity: {...}}
    """
    try:
        user_id = get_current_user_id()

        # Get entity document
        entity_ref = firestore_service.db.collection("users").document(user_id)\
            .collection("children").document(child_id)\
            .collection("entities").document(entity_id)

        entity_doc = entity_ref.get()

        if not entity_doc.exists:
            return jsonify({"success": False, "error": "Entity not found"}), 404

        entity_data = entity_doc.to_dict()

        return jsonify({"success": True, "entity": entity_data}), 200

    except Exception as e:
        logger.error(f"Failed to get entity details: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


# ================================
# KNOWLEDGE GRAPH VISUALIZATION ENDPOINTS
# ================================

@app.route("/api/children/<child_id>/knowledge/graph", methods=["GET"])
@require_device_auth
def get_knowledge_graph_visualization(child_id):
    """
    Get knowledge graph in D3.js force-directed format

    Query params:
    - timeRange: last_week | last_month | all_time (default: all_time)
    - entityTypes: comma-separated types (default: all)
    - edgeTypes: comma-separated edge types (default: all)
    - minWeight: 0.0-1.0 (default: 0.5)
    - limit: max nodes (default: 50)

    Returns:
        JSON with graph data (nodes and links in D3.js format)
    """
    try:
        from graph_query_service import GraphQueryService
        from knowledge_graph_service import knowledge_graph_service
        from datetime import datetime, timedelta

        user_id = g.user_id

        # Parse query parameters
        time_range = request.args.get('timeRange', 'all_time')
        entity_types_param = request.args.get('entityTypes', '')
        edge_types_param = request.args.get('edgeTypes', '')
        min_weight = float(request.args.get('minWeight', 0.5))
        limit = int(request.args.get('limit', 50))

        entity_types = [t.strip() for t in entity_types_param.split(',') if t.strip()] if entity_types_param else None
        edge_types = [t.strip() for t in edge_types_param.split(',') if t.strip()] if edge_types_param else None

        # Get entities with filters
        query_filter = {"limit": limit}
        if entity_types and len(entity_types) == 1:
            query_filter["type"] = entity_types[0]

        entities_result = knowledge_graph_service.get_entities(user_id, child_id, query_filter)
        entities = entities_result.get('entities', [])

        # Apply time filter if needed
        if time_range != 'all_time':
            cutoff_date = datetime.utcnow()
            if time_range == 'last_week':
                cutoff_date -= timedelta(days=7)
            elif time_range == 'last_month':
                cutoff_date -= timedelta(days=30)

            entities = [e for e in entities
                       if e.get('lastMentionedAt') and e['lastMentionedAt'] > cutoff_date]

        # Apply entity type filter (if multiple types)
        if entity_types:
            entities = [e for e in entities if e.get('type') in entity_types]

        entity_ids = {e['id'] for e in entities}

        # Get edges between these entities
        edges_ref = db.collection("users").document(user_id)\
            .collection("children").document(child_id)\
            .collection("edges")

        all_edges = []
        query = edges_ref.where("weight", ">=", min_weight)

        for edge_doc in query.stream():
            edge = edge_doc.to_dict()

            # Check if both entities are in our set
            if edge['sourceEntityId'] in entity_ids and edge['targetEntityId'] in entity_ids:
                # Apply edge type filter
                if not edge_types or edge['edgeType'] in edge_types:
                    all_edges.append(edge)

        # Convert to D3 format
        nodes = []
        for idx, entity in enumerate(entities):
            nodes.append({
                'id': entity['id'],
                'name': entity['name'],
                'type': entity['type'],
                'strength': entity.get('strength', 0),
                'mentionCount': entity.get('mentionCount', 0),
                'group': _get_node_group(entity['type']),  # For color coding
                'centrality': entity.get('centrality', 0),
                'cluster': entity.get('clusterId')
            })

        links = []
        for edge in all_edges:
            links.append({
                'source': edge['sourceEntityId'],
                'target': edge['targetEntityId'],
                'type': edge['edgeType'],
                'weight': edge['weight'],
                'value': edge['weight'] * 10  # D3 link strength
            })

        return jsonify({
            'success': True,
            'graph': {
                'nodes': nodes,
                'links': links,
                'stats': {
                    'nodeCount': len(nodes),
                    'linkCount': len(links),
                    'filters': {
                        'timeRange': time_range,
                        'entityTypes': entity_types,
                        'edgeTypes': edge_types,
                        'minWeight': min_weight
                    }
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Failed to get graph visualization: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/children/<child_id>/knowledge/graph/subgraph", methods=["POST"])
@require_device_auth
def get_knowledge_subgraph(child_id):
    """
    Get subgraph centered on specific entities

    Body:
    {
      "entityIds": ["topic_dinosaurs", "interest_space"],
      "depth": 2,
      "maxNodes": 20
    }

    Returns:
        JSON with subgraph in D3.js format
    """
    try:
        from graph_query_service import GraphQueryService

        user_id = g.user_id
        data = request.json

        entity_ids = data.get('entityIds', [])
        depth = data.get('depth', 2)
        max_nodes = data.get('maxNodes', 20)

        if not entity_ids:
            return jsonify({"success": False, "error": "entityIds required"}), 400

        graph_service = GraphQueryService(db)
        subgraph = graph_service.extract_context_subgraph(
            user_id, child_id, entity_ids, max_nodes, depth
        )

        # Convert to D3 format
        nodes = []
        for entity in subgraph['entities']:
            nodes.append({
                'id': entity['id'],
                'name': entity['name'],
                'type': entity['type'],
                'strength': entity.get('strength', 0),
                'group': _get_node_group(entity['type']),
                'isSeed': entity.get('isSeed', False)
            })

        links = []
        for edge in subgraph['edges']:
            links.append({
                'source': edge['sourceEntityId'],
                'target': edge['targetEntityId'],
                'type': edge['edgeType'],
                'weight': edge['weight'],
                'value': edge['weight'] * 10
            })

        return jsonify({
            'success': True,
            'graph': {
                'nodes': nodes,
                'links': links,
                'stats': {
                    'nodeCount': len(nodes),
                    'linkCount': len(links)
                }
            }
        }), 200

    except Exception as e:
        logger.error(f"Failed to get subgraph: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/children/<child_id>/knowledge/graph/clusters", methods=["GET"])
@require_device_auth
def get_knowledge_clusters(child_id):
    """
    Get interest clusters with visualization data

    Returns:
        JSON with cluster list, each containing entities and graph data
    """
    try:
        from graph_query_service import GraphQueryService

        user_id = g.user_id
        graph_service = GraphQueryService(db)

        # Find clusters
        clusters = graph_service.find_interest_clusters(user_id, child_id, min_cluster_size=2)

        # Build D3 graph for each cluster
        result = []
        for cluster in clusters:
            cluster_entity_ids = [e['id'] for e in cluster['entities']]

            # Get edges within cluster
            edges_ref = db.collection("users").document(user_id)\
                .collection("children").document(child_id)\
                .collection("edges")

            cluster_edges = []
            for edge_doc in edges_ref.where("edgeType", "==", "temporal_cooccurrence").stream():
                edge = edge_doc.to_dict()
                if (edge['sourceEntityId'] in cluster_entity_ids and
                    edge['targetEntityId'] in cluster_entity_ids):
                    cluster_edges.append(edge)

            # Convert to D3 format
            nodes = []
            for entity in cluster['entities']:
                nodes.append({
                    'id': entity['id'],
                    'name': entity['name'],
                    'type': entity['type'],
                    'strength': entity.get('strength', 0),
                    'group': _get_node_group(entity['type'])
                })

            links = []
            for edge in cluster_edges:
                links.append({
                    'source': edge['sourceEntityId'],
                    'target': edge['targetEntityId'],
                    'weight': edge['weight'],
                    'value': edge['weight'] * 10
                })

            result.append({
                'clusterId': cluster['clusterId'],
                'label': cluster['label'],
                'size': cluster['size'],
                'entities': [{'id': e['id'], 'name': e['name'], 'type': e['type']} for e in cluster['entities']],
                'graph': {
                    'nodes': nodes,
                    'links': links
                }
            })

        return jsonify({'success': True, 'clusters': result}), 200

    except Exception as e:
        logger.error(f"Failed to get clusters: {e}", exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


def _get_node_group(entity_type):
    """Map entity type to group number for D3 color coding"""
    type_map = {
        'topic': 1,
        'skill': 2,
        'interest': 3,
        'concept': 4,
        'personality_trait': 5
    }
    return type_map.get(entity_type, 0)


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
