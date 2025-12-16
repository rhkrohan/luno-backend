#!/bin/bash

# Test script for device authentication
# This script tests the authentication middleware with various scenarios

BASE_URL="http://localhost:5005"
USER_ID="test_user_1763434576"
CHILD_ID="test_child_1763434576"
TOY_ID="test_toy_1763434576"
EMAIL="test@lunotoys.com"
SESSION_ID="test_session_123"

echo "=================================================="
echo "Device Authentication Test Suite"
echo "=================================================="
echo ""

echo "Test 1: Valid credentials (should succeed)"
echo "-------------------------------------------"
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: ${USER_ID}" \
  -H "X-Device-ID: ${TOY_ID}" \
  -H "X-Email: ${EMAIL}" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "Test 2: Missing X-Device-ID header (should return 400)"
echo "-------------------------------------------------------"
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: ${USER_ID}" \
  -H "X-Email: ${EMAIL}" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "Test 3: Missing X-Email header (should return 400)"
echo "---------------------------------------------------"
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: ${USER_ID}" \
  -H "X-Device-ID: ${TOY_ID}" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "Test 4: Wrong email (should return 403)"
echo "----------------------------------------"
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: ${USER_ID}" \
  -H "X-Device-ID: ${TOY_ID}" \
  -H "X-Email: wrong@example.com" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "Test 5: Wrong device ID (should return 403)"
echo "--------------------------------------------"
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: ${USER_ID}" \
  -H "X-Device-ID: wrong_device_id" \
  -H "X-Email: ${EMAIL}" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "Test 6: Wrong user ID (should return 404)"
echo "------------------------------------------"
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: wrong_user_id" \
  -H "X-Device-ID: ${TOY_ID}" \
  -H "X-Email: ${EMAIL}" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "Test 7: Cache test - Second request with same session (should use cache)"
echo "-------------------------------------------------------------------------"
echo "Making second request with same session ID..."
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: ${USER_ID}" \
  -H "X-Device-ID: ${TOY_ID}" \
  -H "X-Email: ${EMAIL}" \
  -H "X-Session-ID: ${SESSION_ID}" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "Test 8: Case-insensitive email (should succeed)"
echo "------------------------------------------------"
curl -X GET "${BASE_URL}/auth/test" \
  -H "X-User-ID: ${USER_ID}" \
  -H "X-Device-ID: ${TOY_ID}" \
  -H "X-Email: TEST@LUNOTOYS.COM" \
  -H "X-Session-ID: test_session_case" \
  -w "\nHTTP Status: %{http_code}\n" \
  -s
echo ""
echo ""

echo "=================================================="
echo "Test Suite Complete"
echo "=================================================="
echo ""
echo "Expected Results:"
echo "  Test 1: HTTP 200 - Success"
echo "  Test 2: HTTP 400 - Missing Device ID"
echo "  Test 3: HTTP 400 - Missing Email"
echo "  Test 4: HTTP 403 - Email Mismatch"
echo "  Test 5: HTTP 403 - Device Not Found"
echo "  Test 6: HTTP 404 - User Not Found"
echo "  Test 7: HTTP 200 - Success (cached)"
echo "  Test 8: HTTP 200 - Success (case-insensitive)"
