#!/bin/bash

# Test Directory Selection Improvements
# This script demonstrates the fixes for both error scenarios

set -e

echo "======================================"
echo "Testing Directory Selection Improvements"
echo "======================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test auto-confirm with test service
test_auto_confirm_error() {
    echo -e "${YELLOW}Test 1: Auto-confirm with non-existent service${NC}"
    echo "This should show a clean error message instead of a stack trace"
    echo
    
    python main.py \
        --repo https://github.com/MicrosoftDocs/azure-docs \
        --goal "test error handling" \
        --service "test service" \
        --phases 1 \
        -m "test input" \
        --auto-confirm || true
    
    echo
    echo -e "${GREEN}✓ Test 1 complete - check the error message above${NC}"
    echo
}

# Function to test manual selection
test_manual_selection() {
    echo -e "${YELLOW}Test 2: Manual directory selection (interactive)${NC}"
    echo "This will show the paginated directory browser"
    echo "Try using 'n' for next page, 'p' for previous, or select a number"
    echo
    
    # Note: This will be interactive
    python main.py \
        --repo https://github.com/MicrosoftDocs/azure-docs \
        --goal "Create AKS networking documentation" \
        --service "Azure Kubernetes Service" \
        --phases 1 \
        -m "test input"
    
    echo
    echo -e "${GREEN}✓ Test 2 complete${NC}"
    echo
}

# Function to test successful auto-confirm
test_successful_auto_confirm() {
    echo -e "${YELLOW}Test 3: Auto-confirm with real service${NC}"
    echo "This should work without errors"
    echo
    
    python main.py \
        --repo https://github.com/MicrosoftDocs/azure-docs \
        --goal "Create storage documentation" \
        --service "Azure Storage" \
        --phases 1 \
        -m "Azure Storage provides blob, file, queue, and table storage" \
        --auto-confirm
    
    echo
    echo -e "${GREEN}✓ Test 3 complete${NC}"
    echo
}

# Main menu
echo "Select a test to run:"
echo "1. Test auto-confirm error handling"
echo "2. Test manual directory selection (interactive)"
echo "3. Test successful auto-confirm"
echo "4. Run all tests"
echo
read -p "Enter your choice (1-4): " choice

case $choice in
    1)
        test_auto_confirm_error
        ;;
    2)
        test_manual_selection
        ;;
    3)
        test_successful_auto_confirm
        ;;
    4)
        test_auto_confirm_error
        echo "======================================"
        echo
        echo -e "${YELLOW}Skipping interactive test in batch mode${NC}"
        echo
        echo "======================================"
        echo
        test_successful_auto_confirm
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac

echo
echo "======================================"
echo "All selected tests completed!"
echo "======================================" 