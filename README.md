# Luno Toys Backend & Firestore Integration

**Complete system documentation for the Luno interactive toy companion platform**

> **Google Cloud AI Hackathon 2024** - Reimagining childhood play with AI-powered physical companions

---
<img width="2545" height="1430" alt="image" src="https://github.com/user-attachments/assets/5c4469c6-dcce-4d9a-ab13-caa19c90e364" />


## The Problem

In today's digital age, **children are spending unprecedented amounts of time on screens** - tablets, phones, and computers - leading to decreased physical activity, reduced face-to-face interactions, and growing concerns about developmental impacts. Parents struggle with:

- **Limited alternatives**: Most "smart" toys are still screen-based or lack meaningful AI interaction
- **Safety concerns**: Existing AI companions lack proper content moderation and parental oversight
- **Lost conversations**: Parents have no visibility into what their children talk about, learn, or are curious about
- **Passive consumption**: Digital content promotes passive watching rather than active conversation and critical thinking

**The core challenge**: How do we create an engaging, educational AI companion that keeps children away from screens while ensuring their safety and giving parents peace of mind?

---

## Our Solution

**Luno Toys** is a safety-first, AI-powered physical toy companion platform that combines hardware, cloud AI, and parental oversight to create a new category of interactive play.

### What Makes Luno Different

**Physical-First Design**
Real ESP32-powered toys that children can hold, hug, and interact with naturally - no screens required. The physical presence creates emotional connections that purely digital assistants cannot replicate.

**Google Cloud-Powered Intelligence**
- **Cloud Firestore**: Real-time conversation storage, user management, and scalable data architecture
- **AI Conversations**: Natural language processing for engaging, age-appropriate dialogues
- **Knowledge Graph**: Personalized learning powered by Firestore's graph-like subcollections, tracking each child's interests, skills, and developmental milestones

**Safety-First Architecture**
- Real-time content moderation with automatic flagging for inappropriate content, personal information sharing, and emotional distress indicators
- Comprehensive parent dashboard built on Firestore's real-time sync capabilities
- Severity-based alert system (Critical/High/Medium) with immediate notifications
- Complete conversation transcripts and analytics

**Privacy & Monitoring**
Parents get unprecedented visibility through:
- Real-time conversation monitoring via Firestore listeners
- Usage analytics and engagement metrics
- Safety alerts for flagged conversations
- Multi-child support with personalized profiles

### Key Innovations

**Hardware-Cloud Integration**: Seamless ESP32-to-Google Cloud pipeline with ADPCM audio compression, optimized for low-latency interactions

**Intelligent Knowledge Graphs**: Built on Firestore subcollections (`users/{id}/children/{id}/entities/` and `edges/`), creating personalized learning graphs that grow with each conversation

**Scalable Architecture**: Firestore's document model allows independent scaling of users, children, conversations, and messages with efficient cost management (array-based message storage reduces write operations by 67%)

**Real-time Safety**: Every message is analyzed and flagged in real-time, with updates pushed to parents instantly through Firestore's live listeners

---

## Google Cloud Technologies

**Cloud Firestore (Primary Database)**
- User authentication and management
- Real-time conversation storage with subcollections
- Knowledge graph entities and edges
- Parent dashboard data sync
- Scalable to millions of conversations

**Architecture Benefits**
- **NoSQL Flexibility**: Dynamically structured conversations, varied child profiles, and extensible knowledge graphs
- **Real-time Sync**: Parents see conversations as they happen via Firestore listeners
- **Offline Support**: Firestore SDK enables offline-first mobile apps for parents
- **Security Rules**: Fine-grained access control ensuring parents only see their own data
- **Scalability**: Auto-scaling serverless architecture built for growth

---

## 📋 Table of Contents

1. [System Overview](#system-overview)
2. [Architecture](#architecture)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Setup & Installation](#setup--installation)
6. [Configuration](#configuration)
7. [Backend Services](#backend-services)
8. [Frontend Integration](#frontend-integration)
9. [Data Flow](#data-flow)
10. [API Reference](#api-reference)
11. [Security](#security)
12. [Testing](#testing)
13. [Deployment](#deployment)
14. [Troubleshooting](#troubleshooting)

---

## 🎯 System Overview

Luno Toys is an interactive AI-powered companion platform that enables children to have natural conversations with physical toy devices (ESP32-based). The system consists of:

- **ESP32 Hardware Toys** - Physical devices with audio input/output
- **Flask Backend** - Python server handling STT, GPT, TTS, and Firestore integration
- **React Frontend** - Mobile/web app for parents to manage toys, children, and monitor conversations
- **Firebase/Firestore** - Cloud database for user data, conversations, messages, and stats

### Key Features

✅ **Real-time Conversations** - ESP32 toys communicate with AI backend
✅ **Conversation Tracking** - All conversations saved to Firestore automatically
✅ **Safety Monitoring** - Content moderation with automatic flagging
✅ **Parent Dashboard** - View conversation history, stats, and safety alerts
✅ **Multi-Child Support** - Each toy can be assigned to different children
✅ **Session Management** - Track active conversations with auto-timeout
✅ **Analytics & Stats** - Track usage, duration, and engagement metrics

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         LUNO PLATFORM                            │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐         ┌──────────────┐         ┌──────────────┐
│   ESP32 Toy  │◄───────►│Flask Backend │◄───────►│  Firestore   │
│              │  HTTP   │              │  Admin  │   Database   │
│  - Audio I/O │         │  - STT (AI)  │   SDK   │              │
│  - WiFi      │         │  - GPT-4     │         │ - Users      │
│  - Session   │         │  - TTS (AI)  │         │ - Children   │
└──────────────┘         │  - Firestore │         │ - Toys       │
                         └──────────────┘         │ - Convos     │
                                │                 │ - Messages   │
                                │                 └──────────────┘
                                │                        ▲
                         ┌──────────────┐               │
                         │React Frontend│               │
                         │              │               │
                         │ - Auth UI    │───────────────┘
                         │ - Dashboard  │   Client SDK
                         │ - Analytics  │
                         │ - Settings   │
                         └──────────────┘
```

### Component Responsibilities

| Component | Responsibility | Technology |
|-----------|---------------|------------|
| **ESP32 Toy** | Audio capture, playback, WiFi communication | C++/Arduino |
| **Flask Backend** | Audio processing, AI services, Firestore writes | Python 3.12 |
| **React Frontend** | User management, conversation viewing | React + TypeScript |
| **Firestore** | Data persistence, real-time sync | Google Cloud Firestore |
| **Firebase Auth** | User authentication, authorization | Firebase Authentication |

---

## 🛠️ Technology Stack

### Backend (Python)
- **Flask 2.3.3** - Web framework
- **OpenAI API** - GPT-4 (conversations), Whisper (STT)
- **ElevenLabs API** - Text-to-speech synthesis
- **Firebase Admin SDK 6.0+** - Firestore database access
- **Gunicorn 21.2** - WSGI server for production

### Frontend (React)
- **React 18+** - UI framework
- **TypeScript** - Type safety
- **Firebase Client SDK** - Authentication & Firestore access
- **React Context API** - State management

### Database
- **Cloud Firestore** - NoSQL document database
- **Firebase Authentication** - User management
- **Firebase Storage** - (Future) Audio/media storage

### Hardware
- **ESP32** - WiFi-enabled microcontroller
- **ADPCM Audio Codec** - Compressed audio transmission

---

## 📁 Project Structure

```
luno-platform/
├── backend/                          # Flask Backend
│   ├── app.py                        # Main Flask application
│   ├── firebase_config.py            # Firebase Admin SDK setup
│   ├── firestore_service.py          # Firestore operations service
│   ├── gpt_reply.py                  # GPT conversation logic
│   ├── whisper_stt.py                # Speech-to-text service
│   ├── tts_elevenlabs.py             # Text-to-speech service
│   ├── requirements.txt              # Python dependencies
│   ├── README.md                     # This file
│   └── docs/                         # Documentation
│       ├── QUICK_START.md
│       ├── SETUP.md
│       ├── AUTHENTICATION.md
│       ├── SIMULATOR_GUIDE.md
│       ├── ESP32_INTEGRATION_EXAMPLE.md
│       └── DOCS_SUMMARY.md
│
├── frontend/                         # React Frontend
│   ├── src/
│   │   ├── lib/
│   │   │   └── firebase.ts           # Firebase client config
│   │   ├── contexts/
│   │   │   └── AuthContext.tsx       # Auth state management
│   │   ├── components/               # React components
│   │   └── pages/                    # App pages
│   ├── package.json
│   └── tsconfig.json
│
└── esp32/                            # (Separate repo)
    └── main.cpp                      # ESP32 firmware
```

---

## 🚀 Setup & Installation

### Prerequisites

- **Python 3.12+** installed
- **Node.js 18+** and npm installed
- **Firebase Project** created (console.firebase.google.com)
- **OpenAI API Key** (platform.openai.com)
- **ElevenLabs API Key** (elevenlabs.io)

### Backend Setup

#### 1. Clone and Navigate

```bash
cd backend
```

#### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

Create a `.env` file:

```bash
# OpenAI
OPENAI_API_KEY=sk-proj-...

# ElevenLabs
ELEVENLABS_API_KEY=...

# Firebase (choose one method)
FIREBASE_SERVICE_ACCOUNT_PATH=/path/to/serviceAccountKey.json
# OR
FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'

# Server
PORT=5005
```

#### 5. Get Firebase Service Account Key

1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate New Private Key"
3. Save the JSON file and set `FIREBASE_SERVICE_ACCOUNT_PATH`

#### 6. Run the Server

```bash
# Development
python app.py

# Production
gunicorn -c config/gunicorn.conf.py app:app
```

Backend will be available at: `http://localhost:5005`

### Frontend Setup

#### 1. Navigate to Frontend

```bash
cd frontend
```

#### 2. Install Dependencies

```bash
npm install
```

#### 3. Configure Firebase

Update `src/lib/firebase.ts` with your Firebase config:

```typescript
const firebaseConfig = {
  apiKey: "YOUR_API_KEY",
  authDomain: "YOUR_PROJECT.firebaseapp.com",
  projectId: "YOUR_PROJECT_ID",
  storageBucket: "YOUR_PROJECT.firebasestorage.app",
  messagingSenderId: "YOUR_SENDER_ID",
  appId: "YOUR_APP_ID",
};
```

#### 4. Run Development Server

```bash
npm run dev
```

Frontend will be available at: `http://localhost:5173` (or configured port)

---

## ⚙️ Configuration

### Firebase Security Rules

Configure Firestore security rules:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {

    // Users can only read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;

      // Children subcollection
      match /children/{childId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;

        // Knowledge graph subcollections under children
        match /entities/{entityId} {
          allow read, write: if request.auth != null && request.auth.uid == userId;
        }
        match /edges/{edgeId} {
          allow read, write: if request.auth != null && request.auth.uid == userId;
        }
      }

      // Conversations are directly under users (NOT under children)
      // Messages stored as array field within conversation document
      match /conversations/{conversationId} {
        allow read: if request.auth != null && request.auth.uid == userId;
        allow write: if request.auth != null && request.auth.uid == userId;
      }

      // Toys subcollection
      match /toys/{toyId} {
        allow read, write: if request.auth != null && request.auth.uid == userId;
      }
    }
  }
}
```

**Note:**
- Backend uses Firebase Admin SDK which bypasses these rules. Frontend clients must follow them.
- **Messages are stored as an array field** (`messages[]`) within conversation documents, not as a subcollection.
- Conversations are at `users/{userId}/conversations/` with a `childId` field, not nested under children.

### Backend Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | ✅ | OpenAI API key for GPT & Whisper |
| `ELEVENLABS_API_KEY` | ✅ | ElevenLabs API key for TTS |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | ✅* | Path to Firebase service account JSON |
| `FIREBASE_SERVICE_ACCOUNT_JSON` | ✅* | Or JSON string of service account |
| `PORT` | ❌ | Server port (default: 5005) |

*Choose one Firebase auth method

---

## 🔧 Backend Services

### 1. Firebase Configuration (`firebase_config.py`)

Initializes Firebase Admin SDK with multiple auth methods:

```python
from firebase_config import initialize_firebase, get_firestore_client

# Initialize on startup
db = initialize_firebase()

# Or get client anywhere
db = get_firestore_client()
```

**Features:**
- Auto-initialization on import
- Support for service account JSON file or string
- Graceful degradation if unavailable

### 2. Firestore Service (`firestore_service.py`)

Complete CRUD operations for conversations and messages:

```python
from firestore_service import firestore_service

# Create conversation
# Stored at: users/{user_id}/conversations/{conv_id}
conv_id = firestore_service.create_conversation(
    user_id="user123",
    child_id="child456",
    toy_id="toy789"
)

# Add message
# Messages stored as array field using ArrayUnion (1 write per message)
firestore_service.add_message(
    user_id="user123",
    conversation_id=conv_id,
    sender="child",
    content="Hello Luna!"
)

# End conversation
firestore_service.end_conversation(
    user_id="user123",
    conversation_id=conv_id,
    duration_minutes=15
)
```

**Features:**
- **Array-based message storage** - Messages stored as array field, not subcollection (67% cost reduction)
- Automatic conversation creation at `users/{userId}/conversations/`
- Message safety checking with automatic flagging
- Content moderation (personal info, inappropriate content, emotional distress)
- User stats tracking
- Query operations for frontend
- 150 message cap per conversation with array-based storage

### 3. GPT Reply Service (`gpt_reply.py`)

Handles AI conversation logic with memory:

```python
from gpt_reply import get_gpt_reply

reply = get_gpt_reply(
    user_text="What's your favorite color?",
    session_id="esp32_session_123",
    user_id="user123",
    child_id="child456",
    conversation_id="conv_abc"
)
```

**Features:**
- In-memory conversation history (last 6 messages)
- Automatic Firestore message saving
- Child-friendly Luna character prompt
- GPT-4 powered responses

### 4. Main Application (`app.py`)

Flask routes for ESP32 communication and API:

#### ESP32 Routes
- `POST /upload` - Audio upload (ADPCM/WAV)
- `POST /text_upload` - Text upload (local STT)
- `GET /wakeup` - Get wakeup audio
- `GET /audios` - List filler audio files
- `GET /audio/<filename>` - Serve filler audio

#### API Routes
- `POST /api/conversations/end` - End conversation
- `GET /api/conversations/{id}` - Get conversation
- `GET /api/conversations/{id}/messages` - Get messages
- `GET /api/children/{childId}/conversations` - List conversations
- `PUT /api/conversations/{id}/flag` - Update flag status
- `GET /api/users/{userId}/stats` - Get user stats

---

## 💻 Frontend Integration

### Authentication Context (`AuthContext.tsx`)

Manages user authentication state:

```tsx
import { useAuth } from '@/contexts/AuthContext';

function MyComponent() {
  const { currentUser, login, logout, signup } = useAuth();

  // Login
  await login(email, password);

  // Signup with Firestore user creation
  await signup(email, password, displayName);

  // Google Sign-In
  await googleSignIn();
}
```

**User Document Created on Signup:**
```javascript
{
  uid: "user123",
  email: "parent@example.com",
  displayName: "John Doe",
  createdAt: "2024-01-15T10:30:00Z",
  toys: [],
  preferences: {
    notifications: true,
    theme: "light"
  },
  stats: {
    totalConversations: 0,
    totalConversationDurationSec: 0,
    flaggedConversations: 0,
    lastConversationAt: null,
    lastFlaggedAt: null
  }
}
```

### Firebase Configuration (`firebase.ts`)

```typescript
import { db, auth, storage } from '@/lib/firebase';
import { collection, query, where, getDocs } from 'firebase/firestore';

// Example: Get child's conversations
// Conversations are at users/{userId}/conversations/ with childId as a field
const conversationsRef = collection(
  db,
  'users',
  userId,
  'conversations'
);

const q = query(
  conversationsRef,
  where('childId', '==', childId),
  where('flagged', '==', true),
  orderBy('createdAt', 'desc'),
  limit(50)
);

const snapshot = await getDocs(q);
const conversations = snapshot.docs.map(doc => ({
  id: doc.id,
  ...doc.data()
}));

// Note: Messages are in the messages[] array field within each conversation document
// Access them via: conversation.messages (not a subcollection)
```

### Example: Conversation Viewer Component

```tsx
import { useEffect, useState } from 'react';
import { collection, query, orderBy, onSnapshot } from 'firebase/firestore';
import { db } from '@/lib/firebase';
import { useAuth } from '@/contexts/AuthContext';

function ConversationViewer({ childId }: { childId: string }) {
  const { currentUser } = useAuth();
  const [conversations, setConversations] = useState([]);

  useEffect(() => {
    if (!currentUser) return;

    // Conversations are directly under users, filter by childId field
    const conversationsRef = collection(
      db,
      'users',
      currentUser.uid,
      'conversations'
    );

    const q = query(
      conversationsRef,
      where('childId', '==', childId),
      orderBy('createdAt', 'desc')
    );

    // Real-time subscription
    const unsubscribe = onSnapshot(q, (snapshot) => {
      const convos = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));
      setConversations(convos);
    });

    return () => unsubscribe();
  }, [currentUser, childId]);

  return (
    <div>
      {conversations.map(conv => (
        <div key={conv.id}>
          <h3>{conv.title}</h3>
          <p>Duration: {conv.duration} minutes</p>
          <p>Messages: {conv.messages?.length || 0}</p>
          {conv.flagged && <span>⚠️ Flagged</span>}
        </div>
      ))}
    </div>
  );
}
```

### Example: Safety Center Component

```tsx
import { collection, query, where, getDocs } from 'firebase/firestore';
import { db } from '@/lib/firebase';
import { useAuth } from '@/contexts/AuthContext';

function SafetyCenter() {
  const { currentUser } = useAuth();
  const [flaggedConversations, setFlaggedConversations] = useState([]);

  useEffect(() => {
    if (!currentUser) return;

    // Get all flagged conversations across all children
    const fetchFlagged = async () => {
      // Conversations are directly under users with childId field
      const conversationsRef = collection(
        db,
        'users',
        currentUser.uid,
        'conversations'
      );

      const q = query(
        conversationsRef,
        where('flagged', '==', true),
        where('flagStatus', '==', 'unreviewed')
      );

      const snapshot = await getDocs(q);
      const flagged = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }));

      setFlaggedConversations(flagged);
    };

    fetchFlagged();
  }, [currentUser]);

  const markAsReviewed = async (conversationId: string) => {
    const response = await fetch(
      `http://localhost:5005/api/conversations/${conversationId}/flag`,
      {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: currentUser.uid,
          flag_status: 'reviewed'
        })
      }
    );

    if (response.ok) {
      // Refresh list
      fetchFlagged();
    }
  };

  return (
    <div>
      <h2>Safety Center - Flagged Conversations</h2>
      {flaggedConversations.map(conv => (
        <div key={conv.id} className="alert">
          <h3>{conv.childName} - {conv.title}</h3>
          <p><strong>Reason:</strong> {conv.flagReason}</p>
          <p><strong>Severity:</strong> {conv.severity}</p>
          <p><strong>Preview:</strong> {conv.messagePreview}</p>
          <button onClick={() => markAsReviewed(conv.id)}>
            Mark as Reviewed
          </button>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔄 Data Flow

### Complete Conversation Flow

```
1. PARENT SETUP (Frontend)
   ├─ Parent signs up → Creates user document in Firestore
   ├─ Parent adds child → Creates child document
   └─ Parent pairs toy → Creates toy document with assignedChildId

2. ESP32 TOY STARTS CONVERSATION
   ├─ Child speaks to toy
   ├─ ESP32 records audio (ADPCM)
   ├─ ESP32 sends HTTP POST to /upload with headers:
   │  ├─ X-Session-ID: esp32_abc123
   │  ├─ X-User-ID: user_xyz789
   │  ├─ X-Child-ID: child_def456
   │  └─ X-Toy-ID: toy_ghi789
   └─ Backend receives request

3. BACKEND PROCESSING
   ├─ Checks for existing conversation for session_id
   ├─ If none exists:
   │  └─ Creates new conversation document in Firestore
   │     Path: users/{userId}/conversations/{convId}
   │     (Note: childId stored as field, not in path)
   ├─ Decompresses ADPCM audio → WAV
   ├─ Sends to OpenAI Whisper API → Transcription
   ├─ Saves child message to Firestore using ArrayUnion
   │  Messages stored as array: .../conversations/{convId}.messages[]
   │  ├─ Safety check runs
   │  └─ Flags conversation if issues detected
   ├─ Sends to GPT-4 with conversation history → AI Reply
   ├─ Saves toy message to Firestore using ArrayUnion
   ├─ Sends to ElevenLabs → TTS Audio (WAV)
   └─ Returns audio to ESP32

4. ESP32 PLAYS RESPONSE
   ├─ Receives WAV audio
   ├─ Plays through speaker
   └─ Waits for next input

5. CONVERSATION CONTINUES (Steps 2-4 repeat)
   └─ Each message pair saved to Firestore

6. CONVERSATION ENDS
   ├─ ESP32 detects inactivity timeout (30s)
   ├─ Calls POST /api/conversations/end
   ├─ Backend:
   │  ├─ Calculates duration
   │  ├─ Updates conversation:
   │  │  ├─ endTime
   │  │  ├─ duration
   │  │  └─ messageCount
   │  └─ Updates user stats:
   │     ├─ totalConversations++
   │     ├─ totalConversationDurationSec += duration
   │     ├─ flaggedConversations++ (if flagged)
   │     └─ lastConversationAt = now
   └─ ESP32 generates new session_id for next conversation

7. PARENT VIEWS DATA (Frontend)
   ├─ Frontend queries Firestore directly (Client SDK)
   ├─ Real-time listeners for conversations
   ├─ Dashboard shows:
   │  ├─ Recent conversations
   │  ├─ Usage stats
   │  ├─ Flagged content alerts
   │  └─ Message transcripts
   └─ Security rules ensure parent only sees their own data
```

---

## 📚 API Reference

### ESP32 Communication

#### `POST /upload`

Upload audio from ESP32 (server-side STT).

**Headers:**
```
Content-Type: audio/adpcm
X-Audio-Format: adpcm
X-Session-ID: esp32_session_123
X-User-ID: user_abc
X-Child-ID: child_xyz
X-Toy-ID: toy_def
```

**Body:** Binary audio data (ADPCM or WAV)

**Response:**
```
Content-Type: audio/wav
X-Response-Time: 3.45
X-STT-Time: 1.20
X-GPT-Time: 1.15
X-TTS-Time: 1.10

[WAV audio binary data]
```

#### `POST /text_upload`

Send transcribed text from ESP32 (local STT).

**Headers:**
```
Content-Type: application/json
X-User-ID: user_abc
X-Child-ID: child_xyz
X-Toy-ID: toy_def
```

**Body:**
```json
{
  "text": "What's the weather like?",
  "session_id": "esp32_session_123",
  "user_id": "user_abc",
  "child_id": "child_xyz",
  "toy_id": "toy_def"
}
```

**Response:** Same as `/upload` (audio/wav)

### Conversation Management

#### `POST /api/conversations/end`

End an active conversation session.

**Request:**
```json
{
  "session_id": "esp32_session_123"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Conversation ended for session esp32_session_123"
}
```

#### `GET /api/conversations/{conversation_id}`

Get conversation details.

**Query Parameters:**
- `user_id` (required)

**Response:**
```json
{
  "success": true,
  "conversation": {
    "startTime": "2024-01-15T10:30:00Z",
    "endTime": "2024-01-15T10:45:00Z",
    "duration": 15,
    "type": "conversation",
    "title": "Math Adventure",
    "messageCount": 12,
    "childId": "child_xyz",
    "childName": "Emma",
    "toyName": "Luna",
    "flagged": false,
    "flagReason": null,
    "flagType": null,
    "severity": null,
    "flagStatus": "unreviewed",
    "messagePreview": null,
    "messages": [...]
  }
}
```

**Note:** Messages are included in the conversation document as an array field.

#### `GET /api/conversations/{conversation_id}/messages` (Deprecated)

**Note:** This endpoint is deprecated. Messages are now stored as an array field within the conversation document itself. Use `GET /api/conversations/{conversation_id}` and access the `messages` array in the response.

For backwards compatibility, this endpoint still works:

**Query Parameters:**
- `user_id` (required)

**Response:**
```json
{
  "success": true,
  "messages": [
    {
      "sender": "child",
      "content": "What's 5 plus 5?",
      "timestamp": "2024-01-15T10:30:00Z",
      "flagged": false,
      "flagReason": null
    },
    {
      "sender": "toy",
      "content": "That's 10! Great question!",
      "timestamp": "2024-01-15T10:30:05Z",
      "flagged": false,
      "flagReason": null
    }
  ],
  "count": 2
}
```

#### `GET /api/children/{child_id}/conversations`

Get all conversations for a child.

**Query Parameters:**
- `user_id` (required)
- `limit` (optional, default: 50)

**Response:**
```json
{
  "success": true,
  "conversations": [
    {
      "id": "conv_abc",
      "title": "Math Adventure",
      "startTime": "2024-01-15T10:30:00Z",
      "duration": 15,
      "messageCount": 12,
      "flagged": false
    }
  ],
  "count": 1
}
```

#### `PUT /api/conversations/{conversation_id}/flag`

Update conversation flag status (mark as reviewed).

**Request:**
```json
{
  "user_id": "user_abc",
  "flag_status": "reviewed"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Conversation flag status updated to reviewed"
}
```

#### `GET /api/users/{user_id}/stats`

Get user statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "totalConversations": 45,
    "totalConversationDurationSec": 2700,
    "flaggedConversations": 2,
    "lastConversationAt": "2024-01-15T10:45:00Z",
    "lastFlaggedAt": "2024-01-14T15:20:00Z",
    "lastActivityAt": "2024-01-15T10:45:00Z"
  }
}
```

#### `GET /api/conversations/active`

Get all active conversations for a user.

**Query Parameters:**
- `user_id` (required)
- `limit` (optional, default: 20)

**Response:**
```json
{
  "success": true,
  "conversations": [
    {
      "id": "conv_123",
      "status": "active",
      "childId": "child_xyz",
      "toyId": "toy_abc",
      "startTime": "2024-01-15T10:30:00Z",
      "lastActivityAt": "2024-01-15T10:35:00Z",
      "messageCount": 5
    }
  ],
  "count": 1
}
```

#### `GET /api/conversations/flagged`

Get all flagged conversations for a user.

**Query Parameters:**
- `user_id` (required)
- `limit` (optional, default: 50)

**Response:**
```json
{
  "success": true,
  "conversations": [
    {
      "id": "conv_456",
      "flagged": true,
      "flagReason": "Potential personal info shared",
      "flagStatus": "unreviewed",
      "severity": "medium",
      "childId": "child_xyz",
      "startTime": "2024-01-14T15:20:00Z"
    }
  ],
  "count": 1
}
```

### Knowledge Graph API

#### `POST /api/children/{child_id}/knowledge/entity`

Create a new knowledge graph entity.

**Request:**
```json
{
  "user_id": "user_abc",
  "name": "Dinosaur",
  "entity_type": "interest",
  "metadata": {
    "favorite": "T-Rex"
  }
}
```

#### `GET /api/children/{child_id}/knowledge/entities`

Get all entities for a child.

**Query Parameters:**
- `user_id` (required)

#### `POST /api/children/{child_id}/knowledge/edge`

Create relationship between entities.

**Request:**
```json
{
  "user_id": "user_abc",
  "from_entity_id": "entity_123",
  "to_entity_id": "entity_456",
  "relationship_type": "likes"
}
```

### Setup & Admin API

#### `POST /api/setup/create_account`

Create a new user account with initial data.

**Request:**
```json
{
  "email": "user@example.com",
  "user_id": "user_abc123",
  "display_name": "John Doe"
}
```

#### `POST /api/setup/add_toy`

Add a toy to a user's account.

**Request:**
```json
{
  "user_id": "user_abc123",
  "toy_id": "toy_def456",
  "toy_name": "Luna",
  "assigned_child_id": "child_xyz789"
}
```

#### `POST /api/setup/add_child`

Add a child to a user's account.

**Request:**
```json
{
  "user_id": "user_abc123",
  "child_name": "Emma",
  "age": 8
}
```

### Simulator API

#### `GET /api/simulator/test`

Test simulator connectivity.

#### `POST /api/simulator/message`

Send a test message through the simulator.

**Request:**
```json
{
  "text": "Hello Luna!",
  "user_id": "test_user",
  "child_id": "test_child",
  "toy_id": "test_toy"
}
```

---

## 🔒 Security

### Authentication & Authorization

#### Frontend (Client SDK)
- Uses Firebase Authentication
- Protected by Firestore security rules
- Users can only access their own data
- Token-based authentication for all requests

#### Backend (Admin SDK)
- Firebase Admin SDK bypasses security rules
- Full read/write access to Firestore
- ESP32 doesn't authenticate (trusted device)
- No user tokens required for backend operations

### Data Access Model

```
Frontend (React)
├─ Authenticated with Firebase Auth
├─ Subject to Firestore security rules
└─ Can only read/write own user documents

Backend (Flask)
├─ Authenticated with Service Account
├─ Bypasses Firestore security rules
└─ Trusted to write on behalf of users (ESP32 → Backend → Firestore)

ESP32 Hardware
├─ No authentication
├─ Sends user/child/toy IDs in headers
└─ Backend validates and creates documents
```

### Best Practices

✅ **Never expose service account keys in frontend**
✅ **Use environment variables for API keys**
✅ **Validate user IDs in backend before writes**
✅ **Use HTTPS in production**
✅ **Rotate API keys regularly**
✅ **Monitor Firebase usage quotas**

### Content Safety

The system automatically flags conversations containing:

1. **Personal Information** (Critical)
   - Phone numbers
   - Email addresses
   - Physical addresses
   - Social Security Numbers

2. **Inappropriate Content** (High)
   - Violence keywords
   - Harmful language

3. **Emotional Distress** (Medium)
   - Fear/anxiety indicators
   - Concerning emotional states

Flagged conversations are marked for parent review in the Safety Center.

---

## 🧪 Testing

### Backend Testing

#### Test Firebase Connection

```bash
python -c "from firebase_config import initialize_firebase; db = initialize_firebase(); print('✅ Firebase connected' if db else '❌ Failed')"
```

#### Test API Endpoints

```bash
# Test text upload
curl -X POST http://localhost:5005/text_upload \
  -H "Content-Type: application/json" \
  -H "X-User-ID: test_user" \
  -H "X-Child-ID: test_child" \
  -H "X-Toy-ID: test_toy" \
  -d '{
    "text": "Hello Luna!",
    "session_id": "test_session_1"
  }' --output response.wav

# End conversation
curl -X POST http://localhost:5005/api/conversations/end \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test_session_1"}'

# Get user stats
curl http://localhost:5005/api/users/test_user/stats
```

### Frontend Testing

#### Test Authentication

```typescript
// In browser console
import { auth } from '@/lib/firebase';
import { signInWithEmailAndPassword } from 'firebase/auth';

const user = await signInWithEmailAndPassword(
  auth,
  'test@example.com',
  'password123'
);

console.log('Logged in:', user.uid);
```

#### Test Firestore Queries

```typescript
import { collection, getDocs } from 'firebase/firestore';
import { db } from '@/lib/firebase';

const snapshot = await getDocs(
  collection(db, 'users', userId, 'children')
);

console.log('Children:', snapshot.docs.map(d => d.data()));
```

---

## 🚢 Deployment

### Backend Deployment (Production)

#### Option 1: Traditional Server

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=...
export ELEVENLABS_API_KEY=...
export FIREBASE_SERVICE_ACCOUNT_PATH=/path/to/key.json

# Run with Gunicorn
gunicorn -c gunicorn.conf.py app:app
```

#### Option 2: Docker

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PORT=5005
EXPOSE 5005

CMD ["gunicorn", "-c", "config/gunicorn.conf.py", "app:app"]
```

```bash
docker build -t luno-backend .
docker run -p 5005:5005 \
  -e OPENAI_API_KEY=... \
  -e FIREBASE_SERVICE_ACCOUNT_PATH=/app/key.json \
  luno-backend
```

#### Option 3: Cloud Run / App Engine

```yaml
# app.yaml (Google App Engine)
runtime: python312

env_variables:
  OPENAI_API_KEY: "sk-..."
  FIREBASE_SERVICE_ACCOUNT_JSON: "{...}"

handlers:
  - url: /.*
    script: auto
```

### Frontend Deployment

#### Option 1: Vercel / Netlify

```bash
npm run build
# Deploy build/ folder
```

#### Option 2: Firebase Hosting

```bash
npm install -g firebase-tools
firebase login
firebase init hosting
npm run build
firebase deploy
```

### Environment Configuration

**Production Checklist:**
- [ ] Set `DEBUG=False` in Flask
- [ ] Use production Firestore database
- [ ] Configure CORS for frontend domain
- [ ] Enable HTTPS/SSL
- [ ] Set up monitoring (Firebase Console, Sentry)
- [ ] Configure backup strategy
- [ ] Set rate limits on API endpoints

---

## 🐛 Troubleshooting

### Common Issues

#### Backend won't start

```
Error: "Failed to initialize Firebase"
```

**Solution:**
- Verify `FIREBASE_SERVICE_ACCOUNT_PATH` points to valid JSON
- Check JSON file has correct permissions
- Ensure service account has Firestore access

#### Messages not saving to Firestore

```
Warning: "Missing user/child metadata - Firestore tracking disabled"
```

**Solution:**
- ESP32 must send headers: `X-User-ID`, `X-Child-ID`, `X-Session-ID`
- Check backend logs for Firestore errors
- Verify Firestore database exists

#### Frontend can't read conversations

```
Error: "Permission denied"
```

**Solution:**
- Ensure user is authenticated
- Verify Firestore security rules are configured
- Check that user document exists in Firestore
- Confirm `currentUser.uid` matches `userId` in path

#### Conversations not ending properly

**Solution:**
- Ensure ESP32 calls `/api/conversations/end`
- Check session_id matches between start and end
- Verify backend logs show conversation end

#### High latency on ESP32

**Solution:**
- Check network connection quality
- Monitor `X-Response-Time` header
- Consider using local STT (/text_upload) instead of server STT
- Optimize audio compression settings

### Debug Mode

Enable verbose logging:

```python
# app.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

Check logs for detailed request/response info.

---

## 📈 Monitoring & Analytics

### Firebase Console

Monitor real-time:
- **Authentication**: Active users, sign-ups
- **Firestore**: Read/write operations, document count
- **Performance**: Response times, error rates

### Custom Metrics

Track in your analytics:
- Average conversation duration
- Messages per conversation
- Safety flag rate
- Active toys per user
- Peak usage times

### Alerts

Set up alerts for:
- High error rates
- Safety flags requiring review
- API quota limits
- Unusual usage patterns

---

## 🎓 Additional Resources

### Documentation

- [Quick Start Guide](./docs/QUICK_START.md) - Get started in 5 minutes
- [Setup Guide](./docs/SETUP.md) - Detailed setup instructions
- [Authentication Guide](./docs/AUTHENTICATION.md) - Auth system documentation
- [Simulator Guide](./docs/SIMULATOR_GUIDE.md) - Testing with simulators
- [ESP32 Integration Examples](./docs/ESP32_INTEGRATION_EXAMPLE.md) - Hardware integration
- [Documentation Summary](./docs/DOCS_SUMMARY.md) - Navigation guide

### External Resources

- [Firebase Documentation](https://firebase.google.com/docs)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Flask Documentation](https://flask.palletsprojects.com/)

---

## 📝 License

Proprietary - Luno Toys Platform

---

## 👥 Support

For issues or questions:
- Check backend logs for errors
- Review Firestore console for data issues
- Test with cURL examples above
- Verify all environment variables are set

---

**Built with ❤️ for safe, educational, and fun AI-powered play**
