# Quick Simulator Setup Fix

## Issue: "Firestore unavailable" Error

If you see this error when trying to create an account in the simulator, it means Firebase/Firestore credentials are not set up yet.

## Solution: Use Existing Test Account

The easiest way to test authentication **right now** is to use the existing test account that was created earlier:

### Step 1: Open the Simulator

```bash
# Start backend (if not running)
cd /Users/rohankhan/Desktop/Luno/backend
source venv/bin/activate
python app.py
```

Open in browser: `http://localhost:5005/simulator.html`

### Step 2: Use Existing Test Account

In the **Configuration** section, enter these values:

```
User ID:   test_user_1763434576
Email:     test@lunotoys.com
Child ID:  test_child_1763434576
Toy ID:    test_toy_1763434576
Device ID: test_toy_1763434576
```

### Step 3: Test Authentication

Click **🔐 Test Authentication**

You should see:
```
✓ AUTHENTICATION SUCCESSFUL!
  User: test_user_1763434576
  Email: test@lunotoys.com
  Device: Luna Test (test_toy_1763434576)
  Status: online
  Assigned to child: test_child_1763434576
```

### Step 4: Send Messages

Now you can:
1. Type a message: "Hello Luna!"
2. Click **📤 Send**
3. Get an authenticated response!

---

## Alternative: Initialize Firestore (For Creating New Accounts)

If you want to create your own accounts (not just use the existing test account), you need to initialize Firestore:

### Option 1: Run Setup Script

```bash
cd /Users/rohankhan/Desktop/Luno/backend
source venv/bin/activate
python3 setup_test_data.py
```

This will:
- Initialize Firebase credentials
- Create test user/child/toy in Firestore
- Update simulator_config.json

### Option 2: Set Up Firebase Credentials

If you have Firebase credentials:

```bash
# Set environment variable
export FIREBASE_SERVICE_ACCOUNT_PATH="/path/to/your/serviceAccountKey.json"

# Or use the JSON directly
export FIREBASE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
```

Then restart the backend:
```bash
python app.py
```

---

## Summary

**Quick Test (No Setup Required):**
- Use existing account: `test_user_1763434576` with email `test@lunotoys.com`
- Works immediately for testing authentication

**Create New Accounts (Requires Setup):**
- Run `python3 setup_test_data.py`
- Or set up Firebase credentials
- Then you can create unlimited test accounts via the simulator

---

## Troubleshooting

### Error: "Email does not match user account"

Make sure the email field matches what's in Firestore:
- Existing test account uses: `test@lunotoys.com`

### Error: "Device not associated with user account"

Make sure device_id matches a toy in that user's account:
- For test account, use: `test_toy_1763434576`

### Error: "Firestore not initialized"

Either:
1. Use the existing test account (no setup needed), OR
2. Run `python3 setup_test_data.py` to initialize Firestore

---

## Working Example

```
Configuration Section:
├─ User ID:   test_user_1763434576
├─ Email:     test@lunotoys.com        ← Must match Firestore
├─ Child ID:  test_child_1763434576
├─ Toy ID:    test_toy_1763434576
└─ Device ID: test_toy_1763434576      ← Must exist in user's toys

Click "Test Authentication" → ✓ Success!
Type "Hello" → Click "Send" → Get response!
```

---

## What Was Fixed

### Fix 1: Email Field Now Visible ✅
- Email field is now in the **Account Setup** section
- Clearly marked with asterisk (*) to show it's required

### Fix 2: Better Error Messages ✅
- Shows clear error when Firestore is not initialized
- Provides hint to use existing test account
- Displays instructions for setup

Both issues are now resolved!
