#!/bin/bash
# Test script to verify Phase 3 UPDATE fix

echo "Testing Phase 3 UPDATE fix..."
echo ""

# Run phases 2 and 3 to test the update functionality
python main.py \
    --repo https://github.com/MicrosoftDocs/azure-aks-docs \
    --goal "Update existing cilium how to article to add section on cilium endpoint slices" \
    --service "Azure Kubernetes Service" \
    -m inputs/material.pdf \
    --phases 23 \
    --auto-confirm \
    --content-limit 10000000

echo ""
echo "If Phase 3 completes without the 'missing positional arguments' error, the fix is working!"
echo "Check llm_outputs/preview/update/ for the generated content" 