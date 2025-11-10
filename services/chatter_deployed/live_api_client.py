"""This client is used to encapsulate the live API WebSocket connection logic!!"""

"""This function below is defining: the transition from user audio input on the frontend, to converted text (VIA
LIVE API) so our backend cn process it correctly"""
import asyncio
import os
from pathlib import Path
from google import genai
from google.genai import types
from typing import Optional 

async def audio_to_text(audio_bytes: bytes) -> Optional[str]:
    try:
        print(f"[live-api] Starting transcription, audio size: {len(audio_bytes)} bytes")
        
        # Live API is only available through Google AI API (not Vertex AI)
        # Check for API key first, fall back to Vertex AI if not available
        api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
        
        if api_key:
            # Use Google AI API (requires API key)
            print("[live-api] Using Google AI API (api_key)")
            client = genai.Client(api_key=api_key)
        else:
            # Fallback to Vertex AI (though Live API may not work)
            print("[live-api] No API key found, falling back to Vertex AI (Live API may not be available)")
            project = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
            location = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")
            client = genai.Client(vertexai=True, project=project, location=location)
        
        model = "gemini-live-2.5-flash-preview" #this is the half-cascase audio
    #because half cascade outputs text 
        config = {"response_modalities": ["TEXT"]}

        print(f"[live-api] Connecting to Live API with model: {model}")
        async with client.aio.live.connect(model=model, config=config) as session:
            print("[live-api] Connected")
            
            # Accumulate text chunks
            transcript = ""
            response_count = 0
            
            # Start receiving responses in parallel with sending audio
            async def collect_responses():
                nonlocal transcript, response_count
                print("[live-api] Starting to receive responses...")
                try:
                    async for response in session.receive():
                        response_count += 1
                        print(f"[live-api] Received response {response_count}, type: {type(response)}")
                        
                        # Check multiple possible response formats
                        if hasattr(response, 'text') and response.text is not None:
                            transcript += response.text
                            print(f"[live-api] Received text chunk {response_count}: {response.text[:50]}...")
                        elif hasattr(response, 'candidates') and response.candidates:
                            # Check if response has candidates (common in Gemini API)
                            for candidate in response.candidates:
                                if hasattr(candidate, 'content') and candidate.content:
                                    if hasattr(candidate.content, 'parts'):
                                        for part in candidate.content.parts:
                                            if hasattr(part, 'text') and part.text:
                                                transcript += part.text
                                                print(f"[live-api] Received text from candidate: {part.text[:50]}...")
                        elif hasattr(response, 'parts') and response.parts:
                            # Check if response has parts directly
                            for part in response.parts:
                                if hasattr(part, 'text') and part.text:
                                    transcript += part.text
                                    print(f"[live-api] Received text from part: {part.text[:50]}...")
                        else:
                            print(f"[live-api] Response {response_count} has no recognizable text format")
                            print(f"[live-api] Response str: {str(response)[:200]}")
                except Exception as e:
                    print(f"[live-api] Error in receive loop: {e}")
                    import traceback
                    traceback.print_exc()
                    raise
            
            # Start receiving in background
            receive_task = asyncio.create_task(collect_responses())
            
            # Stream audio in chunks (Live API expects real-time streaming)
            print(f"[live-api] Streaming audio in chunks (total size: {len(audio_bytes)} bytes)...")
            chunk_size = 8192  # 8KB chunks for streaming
            total_chunks = (len(audio_bytes) + chunk_size - 1) // chunk_size
            
            for i in range(0, len(audio_bytes), chunk_size):
                chunk = audio_bytes[i:i + chunk_size]
                chunk_num = (i // chunk_size) + 1
                print(f"[live-api] Sending chunk {chunk_num}/{total_chunks} ({len(chunk)} bytes)...")
                await session.send_realtime_input(audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000"))
                # Small delay to simulate real-time streaming
                await asyncio.sleep(0.01)  # 10ms delay between chunks
            
            print("[live-api] All audio chunks sent, signaling end of stream...")
            await session.send_realtime_input(audio_stream_end=True)
            
            # Give it a moment to process, then wait for responses
            await asyncio.sleep(0.5)
            
            # Wait for responses with timeout
            try:
                print("[live-api] Waiting for transcription (60s timeout)...")
                await asyncio.wait_for(receive_task, timeout=60.0)
            except asyncio.TimeoutError:
                print("[live-api] Timeout waiting for transcription response (60s)")
                print(f"[live-api] Total responses received before timeout: {response_count}")
                receive_task.cancel()  # Cancel the receive task
                try:
                    await receive_task
                except asyncio.CancelledError:
                    pass
                if transcript:
                    print(f"[live-api] Returning partial transcript: {transcript}")
                    return transcript
                else:
                    print("[live-api] No transcript received, returning None")
                    return None
            
            print(f"[live-api] Transcription complete, total chunks: {response_count}, transcript length: {len(transcript)}")
            #return user query if they made one 
            return transcript if transcript else None
    except Exception as e:
        print(f"[live-api-error] Failed to transcribe audio: {e}")
        import traceback
        traceback.print_exc()
        return None 

