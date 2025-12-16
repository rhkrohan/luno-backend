"""
Firebase Admin SDK Configuration
Initializes Firebase Admin SDK for Firestore access
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
import json

# Global Firestore client instance
db = None

def initialize_firebase():
    """
    Initialize Firebase Admin SDK

    Supports three methods:
    1. Service account JSON file (recommended for production)
    2. Service account JSON string from environment variable
    3. Application Default Credentials (for development)

    Project: luno-companion-app-dev
    """
    global db

    if db is not None:
        print("[INFO] Firebase already initialized")
        return db

    try:
        # Method 1: Service Account JSON file
        service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")

        if service_account_path and os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            print(f"[INFO] Firebase initialized with service account: {service_account_path}")

        # Method 2: Service Account JSON string (environment variable)
        elif os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"):
            service_account_json = json.loads(os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON"))
            cred = credentials.Certificate(service_account_json)
            firebase_admin.initialize_app(cred)
            print("[INFO] Firebase initialized with service account JSON from environment")

        # Method 3: Application Default Credentials (local development)
        else:
            # Try with explicit project ID for luno-companion-app-dev
            firebase_admin.initialize_app(options={
                'projectId': 'luno-companion-app-dev'
            })
            print("[INFO] Firebase initialized with Application Default Credentials")
            print("[INFO] Using project: luno-companion-app-dev")

        db = firestore.client()
        print("[INFO] Firestore client initialized successfully")
        print(f"[INFO] Connected to project: {firebase_admin.get_app().project_id}")
        return db

    except Exception as e:
        print(f"[ERROR] Failed to initialize Firebase: {e}")
        print("[HINT] To fix:")
        print("  1. Download service account key from Firebase Console")
        print("  2. Save as: firebase-credentials.json")
        print("  3. Set: export FIREBASE_SERVICE_ACCOUNT_PATH='firebase-credentials.json'")
        print("  OR use existing test account: test_user_1763434576")
        # Return None to allow app to run without Firestore (graceful degradation)
        return None


def get_firestore_client():
    """
    Get the Firestore client instance
    Initializes if not already done
    """
    global db
    if db is None:
        db = initialize_firebase()
    return db


# Auto-initialize on import (optional - you can call explicitly instead)
# db = initialize_firebase()
