#!/usr/bin/env python3
"""
Test script to verify the complete authentication workflow
Tests both valid and invalid authentication scenarios
"""

import requests
import json
import sys

# Configuration from simulator_config.json
CONFIG_FILE = "simulator_config.json"

def load_config():
    """Load configuration"""
    with open(CONFIG_FILE, 'r') as f:
        return json.load(f)

def test_valid_authentication(config):
    """Test with valid credentials"""
    print("\n" + "="*60)
    print("TEST 1: Valid Authentication")
    print("="*60)

    url = f"{config['backend_url']}/auth/test"
    headers = {
        "X-Session-ID": "test_session_workflow",
        "X-User-ID": config['user_id'],
        "X-Device-ID": config['device_id'],
        "X-Email": config['email'],
    }

    print(f"\nRequest URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")

    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 200:
            print("\n✓ TEST PASSED: Authentication successful")
            return True
        else:
            print("\n✗ TEST FAILED: Expected 200, got", response.status_code)
            return False
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False

def test_missing_email(config):
    """Test with missing email header"""
    print("\n" + "="*60)
    print("TEST 2: Missing Email Header")
    print("="*60)

    url = f"{config['backend_url']}/auth/test"
    headers = {
        "X-Session-ID": "test_session_workflow",
        "X-User-ID": config['user_id'],
        "X-Device-ID": config['device_id'],
        # Missing X-Email
    }

    print(f"\nRequest URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print("Note: X-Email header intentionally missing")

    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 400:
            print("\n✓ TEST PASSED: Correctly rejected missing header")
            return True
        else:
            print("\n✗ TEST FAILED: Expected 400, got", response.status_code)
            return False
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False

def test_wrong_email(config):
    """Test with wrong email"""
    print("\n" + "="*60)
    print("TEST 3: Wrong Email")
    print("="*60)

    url = f"{config['backend_url']}/auth/test"
    headers = {
        "X-Session-ID": "test_session_workflow",
        "X-User-ID": config['user_id'],
        "X-Device-ID": config['device_id'],
        "X-Email": "wrong@example.com",  # Wrong email
    }

    print(f"\nRequest URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Note: Email should be '{config['email']}' but using 'wrong@example.com'")

    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 403:
            print("\n✓ TEST PASSED: Correctly rejected wrong email")
            return True
        else:
            print("\n✗ TEST FAILED: Expected 403, got", response.status_code)
            return False
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False

def test_wrong_device(config):
    """Test with wrong device ID"""
    print("\n" + "="*60)
    print("TEST 4: Wrong Device ID")
    print("="*60)

    url = f"{config['backend_url']}/auth/test"
    headers = {
        "X-Session-ID": "test_session_workflow",
        "X-User-ID": config['user_id'],
        "X-Device-ID": "wrong_device_id",  # Wrong device
        "X-Email": config['email'],
    }

    print(f"\nRequest URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Note: Device ID should be '{config['device_id']}' but using 'wrong_device_id'")

    try:
        response = requests.get(url, headers=headers, timeout=5)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {json.dumps(response.json(), indent=2)}")

        if response.status_code == 403:
            print("\n✓ TEST PASSED: Correctly rejected wrong device")
            return True
        else:
            print("\n✗ TEST FAILED: Expected 403, got", response.status_code)
            return False
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False

def test_text_upload_with_auth(config):
    """Test text upload endpoint with authentication"""
    print("\n" + "="*60)
    print("TEST 5: Text Upload with Valid Authentication")
    print("="*60)

    url = f"{config['backend_url']}/text_upload"
    headers = {
        "Content-Type": "application/json",
        "X-Session-ID": "test_session_workflow",
        "X-User-ID": config['user_id'],
        "X-Child-ID": config['child_id'],
        "X-Toy-ID": config['toy_id'],
        "X-Device-ID": config['device_id'],
        "X-Email": config['email'],
    }

    payload = {
        "text": "Hello Luna, this is a test!",
        "session_id": "test_session_workflow",
        "user_id": config['user_id'],
        "child_id": config['child_id'],
        "toy_id": config['toy_id']
    }

    print(f"\nRequest URL: {url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        print(f"\nResponse Status: {response.status_code}")

        if response.status_code == 200:
            print(f"Response Headers:")
            print(f"  X-Response-Time: {response.headers.get('X-Response-Time', 'N/A')}")
            print(f"  X-GPT-Time: {response.headers.get('X-GPT-Time', 'N/A')}")
            print(f"  X-TTS-Time: {response.headers.get('X-TTS-Time', 'N/A')}")
            print(f"  Content-Length: {len(response.content)} bytes")
            print("\n✓ TEST PASSED: Text upload with authentication successful")
            return True
        else:
            print(f"Response Body: {response.text[:200]}")
            print("\n✗ TEST FAILED: Expected 200, got", response.status_code)
            return False
    except Exception as e:
        print(f"\n✗ TEST FAILED: {e}")
        return False

def main():
    """Run all tests"""
    print("\n" + "🔐 " + "="*58)
    print("    DEVICE AUTHENTICATION WORKFLOW TEST SUITE")
    print("="*60)

    try:
        config = load_config()
        print(f"\nLoaded configuration from {CONFIG_FILE}")
        print(f"  User ID:   {config['user_id']}")
        print(f"  Email:     {config['email']}")
        print(f"  Child ID:  {config['child_id']}")
        print(f"  Device ID: {config['device_id']}")
        print(f"  Backend:   {config['backend_url']}")
    except Exception as e:
        print(f"\n✗ ERROR: Failed to load configuration: {e}")
        sys.exit(1)

    # Check backend is running
    print("\n" + "="*60)
    print("Checking backend connection...")
    print("="*60)
    try:
        response = requests.get(config['backend_url'], timeout=5)
        print(f"✓ Backend is running at {config['backend_url']}")
    except Exception as e:
        print(f"✗ ERROR: Backend not accessible: {e}")
        print("\nPlease start the backend server with:")
        print("  cd /Users/rohankhan/Desktop/Luno/backend")
        print("  source venv/bin/activate")
        print("  python app.py")
        sys.exit(1)

    # Run tests
    results = []

    results.append(("Valid Authentication", test_valid_authentication(config)))
    results.append(("Missing Email Header", test_missing_email(config)))
    results.append(("Wrong Email", test_wrong_email(config)))
    results.append(("Wrong Device ID", test_wrong_device(config)))
    results.append(("Text Upload with Auth", test_text_upload_with_auth(config)))

    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {status}: {test_name}")

    print(f"\n  Total: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
