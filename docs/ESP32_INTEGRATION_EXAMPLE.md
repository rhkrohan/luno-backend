# ESP32 Integration Examples

## Required Headers

All requests to `/upload` and `/text_upload` must include these headers:

```cpp
X-Session-ID: <unique_session_id>
X-User-ID: <firebase_user_id>
X-Child-ID: <firebase_child_id>
X-Toy-ID: <firebase_toy_id>
```

## Arduino/ESP32 Code Examples

### Example 1: Upload Audio (ADPCM)

```cpp
#include <HTTPClient.h>

void sendAudioToBackend(uint8_t* audioData, size_t audioLength) {
  HTTPClient http;

  // Server endpoint
  http.begin("http://your-server.com:5005/upload");

  // Add required headers
  http.addHeader("Content-Type", "audio/adpcm");
  http.addHeader("X-Audio-Format", "adpcm");
  http.addHeader("X-Session-ID", sessionId);          // Global session ID
  http.addHeader("X-User-ID", userId);                // From pairing
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

  // Add headers
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-User-ID", userId);
  http.addHeader("X-Child-ID", activeChildId);
  http.addHeader("X-Toy-ID", toyId);

  // Create JSON payload
  StaticJsonDocument<512> doc;
  doc["text"] = transcribedText;
  doc["session_id"] = sessionId;
  doc["user_id"] = userId;        // Can be in JSON or headers
  doc["child_id"] = activeChildId;
  doc["toy_id"] = toyId;

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

### Example 3: End Conversation

```cpp
#include <HTTPClient.h>
#include <ArduinoJson.h>

void endConversation() {
  HTTPClient http;

  // Server endpoint
  http.begin("http://your-server.com:5005/api/conversations/end");
  http.addHeader("Content-Type", "application/json");

  // Create JSON payload
  StaticJsonDocument<256> doc;
  doc["session_id"] = sessionId;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  // Send POST request
  int httpResponseCode = http.POST(jsonPayload);

  if (httpResponseCode == 200) {
    Serial.println("[INFO] Conversation ended successfully");

    // Generate new session ID for next conversation
    sessionId = generateNewSessionId();
  } else {
    Serial.printf("[ERROR] Failed to end conversation: %d\n", httpResponseCode);
  }

  http.end();
}
```

## Session Management

### Generate Session ID

```cpp
String generateNewSessionId() {
  // Use MAC address + timestamp for unique session ID
  uint8_t mac[6];
  WiFi.macAddress(mac);

  char sessionId[64];
  sprintf(sessionId, "esp32_%02X%02X%02X_%lu",
          mac[3], mac[4], mac[5], millis());

  return String(sessionId);
}
```

### Global Variables

```cpp
// Initialize these during toy pairing/setup
String userId = "";           // From Firebase Auth (set during pairing)
String activeChildId = "";    // From user selection (set when child starts using toy)
String toyId = "";            // Unique toy identifier (set during manufacturing)
String sessionId = "";        // Generated at start of each conversation

// Initialize session ID at startup or after ending conversation
void setup() {
  // ... WiFi setup ...

  sessionId = generateNewSessionId();
}
```

## Timing Recommendations

### When to Start a Conversation
- **Automatically** when first audio/text is sent
- No need to explicitly "start" - backend creates it automatically

### When to End a Conversation
Call `endConversation()` when:

```cpp
// 1. Inactivity timeout (30 seconds of silence)
unsigned long lastActivityTime = millis();
const unsigned long TIMEOUT_MS = 30000; // 30 seconds

void loop() {
  if (millis() - lastActivityTime > TIMEOUT_MS) {
    if (conversationActive) {
      endConversation();
      conversationActive = false;
    }
  }
}

// 2. User manually ends session
void onButtonPress() {
  if (conversationActive) {
    endConversation();
    conversationActive = false;
  }
}

// 3. Toy is turned off
void onPowerOff() {
  if (conversationActive) {
    endConversation();
  }
  // ... shutdown ...
}
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

// Global variables
String userId = "user_abc123";
String activeChildId = "child_xyz789";
String toyId = "toy_luno_001";
String sessionId = "";
bool conversationActive = false;
unsigned long lastActivityTime = 0;

void setup() {
  Serial.begin(115200);

  // Connect to WiFi
  WiFi.begin("SSID", "PASSWORD");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n[INFO] WiFi connected");

  // Generate initial session ID
  sessionId = generateNewSessionId();
}

void loop() {
  // Check for audio input
  if (audioDetected()) {
    uint8_t* audioData = recordAudio();
    size_t audioLength = getAudioLength();

    // Send to backend (automatically creates/continues conversation)
    sendAudioToBackend(audioData, audioLength);

    conversationActive = true;
    lastActivityTime = millis();
  }

  // Check for inactivity timeout
  if (conversationActive &&
      (millis() - lastActivityTime > 30000)) {
    Serial.println("[INFO] Inactivity timeout - ending conversation");
    endConversation();
    conversationActive = false;
  }

  delay(100);
}

String generateNewSessionId() {
  uint8_t mac[6];
  WiFi.macAddress(mac);
  char sid[64];
  sprintf(sid, "esp32_%02X%02X%02X_%lu",
          mac[3], mac[4], mac[5], millis());
  return String(sid);
}

void sendAudioToBackend(uint8_t* audioData, size_t audioLength) {
  HTTPClient http;
  http.begin("http://your-server.com:5005/upload");
  http.addHeader("Content-Type", "audio/adpcm");
  http.addHeader("X-Audio-Format", "adpcm");
  http.addHeader("X-Session-ID", sessionId);
  http.addHeader("X-User-ID", userId);
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
  doc["session_id"] = sessionId;
  String payload;
  serializeJson(doc, payload);

  int httpCode = http.POST(payload);
  if (httpCode == 200) {
    Serial.println("[INFO] Conversation ended");
    sessionId = generateNewSessionId(); // New session for next conversation
  }

  http.end();
}
```

## Testing Checklist

- [ ] Headers are included in all requests
- [ ] Session ID is unique and consistent within a conversation
- [ ] Session ID is regenerated after ending a conversation
- [ ] User/Child/Toy IDs match Firebase document IDs
- [ ] Conversation ends after inactivity
- [ ] Audio responses are played correctly
- [ ] Error cases are handled gracefully

## Common Issues

### Issue: "Missing user/child metadata" warning in logs
**Solution:** Ensure all headers (`X-User-ID`, `X-Child-ID`, etc.) are sent

### Issue: Multiple conversations created for same session
**Solution:** Use the same `session_id` for all requests in a conversation

### Issue: Stats not updating
**Solution:** Call `/api/conversations/end` when conversation finishes

---

**For more details, see:** `FIRESTORE_INTEGRATION_GUIDE.md`
