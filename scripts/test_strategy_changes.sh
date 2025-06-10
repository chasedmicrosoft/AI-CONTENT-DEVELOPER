#!/bin/bash
# Test script for strategy generation changes

echo "Testing updated strategy generation with full material content..."
echo "This will test:"
echo "- Full material content is included in prompts (no truncation)"
echo "- Only top 3 most relevant files are analyzed"
echo ""

# Run a test with phase 2 only to see the strategy generation
python main.py https://github.com/MicrosoftDocs/azure-aks-docs \
    "Update existing cilium how to article to add section on cilium endpoint slices" \
    "Azure Kubernetes Service" \
    inputs/material.pdf \
    --phases 2 \
    --auto-confirm \
    --content-limit 10000000

echo ""
echo "Check llm_outputs/phase-02/ for the strategy generation to verify:"
echo "1. Materials include full content without truncation"
echo "2. Only 3 files are analyzed"
echo "3. No [... content truncated ...] markers appear" 