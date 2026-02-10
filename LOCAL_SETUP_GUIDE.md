# NewsJuice Local Demo Setup Guide

This guide walks you through setting up a fully functional local demo of NewsJuice using your own Google Cloud resources.

## Prerequisites

- Google account (personal Gmail is fine)
- Docker and Docker Compose installed
- Node.js and npm installed

## Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click "Add project"
3. Enter project name (e.g., "newsjuice-local-demo")
4. Disable Google Analytics (optional, not needed for demo)
5. Click "Create project"

## Step 2: Enable Firebase Authentication

1. In your Firebase project, click "Authentication" in the left sidebar
2. Click "Get started"
3. Click on "Email/Password" under "Sign-in method"
4. Enable "Email/Password"
5. Click "Save"

## Step 3: Get Firebase Web Credentials

1. In Firebase console, click the gear icon → "Project settings"
2. Scroll down to "Your apps" section
3. Click the "</>" (Web) icon to add a web app
4. Enter app nickname (e.g., "NewsJuice Frontend")
5. Click "Register app"
6. Copy the `firebaseConfig` object - you'll need this later
7. Should look like:
```javascript
{
  apiKey: "AIza...",
  authDomain: "your-project.firebaseapp.com",
  projectId: "your-project-id",
  storageBucket: "your-project.firebasestorage.app",
  messagingSenderId: "123456789",
  appId: "1:123456789:web:abcdef"
}
```

## Step 4: Create Firebase Admin Service Account

1. In Firebase console, click the gear icon → "Project settings"
2. Go to "Service accounts" tab
3. Click "Generate new private key"
4. Click "Generate key" in the confirmation dialog
5. Save the downloaded JSON file as `firebase-admin-key.json`
6. Move this file to `secrets/firebase-admin-key.json` in your project root

## Step 5: Configure Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select the project that was auto-created by Firebase (same name)
3. Enable billing (required for APIs, but free tier should cover demo usage):
   - Click "Billing" in left menu
   - Click "Link a billing account" or "Create billing account"
   - Add credit card (won't be charged within free tier limits)

## Step 6: Enable Required APIs

In Google Cloud Console, enable these APIs:

1. Click "APIs & Services" → "Enable APIs and Services"
2. Search for and enable each of these:
   - **Vertex AI API** (for Gemini)
   - **Cloud Text-to-Speech API**
   - **Cloud Speech-to-Text API**
   - **Cloud Storage API**

## Step 7: Create Service Account for Google Cloud Services

1. Go to "IAM & Admin" → "Service Accounts"
2. Click "Create Service Account"
3. Name it "newsjuice-local-demo"
4. Click "Create and Continue"
5. Add these roles:
   - Vertex AI User
   - Cloud Storage Admin
   - Cloud Text to Speech Admin
   - Cloud Speech-to-Text Admin
6. Click "Continue" → "Done"
7. Click on the service account you just created
8. Go to "Keys" tab
9. Click "Add Key" → "Create new key"
10. Choose "JSON"
11. Save the downloaded file as `sa-key.json`
12. Move this file to `secrets/sa-key.json` in your project root

## Step 8: Create Google Cloud Storage Bucket

1. In Google Cloud Console, go to "Cloud Storage" → "Buckets"
2. Click "Create bucket"
3. Name it something like "newsjuice-local-audio" (must be globally unique)
4. Choose region: "us-central1" (or your preferred region)
5. Choose "Standard" storage class
6. Choose "Uniform" access control
7. Click "Create"
8. Note the bucket name - you'll need it for configuration

## Step 9: Get Google API Key

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "API key"
3. Copy the API key
4. (Optional) Click "Restrict Key" and add:
   - Restrict to "Generative Language API" if you're using Gemini 2.5 Flash
   - Or leave unrestricted for demo purposes
5. Save this key - you'll need it for `.env.local`

## Step 10: Organize Your Credentials

Create a `secrets/` directory in your project root:

```bash
cd /Users/zachary-sardi-santos/AC215-Project/ac215_NewsJuice
mkdir -p secrets
```

You should now have:
- `secrets/firebase-admin-key.json` (from Step 4)
- `secrets/sa-key.json` (from Step 7)
- `secrets/gemini-service-account.json` (copy of sa-key.json is fine)

```bash
# Create a copy for gemini (or use the same file)
cp secrets/sa-key.json secrets/gemini-service-account.json
```

## Step 11: Update Configuration Files

### 11.1 Update Frontend Firebase Config

Edit `services/frontend/podcast-app/src/firebase/config.js`:

Replace the `firebaseConfig` object with your credentials from Step 3.

### 11.2 Update Backend Environment Variables

Edit `services/chatter_deployed/.env.local`:

```env
GOOGLE_API_KEY=<your-api-key-from-step-9>
```

### 11.3 Update Docker Compose

Edit `services/chatter_deployed/docker-compose.local.yml`:

Update these environment variables:
- Line 47: `GOOGLE_CLOUD_PROJECT=<your-project-id>`
- Line 55: `AUDIO_BUCKET=<your-bucket-name-from-step-8>`

## Step 12: Start Your Local Demo

### 12.1 Start Backend Services

```bash
cd services/chatter_deployed
docker-compose -f docker-compose.local.yml up --build
```

Wait for the services to start. You should see:
- PostgreSQL container starting
- Database initialization from init-db.sql
- API service starting on port 8080

### 12.2 Start Frontend

Open a new terminal:

```bash
cd services/frontend/podcast-app
npm install
npm run dev
```

The frontend should start on http://localhost:5173

## Step 13: Test Your Demo

1. Open http://localhost:5173 in your browser
2. Click "Register" and create a new user account
3. Login with your credentials
4. Go to "Preferences" and select:
   - Topics (e.g., Politics, Technology, Research)
   - Sources (e.g., Harvard Crimson, Harvard Gazette)
   - Voice preference
5. Click "Save Preferences"
6. Go to "Podcast" page
7. Click "Generate Daily Brief"
8. Wait for the AI to generate and listen to your personalized news brief!

## Troubleshooting

### Backend fails to start
- Check Docker logs: `docker-compose -f docker-compose.local.yml logs`
- Ensure PostgreSQL is healthy before API starts
- Verify service account files exist in `secrets/` directory

### Firebase Authentication fails
- Verify Firebase config in frontend matches your Firebase project
- Check that Email/Password auth is enabled in Firebase console
- Check browser console for detailed error messages

### Gemini API fails
- Verify Vertex AI API is enabled
- Check service account has "Vertex AI User" role
- Verify GOOGLE_CLOUD_PROJECT matches your actual project ID

### Audio generation fails
- Verify Text-to-Speech API is enabled
- Check GCS bucket exists and name matches AUDIO_BUCKET
- Verify service account has "Cloud Storage Admin" role

### Database connection fails
- Wait for PostgreSQL healthcheck to pass
- Check DATABASE_URL in docker-compose.local.yml
- Verify init-db.sql ran successfully (check docker logs)

## Cost Considerations

All services have generous free tiers:
- **Firebase Auth**: 50,000 free authentications/month
- **Vertex AI (Gemini)**: Free tier for Gemini models
- **Text-to-Speech**: 1 million characters free/month
- **Speech-to-Text**: 60 minutes free/month
- **Cloud Storage**: 5GB storage free/month

For a local demo, you should stay well within free tier limits.

## Security Notes

- Never commit the `secrets/` directory to git (it's already in .gitignore)
- Keep your service account keys secure
- For production, use proper IAM roles and least-privilege access
- Rotate API keys regularly

## Need Help?

If you run into issues:
1. Check the Troubleshooting section above
2. Review Docker logs for backend issues
3. Check browser console for frontend issues
4. Verify all APIs are enabled in Google Cloud Console
5. Double-check service account roles and permissions
