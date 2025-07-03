#!/bin/bash
# Test with Azure docs repository (large repo scenario)

echo "Testing large repository handling with Azure docs..."
echo "This will test the condensed structure feature for repositories with >5000 files"
echo ""

# Test with AKS service area
python main.py https://github.com/MicrosoftDocs/azure-docs \
    "Create comprehensive Azure Kubernetes Service (AKS) troubleshooting guide" \
    "Azure Kubernetes Service" \
    inputs/material.pdf \
    --phases 1 \
    --auto-confirm

echo ""
echo "Check logs/app.log for details about repository size detection" 