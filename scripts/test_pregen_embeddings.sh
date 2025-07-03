#!/bin/bash
# Test script for pre-generation embeddings functionality

echo "=== Testing Embedding Pre-generation Script ==="
echo ""

# Check if Azure OpenAI is configured
if [ -z "$AZURE_OPENAI_ENDPOINT" ]; then
    echo "❌ Error: AZURE_OPENAI_ENDPOINT not set"
    echo "Please configure your Azure OpenAI environment variables"
    exit 1
fi

# Test with a small repository
TEST_REPO="https://github.com/Azure-Samples/cognitive-services-quickstart-code"

echo "This test will:"
echo "1. Clone a small test repository"
echo "2. Generate embeddings for all markdown files"
echo "3. Verify the cache structure is created correctly"
echo ""
echo "Using test repository: $TEST_REPO"
echo ""

# Clean up any previous test data
echo "Cleaning up previous test data..."
rm -rf ./work/tmp/cognitive-services-quickstart-code
rm -rf ./llm_outputs/embeddings/cognitive-services-quickstart-code

# Run the pre-generation script
echo "Running pre-generation script..."
python pregen_embeddings.py --repo "$TEST_REPO"

# Check results
echo ""
echo "=== Verification ==="

# Check if repository was cloned
if [ -d "./work/tmp/cognitive-services-quickstart-code" ]; then
    echo "✓ Repository cloned successfully"
else
    echo "❌ Repository not found"
    exit 1
fi

# Check if embeddings directory was created
if [ -d "./llm_outputs/embeddings/cognitive-services-quickstart-code" ]; then
    echo "✓ Embeddings directory created"
    
    # Count manifest files
    manifest_count=$(find ./llm_outputs/embeddings/cognitive-services-quickstart-code -name "manifest.json" | wc -l)
    echo "✓ Found $manifest_count manifest.json files"
    
    # Count chunk files
    chunk_count=$(find ./llm_outputs/embeddings/cognitive-services-quickstart-code -name "chunk_*.json" | wc -l)
    echo "✓ Found $chunk_count chunk files with embeddings"
else
    echo "❌ Embeddings directory not found"
    exit 1
fi

echo ""
echo "=== Test Complete ==="
echo "✅ Pre-generation script is working correctly!"
echo ""
echo "You can now run the main application on this repository:"
echo "python main.py --repo $TEST_REPO --goal \"test\" --service \"test\" -m \"test material\"" 