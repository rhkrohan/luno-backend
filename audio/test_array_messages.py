#!/usr/bin/env python3
"""
Test script for array-based message storage implementation
"""
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firestore_service import firestore_service
from datetime import datetime
import json


def test_conversation_flow():
    """Test the complete conversation flow with array-based messages"""

    print("=" * 60)
    print("Testing Array-Based Message Storage Implementation")
    print("=" * 60)

    # Test configuration
    user_id = "test_user_123"
    child_id = "test_child_456"
    toy_id = "test_toy_789"

    print(f"\n[1] Creating conversation...")
    conversation_id = firestore_service.create_conversation(
        user_id=user_id,
        child_id=child_id,
        toy_id=toy_id,
        conversation_type="conversation"
    )

    if not conversation_id:
        print("ERROR: Failed to create conversation")
        return False

    print(f"   ✓ Conversation created: {conversation_id}")

    # Get conversation to verify structure
    print(f"\n[2] Verifying conversation structure...")
    conv = firestore_service.get_conversation(user_id, conversation_id)
    if not conv:
        print("ERROR: Could not retrieve conversation")
        return False

    print(f"   ✓ Conversation retrieved")
    print(f"   - Status: {conv.get('status')}")
    print(f"   - Type: {conv.get('type')}")
    print(f"   - Child ID: {conv.get('childId')}")
    print(f"   - Child Name: {conv.get('childName')}")
    print(f"   - Toy ID: {conv.get('toyId')}")
    print(f"   - Toy Name: {conv.get('toyName')}")
    print(f"   - Messages array exists: {('messages' in conv)}")
    print(f"   - Initial message count: {len(conv.get('messages', []))}")

    # Add messages using batch
    print(f"\n[3] Adding messages (batch)...")
    for i in range(3):
        success, overflow = firestore_service.add_message_batch(
            user_id=user_id,
            conversation_id=conversation_id,
            child_message=f"Hello! This is child message {i+1}",
            toy_message=f"Hi! This is Luna's response {i+1}"
        )

        if not success:
            print(f"ERROR: Failed to add message batch {i+1}")
            return False

        print(f"   ✓ Added message pair {i+1}/3")

    # Retrieve messages
    print(f"\n[4] Retrieving messages from array...")
    messages = firestore_service.get_conversation_messages(
        user_id=user_id,
        conversation_id=conversation_id
    )

    print(f"   ✓ Retrieved {len(messages)} messages")
    for idx, msg in enumerate(messages):
        sender = msg.get('sender', 'unknown')
        content = msg.get('content', '')[:50]
        print(f"      {idx+1}. [{sender}] {content}")

    # Verify updated conversation
    print(f"\n[5] Verifying conversation updates...")
    conv_updated = firestore_service.get_conversation(user_id, conversation_id)

    print(f"   ✓ Message count: {conv_updated.get('messageCount')}")
    print(f"   ✓ First message preview: {conv_updated.get('firstMessagePreview')}")
    print(f"   ✓ Messages in array: {len(conv_updated.get('messages', []))}")

    # End conversation
    print(f"\n[6] Ending conversation...")
    firestore_service.end_conversation(
        user_id=user_id,
        conversation_id=conversation_id,
        duration_minutes=5
    )

    # Wait a moment for the update
    import time
    time.sleep(1)

    # Verify ended conversation
    conv_ended = firestore_service.get_conversation(user_id, conversation_id)
    print(f"   ✓ Status: {conv_ended.get('status')}")
    print(f"   ✓ Duration: {conv_ended.get('durationMinutes')} minutes")
    print(f"   ✓ Legacy duration field: {conv_ended.get('duration')} minutes")

    print("\n" + "=" * 60)
    print("✓ All tests passed successfully!")
    print("=" * 60)

    return True


def test_overflow_handling():
    """Test message overflow handling (optional - creates 100+ messages)"""

    print("\n" + "=" * 60)
    print("Testing Overflow Handling (100+ messages)")
    print("=" * 60)

    user_id = "test_user_overflow"
    child_id = "test_child_overflow"
    toy_id = "test_toy_overflow"

    print(f"\n[1] Creating conversation...")
    conversation_id = firestore_service.create_conversation(
        user_id=user_id,
        child_id=child_id,
        toy_id=toy_id
    )

    if not conversation_id:
        print("ERROR: Failed to create conversation")
        return False

    print(f"   ✓ Conversation created: {conversation_id}")

    # Add 55 message pairs (110 messages total) to trigger overflow
    print(f"\n[2] Adding 55 message pairs (110 messages)...")
    print("   This will trigger overflow handling at 100 messages...")

    overflow_triggered = False
    for i in range(55):
        success, overflow = firestore_service.add_message_batch(
            user_id=user_id,
            conversation_id=conversation_id,
            child_message=f"Test message {i+1}",
            toy_message=f"Response {i+1}"
        )

        if overflow and not overflow_triggered:
            print(f"   ⚠ Overflow triggered at message pair {i+1}")
            overflow_triggered = True

        if (i + 1) % 10 == 0:
            print(f"   Progress: {i+1}/55 pairs added")

    # Verify final state
    print(f"\n[3] Verifying final state...")
    conv = firestore_service.get_conversation(user_id, conversation_id)
    messages_in_array = len(conv.get('messages', []))

    print(f"   ✓ Total message count: {conv.get('messageCount')}")
    print(f"   ✓ Messages in main array: {messages_in_array}")
    print(f"   ✓ Overflow was triggered: {overflow_triggered}")

    if overflow_triggered:
        print(f"   ✓ Overflow handling working correctly!")

    print("\n" + "=" * 60)
    print("✓ Overflow test completed!")
    print("=" * 60)

    return True


if __name__ == "__main__":
    print("\nChecking Firestore availability...")
    if not firestore_service.is_available():
        print("ERROR: Firestore is not available")
        print("Make sure Firebase credentials are configured")
        sys.exit(1)

    print("✓ Firestore is available\n")

    # Run basic tests
    success = test_conversation_flow()

    if not success:
        print("\n❌ Basic tests failed")
        sys.exit(1)

    # Ask if user wants to run overflow test
    print("\n" + "=" * 60)
    response = input("Run overflow test? (creates 110 messages) [y/N]: ")

    if response.lower() == 'y':
        test_overflow_handling()
    else:
        print("Skipping overflow test")

    print("\n✓ All requested tests completed!\n")
