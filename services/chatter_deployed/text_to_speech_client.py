"""Google Cloud Text-to-Speech streaming client.

Converts text to audio using Google Cloud Text-to-Speech API and streams audio chunks in real-time.


FUNCTION CONTAINED:

async def text_to_audio_stream(text: str, websocket) -> Optional[str]:

def _pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1, sample_width: int =
2) -> bytes:
(Convert raw PCM audio data to WAV format.)

"""

import struct
from typing import Optional
from google.cloud import texttospeech


# text_to_audio_stream converts text to audio using Google Cloud TTS and streams audio chunks to WebSocket
async def text_to_audio_stream(text: str, websocket) -> Optional[str]:
    """
    Convert text to audio using Google Cloud Text-to-Speech API and stream audio chunks to WebSocket.

    Args:
        text: The podcast text to convert to audio (narrated EXACTLY as written)
        websocket: WebSocket connection to stream audio chunks to frontend

    Returns:
        Success message or None if failed
    """
    try:
        print(f"[cloud-tts] Starting text-to-audio conversion, text length: {len(text)} chars")

        # Initialize Google Cloud Text-to-Speech client
        # Uses ADC (Application Default Credentials) - no API key needed
        client = texttospeech.TextToSpeechClient()

        # Configure the synthesis request
        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Voice configuration - using a natural-sounding English voice
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name="en-US-Studio-O"  # High-quality Studio voice (natural podcaster sound)
            # Note: Studio voices don't require ssml_gender parameter
        )

        # Audio configuration - LINEAR16 (PCM) format at 24kHz
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=24000,
            speaking_rate=1.0,  # Normal speaking speed
            pitch=0.0  # Normal pitch
        )

        print("[cloud-tts] Sending text to Google Cloud Text-to-Speech API...")

        # Perform the text-to-speech request
        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        print(f"[cloud-tts] Received audio data: {len(response.audio_content)} bytes")

        # The response contains raw PCM audio data
        pcm_data = response.audio_content

        # Convert PCM to WAV format
        print("[cloud-tts] Converting PCM to WAV format...")
        wav_data = _pcm_to_wav(pcm_data, sample_rate=24000)

        print(f"[cloud-tts] Converted to WAV: {len(pcm_data)} bytes PCM -> {len(wav_data)} bytes WAV")

        # Stream WAV chunks to frontend via websocket
        chunk_size = 8192
        chunks_sent = 0
        for i in range(0, len(wav_data), chunk_size):
            chunk = wav_data[i : i + chunk_size]
            await websocket.send_bytes(chunk)
            chunks_sent += 1

        print(f"[cloud-tts] Streamed {chunks_sent} WAV audio chunks to frontend")
        return "success"

    except Exception as e:
        print(f"[cloud-tts-error] Failed to convert text to audio: {e}")
        import traceback

        traceback.print_exc()
        return None


def _pcm_to_wav(
    pcm_data: bytes,
    sample_rate: int = 24000,
    channels: int = 1,
    sample_width: int = 2,
) -> bytes:
    """
    Convert raw PCM audio data to WAV format.

    Args:
        pcm_data: Raw PCM audio bytes (16-bit signed integers)
        sample_rate: Sample rate in Hz (default 24000 for LiveAPI)
        channels: Number of audio channels (1 = mono, 2 = stereo)
        sample_width: Bytes per sample (2 = 16-bit)

    Returns:
        WAV file as bytes
    """
    # WAV file header structure
    # RIFF header
    data_size = len(pcm_data)
    file_size = 36 + data_size

    wav_header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",  # ChunkID
        file_size,  # ChunkSize
        b"WAVE",  # Format
        b"fmt ",  # Subchunk1ID
        16,  # Subchunk1Size (PCM)
        1,  # AudioFormat (1 = PCM)
        channels,  # NumChannels
        sample_rate,  # SampleRate
        sample_rate * channels * sample_width,  # ByteRate
        channels * sample_width,  # BlockAlign
        sample_width * 8,  # BitsPerSample
        b"data",  # Subchunk2ID
        data_size,  # Subchunk2Size
    )

    return wav_header + pcm_data
