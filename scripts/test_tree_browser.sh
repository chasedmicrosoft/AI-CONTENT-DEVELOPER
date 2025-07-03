#!/bin/bash

# Test Tree-Based Directory Browser
# This script demonstrates the new interactive tree navigation

set -e

echo "======================================"
echo "Testing Tree-Based Directory Browser"
echo "======================================"
echo

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Interactive Tree-Based Directory Browser Demo${NC}"
echo
echo "This will launch the manual directory selection with the new tree browser."
echo "You can:"
echo -e "${BLUE}  • Navigate into folders by entering their number (1, 2, 3...)${NC}"
echo -e "${BLUE}  • Select the current directory with 's'${NC}"
echo -e "${BLUE}  • Go back up with '..'${NC}"
echo -e "${BLUE}  • Jump to root with '/'${NC}"
echo -e "${BLUE}  • Quit with 'q'${NC}"
echo
echo -e "${GREEN}Launching directory browser...${NC}"
echo

# Run with a test service to trigger manual selection
python main.py \
    --repo https://github.com/mrcloudchase/azure-management-docs \
    --goal "Test tree browser navigation" \
    --service "test service" \
    --phases 1 \
    -m "test input"

echo
echo "======================================"
echo "Demo completed!"
echo "======================================" 