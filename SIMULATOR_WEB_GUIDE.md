# Web Simulator with Authentication - Complete Guide

## Overview

The web simulator (simulator.html) has been fully updated with device authentication and account creation capabilities. You can now test the complete authentication workflow directly from your browser!

## What's New

### 1. **Authentication Fields Added**
- ✅ **Email** field in configuration
- ✅ **Device ID** field in configuration
- ✅ All requests now include `X-Email` and `X-Device-ID` headers

### 2. **Account Setup Section**
Create test accounts directly from the simulator:
- **Display Name**: Parent's name
- **Email**: User email (required for authentication)
- **Child Name**: Child's name
- **Toy Name**: Name for the toy device

### 3. **New Buttons**
- 🔐 **Test Authentication**: Verify your credentials work
- ✨ **Create Complete Account**: Creates user + child + toy in Firestore
- 🦄 **Add Toy to Existing Account**: Add additional toys to an account

## How to Use

### Step 1: Start the Backend

```bash
cd /Users/rohankhan/Desktop/Luno/backend
source venv/bin/activate
python app.py
```

### Step 2: Open the Simulator

Open in your browser:
```
http://localhost:5005/simulator.html
```

### Step 3: Create a Test Account

1. Fill in the **Account Setup** section:
   - Display Name: `Test Parent`
   - Email: `parent@example.com`
   - Child Name: `Alex`
   - Toy Name: `Luna`

2. Click **✨ Create Complete Account**

3. Watch the logs - you'll see:
   ```
   ✨ Creating complete account...
     User ID: user_1733445678
     Email: parent@example.com
     Child ID: child_1733445678
     Toy ID: toy_1733445678
   ✓ Account created successfully!
     Configuration updated with new account
     You can now test authentication!
   ```

4. The configuration fields automatically update with your new IDs!

### Step 4: Test Authentication

1. Click **🔐 Test Authentication**

2. You should see:
   ```
   🔐 Testing authentication...
   ✓ AUTHENTICATION SUCCESSFUL!
     User: user_1733445678
     Email: parent@example.com
     Device: Luna (toy_1733445678)
     Status: online
     Assigned to child: child_1733445678
   ```

### Step 5: Send Messages

Now you can send text or audio messages with full authentication:

1. Type a message: `Hello Luna!`
2. Click **📤 Send**
3. The message is authenticated and processed
4. Listen to the response!

## Configuration Fields

| Field | Description | Example |
|-------|-------------|---------|
| **User ID** | Parent user identifier | `user_1733445678` |
| **Email** | User email for authentication | `parent@example.com` |
| **Child ID** | Child identifier | `child_1733445678` |
| **Toy ID** | Toy/device identifier | `toy_1733445678` |
| **Device ID** | Physical device ID (MAC address) | `toy_1733445678` |
| **Backend URL** | Server URL | `http://localhost:5005` |

## Account Setup Fields

| Field | Purpose | Required |
|-------|---------|----------|
| **Display Name** | Parent's display name | Yes |
| **Email** | User email (for auth) | Yes |
| **Child Name** | Child's name | Yes |
| **Toy Name** | Name for the toy | Yes |

## New API Endpoints

### Create Complete Account
```http
POST /api/setup/create_account
Content-Type: application/json

{
  "user_id": "user_123",
  "email": "user@example.com",
  "display_name": "John Doe",
  "child_id": "child_456",
  "child_name": "Alex",
  "toy_id": "toy_789",
  "toy_name": "Luna"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Account created successfully",
  "user_id": "user_123",
  "child_id": "child_456",
  "toy_id": "toy_789"
}
```

### Add Toy to Account
```http
POST /api/setup/add_toy
Content-Type: application/json

{
  "user_id": "user_123",
  "toy_id": "toy_999",
  "toy_name": "Luna 2",
  "assigned_child_id": "child_456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Toy toy_999 added successfully",
  "toy_id": "toy_999",
  "user_id": "user_123"
}
```

## Testing Scenarios

### Scenario 1: Happy Path
1. Create account with valid data
2. Test authentication → ✓ Success
3. Send text message → ✓ Success
4. Send audio recording → ✓ Success

### Scenario 2: Wrong Email
1. Create account with `user@example.com`
2. Change email field to `wrong@example.com`
3. Test authentication → ✗ 403 Forbidden
4. Logs show: `Email does not match user account`

### Scenario 3: Wrong Device ID
1. Create account
2. Change device ID to `wrong_device`
3. Test authentication → ✗ 403 Forbidden
4. Logs show: `Device not associated with user account`

### Scenario 4: Add Additional Toy
1. Create account (gets toy_1)
2. Enter new toy ID: `toy_second`
3. Enter toy name: `Luna Junior`
4. Click **🦄 Add Toy to Existing Account**
5. Update device ID to `toy_second`
6. Test authentication → ✓ Success with new toy

## What Gets Created in Firestore

When you click **Create Complete Account**, the following is created:

### User Document
```
users/user_123/
├── uid: "user_123"
├── email: "user@example.com"  ← Used for authentication
├── displayName: "John Doe"
├── stats: { totalConversations: 0, ... }
└── preferences: { notifications: true, theme: "light" }
```

### Child Document
```
users/user_123/children/child_456/
├── name: "Alex"
├── ageLevel: "elementary"
├── contentFilterEnabled: true
└── alertTypes: { personalInfo: true, ... }
```

### Toy Document
```
users/user_123/toys/toy_789/
├── name: "Luna"
├── emoji: "🦄"
├── assignedChildId: "child_456"  ← Links toy to child
├── status: "online"
└── serialNumber: "SIM-toy_789"
```

## Authentication Flow in Simulator

```
User clicks "Send Text" or "Send Audio"
    ↓
JavaScript gets values from form:
  - User ID
  - Email       ← NEW
  - Device ID   ← NEW
  - Child ID
  - Toy ID
    ↓
Headers sent to backend:
  X-User-ID: user_123
  X-Email: user@example.com      ← NEW
  X-Device-ID: toy_789           ← NEW
  X-Child-ID: child_456
  X-Toy-ID: toy_789
  X-Session-ID: esp32_web_...
    ↓
Backend auth_middleware validates:
  1. Email matches user document
  2. Device exists in user's toys
    ↓
  ✓ Valid → Process request
  ✗ Invalid → Return 400/403/404
```

## Logs to Watch For

### Successful Authentication
```
🔐 Testing authentication...
✓ AUTHENTICATION SUCCESSFUL!
  User: user_1733445678
  Email: parent@example.com
  Device: Luna (toy_1733445678)
  Status: online
  Assigned to child: child_1733445678
```

### Failed Authentication
```
🔐 Testing authentication...
✗ AUTHENTICATION FAILED (403)
  Error: Email does not match user account
```

### Account Creation
```
✨ Creating complete account...
  User ID: user_1733445678
  Email: parent@example.com
  Child ID: child_1733445678
  Toy ID: toy_1733445678
✓ Account created successfully!
  Configuration updated with new account
  You can now test authentication!
```

### Message Sent
```
📤 Sending text: "Hello Luna!"
✓ Response received (2.34s)
  Total: 2.34s | GPT: 1.2s | TTS: 1.1s
```

## Troubleshooting

### "Authentication failed: Missing X-Email header"
**Fix**: Make sure the Email field is filled in the Configuration section

### "Authentication failed: Email does not match user account"
**Fix**: The email in the config must match the email stored in Firestore for that user

### "Account created successfully" but authentication still fails
**Fix**: Click the **🔄 New Session** button to reload the configuration

### Can't connect to backend
**Fix**: Make sure the backend is running on port 5005:
```bash
cd /Users/rohankhan/Desktop/Luno/backend
source venv/bin/activate
python app.py
```

## Comparison: Python Simulator vs Web Simulator

| Feature | Python Simulator | Web Simulator |
|---------|-----------------|---------------|
| Audio Recording | ✅ Real microphone | ✅ Real microphone |
| Authentication | ✅ Headers included | ✅ Headers included |
| Account Creation | ❌ Manual via script | ✅ Built-in UI |
| Test Auth | ✅ Menu option #7 | ✅ Button |
| Configuration | ✅ JSON + Menu | ✅ Form fields |
| Visual Logs | ❌ Terminal only | ✅ Beautiful UI |
| Ease of Use | Medium | Easy |

## Next Steps

After testing in the web simulator, you can:

1. **Use Python Simulator**: For more advanced testing with menu options
2. **Implement in ESP32**: Use the same authentication headers in your ESP32 firmware
3. **Run Test Suite**: `python3 test_auth_workflow.py` for automated testing

## Quick Test Checklist

- [ ] Open simulator in browser
- [ ] Create new account
- [ ] Test authentication (should succeed)
- [ ] Send text message
- [ ] Change email to wrong value
- [ ] Test authentication (should fail)
- [ ] Restore correct email
- [ ] Add second toy to account
- [ ] Test with new toy ID

## Summary

The web simulator now provides a complete testing environment for:
- ✅ Creating test accounts with email
- ✅ Adding toys to accounts
- ✅ Testing authentication
- ✅ Sending authenticated messages
- ✅ Visual feedback for all operations

All changes are persistent in Firestore, so you can test the same accounts across different simulators (Python and Web)!
