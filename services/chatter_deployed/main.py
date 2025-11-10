

'''
main.py

Main app file for chatter service as a FastAPI

Endpoints:

* /healthz
For checking whether the app works

* /api/chatter
Main chatter endpoint: calls the chatter() function.

'''


#load_dotenv()  # This loads .env file
from dotenv import load_dotenv
load_dotenv()

import os
import logging
from typing import Dict, Any
#uploadfile handels audio file auploads from frontend
from fastapi import FastAPI, Body, HTTPException, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse #streaming response stream audio chunks back to frontend
from speech_to_text_client import audio_to_text  # Speech-to-Text function
from live_api_tts_client import text_to_audio_stream  # LiveAPI Text-to-Audio streaming
import io
from fastapi.middleware.cors import CORSMiddleware
import json
import base64
from typing import Optional 

#importing helper functions
from chatter_handler import chatter
from helpers import call_retriever_service, call_gemini_api
from chatter_handler import model
from openai import OpenAI 




# --------------------------
# Config
# --------------------------
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")
# --------------------------
# App / Clients
# --------------------------
logging.basicConfig(level=logging.INFO)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_methods=["POST", "OPTIONS", "GET"],
    allow_headers=["*"],
)

# --------------------------
# Health
# --------------------------
@app.get("/healthz")
async def healthz_root() -> Dict[str, bool]:
    return {"ok": True}

#------------
#Websocket Audio Endpoint
#------------
#WebSocket route decorator
#/ws/chat - WebSocket endpoint path
@app.websocket("/ws/chat") 
async def websocket_chatter(websocket: WebSocket):
    """WebSocket endpoint for real-time audio streaming.
    
    Protocol:
    - Frontend sends audio chunks as bytes OR JSON with base64 audio
    - Frontend sends {"type": "complete"} when audio is done
    - Backend sends status updates as JSON
    - Backend streams audio response as bytes
    """
    await websocket.accept()
    audio_buffer = bytearray()
    tts_client = OpenAI()  # Initialize once, reuse in loop

    try: 
        while True:
            #receive audio chunks from frontend
            # data = await websocket.receive_bytes()
            #OR if frontedn sends JSON with audio data
            message = await websocket.receive()
            if message["type"] == "websocket.receive":
                # Handle raw audio bytes
                if "bytes" in message:
                    audio_buffer.extend(message["bytes"])
                    await websocket.send_json({"status": "chunk_received", "size": len(audio_buffer)})
                
                # Handle JSON control messages
                elif "text" in message:
                    try:
                        data = json.loads(message["text"])

                        if data.get("type") == "complete":
                            # Check if we have audio to process
                            if len(audio_buffer) == 0:
                                await websocket.send_json({"error": "No audio received"})
                                continue
                            
                            print(f"[websocket] Received complete signal, audio buffer size: {len(audio_buffer)} bytes")
                            
                            # Step 1: Convert audio to text
                            await websocket.send_json({"status": "transcribing"})
                            print("[websocket] Starting transcription...")
                            
                            try:
                                text = await audio_to_text(bytes(audio_buffer))
                                print(f"[websocket] Transcription complete, text: {text[:100] if text else 'None'}...")
                            except Exception as e:
                                print(f"[websocket] Transcription error: {e}")
                                await websocket.send_json({"error": f"Transcription failed: {str(e)}"})
                                audio_buffer.clear()
                                continue
                            
                            if not text:
                                await websocket.send_json({"error": "Failed to transcribe audio (empty response)"})
                                audio_buffer.clear()
                                continue
                            
                            await websocket.send_json({"status": "transcribed", "text": text})
                            
                            # Step 2: Retrieve relevant chunks
                            await websocket.send_json({"status": "retrieving"})
                            chunks = call_retriever_service(text) ##THIS IS WHERE THE RETIREVAL STEP HAPPENS 
                            
                            if not chunks:
                                await websocket.send_json({"warning": "No relevant articles found"})
                            
                            # Step 3: Generate podcast text
                            await websocket.send_json({"status": "generating"})
                            podcast_text, error = call_gemini_api(text, chunks, model)
                            
                            if error or not podcast_text:
                                await websocket.send_json({"error": f"LLM error: {error}"})
                                audio_buffer.clear()
                                continue
                            
                            await websocket.send_json({"status": "podcast_generated", "text": podcast_text})
                            
                            # Step 4: Stream text-to-audio using LiveAPI
                            await websocket.send_json({"status": "converting_to_audio"})
                            try:
                                # Signal that we're starting to stream audio
                                await websocket.send_json({"status": "streaming_audio"})
                                
                                # Use LiveAPI to convert text to audio and stream it
                                result = await text_to_audio_stream(podcast_text, websocket)
                                
                                if not result:
                                    await websocket.send_json({"error": "Failed to generate audio stream"})
                                    audio_buffer.clear()
                                    continue
                                
                                # Signal completion
                                await websocket.send_json({"status": "complete"})
                                
                            except Exception as e:
                                await websocket.send_json({"error": f"TTS failed: {str(e)}"})
                                audio_buffer.clear()
                                continue
                            
                            # Reset buffer for next request
                            audio_buffer.clear()
                            
                        elif data.get("type") == "audio":
                            # JSON with base64 audio data
                            audio_bytes = base64.b64decode(data["data"])
                            audio_buffer.extend(audio_bytes)
                            
                        elif data.get("type") == "reset":
                            # Frontend wants to reset
                            audio_buffer.clear()
                            await websocket.send_json({"status": "reset"})
                            
                    except json.JSONDecodeError:
                        await websocket.send_json({"error": "Invalid JSON"})
                    except Exception as e:
                        await websocket.send_json({"error": str(e)})
    except WebSocketDisconnect:
        print("[websocket] Client disconnected")
    except Exception as e:
        print(f"[websocket-error] {e}")
        try:
            await websocket.send_json({"error": str(e)})
        except:
            pass

            

# --------------------------
# Main Endpoint
# --------------------------
@app.post("/api/chatter")
async def chatter_endpoint(payload: Dict[str, Any] = Body(...)):
    return await chatter(payload)

