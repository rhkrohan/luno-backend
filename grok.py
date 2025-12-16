import os
import logging
from deepgram import DeepgramClient

def transcribe_audio(audio_file_path, api_key=None):
    """
    Transcribe audio file using Deepgram API

    Args:
        audio_file_path (str): Path to the audio file
        api_key (str): Deepgram API key (optional, will use environment variable if not provided)

    Returns:
        str: Transcribed text or None if error
    """
    try:
        # Use provided API key or get from environment
        if api_key:
            client = DeepgramClient(api_key)
        else:
            # Assumes DEEPGRAM_API_KEY environment variable is set
            client = DeepgramClient()

        # Check if file exists
        if not os.path.exists(audio_file_path):
            print(f"Error: Audio file not found at {audio_file_path}")
            return None

        # Transcribe local audio file
        with open(audio_file_path, "rb") as audio_file:
            response = client.listen.v1.media.transcribe_file(
                request=audio_file.read(),
                model="nova-3",
                smart_format=True,
            )

        # Extract transcript from response
        # Access the response object attributes directly
        transcript = response.results.channels[0].alternatives[0].transcript
        return transcript

    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None

def main():
    """
    Example usage - transcribe all audio files in current directory
    """
    # Audio file extensions to look for
    audio_extensions = ['.wav', '.mp3', '.mp4', '.m4a', '.flac', '.ogg']

    # Get current directory
    current_dir = os.getcwd()

    # Find audio files in current directory
    audio_files = []
    for file in os.listdir(current_dir):
        if any(file.lower().endswith(ext) for ext in audio_extensions):
            audio_files.append(file)

    if not audio_files:
        print("No audio files found in current directory")
        return

    print(f"Found {len(audio_files)} audio file(s):")
    for i, file in enumerate(audio_files, 1):
        print(f"{i}. {file}")

    # Transcribe each audio file
    for audio_file in audio_files:
        print(f"\nTranscribing: {audio_file}")
        transcript = transcribe_audio(audio_file)

        if transcript:
            print(f"Transcript: {transcript}")

            # Save transcript to text file
            transcript_file = f"{os.path.splitext(audio_file)[0]}_transcript.txt"
            with open(transcript_file, 'w', encoding='utf-8') as f:
                f.write(transcript)
            print(f"Transcript saved to: {transcript_file}")
        else:
            print("Failed to transcribe audio")

if __name__ == "__main__":
    main()