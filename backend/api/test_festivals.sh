#!/bin/bash

# Festival API Test Script
# Tests festival endpoints (requires running API server and valid auth token)

API_URL="${API_URL:-http://localhost:8000}"
AUTH_TOKEN="${AUTH_TOKEN:-}"

echo "🧪 Festival API Tests"
echo "================================"
echo "API URL: $API_URL"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}⚠️  jq not found. Install for better output formatting${NC}"
    echo ""
fi

# Test 1: List Festivals (public endpoint)
echo "📋 Test 1: List Festivals (Public)"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/festivals")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - List festivals successful"
    count=$(echo "$body" | jq '.count' 2>/dev/null || echo "?")
    echo "   Festivals found: $count"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
    echo "   Response: $body"
fi
echo ""

# Test 2: List Active Festivals
echo "📋 Test 2: List Active Festivals"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/festivals?filter=active")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Filter by active festivals"
    count=$(echo "$body" | jq '.count' 2>/dev/null || echo "?")
    echo "   Active festivals: $count"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Test 3: List Upcoming Festivals
echo "📋 Test 3: List Upcoming Festivals"
response=$(curl -s -w "\n%{http_code}" "$API_URL/api/festivals?filter=upcoming")
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" = "200" ]; then
    echo -e "${GREEN}✓ PASS${NC} - Filter by upcoming festivals"
    count=$(echo "$body" | jq '.count' 2>/dev/null || echo "?")
    echo "   Upcoming festivals: $count"
else
    echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
fi
echo ""

# Authentication Required Tests
if [ -z "$AUTH_TOKEN" ]; then
    echo -e "${YELLOW}⚠️  AUTH_TOKEN not set. Skipping authenticated tests${NC}"
    echo "   Set AUTH_TOKEN environment variable to run authenticated tests"
    echo "   Example: AUTH_TOKEN=your_jwt_token ./test_festivals.sh"
    echo ""
else
    echo "🔐 Running authenticated tests..."
    echo ""
    
    # Test 4: List Applications (requires creator/admin auth)
    echo "📋 Test 4: List Festival Applications"
    response=$(curl -s -w "\n%{http_code}" \
        -H "Authorization: Bearer $AUTH_TOKEN" \
        "$API_URL/api/festivals/applications")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    if [ "$http_code" = "200" ]; then
        echo -e "${GREEN}✓ PASS${NC} - List applications successful"
        count=$(echo "$body" | jq '.count' 2>/dev/null || echo "?")
        echo "   Applications found: $count"
    elif [ "$http_code" = "401" ]; then
        echo -e "${YELLOW}⚠️  SKIP${NC} - Invalid or expired token"
    elif [ "$http_code" = "403" ]; then
        echo -e "${YELLOW}⚠️  SKIP${NC} - Insufficient permissions (creator/admin required)"
    else
        echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
        echo "   Response: $body"
    fi
    echo ""
    
    # Test 5: Create Festival (requires creator/admin auth)
    echo "📋 Test 5: Create Festival"
    read -p "Create a test festival? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        festival_data='{
            "name": "Test Festival '$(date +%s)'",
            "slug": "test-festival-'$(date +%s)'",
            "description": "Test festival created by API test script",
            "tagline": "Testing the Future",
            "start_date": "2025-06-01T00:00:00Z",
            "end_date": "2025-06-07T00:00:00Z",
            "location": "Test City",
            "categories": ["short"],
            "genres": ["experimental"]
        }'
        
        response=$(curl -s -w "\n%{http_code}" \
            -X POST \
            -H "Authorization: Bearer $AUTH_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$festival_data" \
            "$API_URL/api/festivals")
        
        http_code=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)
        
        if [ "$http_code" = "201" ]; then
            echo -e "${GREEN}✓ PASS${NC} - Festival created"
            festival_id=$(echo "$body" | jq -r '.festival.id' 2>/dev/null)
            if [ ! -z "$festival_id" ] && [ "$festival_id" != "null" ]; then
                echo "   Festival ID: $festival_id"
                echo ""
                echo "   View festival: curl $API_URL/api/festivals/$festival_id"
            fi
        elif [ "$http_code" = "401" ]; then
            echo -e "${YELLOW}⚠️  SKIP${NC} - Invalid or expired token"
        elif [ "$http_code" = "403" ]; then
            echo -e "${YELLOW}⚠️  SKIP${NC} - Insufficient permissions (creator/admin required)"
        else
            echo -e "${RED}✗ FAIL${NC} - HTTP $http_code"
            echo "   Response: $body"
        fi
    else
        echo -e "${YELLOW}⚠️  SKIP${NC} - Test skipped"
    fi
    echo ""
fi

echo "================================"
echo "✅ Tests completed!"
echo ""
echo "📚 API Documentation: $API_URL/docs"
echo "📖 Festival API Docs: See FESTIVAL_API.md"
