#!/usr/bin/env python3
"""
Chatter Service

A microservice that:
1. Prompts user for user ID and question
2. Sends question to Google Gemini API
3. Logs conversation in newsdb database
"""

import os
import sys
import psycopg
from datetime import datetime, timezone
from typing import Optional
import json
from google.oauth2 import service_account
from vertexai.generative_models import GenerativeModel

# Configuration
DB_URL = os.environ["DATABASE_URL"]
GEMINI_SERVICE_ACCOUNT_PATH = os.environ.get("GEMINI_SERVICE_ACCOUNT_PATH", "/run/secrets/gemini-service-account.json")
GOOGLE_CLOUD_PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "newsjuice-123456")
GOOGLE_CLOUD_REGION = os.environ.get("GOOGLE_CLOUD_REGION", "us-central1")

# Configure Vertex AI with service account
try:
    if os.path.exists(GEMINI_SERVICE_ACCOUNT_PATH):
        # Set the credentials file path
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = GEMINI_SERVICE_ACCOUNT_PATH
        
        # Initialize the model (using full model path for Vertex AI)
        # Try gemini-2.5-flash first as it's more readily available
        model = GenerativeModel(
            model_name=f'projects/{GOOGLE_CLOUD_PROJECT}/locations/{GOOGLE_CLOUD_REGION}/publishers/google/models/gemini-2.5-flash'
        )
        print("[gemini] Configured with Vertex AI service account authentication")
        print(f"[gemini] Using model: gemini-2.5-flash in {GOOGLE_CLOUD_REGION}")
    else:
        print(f"[gemini-warning] Service account file not found at {GEMINI_SERVICE_ACCOUNT_PATH}")
        model = None
except Exception as e:
    print(f"[gemini-error] Failed to configure service account: {e}")
    model = None


def check_llm_conversations_table():
    """Check if the llm_conversations table exists."""
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'llm_conversations'
                    );
                """)
                exists = cur.fetchone()[0]
                if exists:
                    print("[db] llm_conversations table found")
                else:
                    print("[db-warning] llm_conversations table not found")
                return exists
    except Exception as e:
        print(f"[db-error] Failed to check table: {e}")
        raise


def get_user_input() -> tuple[str, str]:
    """Get user ID and question from terminal input."""
    try:
        user_id = input("Enter your user ID: ").strip()
        if not user_id:
            print("Error: User ID cannot be empty")
            return get_user_input()
        
        question = input("Enter your question: ").strip()
        if not question:
            print("Error: Question cannot be empty")
            return get_user_input()
        
        return user_id, question
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit(0)
    except Exception as e:
        print(f"Error getting input: {e}")
        return get_user_input()


def call_gemini_api(question: str) -> tuple[Optional[str], Optional[str]]:
    """Call Google Gemini API with the question."""
    if not model:
        return None, "Gemini API not configured"
    
    try:
        response = model.generate_content(question)
        return response.text, None
    except Exception as e:
        return None, str(e)


def log_conversation(user_id: str, question: str, response: Optional[str], error_message: Optional[str]):
    """Log the conversation to the database."""
    try:
        # Prepare conversation data as JSON
        conversation_data = {
            "question": question,
            "response": response,
            "error": error_message
        }
        
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO llm_conversations (user_id, model_name, conversation_data)
                    VALUES (%s, %s, %s);
                """, (user_id, 'gemini-2.5-flash', json.dumps(conversation_data)))
                
                print("[db] Conversation logged successfully")
    except Exception as e:
        print(f"[db-error] Failed to log conversation: {e}")


def main():
    """Main function."""
    print("=== NewsJuice Chatter Service ===")
    print("Connecting to database...")
    
    # Test database connection and create table
    try:
        with psycopg.connect(DB_URL, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT current_database(), version();")
                db_name, db_version = cur.fetchone()
                print(f"[db] Connected successfully to '{db_name}'")
                print(f"[db] Server version: {db_version}")
    except Exception as e:
        print(f"[db-error] Failed to connect to database: {e}")
        sys.exit(1)
    
    # Check if the llm_conversations table exists
    check_llm_conversations_table()
    
    print("\nGemini API Status:", "✓ Configured" if model else "✗ Not configured")
    print("=" * 40)
    
    # Main interaction loop
    while True:
        try:
            # Get user input
            user_id, question = get_user_input()
            
            print(f"\nProcessing question for user: {user_id}")
            print(f"Question: {question}")
            
            # Call Gemini API
            print("Calling Gemini API...")
            response, error = call_gemini_api(question)
            
            if response:
                print(f"\nGemini Response:\n{response}")
            else:
                print(f"\nError calling Gemini API: {error}")
            
            # Log conversation
            log_conversation(user_id, question, response, error)
            
            print("\n" + "=" * 40)
            
            # Ask if user wants to continue
            continue_choice = input("Do you want to ask another question? (y/n): ").strip().lower()
            if continue_choice not in ['y', 'yes']:
                break
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            continue
    
    print("Thank you for using NewsJuice Chatter Service!")


if __name__ == "__main__":
    main()
