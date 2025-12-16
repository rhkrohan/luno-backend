import base64
import os
import requests

def synthesize_speechify(text, output_path, voice_id):
    """
    Convert `text` into a WAV file at `output_path` using Speechify API.
    """
    api_key = os.getenv("SPEECHIFY_API_KEY")
    if not api_key:
        raise ValueError("SPEECHIFY_API_KEY environment variable not set")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    data = {
        "input": text,
        "voice_id": voice_id
    }
    
    response = requests.post(
        "https://api.speechify.com/v1/audio/speech",
        headers=headers,
        json=data
    )
    
    if response.status_code == 200:
        audio_data = base64.b64decode(response.json()["audio_data"])
        with open(output_path, "wb") as out:
            out.write(audio_data)
        print(f"[INFO] Audio content written to {output_path}")
    else:
        raise Exception(f"Speechify API error: {response.status_code} - {response.text}")


# Example usage:
synthesize_speechify("Hello, Luna!", "temp/test_speechify.wav", voice_id="kristy")