# Chatter Service - Complete Setup Guide

This guide provides step-by-step instructions to run the **Backend**, **Frontend**, and **Firebase** services for the NewsJuice application.

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Firebase Setup](#firebase-setup)
3. [Backend Setup](#backend-setup)
4. [Frontend Setup](#frontend-setup)
5. [Running the Complete Application](#running-the-complete-application)
6. [Testing](#testing)
7. [Deployment](#deployment)
8. [Troubleshooting](#troubleshooting)

---

## 🔧 Prerequisites

Before starting, ensure you have the following installed:

- **Docker** and **Docker Compose**
- **Node.js** (v16 or higher) and **npm**
- **Google Cloud SDK** (`gcloud`)
- **Firebase CLI** (optional, for Firebase management)
- Access to the following Google Cloud resources:
  - Cloud SQL instance: `newsjuice-123456:us-central1:newsdb-instance`
  - Cloud Storage bucket: `ac215-audio-bucket`
  - Service account keys (see below)

### Required Service Account Keys

You need the following service account JSON files in the parent `secrets/` directory:

```
../secrets/
├── sa-key.json                    # GCP service account for Cloud SQL & GCS
└── gemini-service-account.json    # Service account for Gemini API
```

To download these keys:
```bash
mkdir -p ../secrets
gcloud iam service-accounts keys create ../secrets/sa-key.json \
  --iam-account=YOUR-SA@newsjuice-123456.iam.gserviceaccount.com
gcloud iam service-accounts keys create ../secrets/gemini-service-account.json \
  --iam-account=GEMINI-SA@newsjuice-123456.iam.gserviceaccount.com
```

---

## 🔥 Firebase Setup

### 1. Firebase Project Configuration

The Firebase project is already configured with:
- **Project ID**: `newsjuice-123456`
- **Auth Domain**: `newsjuice-123456.firebaseapp.com`

### 2. Firebase Authentication Setup

1. **Enable Authentication in Firebase Console**:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Select project `newsjuice-123456`
   - Navigate to **Authentication** → **Sign-in method**
   - Enable **Email/Password** authentication

2. **Get Firebase Admin SDK Service Account** (for backend):
   ```bash
   # Download Firebase Admin SDK service account key
   # Go to Firebase Console → Project Settings → Service Accounts
   # Click "Generate new private key" and save as:
   ../secrets/firebase-service-account.json
   ```

3. **Frontend Firebase Config**:
   The frontend Firebase configuration is already set in:
   `services/k-frontend/podcast-app/src/firebase/config.js`

   ```javascript
   const firebaseConfig = {
     apiKey: "AIzaSyBgsCjTT1B_qZUioacHrLHcs5v0tXcmr2c",
     authDomain: "newsjuice-123456.firebaseapp.com",
     projectId: "newsjuice-123456",
     // ... other config
   };
   ```

### 3. Backend Firebase Admin Setup

For local development, set the Firebase service account path in `.env.local`:
```bash
FIREBASE_SERVICE_ACCOUNT_PATH=../secrets/firebase-service-account.json
```

For production (Cloud Run), Firebase Admin uses Workload Identity automatically.

---

## 🚀 Backend Setup

### 1. Navigate to Backend Directory

```bash
cd services/chatter_deployed
```

### 2. Create Environment File

Create a `.env.local` file (this file is gitignored):

```bash
# Database (Local Development - uses Cloud SQL Proxy)
DATABASE_URL=postgresql://postgres:Newsjuice25%2B@cloud-sql-proxy:5432/newsdb
DB_URL=postgresql://postgres:Newsjuice25%2B@cloud-sql-proxy:5432/newsdb

# OpenAI API (for Live API TTS)
OPENAI_API_KEY=sk-proj-XXXXXXXXXXXXXXXXXXXXXXXX

# Google Cloud
GOOGLE_CLOUD_PROJECT=newsjuice-123456
GOOGLE_CLOUD_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/app/sa-key.json
GEMINI_SERVICE_ACCOUNT_PATH=/secrets/gemini-service-account.json

# Google AI API (for Gemini Live API)
GOOGLE_API_KEY=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXX

# Hugging Face (for sentence-transformers model)
HUGGING_FACE_HUB_TOKEN=hf_XXXXXXXXXXXXXXXXXXXXXXXX

# GCS Bucket
AUDIO_BUCKET=ac215-audio-bucket
GCS_PREFIX=podcasts/
CACHE_CONTROL=public, max-age=3600

# CORS (for local frontend)
CORS_ALLOW_ORIGINS=http://localhost:5173,http://localhost:3000,http://localhost:8080

# Server
PORT=8080

# Firebase (Local Development)
FIREBASE_SERVICE_ACCOUNT_PATH=../secrets/firebase-service-account.json
```

### 3. Start Backend Services

The backend runs in Docker Compose with Cloud SQL Proxy:

```bash
# Build and start all services (Cloud SQL Proxy + API)
docker-compose -f docker-compose.local.yml --env-file .env.local up --build
```

This will:
- Start Cloud SQL Proxy container (connects to Cloud SQL on port 5432)
- Start the FastAPI backend on port 8080
- Mount service account keys and secrets

### 4. Verify Backend is Running

```bash
# Check health endpoint
curl http://localhost:8080/healthz
# Should return: {"ok":true}
```

### 5. Backend Endpoints

- **Health Check**: `GET http://localhost:8080/healthz`
- **WebSocket Chat**: `ws://localhost:8080/ws/chat?token=<firebase-token>`
- **User Creation**: `POST http://localhost:8080/api/user/create` (requires auth)
- **User Preferences**: 
  - `GET http://localhost:8080/api/user/preferences` (requires auth)
  - `POST http://localhost:8080/api/user/preferences` (requires auth)
- **Audio History**: `GET http://localhost:8080/api/user/history` (requires auth)

---

## 🎨 Frontend Setup

### 1. Navigate to Frontend Directory

```bash
cd services/k-frontend/podcast-app
```

### 2. Install Dependencies

```bash
npm install
```

### 3. Configure Backend URL

The frontend automatically detects the backend URL based on the hostname:

- **Production**: Uses `https://chatter-919568151211.us-central1.run.app`
- **Local Development**: Uses `http://localhost:8080`

This is configured in the frontend code (check `src/pages/Podcast.jsx` or similar files).

### 4. Start Frontend Development Server

```bash
npm run dev
```

The frontend will start on **http://localhost:5173** (Vite default port).

### 5. Access the Application

Open your browser and navigate to:
```
http://localhost:5173
```

### 6. Frontend Features

- **Login/Registration**: Firebase Authentication
- **Podcast Page**: Voice recording and real-time podcast generation
- **Settings**: User preferences management
- **About Us**: Team information
- **Audio History**: View past podcast interactions

---

## 🎯 Running the Complete Application

### Step-by-Step Startup

1. **Start Backend** (Terminal 1):
   ```bash
   cd services/chatter_deployed
   docker-compose -f docker-compose.local.yml --env-file .env.local up --build
   ```
   Wait for: `Application startup complete` and `Uvicorn running on http://0.0.0.0:8080`

2. **Start Frontend** (Terminal 2):
   ```bash
   cd services/k-frontend/podcast-app
   npm run dev
   ```
   Wait for: `Local: http://localhost:5173/`

3. **Open Browser**:
   - Navigate to `http://localhost:5173`
   - Register a new account or login
   - Start recording voice queries!

### Application Flow

1. **User Registration/Login**:
   - Frontend authenticates with Firebase
   - Backend creates user in Cloud SQL (on first registration)
   - Firebase token is used for all authenticated requests

2. **Voice Interaction**:
   - User presses and holds the record button
   - Audio is streamed via WebSocket to backend
   - Backend transcribes audio using Speech-to-Text
   - Backend retrieves relevant news chunks
   - Backend generates podcast using Gemini
   - Backend streams audio response back via WebSocket
   - Frontend plays the audio response

3. **User Preferences**:
   - User can set preferences in Settings page
   - Preferences are saved to Cloud SQL
   - Preferences are used to personalize future podcasts

---

## 🧪 Testing

### Backend Testing

```bash
# Health check
curl http://localhost:8080/healthz

# Test WebSocket (requires Firebase token)
# Use a WebSocket client or the frontend

# Test authenticated endpoint (requires Firebase token in header)
curl -X GET http://localhost:8080/api/user/preferences \
  -H "Authorization: Bearer <firebase-token>"
```

### Frontend Testing

1. Open `http://localhost:5173`
2. Register a new account
3. Navigate to Podcast page
4. Test voice recording:
   - Press and hold the record button
   - Speak a question (e.g., "What's happening in AI research?")
   - Release the button
   - Wait for podcast response

### End-to-End Testing

1. Ensure backend is running on `http://localhost:8080`
2. Ensure frontend is running on `http://localhost:5173`
3. Register/login in the frontend
4. Record a voice query
5. Verify:
   - Audio is transcribed correctly
   - Relevant news chunks are retrieved
   - Podcast is generated and streamed back
   - Audio plays in the browser

---

## ☁️ Deployment

### Backend Deployment (Cloud Run)

1. **Set up Cloud Build**:
   ```bash
   gcloud config set project newsjuice-123456
   gcloud services enable run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com
   ```

2. **Deploy**:
   ```bash
   cd services/chatter_deployed
   gcloud builds submit \
     --config cloudbuild.yaml \
     --substitutions _HUGGING_FACE_HUB_TOKEN=hf_XXXXXXXXXXXXXX
   ```

3. **Monitor Deployment**:
   ```bash
   # Check build status
   gcloud builds list --limit=1
   
   # Check Cloud Run service
   gcloud run services describe chatter --region us-central1
   
   # View logs
   gcloud run services logs read chatter --region us-central1
   ```

### Frontend Deployment

The frontend is deployed to Firebase Hosting at `www.newsjuiceapp.com`.

See `services/k-frontend/podcast-app/firebase.json` for hosting configuration.

---

## 🔍 Troubleshooting

### Backend Issues

**Problem**: Database connection failed
- **Solution**: Ensure Cloud SQL Proxy is running and `DATABASE_URL` is correct
- Check: `docker-compose logs cloud-sql-proxy`

**Problem**: Firebase authentication not working
- **Solution**: Verify `FIREBASE_SERVICE_ACCOUNT_PATH` is set correctly in `.env.local`
- Check: Service account key file exists at the specified path

**Problem**: WebSocket connection fails
- **Solution**: Check CORS settings in `CORS_ALLOW_ORIGINS`
- Verify frontend URL is included in allowed origins

**Problem**: OpenAI API errors
- **Solution**: Verify `OPENAI_API_KEY` is set in `.env.local`
- Check API key is valid and has credits

### Frontend Issues

**Problem**: Cannot connect to backend
- **Solution**: Verify backend is running on `http://localhost:8080`
- Check browser console for CORS errors
- Verify `CORS_ALLOW_ORIGINS` includes frontend URL

**Problem**: Firebase authentication errors
- **Solution**: Verify Firebase config in `src/firebase/config.js`
- Check Firebase project has Authentication enabled
- Verify email/password sign-in method is enabled

**Problem**: Microphone not working
- **Solution**: Grant microphone permissions in browser
- Use HTTPS or localhost (required for Web Audio API)
- Check browser console for errors

### Database Issues

**Problem**: No articles found
- **Solution**: Run the scraper and loader services first:
  ```bash
  make run -f MakefileBatch scrape
  make run -f MakefileBatch load
  ```

**Problem**: User preferences not saving
- **Solution**: Verify user is authenticated (check Firebase token)
- Check Cloud SQL connection and user table exists

---

## 📚 Additional Resources

- **Backend API Documentation**: See `main.py` for endpoint details
- **Frontend Components**: See `services/k-frontend/podcast-app/src/`
- **Database Schema**: See main `README.md` for table structures
- **Development vs Deployment**: See `README_develop_vs_deploy.md` for differences

---

## 🔐 Security Notes

- **Never commit** `.env.local` or service account keys to git
- Use Secret Manager for production secrets
- Firebase tokens should be validated on every request
- CORS should be restricted to known origins in production

---

## 📞 Support

For issues or questions:
1. Check the troubleshooting section above
2. Review service logs: `docker-compose logs`
3. Check Firebase Console for authentication issues
4. Review Cloud Run logs for deployment issues

---

## 🎉 Success Checklist

- [ ] Backend running on `http://localhost:8080`
- [ ] Frontend running on `http://localhost:5173`
- [ ] Firebase authentication working
- [ ] Can register/login in frontend
- [ ] Can record voice queries
- [ ] Podcast responses are generated and played
- [ ] User preferences can be saved
- [ ] Audio history is tracked

Once all items are checked, you're ready to use NewsJuice! 🚀
