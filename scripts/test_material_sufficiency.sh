#!/bin/bash
# Test script to demonstrate pre-generation material sufficiency check

echo "Testing Pre-Generation Material Sufficiency Check"
echo "================================================="
echo ""
echo "This test will attempt to create a comprehensive troubleshooting guide"
echo "with minimal materials, demonstrating how the system prevents wasted"
echo "generation when materials are insufficient."
echo ""

# Test with insufficient materials (should skip generation)
echo "Test 1: Insufficient Materials (should skip generation)"
echo "------------------------------------------------------"
python main.py \
    --repo https://github.com/MicrosoftDocs/azure-aks-docs \
    --goal "Create a comprehensive troubleshooting guide for all Cilium networking issues including advanced diagnostics, performance tuning, and security troubleshooting" \
    --service "Azure Kubernetes Service" \
    -m https://learn.microsoft.com/en-us/azure/aks/intro-kubernetes \
    --phases 123 \
    --auto-confirm \
    --content-limit 10000000

echo ""
echo "The above should have skipped content generation due to insufficient materials."
echo ""
echo "Test 2: With Better Materials (should proceed with warnings)"
echo "-----------------------------------------------------------"
python main.py \
    --repo https://github.com/MicrosoftDocs/azure-aks-docs \
    --goal "Update the Cilium configuration guide with troubleshooting tips" \
    --service "Azure Kubernetes Service" \
    -m https://learn.microsoft.com/en-us/azure/aks/azure-cni-powered-by-cilium \
    --phases 123 \
    --auto-confirm \
    --content-limit 10000000

echo ""
echo "Test complete! Check the output above to see:"
echo "1. Pre-generation material analysis with AI thinking"
echo "2. Coverage percentage and warnings"
echo "3. Skipped results in the final summary" 