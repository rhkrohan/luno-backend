import os
import requests
import subprocess
import tempfile

def synthesize_speech(text, output_path):
    """
    Convert `text` into a WAV file at `output_path` using ElevenLabs TTS.
    Compatible with existing tts.py interface.
    """
    # Get API key from environment
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set")
    
    # Convert to absolute path to ensure consistency
    abs_output_path = os.path.abspath(output_path)
    
    # ElevenLabs API configuration
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "5oDR2Spw4ffxVYWXiJC2")  # Default: Rachel
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
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
        }
    }
    
    try:
        print(f"[INFO] Generating speech with ElevenLabs for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        
        # Make API request
        response = requests.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Write to temporary file first (MP3 format from ElevenLabs)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as temp_file:
            temp_file.write(response.content)
            temp_path = temp_file.name
        
        print(f"[INFO] ElevenLabs audio received: {len(response.content)} bytes")
        
        try:
            # Convert MP3 to WAV and resample to 16kHz using ffmpeg with exact ESP32 format
            subprocess.run([
                "ffmpeg", "-i", temp_path, 
                "-ar", "16000",         # 16000 Hz sample rate
                "-ac", "1",             # mono channel
                "-acodec", "pcm_s16le", # PCM signed 16-bit little-endian
                "-f", "wav",            # WAV format
                "-y",                   # overwrite output
                abs_output_path
            ], check=True, capture_output=True)
            
            # Verify the output file
            file_size = os.path.getsize(abs_output_path)
            print(f"[INFO] ElevenLabs audio resampled to 16kHz and written to {abs_output_path}")
            print(f"[INFO] Output file size: {file_size} bytes")
            
            # Use ffprobe to verify audio format
            try:
                result = subprocess.run([
                    "ffprobe", "-v", "quiet", "-print_format", "json", 
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
        print(f"[ERROR] ElevenLabs API request failed: {e}")
        raise Exception(f"ElevenLabs TTS failed: {str(e)}")
    except Exception as e:
        print(f"[ERROR] ElevenLabs TTS synthesis failed: {e}")
        raise

# Example usage for testing (commented out)
# synthesize_speech("Hello, this is Luna speaking with ElevenLabs!", "temp/test_elevenlabs.wav")
