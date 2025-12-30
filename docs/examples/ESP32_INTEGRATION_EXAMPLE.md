# ESP32 Integration Examples

> **⚠️ Updated:** Sessions are now backend-managed! ESP32 no longer needs to generate or send session IDs. See [SESSION_MANAGEMENT.md](./SESSION_MANAGEMENT.md) for details.

## Required Headers

All requests to `/upload` and `/text_upload` must include these headers:

```cpp
X-Device-ID: <device_identifier>      // Required for auth
X-User-Email: <user_email>            // Or X-User-ID
X-Child-ID: <firebase_child_id>       // Optional
X-Toy-ID: <firebase_toy_id>           // Optional
// X-Session-ID is DEPRECATED - backend manages sessions automatically
```

## Arduino/ESP32 Code Examples

### Example 1: Upload Audio (ADPCM)

```cpp
#include <HTTPClient.h>

void sendAudioToBackend(uint8_t* audioData, size_t audioLength) {
  HTTPClient http;

  // Server endpoint
  http.begin("http://your-server.com:5005/upload");

  // Add required headers (NO session ID needed!)
  http.addHeader("Content-Type", "audio/adpcm");
  http.addHeader("X-Audio-Format", "adpcm");
  http.addHeader("X-Device-ID", deviceId);            // Device identifier
  http.addHeader("X-User-Email", userEmail);          // Or X-User-ID
  http.addHeader("X-Child-ID", activeChildId);        // Active child
  http.addHeader("X-Toy-ID", toyId);                  // This toy's ID

  // Send POST request
  int httpResponseCode = http.POST(audioData, audioLength);

  if (httpResponseCode == 200) {
    // Get response audio
    WiFiClient* stream = http.getStreamPtr();
    size_t responseLength = http.getSize();

    uint8_t buffer[128];
    while (http.connected() && (responseLength > 0 || responseLength == -1)) {
      size_t available = stream->available();
      if (available) {
        int bytesRead = stream->readBytes(buffer, min(available, sizeof(buffer)));
        // Play audio buffer
        playAudio(buffer, bytesRead);

        if (responseLength > 0) {
          responseLength -= bytesRead;
        }
      }
    }

    Serial.println("[INFO] Response received and played");
  } else {
    Serial.printf("[ERROR] HTTP error: %d\n", httpResponseCode);
  }

  http.end();
}
```

### Example 2: Send Text (Local STT)

```cpp
#include <HTTPClient.h>
#include <ArduinoJson.h>

void sendTextToBackend(const char* transcribedText) {
  HTTPClient http;

  // Server endpoint
  http.begin("http://your-server.com:5005/text_upload");

  // Add headers (NO session ID needed!)
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-ID", deviceId);
  http.addHeader("X-User-Email", userEmail);        // Or X-User-ID
  http.addHeader("X-Child-ID", activeChildId);
  http.addHeader("X-Toy-ID", toyId);

  // Create JSON payload
  StaticJsonDocument<512> doc;
  doc["text"] = transcribedText;
  // Backend manages sessions - no session_id needed!

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  // Send POST request
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode == 200) {
    // Get response audio (same as Example 1)
    WiFiClient* stream = http.getStreamPtr();
    // ... (play audio)

    Serial.println("[INFO] Response received");
  } else {
    Serial.printf("[ERROR] HTTP error: %d\n", httpResponseCode);
  }

  http.end();
}
```

### Example 3: End Conversation (Optional)

> **Note:** Backend automatically ends sessions after 30 minutes of inactivity. Explicit ending is optional.

```cpp
#include <HTTPClient.h>
#include <ArduinoJson.h>

void endConversation() {
  HTTPClient http;

  // Server endpoint
  http.begin("http://your-server.com:5005/api/conversations/end");
  http.addHeader("Content-Type", "application/json");

  // Create JSON payload - backend looks up session by device+user
  StaticJsonDocument<256> doc;
  doc["device_id"] = deviceId;
  doc["user_id"] = userId;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  // Send POST request
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode == 200) {
    Serial.println("[INFO] Conversation ended successfully");
    // Backend creates new session automatically on next request
  } else {
    Serial.printf("[ERROR] Failed to end conversation: %d\n", httpResponseCode);
  }

  http.end();
}
```

## Session Management

> **🔄 Sessions are now backend-managed!** No session ID generation needed on ESP32.

### Global Variables

```cpp
// Initialize these during toy pairing/setup
String deviceId = "";         // Device identifier (MAC address or unique ID)
String userEmail = "";        // From pairing (WiFi config)
String userId = "";           // Or use user_id instead of email
String activeChildId = "";    // From user selection (set when child starts using toy)
String toyId = "";            // Unique toy identifier (set during manufacturing)

// NO SESSION ID NEEDED - backend manages it automatically!

void setup() {
  // ... WiFi setup ...

  // Get device ID from MAC address
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char macStr[18];
  sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X",
          mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  deviceId = String(macStr);

  Serial.printf("[INFO] Device ID: %s\n", deviceId.c_str());
}
```

## Timing Recommendations

### When to Start a Conversation
- **Automatically** when first audio/text is sent
- No need to explicitly "start" - backend creates it automatically

### When to End a Conversation

> **Backend Auto-Ends:** Sessions automatically end after 30 minutes of inactivity. Explicit ending is optional.

**Option 1: Let Backend Handle It (Recommended)**
```cpp
// Do nothing - backend handles session expiration automatically
// No endConversation() call needed
```

**Option 2: Explicit End (Optional)**
Call `endConversation()` when:

```cpp
// 1. User manually ends session
void onButtonPress() {
  if (conversationActive) {
    endConversation();  // Optional - tells backend to end immediately
    conversationActive = false;
  }
}

// 2. Toy is turned off
void onPowerOff() {
  if (conversationActive) {
    endConversation();  // Good practice - immediate cleanup
  }
  // ... shutdown ...
}

// Note: Inactivity timeout is now handled by backend (30 minutes)
// No need to track timeout on ESP32
```

## Error Handling

### Handle HTTP Errors

```cpp
int httpResponseCode = http.POST(payload);

switch (httpResponseCode) {
  case 200:
    // Success - process response
    break;

  case 400:
    Serial.println("[ERROR] Bad request - check headers/payload");
    break;

  case 500:
    Serial.println("[ERROR] Server error - retry?");
    break;

  case -1:
    Serial.println("[ERROR] Connection failed");
    break;

  default:
    Serial.printf("[ERROR] HTTP %d\n", httpResponseCode);
    break;
}
```

### Retry Logic

```cpp
bool sendWithRetry(const char* text, int maxRetries = 3) {
  for (int attempt = 1; attempt <= maxRetries; attempt++) {
    Serial.printf("[INFO] Attempt %d/%d\n", attempt, maxRetries);

    int responseCode = sendTextToBackend(text);

    if (responseCode == 200) {
      return true;
    }

    if (attempt < maxRetries) {
      delay(1000 * attempt); // Exponential backoff
    }
  }

  return false;
}
```

## Complete Example Flow

```cpp
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Global variables (NO SESSION ID NEEDED!)
String deviceId = "";
String userEmail = "parent@example.com";  // From pairing
String userId = "user_abc123";            // Or use this
String activeChildId = "child_xyz789";
String toyId = "toy_luno_001";
bool conversationActive = false;

void setup() {
  Serial.begin(115200);

  // Connect to WiFi
  WiFi.begin("SSID", "PASSWORD");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[INFO] WiFi connected");

  // Get device ID from MAC address
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char macStr[18];
  sprintf(macStr, "%02X:%02X:%02X:%02X:%02X:%02X",
          mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
  deviceId = String(macStr);

  Serial.printf("[INFO] Device ID: %s\n", deviceId.c_str());
}

void loop() {
  // Check for audio input
  if (audioDetected()) {
    uint8_t* audioData = recordAudio();
    size_t audioLength = getAudioLength();

    // Send to backend - it handles session automatically!
    sendAudioToBackend(audioData, audioLength);

    conversationActive = true;
  }

  // Backend handles inactivity timeout (30 min)
  // No need to track timeout on ESP32

  delay(100);
}

void sendAudioToBackend(uint8_t* audioData, size_t audioLength) {
  HTTPClient http;
  http.begin("http://your-server.com:5005/upload");
  http.addHeader("Content-Type", "audio/adpcm");
  http.addHeader("X-Audio-Format", "adpcm");
  // NO X-Session-ID - backend manages it!
  http.addHeader("X-Device-ID", deviceId);
  http.addHeader("X-User-Email", userEmail);  // Or X-User-ID
  http.addHeader("X-Child-ID", activeChildId);
  http.addHeader("X-Toy-ID", toyId);

  int httpCode = http.POST(audioData, audioLength);

  if (httpCode == 200) {
    WiFiClient* stream = http.getStreamPtr();
    // Play audio response
    playAudioStream(stream);
  }

  http.end();
}

void endConversation() {
  HTTPClient http;
  http.begin("http://your-server.com:5005/api/conversations/end");
  http.addHeader("Content-Type", "application/json");

  StaticJsonDocument<256> doc;
  doc["device_id"] = deviceId;  // Backend looks up session
  doc["user_id"] = userId;
  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);
  if (httpCode == 200) {
    Serial.println("[INFO] Conversation ended");
    // Backend creates new session automatically on next request
  }

  http.end();
}
```

## Testing Checklist

- [ ] Headers are included in all requests (X-Device-ID, X-User-Email/ID)
- [ ] ~~Session ID is sent~~ **No longer needed - backend manages sessions!**
- [ ] Device ID is consistent across all requests
- [ ] User/Child/Toy IDs match Firebase document IDs
- [ ] Audio responses are played correctly
- [ ] Error cases are handled gracefully

## Common Issues

### Issue: "Missing user/child metadata" warning in logs
**Solution:** Ensure all headers (`X-Device-ID`, `X-User-Email`, `X-Child-ID`) are sent

### Issue: Multiple conversations created
**Solution:** Ensure device_id and user_id are consistent across requests (backend uses these to manage sessions)

### Issue: Stats not updating
**Solution:** Backend auto-ends sessions after 30 min, or call `/api/conversations/end` explicitly

---

## Related Documentation

- [SESSION_MANAGEMENT.md](./SESSION_MANAGEMENT.md) - **NEW** Backend session management guide
- [AUTHENTICATION.md](./AUTHENTICATION.md) - Authentication system
- [README.md](../README.md) - Complete system documentation

---

**Backend-Managed Sessions - Simplified ESP32 Integration! 🎉**
