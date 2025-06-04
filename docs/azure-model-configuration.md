# Azure OpenAI Model Configuration Guide

## Overview
AI Content Developer now uses Azure OpenAI with Microsoft Entra ID authentication. This guide explains how to configure your Azure OpenAI deployments for different operations.

## Authentication
The application uses `DefaultAzureCredential` which supports multiple authentication methods:
- Azure CLI (recommended for development): `az login`
- Managed Identity (for production/Azure deployment)
- Environment variables (service principal)
- VS Code Azure extension
- Azure PowerShell

## Configuration File
Copy `env.example` to `.env` and update with your Azure OpenAI settings:

```bash
cp env.example .env
```

## Environment Variables

### Required Configuration
- **AZURE_OPENAI_ENDPOINT**: Your Azure OpenAI endpoint URL (required)
  ```
  https://your-resource.openai.azure.com/
  ```

### Deployment Configuration

#### Primary Deployments
These are the main deployments used throughout the application:

- **AZURE_OPENAI_COMPLETION_DEPLOYMENT**: Model deployment for all completion operations
  - Default: `gpt-4`
  - Used for all LLM operations: content generation, material processing, directory detection, TOC management, strategy generation, etc.
  - Recommended models: GPT-4, GPT-4 Turbo
  
- **AZURE_OPENAI_EMBEDDING_DEPLOYMENT**: Embedding model deployment
  - Default: `text-embedding-3-small`
  - Used for semantic similarity searches in the strategy phase
  - Recommended models: text-embedding-3-small, text-embedding-3-large

### Other Settings
- **AZURE_OPENAI_API_VERSION**: API version to use (default: `2024-08-01-preview`)
- **AZURE_OPENAI_TEMPERATURE**: Temperature for most operations (default: `0.3`)
- **AZURE_OPENAI_CREATIVE_TEMPERATURE**: Temperature for creative content (default: `0.7`)

## Example Configurations

### Standard Configuration
```env
AZURE_OPENAI_ENDPOINT=https://my-openai.openai.azure.com/
AZURE_OPENAI_COMPLETION_DEPLOYMENT=gpt-4
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

### Performance-Optimized Configuration
```env
AZURE_OPENAI_ENDPOINT=https://my-openai.openai.azure.com/
AZURE_OPENAI_COMPLETION_DEPLOYMENT=gpt-4-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-large
AZURE_OPENAI_API_VERSION=2024-08-01-preview
```

### Budget-Conscious Configuration
```env
AZURE_OPENAI_ENDPOINT=https://my-openai.openai.azure.com/
AZURE_OPENAI_COMPLETION_DEPLOYMENT=gpt-35-turbo
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_OPENAI_TEMPERATURE=0.2
```

## Creating Deployments in Azure

1. **Navigate to your Azure OpenAI resource** in the Azure Portal

2. **Go to "Model deployments"** section

3. **Create deployments** for each model you need:
   - Click "Create new deployment"
   - Select the model (e.g., gpt-4, gpt-35-turbo)
   - Choose a deployment name (this is what you'll use in the config)
   - Set capacity (TPM - Tokens Per Minute)

4. **Recommended models for each deployment**:
   - **Completion**: GPT-4 or GPT-4 Turbo (used for all LLM operations)
   - **Embedding**: text-embedding-3-small or text-embedding-3-large

## Authentication Troubleshooting

### Azure CLI Authentication
```bash
# Login
az login

# List subscriptions
az account list

# Set subscription
az account set --subscription "Your Subscription Name"

# Verify current account
az account show
```

### Service Principal Authentication
```bash
export AZURE_CLIENT_ID="your-client-id"
export AZURE_CLIENT_SECRET="your-client-secret"
export AZURE_TENANT_ID="your-tenant-id"
```

### Common Issues

1. **"AZURE_OPENAI_ENDPOINT environment variable not set"**
   - Ensure you've set the endpoint in your .env file
   - Format: `https://your-resource.openai.azure.com/`

2. **Authentication failures**
   - Run `az login` to authenticate with Azure CLI
   - Check you have the correct permissions on the OpenAI resource
   - Verify your subscription with `az account show`

3. **"Deployment not found"**
   - Verify the deployment name matches exactly what's in Azure
   - Check the deployment exists in your Azure OpenAI resource
   - Ensure you're using the correct endpoint

4. **Rate limit errors**
   - Check your deployment's TPM (Tokens Per Minute) quota
   - Consider using different deployments for different operations
   - Implement retry logic (already included with tenacity)

## Best Practices

1. **Use appropriate models**: Match deployment capacity to operation complexity
2. **Monitor usage**: Track token consumption in Azure Portal
3. **Set quotas**: Configure TPM limits to control costs
4. **Use deployment names that reflect their purpose**: e.g., `content-gen-gpt4`, `simple-tasks-gpt35`
5. **Regional considerations**: Deploy in regions close to your users for better latency 