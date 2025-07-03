#!/bin/bash
# AI Content Developer Reset Script
# Provides options for partial or full reset

echo "=== AI Content Developer Reset Tool ==="
echo ""

# Parse command line arguments
RESET_TYPE=${1:-"help"}

show_help() {
    echo "Usage: $0 [option]"
    echo ""
    echo "Options:"
    echo "  help        Show this help message"
    echo "  cache       Clear embeddings cache only"
    echo "  outputs     Clear all outputs (preserves cache)"
    echo "  preview     Clear preview files only"
    echo "  full        Full reset (all outputs and work)"
    echo "  deps        Reinstall dependencies"
    echo ""
    echo "Examples:"
    echo "  $0 cache    # Clear embeddings if corrupted"
    echo "  $0 full     # Complete reset before fresh run"
}

confirm_action() {
    echo -n "Are you sure? This cannot be undone. [y/N]: "
    read -r response
    case "$response" in
        [yY][eE][sS]|[yY]) 
            return 0
            ;;
        *)
            echo "Cancelled."
            exit 0
            ;;
    esac
}

case $RESET_TYPE in
    "help")
        show_help
        ;;
        
    "cache")
        echo "This will clear the embeddings cache."
        confirm_action
        echo "Clearing embeddings cache..."
        rm -rf llm_outputs/embeddings/
        echo "✓ Embeddings cache cleared"
        ;;
        
    "outputs")
        echo "This will clear all LLM outputs but preserve embeddings cache."
        confirm_action
        echo "Clearing outputs..."
        rm -rf llm_outputs/materials_summary/
        rm -rf llm_outputs/decisions/
        rm -rf llm_outputs/content_strategy/
        rm -rf llm_outputs/preview/
        rm -rf llm_outputs/generation/
        echo "✓ Outputs cleared (cache preserved)"
        ;;
        
    "preview")
        echo "This will clear preview files only."
        confirm_action
        echo "Clearing preview files..."
        rm -rf llm_outputs/preview/
        echo "✓ Preview files cleared"
        ;;
        
    "full")
        echo "This will perform a FULL RESET:"
        echo "  - Remove all outputs"
        echo "  - Clear work directory"
        echo "  - Remove Python cache"
        echo ""
        confirm_action
        
        echo "Performing full reset..."
        
        # Remove outputs
        echo -n "  Removing outputs... "
        rm -rf llm_outputs/
        echo "✓"
        
        # Clear work directory
        echo -n "  Clearing work directory... "
        rm -rf work/tmp/
        echo "✓"
        
        # Remove Python cache
        echo -n "  Removing Python cache... "
        rm -rf __pycache__/
        find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
        find . -name "*.pyc" -delete 2>/dev/null
        echo "✓"
        
        echo ""
        echo "✅ Full reset complete!"
        echo ""
        echo "Next steps:"
        echo "1. Run health check: ./scripts/health_check.sh"
        echo "2. Run test: ./scripts/test_run.sh"
        ;;
        
    "deps")
        echo "This will reinstall all Python dependencies."
        confirm_action
        echo "Reinstalling dependencies..."
        pip install --force-reinstall -r requirements.txt
        echo "✓ Dependencies reinstalled"
        echo ""
        echo "Run health check to verify: ./scripts/health_check.sh"
        ;;
        
    *)
        echo "Unknown option: $RESET_TYPE"
        echo ""
        show_help
        exit 1
        ;;
esac

# Show disk usage after reset
echo ""
echo "Current disk usage:"
if [ -d "llm_outputs" ]; then
    du -sh llm_outputs/ 2>/dev/null || echo "llm_outputs: not found"
else
    echo "llm_outputs: not found"
fi

if [ -d "work" ]; then
    du -sh work/ 2>/dev/null || echo "work: not found"
else
    echo "work: not found"
fi 