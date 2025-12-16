#!/bin/bash

echo "🚀 Starting Luno Backend..."
echo ""

# Check if Firebase key exists
if [ ! -f "firebase-key.json" ]; then
    echo "❌ Firebase service account key not found!"
    echo ""
    echo "Please download your Firebase service account key:"
    echo "1. Go to: https://console.firebase.google.com/project/luno-companion-app-dev/settings/serviceaccounts"
    echo "2. Click 'Generate new private key'"
    echo "3. Save it as: firebase-key.json in this directory"
    echo ""
    echo "Or set FIREBASE_SERVICE_ACCOUNT_PATH environment variable."
    echo ""
    exit 1
fi

# Set Firebase path
export FIREBASE_SERVICE_ACCOUNT_PATH="$(pwd)/firebase-key.json"
echo "✓ Firebase key found: firebase-key.json"

# Check for API keys
if [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  OPENAI_API_KEY not set"
    echo "   Set it with: export OPENAI_API_KEY='sk-proj-...'"
    echo ""
fi

if [ -z "$ELEVENLABS_API_KEY" ]; then
    echo "⚠️  ELEVENLABS_API_KEY not set"
    echo "   Set it with: export ELEVENLABS_API_KEY='...'"
    echo ""
fi

# Start the backend
echo ""
echo "Starting Flask backend on port 5005..."
echo ""
python app.py
