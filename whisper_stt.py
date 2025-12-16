from openai import OpenAI
import os
import time

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def transcribe_audio(file_path):
    try:
        start_time = time.time()
        print(f"[INFO] Transcribing {file_path} using Whisper API...")
        
        # Check if file exists and has content
        if not os.path.exists(file_path):
            print(f"[ERROR] Audio file not found: {file_path}")
            return None
            
        file_size = os.path.getsize(file_path)
        if file_size == 0:
            print(f"[ERROR] Audio file is empty: {file_path}")
            return None
            
        print(f"[INFO] Processing audio file: {file_size} bytes")
        
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text",  # Get plain text response
                temperature=0.0,        # More deterministic
                language="en"           # English only for speed
            )
            
        transcription_time = time.time() - start_time
        print(f"[INFO] Whisper transcription completed in {transcription_time:.2f}s")
        print(f"[TRANSCRIPT] '{transcript}'")
        
        return transcript.strip() if transcript else None
        
    except Exception as e:
        print(f"[ERROR] Whisper transcription failed: {e}")
        return None

file_path = "/Users/rohankhan/Desktop/plushieAI/temp/a.m4a"
text = transcribe_audio(file_path)

print(f"[TRANSCRIPT] {text}")