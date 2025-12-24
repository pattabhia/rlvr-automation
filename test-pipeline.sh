#!/bin/bash

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}${CYAN}=========================================="
echo -e "  RLVR PIPELINE TEST SCRIPT"
echo -e "==========================================${NC}"
echo ""

# Check if services are running
echo -e "${YELLOW}Checking services...${NC}"
if ! curl -s http://localhost:8000/health > /dev/null 2>&1 && ! curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${RED}❌ API Gateway or QA Orchestrator not running!${NC}"
    echo -e "${YELLOW}Please start services first.${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Services are running${NC}"
echo ""

# Sample questions
questions=(
    "What is machine learning?"
    "Explain the difference between supervised and unsupervised learning"
    "What are neural networks?"
    "How does gradient descent work?"
    "What is the purpose of activation functions?"
)

echo -e "${BOLD}${BLUE}Select a test question:${NC}"
echo ""
for i in "${!questions[@]}"; do
    echo -e "  ${CYAN}$((i+1)).${NC} ${questions[$i]}"
done
echo -e "  ${CYAN}6.${NC} Custom question"
echo ""

read -p "Enter choice (1-6): " choice

if [ "$choice" == "6" ]; then
    read -p "Enter your question: " custom_question
    question="$custom_question"
elif [ "$choice" -ge 1 ] && [ "$choice" -le 5 ]; then
    question="${questions[$((choice-1))]}"
else
    echo -e "${RED}Invalid choice${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Sending question to pipeline...${NC}"
echo -e "${BOLD}Question:${NC} $question"
echo ""

# Send request to API Gateway or QA Orchestrator
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    endpoint="http://localhost:8000/api/v1/qa/ask"
else
    endpoint="http://localhost:8001/api/v1/qa/ask"
fi

response=$(curl -s -X POST "$endpoint" \
    -H "Content-Type: application/json" \
    -d "{
        \"question\": \"$question\",
        \"context\": \"This is a test query for the RLVR pipeline\",
        \"num_candidates\": 3
    }" 2>&1)

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Request sent successfully!${NC}"
    echo ""
    echo -e "${BOLD}Response:${NC}"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo ""
    echo -e "${YELLOW}Now check the dashboard to see the pipeline in action!${NC}"
    echo -e "${CYAN}Run: ./rlvr-dashboard.sh${NC}"
else
    echo -e "${RED}✗ Request failed${NC}"
    echo "$response"
fi

echo ""

