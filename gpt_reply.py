
from openai import OpenAI
import os
import json
from firestore_service import firestore_service

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

CHARACTER_PROMPT = (
    "You are Luna, a magical friendly companion who loves kids! You're playful, curious, and encouraging. Use simple language words. Keep you responses short and conversational. Your aim is to become friendly companions for kids improving their creative and educational abilities while also increasing their curiosity. Keep your answers under 100 words. Keep zero formatting to this prompt, no emojis and just simple answer from lunos perspective."
)

# Simple in-memory session storage (will upgrade to Redis later)
CONVERSATIONS = {}

# Session metadata for Firestore integration
# Format: session_id -> {user_id, child_id, conversation_id, toy_id}
SESSION_METADATA = {}

def clear_session_history(session_id):
    """
    Clear conversation history for a session

    Args:
        session_id: Session ID to clear history for
    """
    if session_id in CONVERSATIONS:
        del CONVERSATIONS[session_id]
        print(f"[INFO] Cleared conversation history for session {session_id}")


def get_session_message_count(session_id):
    """
    Get message count for a session

    Args:
        session_id: Session ID

    Returns:
        int: Number of messages in session history
    """
    return len(CONVERSATIONS.get(session_id, []))


def get_gpt_reply(user_text, session_id="default", user_id=None, conversation_id=None):
    try:
        print(f"[INFO] Session: {session_id}, Message: {user_text}")

        # Get conversation history for this session
        if session_id not in CONVERSATIONS:
            CONVERSATIONS[session_id] = []

        history = CONVERSATIONS[session_id]
        
        # Build messages with context (keep last 6 messages for memory)
        messages = [{"role": "system", "content": CHARACTER_PROMPT}]
        
        # Add recent conversation history
        for msg in history[-6:]:  # Last 3 turns (6 messages)
            messages.append(msg)
        
        # Add current user message
        messages.append({"role": "user", "content": user_text})
        
        print(f"[INFO] Using {len(messages)-1} previous messages for context")
        
        response = client.chat.completions.create(
            model="gpt-4o",  # Faster model
            messages=messages,
            #max_tokens=50,        # Limit response to ~30-40 words
            temperature=0.7,      # Slightly lower for faster, more focused responses
            timeout=30            # Reduced timeout for faster responses
        )
        
        reply = response.choices[0].message.content.strip()

        # Save conversation turn to memory
        CONVERSATIONS[session_id].append({"role": "user", "content": user_text})
        CONVERSATIONS[session_id].append({"role": "assistant", "content": reply})

        # Keep only last 10 messages (5 turns) to manage memory
        if len(CONVERSATIONS[session_id]) > 10:
            CONVERSATIONS[session_id] = CONVERSATIONS[session_id][-10:]

        # Save to Firestore if metadata is provided (USING BATCH WRITES - reduces from 6 to 3 writes)
        if user_id and conversation_id:
            try:
                # Batch save both messages (3 writes total instead of 6)
                firestore_service.add_message_batch(
                    user_id=user_id,
                    conversation_id=conversation_id,
                    child_message=user_text,
                    toy_message=reply
                )

                print(f"[INFO] Messages batch-saved to Firestore for conversation {conversation_id} (3 writes)")
            except Exception as e:
                print(f"[WARNING] Failed to save to Firestore: {e}")
                # Continue execution even if Firestore fails

        print(f"[GPT Reply] {reply}")
        print(f"[INFO] Session {session_id} now has {len(CONVERSATIONS[session_id])} messages")

        return reply
        
    except Exception as e:
        print(f"[ERROR] GPT request failed: {e}")
        return "Hi! I'm Luna! Sorry, I had a little hiccup. Can you try again?"
    

get_gpt_reply("Hello, Luna! How are you?")  # Example call for testing
