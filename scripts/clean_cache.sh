#!/bin/bash

# Clean embeddings cache script for AI Content Developer

echo "AI Content Developer - Cache Cleaner"
echo "===================================="
echo ""

# Check if llm_outputs/embeddings exists
if [ -d "llm_outputs/embeddings" ]; then
    echo "Found embeddings cache directory"
    
    # Show cache size
    CACHE_SIZE=$(du -sh llm_outputs/embeddings 2>/dev/null | cut -f1)
    echo "Current cache size: ${CACHE_SIZE:-unknown}"
    
    # Ask for confirmation unless --force is used
    if [[ "$1" != "--force" ]]; then
        echo ""
        read -p "Are you sure you want to clean the embeddings cache? (y/N) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "Cache cleaning cancelled."
            exit 0
        fi
    fi
    
    # Clean the cache
    echo "Cleaning embeddings cache..."
    rm -rf llm_outputs/embeddings/*
    
    echo "✅ Cache cleaned successfully!"
else
    echo "No embeddings cache found at llm_outputs/embeddings"
fi

echo ""
echo "Note: The cache will be rebuilt automatically on the next run." 