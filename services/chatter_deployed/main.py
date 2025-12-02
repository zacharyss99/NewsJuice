"""
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



"""

# load_dotenv()  # This loads .env file
from dotenv import load_dotenv
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

# uploadfile handels audio file auploads from frontend
from fastapi import (
    FastAPI,
    Body,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)

# from fastapi.responses import StreamingResponse
# streaming response stream audio chunks back to frontend
from speech_to_text_client import audio_to_text  # Speech-to-Text function
from text_to_speech_client import text_to_audio_stream  # Google Cloud Text-to-Speech streaming
from fastapi.middleware.cors import CORSMiddleware
import json
import base64
from firebase_auth import initialize_firebase_admin, verify_token
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request
from user_db import (
    create_user,
    get_user_preferences,
    save_user_preferences,
    save_audio_history,
    get_audio_history,
)

# importing helper functions
# from chatter_handler import chatter [Z] we do not need the chatter_handler.py script
from helpers import call_retriever_service, call_gemini_api
from query_enhancement import enhance_query_with_gemini
from retriever import search_articles_by_preferences

# from chatter_handler import model
# from openai import OpenAI [Z] we do not use OpenAI
from vertexai.generative_models import (
    GenerativeModel,
)  # [Z] initialize Gemini model instance


# --------------------------
# Config
# --------------------------

load_dotenv()
ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://www.newsjuiceapp.com").split(",")

# --------------------------
# Gemini Config
# --------------------------
GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH", "/secrets/gemini-service-account.json")
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
    print(
        f"[firebase-admin-warning] Firebase Admin not initialized: {e}\n"
        "[firebase-admin-warning] Authentication will not work until Firebase Admin is configured"
    )


# --------------------------
# Initialize Gemini Modek
# --------------------------
try:
    if os.path.exists(GEMINI_SERVICE_ACCOUNT_PATH):
        # set credentials file path for Vertex AI
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GEMINI_SERVICE_ACCOUNT_PATH

        # initialize model
        model = GenerativeModel(
            model_name=(
                f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/"
                "publishers/google/models/gemini-2.5-flash"
            )
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


# --------------------------
# Helper Functions
# --------------------------
# [Z]
async def _retrieve_and_generate_podcast(
    websocket: WebSocket,
    enhanced_queries: Dict[str, str],
    # dictionary w/ string keys and string values (each enhanced query)
    original_query: str,
    user_id: Optional[str],
    model: GenerativeModel,
):
    """Retrieve chunks and generate podcast for normal flow and query enhancement."""
    # step2: call the retriever for each enhanced sub-query (if it exists)
    await websocket.send_json({"status": "retrieving"})
    all_chunks = []

    # Extract all enhanced_query_N keys and sort them
    query_keys = sorted([k for k in enhanced_queries.keys() if k.startswith("enhanced_query_")])

    # [Z] assume each sub query runs cosine similarity against the DB to pull chunks
    for query_key in query_keys:
        sub_query = enhanced_queries[query_key]
        print(f"[retriever] Running retrieval for sub-query: {sub_query[:50]}...")
        chunks = call_retriever_service(sub_query)
        if chunks:
            # Print each chunk with its similarity score
            print(f"[retriever] Found {len(chunks)} chunks for '{query_key}':")
            for i, (chunk_id, chunk_text, source_type, score) in enumerate(chunks):
                print(f"  Chunk {i+1} (ID: {chunk_id}, Source: {source_type}, Score: {score:.4f}): {chunk_text[:100]}...")
            all_chunks.extend(chunks)

    # Remove duplicates based on chunk ID (keep first occurrence)
    seen_ids = set()
    unique_chunks = []
    for chunk in all_chunks:
        chunk_id = chunk[0]  # First element is the ID
        if chunk_id not in seen_ids:
            seen_ids.add(chunk_id)
            unique_chunks.append(chunk)
    # makes sense to only have the unique chunks for all enhanced queries
    all_chunks = unique_chunks

    # Print summary of final unique chunks
    print(f"[retriever] After deduplication: {len(all_chunks)} unique chunks")
    for i, (chunk_id, chunk_text, source_type, score) in enumerate(all_chunks):
        print(f"  Final Chunk {i+1} (ID: {chunk_id}, Source: {source_type}, Score: {score:.4f}): {chunk_text}...")

    if not all_chunks: 
        await websocket.send_json({"warning": "No relevant articles found"})

    # step 3: call_gemini_api to generate podcast text with all combined chunks
    await websocket.send_json({"status": "generating"})
    # [Z] assuming we combine all these chunks + sub-queries for the podcast generation
    # Combine all enhanced sub-queries for podcast generation
    combined_enhanced_query = "\n".join([enhanced_queries[k] for k in query_keys])
    print(f"This is the enhanced query {combined_enhanced_query}")

    podcast_text, error = call_gemini_api(combined_enhanced_query, all_chunks, model)
    print(f"Here is the Podcast Text {podcast_text}")

    if error or not podcast_text:
        await websocket.send_json({"error": f"LLM error: {error}"})
        return False

    await websocket.send_json({"status": "podcast_generated", "text": podcast_text})

    # step4: convert podcast text to audio
    await websocket.send_json({"status": "converting_to_audio"})
    try:
        await websocket.send_json({"status": "streaming_audio"})
        result = await text_to_audio_stream(podcast_text, websocket)

        if not result:
            await websocket.send_json({"error": "Failed to generate audio stream"})
            return False

        await websocket.send_json({"status": "complete"})

        # Save audio history if user is authenticated
        if user_id:
            save_audio_history(
                user_id=user_id,
                question_text=original_query,
                podcast_text=podcast_text,
                audio_url=None,
            )
            print(f"[websocket] Audio history saved for user: {user_id}")

    except Exception as e:
        await websocket.send_json({"error": f"TTS failed: {str(e)}"})
        return False

    return True


# ------------
# Websocket Audio Endpoint
# ------------
# WebSocket route decorator
# /ws/chat - WebSocket endpoint path
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

    # get token from query params
    token = websocket.query_params.get("token")
    user_id = None

    if token:
        try:
            decoded_token = verify_token(token)
            user_id = decoded_token["uid"]
            print(f"[websocket] Authenticated user: {user_id}")
        except Exception as e:
            print(f"[websocket-error] Token verification failed: {e}")
            import traceback

            traceback.print_exc()
            await websocket.send_json({"error": f"Invalid token: {str(e)}"})
            await websocket.close()
            return
    else:
        print("[websocket-warning] No token provided, proceeding without auth")

    # Now you have user_id available for the rest of the WebSocket handler
    # Use it to save to CloudSQL:
    # - Save audio history with user_id
    # - Load user preferences with user_id

    audio_buffer = bytearray()  # bytearray data structure is what will hold our audio chunks
    # tts_client = OpenAI()  # Initialize once, reuse in loop
    is_processing = False  # what this is checking is that the backend is already
    # transcribing/generating a response

    try:
        while True:
            # receive audio chunks from frontend
            # data = await websocket.receive_bytes()
            # OR if frontedn sends JSON with audio data
            message = await websocket.receive()
            # the way websocket works is via receiving messages. the backend
            # waits to receive a message from the frontend
            # it could be raw audio bytes, or a JSON message
            if message["type"] == "websocket.receive":  # this is the backend confirming
                # it is a receive event from the frontend

                # handle raw audio bytes
                if "bytes" in message:
                    # if we're processing a previous request, ignore new audio chunks. avoid
                    # overstuffing the audio bujffer
                    if is_processing:
                        print("[websocket] Ignoring audio chunk - still processing previous request")
                        continue
                    chunk_size = len(message["bytes"])
                    audio_buffer.extend(
                        message["bytes"]
                    )  # each audio chunk is appended to this audio_buffer byte array
                    print(
                        "[websocket] Received audio chunk:"
                        f" {chunk_size} bytes, total buffer: {len(audio_buffer)} bytes"
                    )
                    await websocket.send_json({"status": "chunk_received", "size": len(audio_buffer)})

                # Handle JSON control messages
                elif "text" in message:
                    try:
                        data = json.loads(message["text"])
                        print(f"[websocket] Received JSON message: {data}")

                        if data.get("type") == "complete":
                            # Check if we're already processing
                            if is_processing:
                                print("[websocket] Already processing a request, " "ignoring new complete signal")
                                continue

                            # Check if we have audio to process
                            if len(audio_buffer) == 0:
                                print("[websocket] ERROR: No audio received in buffer!")
                                print("[websocket] ERROR: No audio received in buffer!")
                                await websocket.send_json({"error": "No audio received"})
                                continue

                            is_processing = True
                            print(
                                f"""[websocket] Received complete signal, audio buffer size:
                                {len(audio_buffer)} bytes"""
                            )

                            # Step 1: Convert audio to text
                            await websocket.send_json({"status": "transcribing"})
                            # send_json sends a JSON message from backend to frontend
                            # via frontend connection
                            print("[websocket] Starting transcription...")  # backend status print

                            try:
                                # audio_to_text again is the speech_to_text_client.py file,
                                # that converts our frontend audio to text. the transcribed text is
                                # the output from audio_to_text.
                                text = await audio_to_text(
                                    bytes(audio_buffer)
                                )  # and we feed audio_buffer, our chunks of audio, into the
                                # function as input
                                # I think this is what shows up in the backend terminal once the
                                # transcription is complete
                                # so we can monitor progress
                                preview = text[:100] if text else "None"
                                print(f"[websocket] Transcription complete, text: {preview}...")
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
                            # websocket.send_json updates the frontend, status message via websocket
                            # frontend receives this and updates the UI
                            await websocket.send_json({"status": "transcribed", "text": text})

                            # NEW STEP: Query Enhancement - enhance query once and use it directly
                            await websocket.send_json({"status": "enhancing_query"})
                            print("[websocket] Enhancing query...")

                            # Enhance the query once
                            enhancement_result, error = enhance_query_with_gemini(text, model)
                            original_query = text  # Keep original for podcast generation

                            if error or not enhancement_result:
                                print("[websocket] Query enhancement error:" f" {error}, using original query")
                                # Use original query as single sub-query if enhancement fails
                                enhanced_queries = {"enhanced_query_1": text}
                            else:
                                # Extract all enhanced_query_N keys from the result
                                enhanced_queries = {
                                    k: v for k, v in enhancement_result.items() if k.startswith("enhanced_query_")
                                }
                                if not enhanced_queries:
                                    # Fallback if format is unexpected
                                    enhanced_queries = {
                                        "enhanced_query_1": enhancement_result.get("enhanced_query", text)
                                    }
                                print("[websocket] Query enhanced into" f" {len(enhanced_queries)} sub-queries")

                            # Use the helper function to retrieve and generate podcast
                            success = await _retrieve_and_generate_podcast(
                                websocket,
                                enhanced_queries,
                                original_query,
                                user_id,
                                model,
                            )

                            if not success:
                                audio_buffer.clear()
                                is_processing = False
                                continue

                            # Reset buffer for next request
                            audio_buffer.clear()
                            is_processing = False
                            print("[websocket] Request processing complete, ready for next" " recording")

                        elif data.get("type") == "audio":
                            # JSON with base64 audio data
                            audio_bytes = base64.b64decode(data["data"])
                            audio_buffer.extend(audio_bytes)

                        elif data.get("type") == "reset":
                            # Frontend wants to reset
                            audio_buffer.clear()
                            is_processing = False
                            await websocket.send_json({"status": "reset"})
                            print("[websocket] Reset signal, cleared buffer & processing flag")

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
        except Exception:
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
            user_id = decoded_token["uid"]

            # Attach user info to request state
            request.state.user_id = user_id
            request.state.user_email = decoded_token.get("email")

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
            return {"status": "success", "user_id": user_id}
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


# --------------------------
# Daily Brief Endpoints
# --------------------------

@app.post("/api/daily-brief")
async def generate_daily_brief_endpoint(request: Request):
    """Generate a personalized daily news briefing based on user preferences."""
    try:
        user_id = request.state.user_id
        print(f"[daily-brief] Generating for user: {user_id}")

        # Load user preferences from user_preferences table in CloudSQL
        #  (this function comes from the user_db.py script)
        preferences = get_user_preferences(user_id)
        """
        Example rows for a single user in user_preferences table is 
        ──────────┬────────────────────────────────┬─────────────────────────────────────────┬─────────────────────┐
│ user_id  │ preference_key                 │ preference_value                        │ updated_at          │
├──────────┼────────────────────────────────┼─────────────────────────────────────────┼─────────────────────┤
│ abc123   │ topics                         │ ["Politics","Technology","Health"]      │ 2025-12-02 10:30:00 │
├──────────┼────────────────────────────────┼─────────────────────────────────────────┼─────────────────────┤
│ abc123   │ sources                        │ ["Harvard Gazette","Harvard Crimson"]   │ 2025-12-02 10:30:00 │
├──────────┼────────────────────────────────┼─────────────────────────────────────────┼─────────────────────┤
│ abc123   │ last_daily_brief_generated     │ 2025-12-02T14:25:00Z                    │ 2025-12-02 14:25:00 │

so this function is literally pulling the values from the associated preference
topics_str = preference.get("topics", "[]") pulls the list of preferred topics (inside preference_value) based on the preference_key, "topics".
        
        """

        # parse topics and sources from the preferences
        topics_str = preferences.get("topics", "[]")
        sources_str = preferences.get("sources", "[]")

        try:
            #these arrays of topics and sources are stored as JSON strings, so they need to be parsed back
            #via json.loads()
            topics = json.loads(topics_str) if isinstance(topics_str, str) else topics_str
            sources = json.loads(sources_str) if isinstance(sources_str, str) else sources_str
        except json.JSONDecodeError:
            topics = []
            sources = []

        print(f"[daily-brief] Topics: {topics}")
        print(f"[daily-brief] Sources: {sources}")

        if not topics or not sources:
            raise HTTPException(
                status_code=400,
                detail="No preferences set. Please configure topics and sources first."
            )

        # retreive the chunks based on their preferred topics and sources
        #w/ associated parameters (30 chunks, 2 days back)
        chunks = search_articles_by_preferences(
            topics=topics,
            sources=sources,
            limit=30,
            days_back=2
        )

        if not chunks:
            raise HTTPException(
                status_code=404,
                detail="No articles found matching your preferences"
            )

        print(f"[daily-brief] Retrieved {len(chunks)} chunks")

        # format context for Gemini API so that the podcast generation accuratelty mentions the news source title where the info came from
        #so context_text is literally a list of [Article Title: "title" \n "chunk"] for however many chunks we return
        context_text = "\n\n".join([
            f"Article Title: {source_type}\n{chunk}"
            for _, chunk, source_type, score in chunks
        ])

        
        try:
            # Create custom prompt for daily brief
            today_date = datetime.now(timezone.utc).strftime("%B %d, %Y")
            
            # build the full prompt for the gemini API call using the DAILY_BRIEF_PROMPT
            
            DAILY_BRIEF_PROMPT = """
        You are a professional news anchor creating a daily briefing for Harvard community members.

        OBJECTIVE:
        Create an engaging, comprehensive daily news summary covering the most important Harvard news stories from the provided articles.

        STRUCTURE:
        1. Opening: Brief welcome and overview of today's top stories (mention the date)
        2. Main stories: Cover 3-5 major developments in detail with proper context
        3. Quick hits: Mention 2-3 additional noteworthy items briefly
        4. Closing: Brief wrap-up

        DELIVERY STYLE:
        - Professional yet conversational tone (like NPR's "The Daily")
        - Natural narration - NO markdown formatting (**bold**, *italics*, ### headers, etc.)
        - DO NOT use special characters or formatting - write in plain text only
        - This will be converted to speech, so write for listening, not reading
        - Clearly attribute information by naturally mentioning article sources
        - Example: "According to the Harvard Gazette article 'Research Breakthrough,' scientists have discovered..."
        - Smooth transitions between topics
        - Appropriate pacing for audio consumption

        IMPORTANT:
        - Focus on the most significant and interesting stories
        - Provide context and explain why stories matter to the Harvard community
        - Keep total length around 3-5 minutes when spoken (approximately 500-750 words)
        - Be authoritative and well-informed
        - Make it engaging - this is the user's personalized morning briefing

        Begin with: "Good morning, this is your Harvard News Daily Brief for [today's date]..."

        End with: "That's your Harvard News Daily Brief. Have a great day!"
        """

            full_prompt = f"""{DAILY_BRIEF_PROMPT} 

Today's date: {today_date}

Here are the news articles to summarize:

{context_text}

Now generate your daily briefing:"""
            #this is literally calling the gemini_api directly to generate a podcast
            # the call_gemini_api() is a script that is solely used for the interactive Q&A
            #creating a separate helper for one use case is "overkill" according to claude, I think it is actually helpful, but eh
            response = model.generate_content(full_prompt)
            podcast_text = response.text

            if not podcast_text:
                raise HTTPException(status_code=500, detail="Failed to generate briefing text")

            print(f"[daily-brief] Generated text: {len(podcast_text)} chars")

        except Exception as e:
            print(f"[daily-brief] Gemini error: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to generate briefing: {str(e)}")

        # Convert to audio (using existing TTS - for now we'll save without audio URL)
        # TODO: Implement audio generation for daily brief
        audio_url = None  # Placeholder for now

        # Save to audio_history with question_text="Daily Brief"
        save_audio_history(
            user_id=user_id,
            question_text="Daily Brief",
            podcast_text=podcast_text,
            audio_url=audio_url
        )

        # Update last_daily_brief_generated timestamp
        current_time = datetime.now(timezone.utc).isoformat()
        save_user_preferences(user_id, {"last_daily_brief_generated": current_time})

        print(f"[daily-brief] Successfully generated and saved")

        return {
            "success": True,
            "text": podcast_text,
            "audio_url": audio_url,
            "created_at": current_time
        }

    except HTTPException:
        raise
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")
    except Exception as e:
        print(f"[daily-brief-error] {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to generate daily brief: {str(e)}")


#we check status first to avoid regenerating the same brief multiple times
#one brief per user per day
@app.get("/api/daily-brief/status")
async def check_daily_brief_status_endpoint(request: Request):
    """Check if daily brief was generated today."""
    try:
        user_id = request.state.user_id

        # Load last_daily_brief_generated timestamp
        preferences = get_user_preferences(user_id)
        last_generated_str = preferences.get("last_daily_brief_generated")

        if not last_generated_str:
            return {"generated_today": False}

        # Parse timestamp and check if it's today
        try:
            last_generated = datetime.fromisoformat(last_generated_str.replace('Z', '+00:00'))
            today = datetime.now(timezone.utc).date()
            last_date = last_generated.date()

            generated_today = (last_date == today)

            return {
                "generated_today": generated_today,
                "last_generated": last_generated_str
            }

        except (ValueError, AttributeError):
            return {"generated_today": False}

    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")
    except Exception as e:
        print(f"[daily-brief-status-error] {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check status: {str(e)}")

#retrieve most recent daily brief from user's history to display existing brief without regenerating
@app.get("/api/daily-brief/latest")
async def get_latest_daily_brief_endpoint(request: Request):
    """Get the most recent daily brief from history."""
    try:
        user_id = request.state.user_id

        # Get all history and filter for "Daily Brief"
        history = get_audio_history(user_id, limit=50)

        # Find most recent daily brief
        daily_briefs = [h for h in history if h.get("question_text") == "Daily Brief"]

        if not daily_briefs:
            raise HTTPException(status_code=404, detail="No daily brief found")

        # Return most recent (first in list since get_audio_history returns newest first)
        latest_brief = daily_briefs[0]

        return {
            "id": latest_brief.get("id"),
            "question_text": latest_brief.get("question_text"),
            "podcast_text": latest_brief.get("podcast_text"),
            "audio_url": latest_brief.get("audio_url"),
            "created_at": latest_brief.get("created_at")
        }

    except HTTPException:
        raise
    except AttributeError:
        raise HTTPException(status_code=401, detail="User not authenticated")
    except Exception as e:
        print(f"[daily-brief-latest-error] {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get latest brief: {str(e)}")
