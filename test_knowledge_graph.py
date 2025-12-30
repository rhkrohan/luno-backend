#!/usr/bin/env python3
"""
Test script for Knowledge Graph feature

This script tests the end-to-end flow:
1. Creates a test conversation with sample messages
2. Ends the conversation (triggers extraction)
3. Waits for async extraction to complete
4. Verifies entities, observations, and summary were created
5. Cleans up test data

Usage:
    python test_knowledge_graph.py
"""

import os
import sys
import time
from datetime import datetime
from google.cloud import firestore

# Add backend directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from firestore_service import firestore_service
from knowledge_graph_service import knowledge_graph_service
from logging_config import get_logger

logger = get_logger(__name__)

# Test data
TEST_USER_ID = "test_user_kg_" + datetime.now().strftime("%Y%m%d_%H%M%S")
TEST_CHILD_ID = "test_child_kg_001"
TEST_TOY_ID = "test_toy_kg_001"
TEST_CONVERSATION_ID = f"{TEST_CHILD_ID}_{TEST_TOY_ID}_20251229_kg_test"

# Sample conversation about dinosaurs (should extract multiple entities)
SAMPLE_MESSAGES = [
    {"sender": "child", "content": "Hi Luna! Tell me about dinosaurs!"},
    {"sender": "toy", "content": "Oh wow! I love dinosaurs! They were amazing creatures that lived millions of years ago! What would you like to know about them?"},
    {"sender": "child", "content": "What did T-Rex eat?"},
    {"sender": "toy", "content": "Great question! T-Rex was a carnivore, which means it ate meat! It hunted other dinosaurs. T-Rex had super strong jaws and sharp teeth!"},
    {"sender": "child", "content": "Why did they go extinct?"},
    {"sender": "toy", "content": "Scientists believe a giant asteroid hit Earth 65 million years ago. This caused big changes to the climate and food supply, and sadly the dinosaurs couldn't survive."},
    {"sender": "child", "content": "Can you count to 20 with me?"},
    {"sender": "toy", "content": "Yes! Let's count together! 1, 2, 3..."},
    {"sender": "child", "content": "1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20!"},
    {"sender": "toy", "content": "Wow! You counted all the way to 20! That's amazing! You're so smart!"},
]


def print_section(title):
    """Print a section header"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def create_test_user():
    """Create test user in Firestore"""
    print_section("STEP 1: Creating Test User")

    try:
        user_ref = firestore_service.db.collection("users").document(TEST_USER_ID)
        user_ref.set({
            "uid": TEST_USER_ID,
            "email": f"{TEST_USER_ID}@test.com",
            "displayName": "Knowledge Graph Test User",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "onboardingCompleted": True,
            "stats": {
                "totalConversations": 0,
                "totalConversationDurationSec": 0,
                "flaggedConversations": 0,
                "lastConversationAt": None,
                "lastFlaggedAt": None
            }
        })

        print(f"✓ Created test user: {TEST_USER_ID}")
        return True
    except Exception as e:
        print(f"✗ Failed to create test user: {e}")
        return False


def create_test_child():
    """Create test child in Firestore"""
    print_section("STEP 2: Creating Test Child")

    try:
        child_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)

        child_ref.set({
            "name": "Test Child Emma",
            "birthDate": "01/15/2018",
            "avatar": "🧒",
            "ageLevel": "elementary",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "contentFilterEnabled": True,
            "quietHoursEnabled": False,
            "dailyLimitEnabled": False,
            "creativeModeEnabled": True,
            "recordConversations": True,
            "dailyLimitHours": 2,
            "blockedTopics": {
                "violence": True,
                "matureContent": True,
                "politics": False,
                "religion": False,
                "personalInfo": True
            },
            "alertTypes": {
                "personalInfo": True,
                "inappropriateContent": True,
                "emotionalDistress": True,
                "unusualPatterns": False
            },
            "alertSensitivity": "Medium"
        })

        print(f"✓ Created test child: {TEST_CHILD_ID}")
        print(f"  Name: Test Child Emma")
        print(f"  Age Level: elementary")
        return True
    except Exception as e:
        print(f"✗ Failed to create test child: {e}")
        return False


def create_test_conversation():
    """Create test conversation with sample messages"""
    print_section("STEP 3: Creating Test Conversation")

    try:
        # Create conversation document
        conversation_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("conversations").document(TEST_CONVERSATION_ID)

        conversation_ref.set({
            "status": "active",
            "type": "conversation",
            "createdAt": firestore.SERVER_TIMESTAMP,
            "childId": TEST_CHILD_ID,
            "toyId": TEST_TOY_ID,
            "childName": "Test Child Emma",
            "toyName": "Test Toy Luna",
            "startTime": firestore.SERVER_TIMESTAMP,
            "lastActivityAt": firestore.SERVER_TIMESTAMP,
            "endTime": None,
            "durationMinutes": 0,
            "messageCount": len(SAMPLE_MESSAGES),
            "title": "Untitled",
            "flagged": False,
            "messages": SAMPLE_MESSAGES
        })

        print(f"✓ Created test conversation: {TEST_CONVERSATION_ID}")
        print(f"  Messages: {len(SAMPLE_MESSAGES)}")
        print(f"  Sample topics: Dinosaurs, T-Rex, Counting")
        return True
    except Exception as e:
        print(f"✗ Failed to create test conversation: {e}")
        return False


def end_conversation_and_trigger_extraction():
    """End conversation and trigger knowledge graph extraction"""
    print_section("STEP 4: Ending Conversation & Triggering Extraction")

    try:
        print("Calling end_conversation()...")
        firestore_service.end_conversation(
            user_id=TEST_USER_ID,
            conversation_id=TEST_CONVERSATION_ID,
            duration_minutes=5
        )

        print("✓ Conversation ended successfully")
        print("✓ Knowledge extraction triggered in background thread")
        print("\nWaiting for async extraction to complete...")

        # Wait for extraction to complete (async thread)
        for i in range(15):
            time.sleep(1)
            print(f"  Waiting... {i+1}s", end="\r")
        print("\n✓ Extraction should be complete")

        return True
    except Exception as e:
        print(f"✗ Failed to end conversation: {e}")
        return False


def verify_entities():
    """Verify entities were extracted"""
    print_section("STEP 5: Verifying Entities")

    try:
        entities_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)\
            .collection("entities")

        entities = list(entities_ref.stream())

        print(f"✓ Found {len(entities)} entities")

        if len(entities) == 0:
            print("✗ WARNING: No entities found! Extraction may have failed.")
            return False

        # Group by type
        by_type = {}
        for entity_doc in entities:
            entity = entity_doc.to_dict()
            entity_type = entity.get("type", "unknown")
            if entity_type not in by_type:
                by_type[entity_type] = []
            by_type[entity_type].append(entity)

        # Display entities by type
        print("\nEntities by type:")
        for entity_type, entities_list in by_type.items():
            print(f"\n  {entity_type.upper()} ({len(entities_list)}):")
            for entity in entities_list:
                name = entity.get("name", "Unknown")
                strength = entity.get("strength", 0)
                mention_count = entity.get("mentionCount", 0)
                print(f"    - {name} (strength: {strength:.2f}, mentions: {mention_count})")

        return True
    except Exception as e:
        print(f"✗ Failed to verify entities: {e}")
        return False


def verify_observations():
    """Verify observations were created"""
    print_section("STEP 6: Verifying Observations")

    try:
        observations_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)\
            .collection("observations")

        observations = list(observations_ref.stream())

        print(f"✓ Found {len(observations)} observations")

        if len(observations) == 0:
            print("✗ WARNING: No observations found!")
            return False

        # Display observations
        for obs_doc in observations:
            obs = obs_doc.to_dict()
            obs_id = obs.get("id", "Unknown")
            entity_count = len(obs.get("entities", []))
            print(f"\n  Observation: {obs_id}")
            print(f"    Entities observed: {entity_count}")
            print(f"    Conversation: {obs.get('conversationId', 'Unknown')}")

        return True
    except Exception as e:
        print(f"✗ Failed to verify observations: {e}")
        return False


def verify_summary():
    """Verify summary document was created"""
    print_section("STEP 7: Verifying Summary Document")

    try:
        summary_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)\
            .collection("knowledgeGraph").document("summary")

        summary_doc = summary_ref.get()

        if not summary_doc.exists:
            print("✗ WARNING: Summary document not found!")
            return False

        summary = summary_doc.to_dict()
        stats = summary.get("stats", {})

        print("✓ Summary document created")
        print(f"\nStats:")
        print(f"  Total Entities: {stats.get('totalEntities', 0)}")
        print(f"  Topics: {stats.get('topicsCount', 0)}")
        print(f"  Skills: {stats.get('skillsCount', 0)}")
        print(f"  Interests: {stats.get('interestsCount', 0)}")
        print(f"  Concepts: {stats.get('conceptsCount', 0)}")
        print(f"  Traits: {stats.get('traitsCount', 0)}")

        # Display top items
        top_topics = summary.get("topTopics", [])
        if top_topics:
            print(f"\n  Top Topics:")
            for topic in top_topics[:3]:
                print(f"    - {topic.get('name')} (count: {topic.get('count', 0)})")

        top_interests = summary.get("topInterests", [])
        if top_interests:
            print(f"\n  Top Interests:")
            for interest in top_interests[:3]:
                print(f"    - {interest.get('name')} (strength: {interest.get('strength', 0):.2f})")

        top_skills = summary.get("topSkills", [])
        if top_skills:
            print(f"\n  Top Skills:")
            for skill in top_skills[:3]:
                print(f"    - {skill.get('name')} (level: {skill.get('level', 'unknown')})")

        return True
    except Exception as e:
        print(f"✗ Failed to verify summary: {e}")
        return False


def test_api_query():
    """Test querying via knowledge graph service"""
    print_section("STEP 8: Testing API Query Methods")

    try:
        # Test get_summary
        print("Testing get_summary()...")
        summary = knowledge_graph_service.get_summary(TEST_USER_ID, TEST_CHILD_ID)
        if summary:
            print(f"✓ get_summary() returned data")
        else:
            print(f"✗ get_summary() returned None")

        # Test get_entities
        print("\nTesting get_entities()...")
        entities = knowledge_graph_service.get_entities(
            TEST_USER_ID,
            TEST_CHILD_ID,
            {"type": "topic", "limit": 10, "orderBy": "strength"}
        )
        print(f"✓ get_entities() returned {len(entities)} topics")

        return True
    except Exception as e:
        print(f"✗ API query test failed: {e}")
        return False


def cleanup_test_data():
    """Clean up test data from Firestore"""
    print_section("STEP 9: Cleanup Test Data")

    try:
        print("Do you want to delete the test data? (y/n): ", end="")
        response = input().strip().lower()

        if response != 'y':
            print("✓ Skipping cleanup - test data preserved for manual inspection")
            print(f"\nTest User ID: {TEST_USER_ID}")
            print(f"Test Child ID: {TEST_CHILD_ID}")
            print(f"Test Conversation ID: {TEST_CONVERSATION_ID}")
            return True

        print("\nDeleting test data...")

        # Delete entities
        entities_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)\
            .collection("entities")
        for doc in entities_ref.stream():
            doc.reference.delete()
        print("  ✓ Deleted entities")

        # Delete observations
        observations_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)\
            .collection("observations")
        for doc in observations_ref.stream():
            doc.reference.delete()
        print("  ✓ Deleted observations")

        # Delete knowledge graph summary
        summary_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)\
            .collection("knowledgeGraph").document("summary")
        summary_ref.delete()
        print("  ✓ Deleted summary")

        # Delete child
        child_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("children").document(TEST_CHILD_ID)
        child_ref.delete()
        print("  ✓ Deleted child")

        # Delete conversation
        conversation_ref = firestore_service.db.collection("users").document(TEST_USER_ID)\
            .collection("conversations").document(TEST_CONVERSATION_ID)
        conversation_ref.delete()
        print("  ✓ Deleted conversation")

        # Delete user
        user_ref = firestore_service.db.collection("users").document(TEST_USER_ID)
        user_ref.delete()
        print("  ✓ Deleted user")

        print("\n✓ All test data cleaned up successfully")
        return True
    except Exception as e:
        print(f"✗ Cleanup failed: {e}")
        return False


def main():
    """Run the complete test suite"""
    print("\n" + "=" * 70)
    print("  KNOWLEDGE GRAPH END-TO-END TEST")
    print("=" * 70)
    print(f"\nTest User ID: {TEST_USER_ID}")
    print(f"Test Child ID: {TEST_CHILD_ID}")
    print(f"Test Conversation ID: {TEST_CONVERSATION_ID}")

    # Check Firestore connection
    if not firestore_service.is_available():
        print("\n✗ ERROR: Firestore is not available!")
        print("  Make sure Firebase credentials are configured correctly.")
        return 1

    results = []

    # Run test steps
    results.append(("Create Test User", create_test_user()))
    results.append(("Create Test Child", create_test_child()))
    results.append(("Create Test Conversation", create_test_conversation()))
    results.append(("End Conversation & Extract", end_conversation_and_trigger_extraction()))
    results.append(("Verify Entities", verify_entities()))
    results.append(("Verify Observations", verify_observations()))
    results.append(("Verify Summary", verify_summary()))
    results.append(("Test API Queries", test_api_query()))

    # Print results summary
    print_section("TEST RESULTS SUMMARY")

    passed = 0
    failed = 0

    for step_name, success in results:
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {step_name}")
        if success:
            passed += 1
        else:
            failed += 1

    print(f"\nTotal: {passed} passed, {failed} failed out of {len(results)} tests")

    # Cleanup
    cleanup_test_data()

    # Return exit code
    if failed > 0:
        print("\n✗ Some tests failed. Please check the logs above.")
        return 1
    else:
        print("\n✓ All tests passed successfully!")
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
