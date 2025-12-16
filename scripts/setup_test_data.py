#!/usr/bin/env python3
"""
Setup Test Data for Luno Backend Testing
Creates test user, child, and toy documents in Firestore
"""

import json
import os
from datetime import datetime
from firebase_config import get_firestore_client

def print_header():
    print("\n" + "="*60)
    print("   🚀 Luno Backend - Test Data Setup")
    print("="*60 + "\n")

def create_test_user(db, user_id, email, display_name):
    """Create a test user document"""
    user_data = {
        "uid": user_id,
        "email": email,
        "displayName": display_name,
        "createdAt": datetime.now().isoformat(),
        "onboardingCompleted": True,
        "preferences": {
            "notifications": True,
            "theme": "light"
        },
        "childrenCount": 0,
        "toys": [],
        "stats": {
            "totalConversations": 0,
            "totalConversationDurationSec": 0,
            "flaggedConversations": 0,
            "lastConversationAt": None,
            "lastFlaggedAt": None,
            "lastActivityAt": datetime.now().isoformat()
        }
    }

    db.collection("users").document(user_id).set(user_data)
    print(f"✓ Created user: {user_id}")
    print(f"  Email: {email}")
    print(f"  Display Name: {display_name}\n")

    return user_data

def create_test_child(db, user_id, child_id, name, age_level="elementary"):
    """Create a test child document"""
    child_data = {
        "name": name,
        "birthDate": "01/15/2015",
        "avatar": "🧒",
        "ageLevel": age_level,
        "dailyLimitHours": 2,
        "createdAt": datetime.now().isoformat(),

        # Parental Controls
        "contentFilterEnabled": True,
        "quietHoursEnabled": False,
        "dailyLimitEnabled": True,
        "creativeModeEnabled": True,
        "recordConversations": True,

        # Blocked Topics
        "blockedTopics": {
            "violence": True,
            "matureContent": True,
            "politics": False,
            "religion": False,
            "personalInfo": True
        },

        # Alert Settings
        "alertTypes": {
            "personalInfo": True,
            "inappropriateContent": True,
            "emotionalDistress": True,
            "unusualPatterns": True
        },
        "alertSensitivity": "Medium"
    }

    db.collection("users").document(user_id)\
        .collection("children").document(child_id).set(child_data)

    # Update user's childrenCount
    db.collection("users").document(user_id).update({
        "childrenCount": 1
    })

    print(f"✓ Created child: {child_id}")
    print(f"  Name: {name}")
    print(f"  Age Level: {age_level}\n")

    return child_data

def create_test_toy(db, user_id, toy_id, name, assigned_child_id=None):
    """Create a test toy document"""
    toy_data = {
        "name": name,
        "emoji": "🦄",
        "assignedChildId": assigned_child_id,
        "pairedAt": datetime.now().isoformat(),
        "status": "online",
        "batteryLevel": 85,
        "lastConnected": datetime.now().isoformat(),

        # Device Information
        "model": "Luno Gen 2 Simulator",
        "serialNumber": f"SIM-{toy_id}",
        "firmwareVersion": "v2.1.4-simulator",

        # Device Settings
        "volume": 70,
        "ledBrightness": "Medium",
        "soundEffects": True,
        "voiceType": "Female, Child-friendly",
        "autoUpdate": True,

        # Connection
        "connectionType": "Wi-Fi",
        "wifiNetwork": "Simulator-Network"
    }

    db.collection("users").document(user_id)\
        .collection("toys").document(toy_id).set(toy_data)

    # Add toy to user's toys array
    db.collection("users").document(user_id).update({
        "toys": [toy_id]
    })

    print(f"✓ Created toy: {toy_id}")
    print(f"  Name: {name}")
    if assigned_child_id:
        print(f"  Assigned to: {assigned_child_id}\n")
    else:
        print(f"  Assigned to: None\n")

    return toy_data

def update_simulator_config(user_id, child_id, toy_id):
    """Update simulator configuration with test IDs"""
    config = {
        "user_id": user_id,
        "child_id": child_id,
        "toy_id": toy_id,
        "backend_url": "http://localhost:5005",
        "auto_play_response": True,
        "save_conversations": True
    }

    with open("simulators/simulator_config.json", "w") as f:
        json.dump(config, f, indent=2)

    print("✓ Updated simulator_config.json\n")

def print_instructions(user_id, child_id, toy_id):
    """Print next steps"""
    print("\n" + "="*60)
    print("   ✅ Setup Complete!")
    print("="*60 + "\n")

    print("Your test data has been created in Firestore:")
    print(f"  User ID:  {user_id}")
    print(f"  Child ID: {child_id}")
    print(f"  Toy ID:   {toy_id}\n")

    print("Next steps:\n")
    print("1. Verify data in Firebase Console:")
    print("   https://console.firebase.google.com/project/luno-companion-app-dev/firestore\n")

    print("2. Test with CLI Simulator:")
    print("   python esp32_simulator.py\n")

    print("3. Test with Web Simulator:")
    print("   Open: http://localhost:5005/simulator\n")

    print("4. The simulators are already configured with your test IDs!")
    print("   (Check simulator_config.json)\n")

    print("="*60 + "\n")

def main():
    print_header()

    # Initialize Firestore
    print("Connecting to Firestore...\n")
    db = get_firestore_client()

    if db is None:
        print("❌ Error: Could not connect to Firestore")
        print("\nMake sure you have:")
        print("1. Set FIREBASE_SERVICE_ACCOUNT_PATH environment variable")
        print("2. Downloaded service account key from Firebase Console")
        print("3. Pointed the path to your JSON key file\n")
        return

    print("✓ Connected to Firestore\n")
    print("-"*60 + "\n")

    # Generate test IDs
    import uuid
    timestamp = int(datetime.now().timestamp())

    user_id = f"test_user_{timestamp}"
    child_id = f"test_child_{timestamp}"
    toy_id = f"test_toy_{timestamp}"

    print(f"Creating test data with IDs:\n")
    print(f"  User:  {user_id}")
    print(f"  Child: {child_id}")
    print(f"  Toy:   {toy_id}\n")
    print("-"*60 + "\n")

    try:
        # Create test user
        create_test_user(
            db=db,
            user_id=user_id,
            email="test@lunotoys.com",
            display_name="Test Parent"
        )

        # Create test child
        create_test_child(
            db=db,
            user_id=user_id,
            child_id=child_id,
            name="Test Child",
            age_level="elementary"
        )

        # Create test toy
        create_test_toy(
            db=db,
            user_id=user_id,
            toy_id=toy_id,
            name="Luna Test",
            assigned_child_id=child_id
        )

        # Update simulator configuration
        update_simulator_config(user_id, child_id, toy_id)

        # Print instructions
        print_instructions(user_id, child_id, toy_id)

    except Exception as e:
        print(f"\n❌ Error creating test data: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
