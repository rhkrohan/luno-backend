# auth_middleware.py

import functools
import time
from flask import request, jsonify
from firestore_service import firestore_service

# Simple in-memory cache
auth_cache = {}
CACHE_TTL_SECONDS = 300  # 5 minutes


class AuthenticationError(Exception):
    def __init__(self, message, status=403):
        super().__init__(message)
        self.message = message
        self.status = status


def validate_auth_headers():
    """
    Extract and validate required headers.

    ESP32 can authenticate with EITHER:
    - X-User-Email (or X-Email) + X-Device-ID (ESP32 knows email from WiFi pairing)
    - X-User-ID + X-Device-ID (for testing/simulator)

    Note: Accepts both X-Email and X-User-Email for backward compatibility
    """
    # Accept both X-User-Email (mobile app standard) and X-Email (legacy)
    email = request.headers.get("X-User-Email") or request.headers.get("X-Email")
    user_id = request.headers.get("X-User-ID")
    device_id = request.headers.get("X-Device-ID")
    session_id = request.headers.get("X-Session-ID")

    # Log if ESP32 still sends session ID (backward compatibility during migration)
    if session_id:
        print(f"[INFO] Ignoring ESP32-provided session ID: {session_id} (backend manages sessions)")

    if not device_id:
        raise AuthenticationError("Missing required header: X-Device-ID", 400)

    if not email and not user_id:
        raise AuthenticationError("Missing required header: X-User-Email (or X-Email) or X-User-ID", 400)

    return email, user_id, device_id, session_id


def check_cache(email, user_id, device_id, session_id):
    # Cache key uses email OR user_id (whichever is provided)
    # Note: session_id removed from cache key (sessions managed separately by session_manager)
    cache_key = email if email else user_id
    key = f"{cache_key}:{device_id}"
    entry = auth_cache.get(key)

    if entry and entry["expires_at"] > time.time():
        return entry.get("auth_context")

    return None


def write_cache(email, user_id, device_id, session_id, auth_context):
    # Cache key uses email OR user_id (whichever is provided)
    # Note: session_id removed from cache key (sessions managed separately by session_manager)
    cache_key = email if email else user_id
    key = f"{cache_key}:{device_id}"
    auth_cache[key] = {
        "auth_context": auth_context,
        "expires_at": time.time() + CACHE_TTL_SECONDS,
    }


def validate_with_firestore(email, user_id, device_id):
    """
    Validates device authentication using email OR user_id.

    Args:
        email: User email (from ESP32 WiFi pairing)
        user_id: User ID (from simulator/testing)
        device_id: Device/toy ID

    Returns:
        dict: Contains user_data and toy_data for caching
    """
    if not firestore_service.db:
        raise AuthenticationError("Authentication service unavailable", 503)

    # Look up user by email OR user_id
    if email:
        # Query users collection by email
        users_ref = firestore_service.db.collection("users")
        query = users_ref.where("email", "==", email.lower().strip()).limit(1)
        users = list(query.stream())

        if not users:
            raise AuthenticationError("User not found with email", 404)

        user_doc = users[0]
        user_id = user_doc.id  # Get the actual user_id from the document
        print(f"[AUTH] ✓ User found by email: {email} -> {user_id}")
    else:
        # Direct lookup by user_id
        user_ref = firestore_service.db.collection("users").document(user_id)
        user_doc = user_ref.get()

        if not user_doc.exists:
            raise AuthenticationError("User not found", 404)

        print(f"[AUTH] ✓ User {user_id} verified")

    # Check if device/toy exists in user's toys subcollection
    toy_ref = firestore_service.db.collection("users").document(user_id)\
        .collection("toys").document(device_id)
    toy_doc = toy_ref.get()

    if not toy_doc.exists:
        raise AuthenticationError("Device not associated with this user", 403)

    print(f"[AUTH] ✓ Device {device_id} verified")

    # Return validation data for caching
    return {
        "user_id": user_id,
        "device_id": device_id,
        "email": user_doc.to_dict().get("email", ""),
        "user_data": user_doc.to_dict(),
        "toy_data": toy_doc.to_dict()
    }


def require_device_auth(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        try:
            email, user_id, device_id, session_id = validate_auth_headers()

            # Check cache
            cached_context = check_cache(email, user_id, device_id, session_id)
            if cached_context:
                print("[AUTH] ✓ Cache hit")
                request.auth_context = cached_context
                return f(*args, **kwargs)

            # Validate with Firestore
            print("[AUTH] Cache miss → Validating with Firestore…")
            auth_context = validate_with_firestore(email, user_id, device_id)

            # Cache the result
            write_cache(email, user_id, device_id, session_id, auth_context)

            # Set context for the endpoint to use
            request.auth_context = auth_context

            print("[AUTH] ✓ Auth succeeded")
            return f(*args, **kwargs)

        except AuthenticationError as e:
            print(f"[AUTH] ✗ {e.message}")
            return jsonify({"error": e.message}), e.status

        except Exception as e:
            print(f"[AUTH] Unexpected error: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({"error": "Internal server error"}), 500

    return wrapper
