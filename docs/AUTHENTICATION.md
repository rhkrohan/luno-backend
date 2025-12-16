# 🔐 Authentication System Guide

Complete guide to the Luno backend authentication system.

---

## Overview

The Luno backend uses a **custom header-based authentication system** with Firestore validation. This system is specifically designed for IoT devices (ESP32 toys) that cannot use traditional OAuth or JWT tokens.

### Key Features

- ✅ Header-based authentication (no tokens required)
- ✅ Firestore validation (email + device ownership)
- ✅ In-memory caching (5-minute TTL for performance)
- ✅ Supports both email and user_id authentication
- ✅ Automatic device verification

---

## Authentication Flow

```
┌─────────────────┐
│  ESP32 Device   │
│  or Simulator   │
└────────┬────────┘
         │
         │ HTTP Request with Headers:
         │ ├─ X-Email: user@example.com
         │ ├─ X-User-ID: user123
         │ ├─ X-Device-ID: toy_abc
         │ ├─ X-Child-ID: child_xyz
         │ ├─ X-Toy-ID: toy_abc
         │ └─ X-Session-ID: session_123
         │
         ▼
┌─────────────────┐
│ Authentication  │
│   Middleware    │
│ (@require_      │
│  device_auth)   │
└────────┬────────┘
         │
         │ Step 1: Check Cache
         │ ├─ Cache Key: email:device_id:session_id
         │ └─ TTL: 5 minutes
         │
         ├─ Cache Hit? ────────► Continue to endpoint
         │
         ├─ Cache Miss?
         │
         │ Step 2: Validate with Firestore
         │ ├─ Look up user by email
         │ ├─ Verify device exists in user's toys
         │ └─ Build auth_context
         │
         │ Step 3: Write to Cache
         │ └─ Store for future requests
         │
         ▼
┌─────────────────┐
│  Flask Endpoint │
│  (Protected)    │
│                 │
│  request.       │
│  auth_context   │
│  available      │
└─────────────────┘
```

---

## Required Headers

### Core Headers

All authenticated requests must include:

| Header | Required | Description | Example |
|--------|----------|-------------|---------|
| `X-Device-ID` | ✅ Yes | Device/toy identifier | `toy_abc123` or `AA:BB:CC:DD:EE:FF` |
| `X-Email` | ✅ Yes* | User's email address | `parent@example.com` |
| `X-User-ID` | ✅ Yes* | Firebase user ID | `user_abc123` |
| `X-Session-ID` | ❌ No | Session identifier | `esp32_session_123` |
| `X-Child-ID` | ❌ No | Child ID (for conversations) | `child_xyz789` |
| `X-Toy-ID` | ❌ No | Toy ID (for conversations) | `toy_abc123` |

*One of `X-Email` or `X-User-ID` must be provided

### Authentication Options

**Option 1: Email + Device ID** (Recommended for ESP32)
```bash
-H "X-Email: parent@example.com"
-H "X-Device-ID: AA:BB:CC:DD:EE:FF"
```

**Option 2: User ID + Device ID** (Testing/Simulator)
```bash
-H "X-User-ID: user_abc123"
-H "X-Device-ID: toy_abc123"
```

---

## Implementation

### Backend (auth_middleware.py)

#### Decorator Usage

```python
from auth_middleware import require_device_auth

@app.route("/upload", methods=["POST"])
@require_device_auth
def upload_audio():
    # Access authenticated context
    auth_context = request.auth_context

    user_id = auth_context['user_id']
    device_id = auth_context['device_id']
    email = auth_context['email']
    toy_data = auth_context['toy_data']
    user_data = auth_context['user_data']

    # Your endpoint logic here
    return response
```

#### Authentication Context

When authentication succeeds, `request.auth_context` contains:

```python
{
    "user_id": "user_abc123",
    "device_id": "toy_abc123",
    "email": "parent@example.com",
    "user_data": {
        "uid": "user_abc123",
        "email": "parent@example.com",
        "displayName": "John Doe",
        # ... other user fields
    },
    "toy_data": {
        "name": "Luna",
        "assignedChildId": "child_xyz789",
        "status": "online",
        "batteryLevel": 85,
        # ... other toy fields
    }
}
```

### ESP32 Hardware Implementation

#### C++/Arduino Code

```cpp
#include <HTTPClient.h>
#include <WiFi.h>

// Store during pairing/setup
String userEmail = "parent@example.com";
String userId = "user_abc123";
String deviceId = WiFi.macAddress();  // Or ESP.getChipId()

void sendRequest() {
    HTTPClient http;
    http.begin("http://your-server.com:5005/upload");

    // Add authentication headers
    http.addHeader("X-Email", userEmail);
    http.addHeader("X-User-ID", userId);
    http.addHeader("X-Device-ID", deviceId);
    http.addHeader("X-Session-ID", currentSessionId);
    http.addHeader("X-Child-ID", activeChildId);
    http.addHeader("X-Toy-ID", toyId);

    // Send request
    int httpCode = http.POST(audioData, audioLength);

    if (httpCode == 200) {
        // Success
    } else if (httpCode == 403) {
        // Authentication failed
        displayError("Please re-pair device");
    } else if (httpCode == 503) {
        // Service unavailable - retry with backoff
        retryWithBackoff();
    }
}
```

---

## Validation Process

### Step 1: Header Extraction

```python
email = request.headers.get("X-Email")
user_id = request.headers.get("X-User-ID")
device_id = request.headers.get("X-Device-ID")
session_id = request.headers.get("X-Session-ID", "default")
```

### Step 2: Required Headers Check

- `device_id` is **always required**
- At least one of `email` or `user_id` must be provided

### Step 3: Cache Lookup

```python
cache_key = f"{email or user_id}:{device_id}:{session_id}"
cached_context = auth_cache.get(cache_key)

if cached_context and not expired:
    return cached_context  # Skip Firestore query
```

### Step 4: Firestore Validation

#### If email provided:
```python
# 1. Find user by email
users_ref = firestore.db.collection("users")
query = users_ref.where("email", "==", email.lower()).limit(1)
user_doc = query.stream()[0]
user_id = user_doc.id

# 2. Verify device exists
toy_ref = firestore.db.collection("users").document(user_id) \
    .collection("toys").document(device_id)
toy_doc = toy_ref.get()

if not toy_doc.exists:
    raise AuthenticationError("Device not associated with this user", 403)
```

#### If user_id provided:
```python
# 1. Verify user exists
user_ref = firestore.db.collection("users").document(user_id)
user_doc = user_ref.get()

if not user_doc.exists:
    raise AuthenticationError("User not found", 404)

# 2. Verify device exists
toy_ref = user_ref.collection("toys").document(device_id)
toy_doc = toy_ref.get()

if not toy_doc.exists:
    raise AuthenticationError("Device not associated with this user", 403)
```

### Step 5: Cache Result

```python
auth_cache[cache_key] = {
    "auth_context": {...},
    "expires_at": time.time() + 300  # 5 minutes
}
```

---

## HTTP Status Codes

| Code | Meaning | Cause | Solution |
|------|---------|-------|----------|
| **200** | Success | Authentication valid | Request processed |
| **400** | Bad Request | Missing required headers | Add `X-Device-ID` and `X-Email`/`X-User-ID` |
| **403** | Forbidden | Email mismatch or device not associated | Verify email and device are paired |
| **404** | Not Found | User ID not found | Check user exists in Firestore |
| **503** | Service Unavailable | Firestore temporarily down | Retry with exponential backoff |

---

## Testing Authentication

### Test Endpoint

```bash
curl -X GET http://localhost:5005/auth/test \
  -H "X-User-ID: test_user_1763434576" \
  -H "X-Device-ID: test_toy_1763434576" \
  -H "X-Email: test@lunotoys.com" \
  -H "X-Session-ID: test_session"
```

**Success Response (200):**
```json
{
  "success": true,
  "message": "Authentication successful",
  "user_id": "test_user_1763434576",
  "device_id": "test_toy_1763434576",
  "email": "test@lunotoys.com",
  "device_name": "Test Toy",
  "assigned_child": "test_child_1763434576",
  "device_status": "online"
}
```

**Error Response (403):**
```json
{
  "error": "Device not associated with this user"
}
```

### Using the Simulator

#### Web Simulator
1. Go to `http://localhost:5005/simulator`
2. Fill in configuration fields
3. Click **"🔐 Test Authentication"**
4. View results in the status area

#### CLI Simulator
```bash
python esp32_simulator.py
# Press 7 to test authentication
```

---

## Security Considerations

### What This System Protects Against

✅ **Unauthorized device access** - Devices must be registered in Firestore
✅ **Email spoofing** - Email must match Firestore user record
✅ **Device hijacking** - Device must exist in user's toys collection
✅ **Session isolation** - Cache keys include session_id

### What This System Does NOT Protect Against

❌ **Header spoofing** - If someone knows valid headers, they can impersonate
❌ **Network sniffing** - Headers sent in plaintext (use HTTPS in production)
❌ **Replay attacks** - Same headers can be reused (consider adding HMAC signing)

### Production Recommendations

1. **Use HTTPS** - Encrypt all traffic
2. **Add HMAC Signing** - Sign headers with shared secret
3. **Implement Rate Limiting** - Prevent brute force attacks
4. **Monitor Failed Auth** - Alert on suspicious patterns
5. **Rotate Device Secrets** - Periodically update device credentials

---

## Performance Optimization

### Caching Strategy

```
First Request (Cache Miss):
├─ Firestore query: ~100-200ms
├─ Cache write: <1ms
└─ Total: ~100-200ms

Subsequent Requests (Cache Hit):
├─ Cache lookup: <1ms
└─ Total: <1ms

Expected Cache Hit Rate: >90%
```

### Cache Configuration

```python
# auth_middleware.py
CACHE_TTL_SECONDS = 300  # 5 minutes

# Adjust based on your needs:
# - Lower TTL: More Firestore queries, more secure
# - Higher TTL: Fewer Firestore queries, less responsive to changes
```

---

## Troubleshooting

### "Missing required header: X-Device-ID"

**Cause:** Request missing `X-Device-ID` header

**Solution:**
```bash
curl ... -H "X-Device-ID: your_device_id"
```

### "Missing required header: X-Email or X-User-ID"

**Cause:** Request missing both `X-Email` and `X-User-ID`

**Solution:** Add at least one:
```bash
curl ... -H "X-Email: user@example.com"
# OR
curl ... -H "X-User-ID: user_abc123"
```

### "User not found with email"

**Cause:** Email doesn't exist in Firestore

**Solution:** Create user account:
```bash
curl -X POST http://localhost:5005/api/setup/create_account \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", ...}'
```

### "Device not associated with this user"

**Cause:** Device ID not in user's toys collection

**Solution:** Add toy to user account:
```bash
curl -X POST http://localhost:5005/api/setup/add_toy \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user_abc123",
    "toy_id": "toy_abc123",
    "toy_name": "Luna"
  }'
```

### "Authentication service unavailable"

**Cause:** Firestore not initialized or temporarily down

**Solution:**
1. Check Firebase credentials are configured
2. Verify Firestore database exists
3. Check network connectivity
4. Retry with exponential backoff

---

## Protected Endpoints

The following endpoints require authentication:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/upload` | POST | Upload audio for processing |
| `/text_upload` | POST | Upload text for processing |
| `/auth/test` | GET | Test authentication |
| `/device/info` | GET | Get device information |

---

## Future Enhancements

Potential improvements to the authentication system:

1. **HMAC Signing** - Sign headers with shared secret
2. **JWT Tokens** - Issue short-lived tokens after initial auth
3. **Device Certificates** - PKI-based device authentication
4. **OAuth 2.0** - Standard OAuth flow for mobile apps
5. **API Keys** - Alternative to header-based auth

---

## Related Documentation

- [SETUP.md](./SETUP.md) - Backend setup and configuration
- [SIMULATOR_GUIDE.md](./SIMULATOR_GUIDE.md) - Testing with simulators
- [ESP32_INTEGRATION_EXAMPLE.md](./ESP32_INTEGRATION_EXAMPLE.md) - Hardware implementation
- [README.md](../README.md) - Complete system documentation

---

**Authentication System Ready! 🔐**

Your backend is protected with Firestore-validated authentication.
