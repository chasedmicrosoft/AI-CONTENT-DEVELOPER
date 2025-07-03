# Embedding Pre-generation Script

This standalone script pre-generates embeddings for all directories in a repository, creating the exact cache structure that AI Content Developer expects. This significantly speeds up the first run of the main application.

## Purpose

When you first run AI Content Developer on a repository, it needs to:
1. Chunk all markdown files
2. Generate embeddings for each chunk (slow, many API calls)
3. Cache the results

This script does all of that upfront, so your first run is as fast as subsequent runs.

## Setup

### 1. Install Dependencies

```bash
pip install -r pregen_embeddings_requirements.txt
```

### 2. Configure Azure OpenAI

Create a `.env` file or set environment variables:

```bash
# Required
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_EMBEDDING_DEPLOYMENT="text-embedding-3-small"

# Optional
export AZURE_OPENAI_API_VERSION="2024-08-01-preview"
export GITHUB_TOKEN="your-token"  # Only for private repos
```

### 3. Authenticate with Azure

```bash
az login
```

## Usage

### Basic Usage

```bash
python pregen_embeddings.py --repo https://github.com/MicrosoftDocs/azure-docs
```

### What It Does

1. **Clones the repository** to `./work/tmp/{repo-name}/`
2. **Finds all directories** containing markdown files
3. **Chunks every markdown file** using the same algorithm as the main app
4. **Generates embeddings** for every chunk
5. **Creates cache structure** in `./llm_outputs/embeddings/{repo-name}/`

### Example Output

```
🚀 Pre-generating embeddings for https://github.com/MicrosoftDocs/azure-docs
📥 Cloning repository...
   ✓ Repository cloned successfully
📁 Found 127 directories to process

📂 Processing (1/127): articles
   📄 Processing 15 markdown files...
   ✓ Generated 234 embeddings from 234 chunks

📂 Processing (2/127): articles/aks
   📄 Processing 89 markdown files...
   ✓ Generated 1456 embeddings from 1456 chunks

[... continues for all directories ...]

============================================================
✅ Setup complete! Repository is ready for AI Content Developer
============================================================

Summary:
  • Directories processed: 127
  • Total files: 3,456
  • Total chunks: 28,934
  • Total embeddings: 28,934
  • Time taken: 0:15:32
  • Cache size: 487.3 MB

Your repository is now optimized for fast content generation!
```

## How It Works

The script exactly mirrors the main application's logic:

1. **Same Chunking Algorithm**: Uses identical heading-aware chunking with same size limits
2. **Same Hash Functions**: Generates identical chunk IDs
3. **Same Cache Format**: Creates identical `manifest.json` and chunk files
4. **Same Embedding Context**: Builds embedding text with same frontmatter and heading context

## Performance Notes

- **Time**: Expect ~1 minute per 100 markdown files (depends on file sizes)
- **API Calls**: One embedding call per chunk (typically 5-10 chunks per file)
- **Storage**: ~15-20 MB per 100 files
- **Memory**: Processes files one at a time to minimize memory usage

## Troubleshooting

### "AZURE_OPENAI_ENDPOINT not set"
Make sure you've configured your Azure OpenAI environment variables.

### "Failed to generate embedding"
Check your Azure OpenAI deployment name and ensure you have quota available.

### "Permission denied" on clone
For private repositories, set the `GITHUB_TOKEN` environment variable.

## Integration with Main App

After running this script, when you run the main AI Content Developer:

```bash
python main.py --repo https://github.com/MicrosoftDocs/azure-docs \
    --goal "Create networking guide" \
    --service "Azure Kubernetes Service" \
    -m guide.pdf
```

The application will:
- ✓ Find the repository already cloned
- ✓ Find all embeddings already cached
- ✓ Skip to strategy generation immediately

This typically reduces first-run time from 10-15 minutes to under 1 minute! 