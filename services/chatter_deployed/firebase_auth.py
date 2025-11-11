"""Firebase Admin SDK initialization and token verification."""

import os
import firebase_admin
from firebase_admin import credentials, auth
from typing import Dict

def initialize_firebase_admin():
    """Initialize Firebase Admin SDK."""
    # Check if already initialized
    if len(firebase_admin._apps) > 0:
        print("[firebase-admin] Already initialized")
        return
    
    # Option 1: Use service account JSON file (for local dev)
    service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if service_account_path and os.path.exists(service_account_path):
        cred = credentials.Certificate(service_account_path)
        firebase_admin.initialize_app(cred)
        print("[firebase-admin] Initialized with service account file")
        return
   
    # Option 2: Use default credentials (for Cloud Run with Workload Identity)
    try:
        firebase_admin.initialize_app()
        print("[firebase-admin] Initialized with default credentials")
    except Exception as e:
        print(f"[firebase-admin-error] Failed to initialize: {e}")
        raise

def verify_token(token: str) -> Dict:
    """
    Verify the Firebase ID token and return the decoded token.
    
    Args:
        token: Firebase ID token string
        
    Returns:
        Decoded token dictionary containing user data (uid, email, etc.)
        
    Raises:
        Exception: If token is invalid or expired
    """
    try:
        decoded_token = auth.verify_id_token(token)
        return decoded_token
    except Exception as e:
        print(f"[firebase-admin-error] Token verification failed: {e}")
        raise
