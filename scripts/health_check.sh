#!/bin/bash
# AI Content Developer Health Check Script

echo "=== AI Content Developer Health Check ==="
echo "Date: $(date)"
echo ""

# Check Python
echo -n "Python: "
python --version 2>&1 || echo "NOT FOUND"

# Check Python path
echo -n "Python Path: "
which python || echo "NOT FOUND"

# Check API Key
echo -n "OpenAI API Key: "
if [ -z "$OPENAI_API_KEY" ]; then
    echo "NOT SET ❌"
else
    echo "SET ✓ (${#OPENAI_API_KEY} chars)"
fi

# Check dependencies
echo ""
echo "Dependencies:"
echo -n "  openai: "
pip show openai 2>/dev/null | grep Version || echo "NOT INSTALLED ❌"
echo -n "  PyPDF2: "
pip show PyPDF2 2>/dev/null | grep Version || echo "NOT INSTALLED ❌"
echo -n "  python-docx: "
pip show python-docx 2>/dev/null | grep Version || echo "NOT INSTALLED ❌"
echo -n "  beautifulsoup4: "
pip show beautifulsoup4 2>/dev/null | grep Version || echo "NOT INSTALLED ❌"
echo -n "  gitpython: "
pip show gitpython 2>/dev/null | grep Version || echo "NOT INSTALLED ❌"

# Check directories
echo ""
echo "Directory Structure:"
if [ -d "llm_outputs" ]; then
    echo "  llm_outputs/ ✓"
    subdirs=("materials_summary" "decisions" "content_strategy" "embeddings" "preview")
    for dir in "${subdirs[@]}"; do
        if [ -d "llm_outputs/$dir" ]; then
            echo "    - $dir/ ✓"
        else
            echo "    - $dir/ ✗ (will be created on first run)"
        fi
    done
else
    echo "  llm_outputs/ ✗ (will be created on first run)"
fi

if [ -d "work" ]; then
    echo "  work/ ✓"
else
    echo "  work/ ✗ (will be created on first run)"
fi

if [ -d "plans" ]; then
    echo "  plans/ ✓"
    echo -n "    - Active plans: "
    find plans -name "*.md" -not -name "*_todo.md" -not -name "*_summary.md" -not -name "TEMPLATE_*.md" 2>/dev/null | wc -l
else
    echo "  plans/ ✗ (create for development workflow)"
fi

# Check file permissions
echo ""
echo "File Permissions:"
echo -n "  main.py: "
if [ -r "main.py" ]; then
    echo "readable ✓"
else
    echo "NOT READABLE ❌"
fi

# Network connectivity
echo ""
echo "Network Connectivity:"
echo -n "  GitHub: "
if ping -c 1 github.com &> /dev/null; then
    echo "✓"
else
    echo "❌"
fi
echo -n "  OpenAI API: "
if ping -c 1 api.openai.com &> /dev/null; then
    echo "✓"
else
    echo "❌"
fi

# Summary
echo ""
echo "=== Summary ==="
errors=0

if [ -z "$OPENAI_API_KEY" ]; then
    echo "❌ OpenAI API key not set"
    ((errors++))
fi

if ! command -v python &> /dev/null; then
    echo "❌ Python not found"
    ((errors++))
fi

if ! pip show openai &> /dev/null; then
    echo "❌ Required packages not installed"
    ((errors++))
fi

if [ $errors -eq 0 ]; then
    echo "✅ All checks passed! Ready to run."
else
    echo "❌ $errors issue(s) found. Please fix before running."
fi 