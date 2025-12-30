import os
import requests
import subprocess
import tempfile

def synthesize_speech_streaming(text, output_path):
    """
    Convert `text` into a WAV file at `output_path` using ElevenLabs streaming TTS.
    This version streams audio chunks for lower latency.
    """
    # Get API key from environment
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set")

    # Convert to absolute path to ensure consistency
    abs_output_path = os.path.abspath(output_path)

    # ElevenLabs API configuration - use the same voice and settings
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "5oDR2Spw4ffxVYWXiJC2")  # Rachel
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }

    data = {
        "text": text,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.6,
            "similarity_boost": 0.5,
            "style": 0.0,
            "use_speaker_boost": True,
            "speed": 0.85
        },
        "optimize_streaming_latency": 3  # 0-4, higher = lower latency but potentially lower quality
    }

    try:
        print(f"[INFO] Streaming speech with ElevenLabs for: '{text[:50]}{'...' if len(text) > 50 else ''}'")

        # Make streaming API request
        response = requests.post(url, json=data, headers=headers, timeout=30, stream=True)
        response.raise_for_status()

        # Write streaming chunks to temporary file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            bytes_received = 0
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    temp_file.write(chunk)
                    bytes_received += len(chunk)
            temp_path = temp_file.name

        print(f"[INFO] ElevenLabs streaming audio received: {bytes_received} bytes")

        try:
            # Convert MP3 to WAV and resample to 16kHz using ffmpeg with exact ESP32 format
            subprocess.run([
                "/usr/local/bin/ffmpeg", "-i", temp_path,
                "-ar", "16000",         # 16000 Hz sample rate
                "-ac", "1",             # mono channel
                "-acodec", "pcm_s16le", # PCM signed 16-bit little-endian
                "-f", "wav",            # WAV format
                "-y",                   # overwrite output
                abs_output_path
            ], check=True, capture_output=True)

            # Verify the output file
            file_size = os.path.getsize(abs_output_path)
            print(f"[INFO] ElevenLabs streaming audio resampled to 16kHz and written to {abs_output_path}")
            print(f"[INFO] Output file size: {file_size} bytes")

            # Use ffprobe to verify audio format
            try:
                result = subprocess.run([
                    "/usr/local/bin/ffprobe", "-v", "quiet", "-print_format", "json",
                    "-show_format", "-show_streams", abs_output_path
                ], capture_output=True, text=True, check=True)
                import json
                info = json.loads(result.stdout)
                if 'streams' in info and len(info['streams']) > 0:
                    stream = info['streams'][0]
                    print(f"[INFO] Audio format: {stream.get('codec_name')} {stream.get('sample_rate')}Hz {stream.get('channels')}ch")
            except:
                print("[WARN] Could not verify audio format with ffprobe")

        except subprocess.CalledProcessError as e:
            print(f"[ERROR] FFmpeg conversion failed: {e}")
            # Fallback: rename original MP3 to output path (not ideal for ESP32)
            os.rename(temp_path, abs_output_path)
            print(f"[WARN] Using original MP3 format at {abs_output_path}")
        finally:
            # Clean up temp file if it still exists
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    except requests.RequestException as e:
        print(f"[ERROR] ElevenLabs streaming API request failed: {e}")
        raise Exception(f"ElevenLabs streaming TTS failed: {str(e)}")
    except Exception as e:
        print(f"[ERROR] ElevenLabs streaming TTS synthesis failed: {e}")
        raise


# Keep the same function name for drop-in replacement
def synthesize_speech(text, output_path):
    """Wrapper to maintain compatibility with existing code"""
    return synthesize_speech_streaming(text, output_path)
