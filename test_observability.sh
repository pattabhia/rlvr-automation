#!/bin/bash
# Test script for RLVR Observability Implementation
#
# This script validates the observability setup without requiring
# OpenTelemetry packages to be installed.

set -e

echo "🧪 Testing RLVR Observability Implementation"
echo "=============================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Test function
test_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $description"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $description (file not found: $file)"
        ((TESTS_FAILED++))
    fi
}

test_directory() {
    local dir=$1
    local description=$2
    
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✅ PASS${NC}: $description"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $description (directory not found: $dir)"
        ((TESTS_FAILED++))
    fi
}

echo "📁 Testing File Structure"
echo "-------------------------"

# Test configuration files
test_file "infrastructure/otel-collector-config.yml" "OpenTelemetry Collector config exists"
test_file "infrastructure/prometheus.yml" "Prometheus config exists"
test_file "infrastructure/loki-config.yml" "Loki config exists"
test_file "infrastructure/tempo-config.yml" "Tempo config exists"
test_file "infrastructure/docker-compose.observability.yml" "Docker Compose observability file exists"

# Test Grafana files
test_file "infrastructure/grafana/datasources.yml" "Grafana datasources config exists"
test_file "infrastructure/grafana/dashboards.yml" "Grafana dashboards config exists"
test_file "infrastructure/grafana/dashboards/rlvr-overview.json" "RLVR overview dashboard exists"

# Test shared module
test_file "shared/observability.py" "Shared observability module exists"
test_file "shared/__init__.py" "Shared module __init__ exists"

# Test documentation
test_file "OBSERVABILITY_QUICKSTART.md" "Quick start guide exists"
test_file "runpod_launch_with_observability.sh" "RunPod deployment script exists"

echo ""
echo "🔍 Testing Docker Compose Configuration"
echo "---------------------------------------"

# Test Docker Compose syntax
if command -v docker &> /dev/null; then
    if docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.observability.yml config > /dev/null 2>&1; then
        echo -e "${GREEN}✅ PASS${NC}: Docker Compose configuration is valid"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: Docker Compose configuration has errors"
        ((TESTS_FAILED++))
    fi
else
    echo -e "${YELLOW}⚠️  SKIP${NC}: Docker not installed, skipping compose validation"
fi

echo ""
echo "📦 Testing Requirements"
echo "----------------------"

# Check if OpenTelemetry packages are in requirements.txt
if grep -q "opentelemetry-api" requirements.txt; then
    echo -e "${GREEN}✅ PASS${NC}: OpenTelemetry packages in requirements.txt"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: OpenTelemetry packages missing from requirements.txt"
    ((TESTS_FAILED++))
fi

echo ""
echo "🔧 Testing Service Instrumentation"
echo "----------------------------------"

# Check if services have been instrumented
for service in api-gateway qa-orchestrator document-ingestion training-data ground-truth; do
    service_file="services/$service/src/main.py"
    if [ -f "$service_file" ]; then
        if grep -q "setup_observability" "$service_file"; then
            echo -e "${GREEN}✅ PASS${NC}: $service is instrumented"
            ((TESTS_PASSED++))
        else
            echo -e "${RED}❌ FAIL${NC}: $service is NOT instrumented"
            ((TESTS_FAILED++))
        fi
    else
        echo -e "${YELLOW}⚠️  SKIP${NC}: $service main.py not found"
    fi
done

echo ""
echo "=============================================="
echo "📊 Test Results"
echo "=============================================="
echo -e "Tests Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Tests Failed: ${RED}$TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All tests passed!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Install dependencies: pip install -r requirements.txt"
    echo "2. Start the platform: cd infrastructure && docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d"
    echo "3. Access Grafana: http://localhost:3000 (admin/admin)"
    exit 0
else
    echo -e "${RED}❌ Some tests failed. Please review the errors above.${NC}"
    exit 1
fi

