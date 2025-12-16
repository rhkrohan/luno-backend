# Firebase Backend Setup Guide

## Important: Client vs Server Credentials

The Firebase config you have is for **client-side apps** (web/React Native):
```typescript
const firebaseConfig = {
  apiKey: "AIzaSyA3Lf7ydukXAo0UWdXwSo4mVVWB8r4DNGs",
  authDomain: "luno-companion-app-dev.firebaseapp.com",
  projectId: "luno-companion-app-dev",
  // ... other client keys
};
```

For the **backend (Python)**, you need a **Service Account Key** (different credentials).

## How to Get Service Account Key

### Step 1: Go to Firebase Console

1. Visit: https://console.firebase.google.com/
2. Select your project: **luno-companion-app-dev**

### Step 2: Generate Service Account Key

1. Click the **gear icon** ⚙️ (Settings) → **Project settings**
2. Go to **Service accounts** tab
3. Click **Generate new private key**
4. Click **Generate key** → Downloads a JSON file

### Step 3: Save the JSON File

Save it as:
```bash
/Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json
```

**IMPORTANT**: Add to `.gitignore` to keep it secret!

### Step 4: Set Environment Variable

Option A - In your terminal:
```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json"
```

Option B - Create `.env` file:
```bash
# /Users/rohankhan/Desktop/Luno/backend/.env
FIREBASE_SERVICE_ACCOUNT_PATH=/Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json
```

### Step 5: Restart Backend

```bash
cd /Users/rohankhan/Desktop/Luno/backend
source venv/bin/activate
python app.py
```

You should see:
```
[INFO] Firebase initialized with service account: /Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json
[INFO] Firestore client initialized successfully
```

---

## Alternative: Quick Test Without Service Account

If you can't get the service account key right now, you can still test with the existing test data:

### Option 1: Use Existing Test Account (Immediate)

The test account is already in Firestore:
```
User ID:   test_user_1763434576
Email:     test@lunotoys.com
Child ID:  test_child_1763434576
Toy ID:    test_toy_1763434576
```

Just use these values in the simulator!

### Option 2: Run Setup Script (If Credentials Available)

```bash
python3 setup_test_data.py
```

This will create test data if Firestore is accessible.

---

## What the Service Account JSON Looks Like

```json
{
  "type": "service_account",
  "project_id": "luno-companion-app-dev",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "firebase-adminsdk-xxxxx@luno-companion-app-dev.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "...",
  "universe_domain": "googleapis.com"
}
```

This is different from the client-side config and gives the backend full admin access to Firestore.

---

## Security Notes

⚠️ **Never commit service account keys to Git!**

Add to `.gitignore`:
```
# .gitignore
firebase-credentials.json
*.json
!package.json
!tsconfig.json
```

✅ **Use environment variables in production:**
```bash
export FIREBASE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
```

---

## Current Backend Configuration

The backend (`firebase_config.py`) supports 3 methods:

1. **Service Account File** (recommended):
   ```bash
   export FIREBASE_SERVICE_ACCOUNT_PATH="path/to/credentials.json"
   ```

2. **Service Account JSON String** (for production):
   ```bash
   export FIREBASE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
   ```

3. **Application Default Credentials** (local development):
   ```bash
   gcloud auth application-default login
   ```

---

## Testing the Connection

After setting up credentials:

### Test 1: Backend Logs
Start the backend and look for:
```
[INFO] Firebase initialized with service account
[INFO] Firestore client initialized successfully
```

### Test 2: Create Account in Simulator
1. Open: http://localhost:5005/simulator.html
2. Fill in Account Setup fields
3. Click "✨ Create Complete Account"
4. Should see: "✓ Account created successfully!"

### Test 3: Python Script
```bash
python3 setup_test_data.py
```

Should output:
```
✓ Connected to Firestore
Creating test data with IDs:
  User:  test_user_123456789
  Child: test_child_123456789
  Toy:   test_toy_123456789
✓ User created successfully
✓ Child created successfully
✓ Toy created successfully
```

---

## Quick Summary

**What you have**: Client-side Firebase config (for web/mobile apps)
**What you need**: Service account key (for backend Python app)

**How to get it**:
1. Firebase Console → Project Settings → Service Accounts
2. Generate new private key
3. Save as `firebase-credentials.json`
4. Set `FIREBASE_SERVICE_ACCOUNT_PATH` environment variable
5. Restart backend

**Then you can**:
- Create unlimited test accounts via simulator
- Test authentication end-to-end
- Store conversations in Firestore

---

## Need Help?

If you don't have access to the Firebase Console:
1. Ask your Firebase project admin to generate the service account key
2. Or continue using the existing test account for now: `test_user_1763434576`
