import firebase_admin
from firebase_admin import auth, credentials
from typing import Dict
import os

"""Firebase Admin SDK initialization and token verification."""

"""
FUNCTIONS CONTAINED:

initialize_firebase_admin()   ---- called by main.py
verify_token(token: str) -> Dict --- called by main.py

"""


def initialize_firebase_admin():
    """Initialize Firebase Admin SDK."""
    # Check if already initialized
    if len(firebase_admin._apps) > 0:
        print("[firebase-admin] Already initialized")
        return

    # Try to use Firebase-specific service account first (for local development)
    service_account_path = os.environ.get("FIREBASE_SERVICE_ACCOUNT_PATH")
    if service_account_path and os.path.exists(service_account_path):
        try:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print(f"[firebase-admin] Initialized with service account file: {service_account_path}")
            return
        except Exception as e:
            print(f"[firebase-admin-warning] Failed to init with service account: {e}")

    # Fallback to default credentials (for cloud deployment)
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
