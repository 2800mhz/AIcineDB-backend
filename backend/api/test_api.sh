#!/bin/bash

# AI Cine Analyzer - API Test Script
# Tests all major endpoints

API_URL="http://localhost:8000"

echo "🧪 AI Cine Analyzer - API Tests"
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo "📋 Test 1: Health Check"
response=$(curl -s -w "\n%{http_code}" "$API_URL/health")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Health check successful"
    echo "   Response: $body"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 2: Root endpoint
echo "📋 Test 2: Root Endpoint"
response=$(curl -s -w "\n%{http_code}" "$API_URL/")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Root endpoint successful"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 3: List films
echo "📋 Test 3: List Films"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/films")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - List films successful"
    echo "   Films found: $(echo "$body" | jq 'length' 2>/dev/null || echo "0")"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 4: List jobs
echo "📋 Test 4: List Jobs"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/jobs")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - List jobs successful"
    echo "   Jobs found: $(echo "$body" | jq 'length' 2>/dev/null || echo "0")"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 5: Get stats
echo "📋 Test 5: Platform Stats"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/stats")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Stats successful"
    echo "   $body" | jq '.' 2>/dev/null || echo "   $body"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 6: Submit analysis (requires confirmation)
echo "📋 Test 6: Submit Analysis"
echo -e "${YELLOW}⚠️  This will submit a real video for analysis${NC}"
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    # Use a short test video
    TEST_URL="https://www.youtube.com/watch?v=jNQXAC9IVRw"  # "Me at the zoo" - first YouTube video (18 seconds)
    
    echo "   Submitting: $TEST_URL"
    
    response=$(curl -s -w "\n%{http_code}" -X POST "$API_URL/api/analyze" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"$TEST_URL\", \"priority\": 5}")
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "202" ]; then
        echo -e "${GREEN}✓ PASS${NC} - Analysis queued"
        job_id=$(echo "$body" | jq -r '.job_id' 2>/dev/null)
        
        if [ ! -z "$job_id" ] && [ "$job_id" != "null" ]; then
            echo "   Job ID: $job_id"
            echo ""
            echo "   Track progress with:"
            echo "   curl $API_URL/api/jobs/$job_id"
        fi
    elif [ "$http_code" = "409" ]; then
        echo -e "${YELLOW}⚠️  SKIP${NC} - Video already analyzed"
        echo "   $body" | jq -r '.detail' 2>/dev/null || echo "   $body"
    else
        echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
        echo "   Response: $body"
    fi
else
    echo -e "${YELLOW}⚠️  SKIP${NC} - Test skipped"
fi
echo ""

echo "================================"
echo "✅ Tests completed!"
echo ""
echo "📚 API Documentation: $API_URL/docs"
echo "🌸 Task Monitor (Flower): http://localhost:5555"