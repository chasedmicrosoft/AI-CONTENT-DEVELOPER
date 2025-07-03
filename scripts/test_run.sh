#!/bin/bash
# AI Content Developer Test Run Script
# Tests basic functionality with minimal inputs

echo "=== AI Content Developer Test Run ==="
echo "This will test basic functionality with AKS documentation materials."
echo ""

# Check if Azure OpenAI is configured
if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo "❌ Error: AZURE_OPENAI_ENDPOINT not set"
    echo "Please set your Azure OpenAI environment variables"
    exit 1
fi

# Use the actual test file and URL
test_file="./inputs/aks-prd-02.docx"
test_url="https://learn.microsoft.com/en-us/azure/aks/azure-cni-powered-by-cilium"
repo_url="https://github.com/MicrosoftDocs/azure-aks-docs"

# Check if test file exists
if [ ! -f "$test_file" ]; then
    echo "❌ Error: Test file not found: $test_file"
    exit 1
fi

echo "Using test materials:"
echo "  - File: $test_file"
echo "  - URL: $test_url"
echo ""

# Phase 1 Test
echo "=== Testing Phase 1: Repository Analysis ==="
python main.py \
    --repo "$repo_url" \
    --goal "Document Cilium networking for AKS" \
    --service "Azure Kubernetes Service" \
    -m "$test_file" "$test_url" \
    --phases 1 \
    --auto-confirm

phase1_result=$?

if [ $phase1_result -eq 0 ]; then
    echo "✅ Phase 1 completed successfully"
else
    echo "❌ Phase 1 failed with exit code: $phase1_result"
    exit $phase1_result
fi

# Check outputs
echo ""
echo "Checking Phase 1 outputs:"
if [ -d "llm_outputs/phase-01" ]; then
    echo "  ✓ Phase 1 output directory created"
    file_count=$(ls -1 llm_outputs/phase-01/step-*/*.json 2>/dev/null | wc -l)
    echo "  ✓ Found $file_count interaction file(s)"
else
    echo "  ✗ Phase 1 output directory not found"
fi

if [ -d "work/tmp" ]; then
    echo "  ✓ Repository cloned/updated"
else
    echo "  ✗ Repository directory not found"
fi

# Phase 2 Test
echo ""
echo "=== Testing Phase 2: Content Discovery ==="
python main.py \
    --repo "$repo_url" \
    --goal "Document Cilium networking for AKS" \
    --service "Azure Kubernetes Service" \
    -m "$test_file" "$test_url" \
    --phases 2 \
    --auto-confirm

phase2_result=$?

if [ $phase2_result -eq 0 ]; then
    echo "✅ Phase 2 completed successfully"
else
    echo "❌ Phase 2 failed with exit code: $phase2_result"
fi

# Check Phase 2 outputs
echo ""
echo "Checking Phase 2 outputs:"
if [ -d "llm_outputs/embeddings" ]; then
    echo "  ✓ Embeddings directory created"
    cache_count=$(find llm_outputs/embeddings -name "*.json" 2>/dev/null | wc -l)
    echo "  ✓ Found $cache_count embedding cache file(s)"
else
    echo "  ✗ Embeddings directory not found"
fi

if [ -d "llm_outputs/phase-02" ]; then
    echo "  ✓ Phase 2 output directory created"
    strategy_count=$(ls -1 llm_outputs/phase-02/step-*/*.json 2>/dev/null | wc -l)
    echo "  ✓ Found $strategy_count strategy file(s)"
else
    echo "  ✗ Phase 2 output directory not found"
fi

# Phase 3 Test
echo ""
echo "=== Testing Phase 3: Content Generation ==="
python main.py \
    --repo "$repo_url" \
    --goal "Document Cilium networking for AKS" \
    --service "Azure Kubernetes Service" \
    -m "$test_file" "$test_url" \
    --phases 3 \
    --auto-confirm

phase3_result=$?

if [ $phase3_result -eq 0 ]; then
    echo "✅ Phase 3 completed successfully"
else
    echo "❌ Phase 3 failed with exit code: $phase3_result"
fi

# Check Phase 3 outputs
echo ""
echo "Checking Phase 3 outputs:"
if [ -d "llm_outputs/preview" ]; then
    echo "  ✓ Preview directory created"
    preview_count=$(find llm_outputs/preview -name "*.md" 2>/dev/null | wc -l)
    echo "  ✓ Found $preview_count generated content file(s)"
    
    # Show generated files
    if [ $preview_count -gt 0 ]; then
        echo ""
        echo "Generated files:"
        find llm_outputs/preview -name "*.md" -type f | head -5
    fi
else
    echo "  ✗ Preview directory not found"
fi

# Phase 4 Test
echo ""
echo "=== Testing Phase 4: TOC Management ==="
python main.py \
    --repo "$repo_url" \
    --goal "Document Cilium networking for AKS" \
    --service "Azure Kubernetes Service" \
    -m "$test_file" "$test_url" \
    --phases 4 \
    --auto-confirm

phase4_result=$?

if [ $phase4_result -eq 0 ]; then
    echo "✅ Phase 4 completed successfully"
else
    echo "❌ Phase 4 failed with exit code: $phase4_result"
fi

# Check Phase 4 outputs
echo ""
echo "Checking Phase 4 outputs:"
if [ -d "llm_outputs/phase-04" ]; then
    echo "  ✓ Phase 4 output directory created"
    toc_count=$(ls -1 llm_outputs/phase-04/step-*/*.json 2>/dev/null | wc -l)
    echo "  ✓ Found $toc_count TOC interaction file(s)"
else
    echo "  ✗ Phase 4 output directory not found"
fi

if [ -d "llm_outputs/preview/toc" ]; then
    echo "  ✓ TOC preview directory created"
    toc_preview_count=$(ls -1 llm_outputs/preview/toc/*.yml 2>/dev/null | wc -l)
    echo "  ✓ Found $toc_preview_count TOC preview file(s)"
else
    echo "  ✗ TOC preview directory not found"
fi

# Summary
echo ""
echo "=== Test Summary ==="
total_errors=0
if [ $phase1_result -ne 0 ]; then
    echo "❌ Phase 1: Failed"
    ((total_errors++))
else
    echo "✅ Phase 1: Passed"
fi

if [ $phase2_result -ne 0 ]; then
    echo "❌ Phase 2: Failed"
    ((total_errors++))
else
    echo "✅ Phase 2: Passed"
fi

if [ $phase3_result -ne 0 ]; then
    echo "❌ Phase 3: Failed"
    ((total_errors++))
else
    echo "✅ Phase 3: Passed"
fi

if [ $phase4_result -ne 0 ]; then
    echo "❌ Phase 4: Failed"
    ((total_errors++))
else
    echo "✅ Phase 4: Passed"
fi

echo ""
if [ $total_errors -eq 0 ]; then
    echo "🎉 All tests passed! The application is working correctly."
    exit 0
else
    echo "❌ $total_errors phase(s) failed. Check the logs above for details."
    exit 1
fi 