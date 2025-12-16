import os
from openai import OpenAI
import subprocess
import tempfile

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def synthesize_speech(text, output_path):
    """
    Convert `text` into a WAV file at `output_path` using OpenAI TTS-1.
    """
    # Convert to absolute path to ensure consistency
    abs_output_path = os.path.abspath(output_path)
    
    response = client.audio.speech.create(
        model="tts-1",  # or "tts-1-hd"
        voice="nova",   # or "alloy", "echo", "fable", "onyx", "shimmer"
        input=text,
        speed=0.80,
        response_format="wav"
    )
    
    # Write to temporary file first
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_file.write(response.content)
        temp_path = temp_file.name
    
    try:
        # Resample to 16kHz using ffmpeg with exact ESP32 format
        subprocess.run([
            "/usr/bin/ffmpeg", "-i", temp_path, 
            "-ar", "16000",         # 16000 Hz sample rate
            "-ac", "1",             # mono channel
            "-acodec", "pcm_s16le", # PCM signed 16-bit little-endian
            "-f", "wav",            # WAV format
            "-y",                   # overwrite output
            abs_output_path
        ], check=True, capture_output=True)
        # Verify the output file
        file_size = os.path.getsize(abs_output_path)
        print(f"[INFO] Audio resampled to 16kHz and written to {abs_output_path}")
        print(f"[INFO] Output file size: {file_size} bytes")
        
        # Use ffprobe to verify audio format
        try:
            result = subprocess.run([
                "/usr/bin/ffprobe", "-v", "quiet", "-print_format", "json", 
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
        print(f"[ERROR] FFmpeg failed: {e}")
        # Fallback: use original file
        os.rename(temp_path, abs_output_path)
        print(f"[WARN] Using original audio without resampling at {abs_output_path}")
    finally:
        # Clean up temp file if it still exists
        if os.path.exists(temp_path):
            os.unlink(temp_path)

#synthesize_speech("Hello, Sarim?", "temp/test_output.wav")  # Example call for testing