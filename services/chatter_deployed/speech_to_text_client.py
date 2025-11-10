"""Speech-to-Text client for converting audio bytes to text.

This replaces live_api_client.py and uses Google Cloud Speech-to-Text API
for reliable batch transcription of audio.
"""

import os
from typing import Optional

# Try Google Cloud Speech-to-Text first (preferred)
try:
    from google.cloud import speech
    GOOGLE_SPEECH_AVAILABLE = True
except ImportError:
    GOOGLE_SPEECH_AVAILABLE = False
    print("[speech-to-text] google-cloud-speech not available, will try OpenAI Whisper")

# Fallback to OpenAI Whisper if Google Speech not available
try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


async def audio_to_text(audio_bytes: bytes) -> Optional[str]:
    """
    Convert audio bytes (PCM 16kHz mono) to text using Speech-to-Text API.
    
    Args:
        audio_bytes: Raw audio data in PCM 16kHz mono format
        
    Returns:
        Transcribed text string, or None if transcription fails
    """
    try:
        print(f"[speech-to-text] Starting transcription, audio size: {len(audio_bytes)} bytes")
        
        # Try Google Cloud Speech-to-Text first
        if GOOGLE_SPEECH_AVAILABLE:
            return await _transcribe_with_google_speech(audio_bytes)
        
        # Fallback to OpenAI Whisper
        elif OPENAI_AVAILABLE:
            return await _transcribe_with_openai_whisper(audio_bytes)
        
        else:
            print("[speech-to-text-error] No speech-to-text library available")
            return None
            
    except Exception as e:
        print(f"[speech-to-text-error] Failed to transcribe audio: {e}")
        import traceback
        traceback.print_exc()
        return None


async def _transcribe_with_google_speech(audio_bytes: bytes) -> Optional[str]:
    """Transcribe using Google Cloud Speech-to-Text API."""
    try:
        # Initialize client (uses GOOGLE_APPLICATION_CREDENTIALS from env)
        client = speech.SpeechClient()
        
        # Create audio object
        audio = speech.RecognitionAudio(content=audio_bytes)
        
        # Try multiple sample rates (browsers often use 44.1kHz or 48kHz, not 16kHz)
        sample_rates_to_try = [44100, 48000, 16000, 22050, 32000]
        
        print("[speech-to-text] Trying multiple sample rates...")
        
        for sample_rate in sample_rates_to_try:
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=sample_rate,
                language_code="en-US",
                enable_automatic_punctuation=True,
                enable_word_time_offsets=False,
                audio_channel_count=1,  # Mono
            )
            
            print(f"[speech-to-text] Trying sample rate: {sample_rate} Hz...")
            
            try:
                # Perform transcription
                response = client.recognize(config=config, audio=audio)
        
                # Debug: Print full response
                print(f"[speech-to-text] Response received: {len(response.results)} results")
                
                # Extract transcript from response
                transcript_parts = []
                for i, result in enumerate(response.results):
                    if result.alternatives:
                        transcript_text = result.alternatives[0].transcript
                        confidence = result.alternatives[0].confidence if hasattr(result.alternatives[0], 'confidence') else None
                        print(f"[speech-to-text] Result {i}: '{transcript_text}' (confidence: {confidence})")
                        if transcript_text.strip():  # Only add non-empty transcripts
                            transcript_parts.append(transcript_text)
                
                transcript = " ".join(transcript_parts)
                
                if transcript.strip():
                    print(f"[speech-to-text] Transcription successful at {sample_rate}Hz: {transcript[:100]}...")
                    return transcript.strip()
                else:
                    print(f"[speech-to-text] No transcript at {sample_rate}Hz, trying next...")
                    continue  # Try next sample rate
                    
            except Exception as e:
                print(f"[speech-to-text] Error at {sample_rate}Hz: {e}, trying next...")
                continue  # Try next sample rate
        
        # If we get here, none of the sample rates worked
        print("[speech-to-text] No transcript returned from any sample rate")
        return None
            
    except Exception as e:
        print(f"[speech-to-text-error] Google Speech-to-Text error: {e}")
        raise


async def _transcribe_with_openai_whisper(audio_bytes: bytes) -> Optional[str]:
    """Transcribe using OpenAI Whisper API (fallback)."""
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("[speech-to-text-error] OPENAI_API_KEY not set")
            return None
        
        client = OpenAI(api_key=api_key)
        
        print("[speech-to-text] Sending audio to OpenAI Whisper...")
        
        # OpenAI Whisper expects a file-like object
        import io
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.pcm"  # Give it a name
        
        # Call Whisper API
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="en",
            response_format="text"
        )
        
        if transcript:
            print(f"[speech-to-text] Transcription successful: {transcript[:100]}...")
            return transcript.strip()
        else:
            print("[speech-to-text] No transcript returned from OpenAI Whisper")
            return None
            
    except Exception as e:
        print(f"[speech-to-text-error] OpenAI Whisper error: {e}")
        raise

