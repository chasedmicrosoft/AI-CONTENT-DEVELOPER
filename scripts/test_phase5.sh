#!/bin/bash
# Test Phase 5 functionality

echo "Testing Phase 5: Content Remediation"
echo "===================================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test repository (small repo for testing)
TEST_REPO="https://github.com/Azure-Samples/aks-store-demo"
TEST_GOAL="Create comprehensive documentation for AKS Store Demo application"
TEST_SERVICE="Azure Kubernetes Service"
TEST_MATERIAL="README.md"

echo -e "${YELLOW}Running Phase 1-3 to generate content first...${NC}"

# Run phases 1-3 to generate content
python main.py \
    --repo "$TEST_REPO" \
    --goal "$TEST_GOAL" \
    --service "$TEST_SERVICE" \
    -m "$TEST_MATERIAL" \
    --phases 123 \
    --auto-confirm \
    --work-dir ./test_phase5_work

if [ $? -ne 0 ]; then
    echo -e "${RED}Failed to run phases 1-3${NC}"
    exit 1
fi

echo -e "${GREEN}Phases 1-3 completed successfully${NC}"
echo ""

echo -e "${YELLOW}Now running Phase 5 (Content Remediation)...${NC}"

# Run phase 5 only
python main.py \
    --repo "$TEST_REPO" \
    --goal "$TEST_GOAL" \
    --service "$TEST_SERVICE" \
    -m "$TEST_MATERIAL" \
    --phases 5 \
    --auto-confirm \
    --work-dir ./test_phase5_work

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Phase 5 completed successfully!${NC}"
    echo ""
    echo "Check the output in:"
    echo "  ./llm_outputs/preview/phase5/seo/"
    echo "  ./llm_outputs/preview/phase5/security/"
    echo "  ./llm_outputs/preview/phase5/final/"
else
    echo -e "${RED}Phase 5 failed${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}Testing all phases (1-5) in one run...${NC}"

# Clean up for fresh test
rm -rf ./test_phase5_work
rm -rf ./llm_outputs/preview/phase5/

# Run all phases
python main.py \
    --repo "$TEST_REPO" \
    --goal "$TEST_GOAL" \
    --service "$TEST_SERVICE" \
    -m "$TEST_MATERIAL" \
    --phases all \
    --auto-confirm \
    --work-dir ./test_phase5_work

if [ $? -eq 0 ]; then
    echo -e "${GREEN}All phases (1-5) completed successfully!${NC}"
else
    echo -e "${RED}Full workflow failed${NC}"
    exit 1
fi

# Clean up test directories
echo ""
echo -e "${YELLOW}Cleaning up test directories...${NC}"
rm -rf ./test_phase5_work

echo -e "${GREEN}Phase 5 testing complete!${NC}" 