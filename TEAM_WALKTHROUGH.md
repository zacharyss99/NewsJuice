# Team Walkthrough: NewsJuice Progress Update
**Date:** Today | **Focus:** Firebase Auth, CloudSQL, Real-time Audio Streaming

---

## 🎯 What We've Built Since Last Meeting

### 1. **Complete Real-Time Audio Pipeline** ✅
- Frontend → Backend: Live audio streaming via WebSocket
- Backend → Frontend: Real-time podcast audio streaming
- End-to-end latency: ~2-5 seconds from recording to playback

### 2. **Firebase Authentication Integration** ✅
- User registration & login
- JWT token validation on backend
- Protected API endpoints

### 3. **CloudSQL Database Schema** ✅
- `users` table (user_id, email, timestamps)
- `user_preferences` table (personalization settings)
- `audio_history` table (question, podcast text, timestamps)

### 4. **React Frontend Integration** ✅
- Migrated from static HTML to React (`k-frontend/podcast-app`)
- WebSocket audio streaming integrated
- Real-time status updates

---

## 📊 High-Level Architecture

```
┌─────────────────┐
│  React Frontend │
│  (Podcast.jsx)  │
└────────┬────────┘
         │
         │ 1. User presses & holds button
         │ 2. Audio chunks (PCM) → WebSocket
         │
         ▼
┌─────────────────────────────────────┐
│      WebSocket Connection           │
│      /ws/chat?token=<JWT>           │
└────────┬────────────────────────────┘
         │
         │ 3. Accumulate audio chunks
         │ 4. Send {type: "complete"}
         │
         ▼
┌─────────────────────────────────────┐
│      FastAPI Backend                │
│      (main.py)                      │
└────────┬────────────────────────────┘
         │
         ├─► 5. Google Cloud Speech-to-Text
         │    (speech_to_text_client.py)
         │
         ├─► 6. RAG Retriever
         │    (call_retriever_service)
         │    → Vector DB (pgvector)
         │
         ├─► 7. Gemini API
         │    (call_gemini_api)
         │    → Generate podcast text
         │
         ├─► 8. LiveAPI TTS
         │    (live_api_tts_client.py)
         │    → Stream audio chunks back
         │
         └─► 9. Save to CloudSQL
            (user_db.py)
            → audio_history table
```

---

## 🔄 Complete Data Flow (Step-by-Step)

### **Phase 1: Audio Capture & Streaming**
**File:** `services/k-frontend/podcast-app/src/pages/Podcast.jsx`

1. **User Action:** Press & hold button
2. **Frontend:**
   - Creates `AudioContext` (44.1kHz, mono)
   - Uses `ScriptProcessorNode` to capture audio
   - Converts Float32 → Int16 PCM
   - Sends chunks via WebSocket: `ws.send(pcmData.buffer)`

3. **Backend Receives:**
   - Accumulates chunks in `audio_buffer` (bytearray)
   - Sends status: `{"status": "chunk_received", "size": X}`

### **Phase 2: Transcription**
**File:** `services/chatter_deployed/speech_to_text_client.py`

4. **User releases button** → Frontend sends: `{type: "complete"}`
5. **Backend:**
   - Tries multiple sample rates (44.1kHz, 48kHz, 16kHz, etc.)
   - Uses Google Cloud Speech-to-Text API
   - Fallback: OpenAI Whisper (if Google fails)
   - Returns transcribed text

### **Phase 3: RAG (Retrieval-Augmented Generation)**
**File:** `services/chatter_deployed/helpers.py`

6. **Retriever:**
   - Takes transcribed question
   - Searches vector database (pgvector)
   - Returns top-k relevant article chunks
   - Uses sentence-transformers embeddings

### **Phase 4: LLM Generation**
**File:** `services/chatter_deployed/helpers.py` → `call_gemini_api()`

7. **Gemini API:**
   - Input: Question + Retrieved chunks
   - Prompt: "You are a news podcast host..."
   - Output: Podcast-style text response

### **Phase 5: Text-to-Speech Streaming**
**File:** `services/chatter_deployed/live_api_tts_client.py`

8. **LiveAPI TTS:**
   - Sends podcast text to Google LiveAPI
   - Receives PCM audio chunks in real-time
   - Converts PCM → WAV format
   - Streams WAV chunks back via WebSocket

### **Phase 6: Audio Playback**
**File:** `services/k-frontend/podcast-app/src/pages/Podcast.jsx`

9. **Frontend:**
   - Accumulates WAV chunks in `audioBufferRef`
   - On "complete" status: Creates Blob → Audio URL
   - Plays via HTML5 `<audio>` element

### **Phase 7: Data Persistence**
**File:** `services/chatter_deployed/user_db.py`

10. **Save to CloudSQL:**
    - `audio_history` table
    - Stores: user_id, question_text, podcast_text, timestamp

---

## 📁 Key Files & Their Roles

### **Frontend**
```
services/k-frontend/podcast-app/
├── src/pages/Podcast.jsx          # Main audio streaming logic
├── src/pages/Login.jsx            # Firebase Auth login
├── src/pages/Registration.jsx     # Firebase Auth signup
└── src/firebase/config.js         # Firebase SDK config
```

**Key Functions in Podcast.jsx:**
- `startRecording()` - Captures audio, sends via WebSocket
- `stopRecording()` - Sends "complete" signal
- `connectWebSocket()` - Establishes WebSocket with JWT token
- `handleAudioChunk()` - Accumulates incoming audio
- `finalizeAudio()` - Plays accumulated audio

### **Backend**
```
services/chatter_deployed/
├── main.py                        # FastAPI app, WebSocket handler
├── speech_to_text_client.py       # Google Speech-to-Text
├── live_api_tts_client.py         # LiveAPI TTS streaming
├── firebase_auth.py               # Firebase Admin SDK
├── user_db.py                     # CloudSQL operations
└── helpers.py                     # RAG + Gemini API
```

**Key Functions in main.py:**
- `@app.websocket("/ws/chat")` - WebSocket endpoint
- `FirebaseAuthMiddleware` - Validates JWT tokens
- `/api/user/create` - Creates user in CloudSQL
- `/api/user/preferences` - Get/set user preferences
- `/api/user/history` - Get audio history

---

## 🔐 Firebase Authentication Flow

### **Registration:**
1. User fills form → `Registration.jsx`
2. Firebase Auth: `createUserWithEmailAndPassword()`
3. Get JWT token: `user.getIdToken()`
4. Store in `localStorage`: `auth_token`, `user_id`
5. Call backend: `POST /api/user/create` (with JWT)
6. Backend verifies token → Creates user in CloudSQL

### **Login:**
1. User logs in → `Login.jsx`
2. Firebase Auth: `signInWithEmailAndPassword()`
3. Get JWT token → Store in `localStorage`
4. Navigate to Podcast page

### **WebSocket Authentication:**
- Frontend: `ws://localhost:8080/ws/chat?token=<JWT>`
- Backend: Extracts token from query params
- Verifies via `verify_token()` → Extracts `user_id`

---

## 🗄️ CloudSQL Schema

```sql
-- Users table
CREATE TABLE users (
    user_id VARCHAR(255) PRIMARY KEY,  -- Firebase UID
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- User preferences (separate table for flexibility)
CREATE TABLE user_preferences (
    user_id VARCHAR(255) PRIMARY KEY REFERENCES users(user_id),
    preferences JSONB,  -- Flexible JSON structure
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Audio history (tracks all interactions)
CREATE TABLE audio_history (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) REFERENCES users(user_id),
    question_text TEXT,
    podcast_text TEXT,
    audio_url VARCHAR(500),  -- Optional: GCS URL
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Why separate `user_preferences` table?**
- Flexible JSON structure (can add new preferences without schema changes)
- Better normalization
- Easier to query/update preferences independently

---

## 🎤 Audio Streaming Technical Details

### **Frontend → Backend:**
- **Format:** PCM Int16, 44.1kHz, mono
- **Chunk Size:** 4096 samples (~93ms at 44.1kHz)
- **Transport:** WebSocket binary messages
- **Timing:** Real-time streaming (no buffering)

### **Backend → Frontend:**
- **Format:** WAV (PCM wrapped in WAV header)
- **Sample Rate:** 24kHz (LiveAPI output)
- **Chunk Size:** 8KB chunks
- **Transport:** WebSocket binary messages
- **Playback:** HTML5 Audio element (Blob URL)

### **Key Challenge Solved:**
- **Problem:** Audio chunks arriving before "complete" signal
- **Solution:** Use `isRecordingRef` (ref instead of state) to avoid React timing issues
- **Result:** All chunks properly accumulated before processing

---

## 🐛 Challenges Solved

### 1. **CORS Issues**
- **Problem:** Authorization header blocked
- **Fix:** Added `allow_credentials=True` to CORS middleware
- **Fix:** Skip OPTIONS requests in auth middleware

### 2. **Empty Audio Buffer**
- **Problem:** "complete" signal received but buffer empty
- **Fix:** Use refs instead of state for recording flag
- **Fix:** Added delays to ensure chunks sent before "complete"

### 3. **Sample Rate Mismatch**
- **Problem:** Frontend sends 44.1kHz, backend expects 16kHz
- **Fix:** Try multiple sample rates in Speech-to-Text client

### 4. **WebSocket State Management**
- **Problem:** Multiple recordings causing conflicts
- **Fix:** Added `is_processing` flag to ignore new requests while processing

### 5. **PCM → WAV Conversion**
- **Problem:** HTML5 Audio can't play raw PCM
- **Fix:** Convert PCM to WAV format with proper headers

---

## 📊 Current Status

### ✅ **Working:**
- Firebase Authentication (login/register)
- WebSocket audio streaming (frontend → backend)
- Speech-to-Text transcription
- RAG retrieval
- Gemini API podcast generation
- LiveAPI TTS streaming (backend → frontend)
- Audio playback on frontend
- CloudSQL user data persistence
- Audio history saving

### 🔧 **In Progress / Needs Testing:**
- User preferences API (endpoints exist, need frontend UI)
- Audio history display (endpoint exists, need frontend UI)
- Error handling edge cases
- Performance optimization

### 📝 **Next Steps:**
1. Build preferences UI page
2. Build history UI page
3. Add audio file storage (GCS) for history playback
4. Add user preference loading into RAG/LLM prompts
5. Testing & bug fixes

---

## 🚀 How to Run

### **Backend:**
```bash
cd services/chatter_deployed
docker-compose -f docker-compose.local.yml up
```

### **Frontend:**
```bash
cd services/k-frontend/podcast-app
npm install
npm run dev  # Runs on http://localhost:3000
```

### **Environment Variables Needed:**
- `GOOGLE_API_KEY` - For LiveAPI TTS
- `OPENAI_API_KEY` - For Whisper fallback
- `DATABASE_URL` - CloudSQL connection string
- `FIREBASE_SERVICE_ACCOUNT_PATH` - Firebase Admin SDK credentials

---

## 💡 Key Takeaways

1. **Real-time streaming works end-to-end** - From microphone to speaker
2. **Firebase Auth fully integrated** - Users can register/login
3. **CloudSQL persistence** - All interactions saved
4. **WebSocket is the backbone** - Handles both audio streaming and status updates
5. **React state management** - Used refs for audio processing to avoid timing issues

---

## ❓ Questions for Discussion

1. **User Preferences:** What preferences should we track? (topics, voice style, length, etc.)
2. **Audio Storage:** Should we store audio files in GCS for history playback?
3. **Error Handling:** What should happen if transcription/LLM/TTS fails?
4. **Performance:** Should we add caching for common questions?
5. **UI/UX:** How should preferences/history pages look?

---

## 📚 Code References

**Main WebSocket Handler:**
- `services/chatter_deployed/main.py` (lines 86-270)

**Frontend Audio Streaming:**
- `services/k-frontend/podcast-app/src/pages/Podcast.jsx` (lines 204-337)

**Firebase Integration:**
- `services/chatter_deployed/firebase_auth.py`
- `services/k-frontend/podcast-app/src/firebase/config.js`

**Database Operations:**
- `services/chatter_deployed/user_db.py`

---

**End of Walkthrough** 🎉

