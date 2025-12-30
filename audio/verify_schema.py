#!/usr/bin/env python3
"""
Verify that the firestore_service implementation matches the exact schema
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firestore_service import firestore_service
import json


def verify_conversation_schema():
    """Verify conversation document has all required fields"""

    print("=" * 70)
    print("SCHEMA VERIFICATION - Array-Based Conversation Storage")
    print("=" * 70)

    # Create test conversation
    user_id = "schema_test_user"
    child_id = "schema_test_child"
    toy_id = "schema_test_toy"

    print("\n[1] Creating test conversation...")
    conv_id = firestore_service.create_conversation(
        user_id=user_id,
        child_id=child_id,
        toy_id=toy_id,
        conversation_type="conversation"
    )

    if not conv_id:
        print("❌ Failed to create conversation")
        return False

    print(f"✓ Conversation created: {conv_id}")

    # Get conversation
    print("\n[2] Retrieving conversation to verify schema...")
    conv = firestore_service.get_conversation(user_id, conv_id)

    if not conv:
        print("❌ Failed to retrieve conversation")
        return False

    # Define required schema
    required_fields = {
        # Core metadata
        "startTime": "timestamp",
        "endTime": "timestamp | null",
        "duration": "number (minutes, legacy)",
        "durationMinutes": "number (minutes)",
        "type": "string",
        "title": "string",
        "messageCount": "number",
        "createdAt": "timestamp",
        "lastActivityAt": "timestamp",
        "status": "string",

        # References
        "childId": "string",
        "childName": "string | null",
        "toyId": "string | null",
        "toyName": "string | null",

        # Content
        "firstMessagePreview": "string | null",
        "titleGeneratedAt": "timestamp | null",

        # Safety / flag metadata
        "flagged": "boolean",
        "flagReason": "string | null",
        "flagType": "string | null",
        "severity": "string | null",
        "flagStatus": "string | null",

        # Compact structure
        "messages": "array"
    }

    print("\n[3] Verifying schema fields...")
    print("-" * 70)

    all_present = True
    for field, expected_type in required_fields.items():
        present = field in conv
        status = "✓" if present else "❌"

        if present:
            actual_value = conv[field]
            # Get type representation
            if actual_value is None:
                value_repr = "null"
            elif isinstance(actual_value, bool):
                value_repr = "boolean"
            elif isinstance(actual_value, int):
                value_repr = "number"
            elif isinstance(actual_value, str):
                value_repr = f"string: '{actual_value}'"
            elif isinstance(actual_value, list):
                value_repr = f"array (length: {len(actual_value)})"
            else:
                value_repr = str(type(actual_value).__name__)

            print(f"{status} {field:25} {value_repr}")
        else:
            print(f"{status} {field:25} MISSING")
            all_present = False

    # Verify message array structure
    print("\n[4] Adding test messages...")
    success, _ = firestore_service.add_message_batch(
        user_id=user_id,
        conversation_id=conv_id,
        child_message="Hello Luna!",
        toy_message="Hi there! How can I help you today?"
    )

    if not success:
        print("❌ Failed to add messages")
        return False

    print("✓ Messages added")

    # Get updated conversation
    conv_updated = firestore_service.get_conversation(user_id, conv_id)
    messages = conv_updated.get("messages", [])

    print(f"\n[5] Verifying message array structure...")
    print(f"   Messages in array: {len(messages)}")

    if len(messages) > 0:
        print("\n   Message 1 structure:")
        msg = messages[0]
        required_msg_fields = ["sender", "content", "timestamp", "flagged", "flagReason"]

        for field in required_msg_fields:
            present = field in msg
            status = "✓" if present else "❌"
            value = msg.get(field, "MISSING")
            print(f"   {status} {field:15} {value}")

    # Verify field values match expected types
    print("\n[6] Verifying field values...")
    print("-" * 70)

    checks = [
        ("status", conv_updated.get("status") == "active", "Status is 'active'"),
        ("type", conv_updated.get("type") == "conversation", "Type is 'conversation'"),
        ("childId", conv_updated.get("childId") == child_id, "childId matches"),
        ("toyId", conv_updated.get("toyId") == toy_id, "toyId matches"),
        ("messageCount", conv_updated.get("messageCount") == 2, "messageCount is 2"),
        ("messages", len(messages) == 2, "2 messages in array"),
        ("flagged", conv_updated.get("flagged") == False, "Not flagged"),
        ("flagStatus", conv_updated.get("flagStatus") == "unreviewed", "flagStatus is 'unreviewed'"),
        ("duration", conv_updated.get("duration") == 0, "duration initialized to 0"),
        ("durationMinutes", conv_updated.get("durationMinutes") == 0, "durationMinutes initialized to 0"),
    ]

    all_checks_passed = True
    for field, check, description in checks:
        status = "✓" if check else "❌"
        print(f"{status} {description}")
        if not check:
            all_checks_passed = False

    # End conversation
    print("\n[7] Testing end_conversation()...")
    firestore_service.end_conversation(user_id, conv_id, duration_minutes=3)

    import time
    time.sleep(1)

    conv_ended = firestore_service.get_conversation(user_id, conv_id)

    end_checks = [
        ("status", conv_ended.get("status") == "ended", "Status changed to 'ended'"),
        ("duration", conv_ended.get("duration") == 3, "duration set to 3"),
        ("durationMinutes", conv_ended.get("durationMinutes") == 3, "durationMinutes set to 3"),
        ("endTime", conv_ended.get("endTime") is not None, "endTime is set"),
    ]

    for field, check, description in end_checks:
        status = "✓" if check else "❌"
        print(f"{status} {description}")
        if not check:
            all_checks_passed = False

    # Final summary
    print("\n" + "=" * 70)
    if all_present and all_checks_passed:
        print("✅ SCHEMA VERIFICATION PASSED")
        print("   All required fields present and values correct")
        print("   Implementation matches exact schema specification")
    else:
        print("❌ SCHEMA VERIFICATION FAILED")
        if not all_present:
            print("   Some required fields are missing")
        if not all_checks_passed:
            print("   Some field values are incorrect")
    print("=" * 70)

    return all_present and all_checks_passed


if __name__ == "__main__":
    if not firestore_service.is_available():
        print("❌ Firestore not available")
        print("Cannot run schema verification without Firestore")
        sys.exit(1)

    success = verify_conversation_schema()
    sys.exit(0 if success else 1)
