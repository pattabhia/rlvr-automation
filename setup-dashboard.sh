#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

clear

echo -e "${BOLD}${CYAN}=========================================="
echo -e "  RLVR DASHBOARD SETUP"
echo -e "==========================================${NC}"
echo ""

# Step 1: Make scripts executable
echo -e "${YELLOW}Step 1: Making scripts executable...${NC}"
chmod +x rlvr-dashboard.sh 2>/dev/null
chmod +x test-pipeline.sh 2>/dev/null
chmod +x inject-sample-data.sh 2>/dev/null
echo -e "${GREEN}✓ Scripts are now executable${NC}"
echo ""

# Step 2: Check if services are running
echo -e "${YELLOW}Step 2: Checking services...${NC}"
services_running=0

if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ QA Orchestrator is running${NC}"
    services_running=1
else
    echo -e "${RED}✗ QA Orchestrator is not running${NC}"
fi

if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ API Gateway is running${NC}"
    services_running=1
else
    echo -e "${RED}✗ API Gateway is not running${NC}"
fi

echo ""

# Step 3: Check for existing data
echo -e "${YELLOW}Step 3: Checking for existing pipeline data...${NC}"
if [ -f "/workspace/logs/qa-orchestrator.log" ] && [ -s "/workspace/logs/qa-orchestrator.log" ]; then
    log_lines=$(wc -l < /workspace/logs/qa-orchestrator.log)
    echo -e "${GREEN}✓ Found existing logs ($log_lines lines)${NC}"
    has_data=1
else
    echo -e "${YELLOW}⚠ No existing logs found${NC}"
    has_data=0
fi

dpo_files=$(find /workspace/rlvr-automation/data -name "*dpo*.json" 2>/dev/null | wc -l)
if [ $dpo_files -gt 0 ]; then
    echo -e "${GREEN}✓ Found $dpo_files DPO files${NC}"
else
    echo -e "${YELLOW}⚠ No DPO files found${NC}"
fi

echo ""

# Step 4: Offer options
echo -e "${BOLD}${BLUE}What would you like to do?${NC}"
echo ""
echo -e "  ${CYAN}1.${NC} View dashboard with existing data (if any)"
echo -e "  ${CYAN}2.${NC} Inject sample data and view dashboard"
echo -e "  ${CYAN}3.${NC} Send test query and view dashboard"
echo -e "  ${CYAN}4.${NC} Just view the dashboard"
echo -e "  ${CYAN}5.${NC} Exit"
echo ""

read -p "Enter choice (1-5): " choice

case $choice in
    1)
        echo ""
        echo -e "${GREEN}Launching dashboard with existing data...${NC}"
        sleep 1
        ./rlvr-dashboard.sh
        ;;
    2)
        echo ""
        echo -e "${YELLOW}Injecting sample data...${NC}"
        ./inject-sample-data.sh
        echo ""
        echo -e "${GREEN}Launching dashboard...${NC}"
        sleep 2
        ./rlvr-dashboard.sh
        ;;
    3)
        if [ $services_running -eq 0 ]; then
            echo ""
            echo -e "${RED}Error: Services are not running!${NC}"
            echo -e "${YELLOW}Please start the services first.${NC}"
            exit 1
        fi
        echo ""
        echo -e "${YELLOW}Sending test query...${NC}"
        ./test-pipeline.sh
        echo ""
        echo -e "${GREEN}Launching dashboard...${NC}"
        sleep 2
        ./rlvr-dashboard.sh
        ;;
    4)
        echo ""
        echo -e "${GREEN}Launching dashboard...${NC}"
        sleep 1
        ./rlvr-dashboard.sh
        ;;
    5)
        echo ""
        echo -e "${YELLOW}Exiting...${NC}"
        exit 0
        ;;
    *)
        echo ""
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

