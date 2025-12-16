# How to Get Firebase Service Account Key

## Your Project Details

**Project ID**: `luno-companion-app-dev`
**Project Name**: Luno Companion App Dev

---

## Step-by-Step Instructions

### 1. Open Firebase Console

Go to: https://console.firebase.google.com/project/luno-companion-app-dev/settings/serviceaccounts/adminsdk

Or manually:
1. Visit: https://console.firebase.google.com/
2. Click on **luno-companion-app-dev** project

### 2. Navigate to Service Accounts

1. Click the **⚙️ gear icon** (top left)
2. Select **Project settings**
3. Go to **Service accounts** tab

### 3. Generate Private Key

1. You should see: **Firebase Admin SDK**
2. Click the button: **Generate new private key**
3. Confirm by clicking **Generate key**
4. A JSON file will download (e.g., `luno-companion-app-dev-xxxxx.json`)

### 4. Save the File

Rename and move it:
```bash
# Save as firebase-credentials.json in backend folder
mv ~/Downloads/luno-companion-app-dev-*.json /Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json
```

### 5. Set Environment Variable

Add to your shell profile (`~/.zshrc` or `~/.bashrc`):
```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json"
```

Or just run it in your terminal (temporary):
```bash
export FIREBASE_SERVICE_ACCOUNT_PATH="/Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json"
```

### 6. Restart Backend

```bash
cd /Users/rohankhan/Desktop/Luno/backend
source venv/bin/activate
python app.py
```

### 7. Verify Connection

You should see:
```
[INFO] Firebase initialized with service account: /Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json
[INFO] Firestore client initialized successfully
[INFO] Connected to project: luno-companion-app-dev
 * Running on http://127.0.0.1:5005
```

---

## Quick Test

### Test 1: Create Account
```bash
# Open simulator
http://localhost:5005/simulator.html

# Fill in Account Setup and click "Create Complete Account"
# Should now work without "Firestore unavailable" error!
```

### Test 2: Run Setup Script
```bash
cd /Users/rohankhan/Desktop/Luno/backend
python3 setup_test_data.py
```

Should output:
```
✓ Connected to Firestore
Creating test data with IDs...
✓ User created successfully
✓ Child created successfully
✓ Toy created successfully
```

---

## Security Checklist

- [ ] Downloaded service account JSON file
- [ ] Saved as `firebase-credentials.json`
- [ ] Added to `.gitignore` (to prevent committing)
- [ ] Set environment variable
- [ ] Tested backend connection

### Add to .gitignore

Create or update `.gitignore`:
```bash
# Firebase credentials
firebase-credentials.json
*-firebase-adminsdk-*.json

# Environment files
.env
.env.local

# Python
__pycache__/
*.pyc
venv/
```

---

## Alternative: Manual JSON Creation (Not Recommended)

If you can't access Firebase Console, ask your project admin to share the service account JSON with you securely.

**NEVER share this file publicly or commit it to Git!**

---

## Troubleshooting

### Error: "Failed to initialize Firebase"

**Solution**: Make sure the environment variable is set:
```bash
echo $FIREBASE_SERVICE_ACCOUNT_PATH
# Should output: /Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json
```

### Error: "Permission denied"

**Solution**: Check file permissions:
```bash
chmod 600 /Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json
```

### Error: "Project not found"

**Solution**: Make sure you're downloading the key from the correct project (`luno-companion-app-dev`)

---

## What This Enables

Once connected, you can:
- ✅ Create unlimited test accounts via simulator
- ✅ Test authentication end-to-end
- ✅ Store conversations in Firestore
- ✅ View data in Firebase Console
- ✅ Use the complete backend functionality

---

## Current Status

**Before Service Account Key**:
- Can only use existing test account: `test_user_1763434576`
- Cannot create new accounts
- Limited testing

**After Service Account Key**:
- Create unlimited test accounts
- Full Firestore access
- Complete backend functionality
- All simulator features work

---

## Quick Command Reference

```bash
# Download and setup (after getting the JSON file from Firebase Console)
mv ~/Downloads/luno-companion-app-dev-*.json /Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json

# Set environment variable
export FIREBASE_SERVICE_ACCOUNT_PATH="/Users/rohankhan/Desktop/Luno/backend/firebase-credentials.json"

# Start backend
cd /Users/rohankhan/Desktop/Luno/backend
source venv/bin/activate
python app.py

# Test
python3 setup_test_data.py
```

Done! 🎉
