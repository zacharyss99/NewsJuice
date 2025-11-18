

'''
main.py

Main app file for chatter service as a FastAPI

ENDPOINTS CONTAINED:

@app.get("/healthz")
For checking whether the app works

@app.post("/api/chatter")
Main chatter endpoint: calls the chatter() function.

@app.websocket("/ws/chat") 

@app.post("/api/user/create")

@app.get("/api/user/preferences")

@app.post("/api/user/preferences")

@app.get("/api/user/history")

class FirebaseAuthMiddleware(BaseHTTPMiddleware):



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
from firebase_auth import initialize_firebase_admin, verify_token
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, HTTPException
from user_db import create_user, get_user_preferences, save_user_preferences, save_audio_history, get_audio_history

#importing helper functions 
# from chatter_handler import chatter [Z] we do not need the chatter_handler.py script
from helpers import call_retriever_service, call_gemini_api
# from chatter_handler import model
# from openai import OpenAI [Z] we do not use OpenAI 
from vertexai.generative_models import GenerativeModel #[Z] initialize Gemini model instance



# --------------------------
# Config
# --------------------------
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")

# --------------------------
# Gemini Config
# --------------------------
GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get(
    "GEMINI_SERVICE_ACCOUNT_PATH",
    "/secrets/gemini-service-account.json"
)
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

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
    allow_credentials=True,  # Required for Authorization header
)
try:
    initialize_firebase_admin()
except Exception as e:
    print(f"[firebase-admin-warning] Firebase Admin not initialized: {e}")
    print("[firebase-admin-warning] Authentication will not work until Firebase Admin is configured")


# --------------------------
# Initialize Gemini Modek
# --------------------------
try:
    if os.path.exists(GEMINI_SERVICE_ACCOUNT_PATH):
        #set credentials file path for Vertex AI
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GEMINI_SERVICE_ACCOUNT_PATH

        #initialize model
        model = GenerativeModel(
            model_name=f'projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/publishers/google/models/gemini-2.5-flash'
        )
    else: 
        model = None
except Exception as e:
    print(f"[gemini-error] Failed to configure service account: {e}")
    model = None

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

    #get token from query params
    token = websocket.query_params.get("token")
    user_id = None
    
    if token:
        try:
            decoded_token = verify_token(token)
            user_id = decoded_token['uid']
            print(f"[websocket] Authenticated user: {user_id}")
        except Exception as e:
            await websocket.send_json({"error": "Invalid token"})
            await websocket.close()
            return
    else:
        print("[websocket-warning] No token provided, proceeding without auth")
    
    # Now you have user_id available for the rest of the WebSocket handler
    # Use it to save to CloudSQL:
    # - Save audio history with user_id
    # - Load user preferences with user_id
    
    audio_buffer = bytearray() #bytearray data structure is what will hold our audio chunks
    # tts_client = OpenAI()  # Initialize once, reuse in loop
    is_processing = False  # what this is checking is that the backend is already transcribing/generating a response

    
    try: 
        while True:
            #receive audio chunks from frontend
            # data = await websocket.receive_bytes()
            #OR if frontedn sends JSON with audio data
            message = await websocket.receive()
            #the way websocket works is via receiving messages. the backend
            # waits to receive a message from the frontend
            #it could be raw audio bytes, or a JSON message
            if message["type"] == "websocket.receive": #this is the backend confirming
                #it is a receive event from the frontend

                # handle raw audio bytes
                if "bytes" in message:
                    # if we're processing a previous request, ignore new audio chunks. avoid overstuffing the audio bujffer
                    if is_processing:
                        print(f"[websocket] Ignoring audio chunk - still processing previous request")
                        continue
                    chunk_size = len(message["bytes"])
                    audio_buffer.extend(message["bytes"]) #each audio chunk is appended to this audio_buffer byte array
                    print(f"[websocket] Received audio chunk: {chunk_size} bytes, total buffer: {len(audio_buffer)} bytes")
                    await websocket.send_json({"status": "chunk_received", "size": len(audio_buffer)})
                
                # Handle JSON control messages
                elif "text" in message:
                    try:
                        data = json.loads(message["text"])
                        print(f"[websocket] Received JSON message: {data}")

                        if data.get("type") == "complete":
                            # Check if we're already processing
                            if is_processing:
                                print("[websocket] Already processing a request, ignoring new complete signal")
                                continue
                            
                            # Check if we have audio to process
                            if len(audio_buffer) == 0:
                                print("[websocket] ERROR: No audio received in buffer!")
                                await websocket.send_json({"error": "No audio received"})
                                continue
                            
                            is_processing = True
                            print(f"[websocket] Received complete signal, audio buffer size: {len(audio_buffer)} bytes")
                            
                            # Step 1: Convert audio to text
                            await websocket.send_json({"status": "transcribing"}) # send.json sends a JSON message from backend to frontend
                            #via frontend connection
                            print("[websocket] Starting transcription...") #backend status print
                            
                            try:
                                #audio_to_text again is the speech_to_text_client.py file, that converts our frontend
                                #audio to text. the transcribed text is the output from audio_to_text.
                                text = await audio_to_text(bytes(audio_buffer)) #and we feed audio_buffer, our chunks of audio, into the function as input
                                #I think this is what shows up in the backend terminal once the transcription is complete
                                #so we can monitor progress
                                print(f"[websocket] Transcription complete, text: {text[:100] if text else 'None'}...")
                            except Exception as e:
                                print(f"[websocket] Transcription error: {e}")
                                await websocket.send_json({"error": f"Transcription failed: {str(e)}"})
                                audio_buffer.clear()
                                is_processing = False
                                continue
                            
                            if not text:
                                await websocket.send_json({"error": "Failed to transcribe audio (empty response)"})
                                audio_buffer.clear()
                                is_processing = False
                                continue
                            #websocket.send_json updates the frontend, status message via websocket
                            #frontend receives this and updates the UI
                            await websocket.send_json({"status": "transcribed", "text": text})
                            
                            #step2: once the audio is transcribed, we call the retriever using the transcribed text
                            #nothing has changed from the call_retriever_service
                            #still searches vector detabase 
                            await websocket.send_json({"status": "retrieving"})
                            chunks = call_retriever_service(text) ##THIS IS WHERE THE RETIREVAL STEP HAPPENS 
                            ##this returns most relevant chunks based on 
                            # SELECT id, chunk, embedding <=> %s AS score
                             # FROM {}
                             # ORDER BY embedding <=> %s
                            # LIMIT %s;
                            
                            if not chunks:
                                await websocket.send_json({"warning": "No relevant articles found"})
                            
                            #step 3: call_gemini_api to actually generate podcast text based on the text, chunks, model
                            #podcast_text = call_gemini_api(text,chunks,model)
                            await websocket.send_json({"status": "generating"})
                            podcast_text, error = call_gemini_api(text, chunks, model)
                            
                            if error or not podcast_text:
                                await websocket.send_json({"error": f"LLM error: {error}"})
                                audio_buffer.clear()
                                is_processing = False
                                continue
                            
                            await websocket.send_json({"status": "podcast_generated", "text": podcast_text})
                            
                            #step4: call_gemini_api gives us a podcast text output, which then we convert to audio
                            await websocket.send_json({"status": "converting_to_audio"})
                            try:
                                # [Z] signal that we're starting to stream audio to frontend
                                await websocket.send_json({"status": "streaming_audio"})
                                
                                # [Z] use LiveAPI to convert text to audio and stream it
                                result = await text_to_audio_stream(podcast_text, websocket)
                                
                                if not result:
                                    await websocket.send_json({"error": "Failed to generate audio stream"})
                                    audio_buffer.clear()
                                    continue
                                
                                # Signal completion
                                await websocket.send_json({"status": "complete"})

                                # Save audio history if user is authenticated
                                if user_id:
                                    save_audio_history(
                                        user_id=user_id,
                                        question_text=text,  # The transcribed question
                                        podcast_text=podcast_text,  # The generated podcast text
                                        audio_url=None  # Optional: add if you store audio files
                                    )
                                    print(f"[websocket] Audio history saved for user: {user_id}")
                            
                            except Exception as e:
                                await websocket.send_json({"error": f"TTS failed: {str(e)}"})
                                audio_buffer.clear()
                                is_processing = False
                                continue
                            
                            # Reset buffer for next request
                            audio_buffer.clear()
                            is_processing = False
                            print("[websocket] Request processing complete, ready for next recording")
                            
                        elif data.get("type") == "audio":
                            # JSON with base64 audio data
                            audio_bytes = base64.b64decode(data["data"])
                            audio_buffer.extend(audio_bytes)
                            
                        elif data.get("type") == "reset":
                            # Frontend wants to reset
                            audio_buffer.clear()
                            is_processing = False
                            await websocket.send_json({"status": "reset"})
                            print("[websocket] Reset signal received, cleared buffer and processing flag")
                            
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
# [Z] we do not need this /api/chatter endpoint  
# @app.post("/api/chatter")
# async def chatter_endpoint(payload: Dict[str, Any] = Body(...)):
#     return await chatter(payload)


# ----------------------
# Firebase middleware class
# ----------------------
class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate Firebase tokens for protected routes."""
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for OPTIONS (CORS preflight) requests
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Skip auth for health check and public endpoints
        if request.url.path in ["/", "/healthz", "/docs", "/openapi.json"]:
            return await call_next(request)
        
        # WebSocket handles auth separately (see below)
        if request.url.path.startswith("/ws/"):
            return await call_next(request)
        
        # Get token from header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
        
        token = auth_header.split("Bearer ")[1]
        
        try:
            # Verify token
            decoded_token = verify_token(token)
            user_id = decoded_token['uid']
            
            # Attach user info to request state
            request.state.user_id = user_id
            request.state.user_email = decoded_token.get('email')
            
        except Exception as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
        
        return await call_next(request)

# Add middleware to app
app.add_middleware(FirebaseAuthMiddleware)

@app.post("/api/user/create")
async def create_user_endpoint(request: Request):
    "create new user in CloudSQL after FIrebase registration"
    try:
        user_id = request.state.user_id
        user_email = request.state.user_email
        success = create_user(user_id, user_email)
        if success:
            return{"status":"success", "user_id":user_id}
        else:
            raise HTTPException(status_code=500, detail="Failed to create user")
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")

@app.get("/api/user/preferences")
async def get_preferences_endpoint(request: Request):
    """Get user preferences."""
    try:
        user_id = request.state.user_id
        preferences = get_user_preferences(user_id)
        return {"status": "success", "preferences": preferences}
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")

@app.post("/api/user/preferences")
async def save_preferences_endpoint(request: Request, preferences: Dict[str, Any] = Body(...)):
    """Save user preferences."""
    try:
        user_id = request.state.user_id
        success = save_user_preferences(user_id, preferences)
        if success:
            return {"status": "success", "message": "Preferences saved"}
        else:
            raise HTTPException(status_code=500, detail="Failed to save preferences")
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")

@app.get("/api/user/history")
async def get_history_endpoint(request: Request, limit: int = 10):
    """Get user's audio history."""
    try:
        user_id = request.state.user_id
        history = get_audio_history(user_id, limit)
        return {"status": "success", "history": history}
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")