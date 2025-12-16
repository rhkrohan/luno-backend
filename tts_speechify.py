import base64
import os
import requests

def synthesize_speech(text, output_path):
    """
    Convert `text` into a WAV file at `output_path` using Speechify API.
    Compatible with existing tts.py interface.
    """
    api_key = os.getenv("SPEECHIFY_API_KEY")
    if not api_key:
        raise ValueError("SPEECHIFY_API_KEY environment variable not set")

    # Get voice_id from environment variable, default to "kristy"
    voice_id = os.getenv("SPEECHIFY_VOICE_ID", "kristy")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "input": text,
        "voice_id": voice_id
    }

    try:
        print(f"[INFO] Generating speech with Speechify for: '{text[:50]}{'...' if len(text) > 50 else ''}'")

        response = requests.post(
            "https://api.speechify.com/v1/audio/speech",
            headers=headers,
            json=data,
            timeout=30
        )

        if response.status_code == 200:
            audio_data = base64.b64decode(response.json()["audio_data"])

            # Convert to absolute path
            abs_output_path = os.path.abspath(output_path)

            with open(abs_output_path, "wb") as out:
                out.write(audio_data)

            file_size = os.path.getsize(abs_output_path)
            print(f"[INFO] Speechify audio written to {abs_output_path}")
            print(f"[INFO] Output file size: {file_size} bytes")
        else:
            raise Exception(f"Speechify API error: {response.status_code} - {response.text}")

    except requests.RequestException as e:
        print(f"[ERROR] Speechify API request failed: {e}")
        raise Exception(f"Speechify TTS failed: {str(e)}")
    except Exception as e:
        print(f"[ERROR] Speechify TTS synthesis failed: {e}")
        raise


# Example usage:
# synthesize_speech("Hello, Luna!", "temp/test_speechify.wav")