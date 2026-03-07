# RunPod Serverless Setup Guide

## Overview
Deploy your fine-tuned Qwen model as a RunPod Serverless endpoint for auto-scaling, pay-per-request inference.

## Benefits
- **Auto-scaling**: 0 to N GPUs based on demand
- **Pay per request**: No idle GPU costs
- **Cold start**: ~30-60s (first request after idle)
- **Warm requests**: ~2-5s per request

## Step 1: Prepare Docker Image

### Option A: Build Locally (if you have Docker + NVIDIA GPU)
```bash
cd backend/finetuning

# Copy your LoRA adapter files
cp -r /path/to/finetuned_models ./finetuned_models

# Build image
docker build -f Dockerfile.serverless -t yourusername/qwen-serverless:latest .

# Push to Docker Hub
docker login
docker push yourusername/qwen-serverless:latest
```

### Option B: Build on RunPod (Recommended)
1. Create a GPU Pod on RunPod (temporary, for building)
2. Upload files via Jupyter:
   - `runpod_serverless_handler.py`
   - `Dockerfile.serverless`
   - Your LoRA adapter folder
3. Build in terminal:
```bash
cd /workspace
docker build -f Dockerfile.serverless -t yourusername/qwen-serverless:latest .
docker push yourusername/qwen-serverless:latest
```

## Step 2: Create Serverless Endpoint

1. Go to [RunPod Serverless](https://www.runpod.io/console/serverless)
2. Click **"New Endpoint"**
3. Configure:
   - **Name**: `qwen-coder-serverless`
   - **Docker Image**: `yourusername/qwen-serverless:latest`
   - **GPU Type**: RTX 4090 or A100 (24GB+ VRAM)
   - **Max Workers**: 3 (adjust based on load)
   - **Idle Timeout**: 5 seconds (for cost savings)
   - **Flash Boot**: Enable (faster cold starts)

4. Click **"Create Endpoint"**
5. Copy the **Endpoint ID** (e.g., `abc123xyz`)

## Step 3: Configure BharatBuild

Update your `.env`:
```env
# RunPod Serverless endpoint
QWEN_API_URL=https://api.runpod.ai/v2/abc123xyz
QWEN_SERVERLESS=true
RUNPOD_API_KEY=your_runpod_api_key
```

Get your RunPod API Key:
1. Go to [RunPod Settings](https://www.runpod.io/console/user/settings)
2. Create new API Key
3. Copy and add to `.env`

## Step 4: Update qwen_client.py

The client needs to use RunPod's serverless API format:

```python
# Request format for serverless
{
    "input": {
        "prompt": "Your prompt here",
        "max_tokens": 8192,
        "temperature": 0.7
    }
}

# Endpoint: POST https://api.runpod.ai/v2/{endpoint_id}/runsync
# Headers: Authorization: Bearer {RUNPOD_API_KEY}
```

## Step 5: Test the Endpoint

```bash
curl -X POST "https://api.runpod.ai/v2/YOUR_ENDPOINT_ID/runsync" \
  -H "Authorization: Bearer YOUR_RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "Create a React button component",
      "max_tokens": 1000
    }
  }'
```

## Pricing Estimate

| GPU | Price/sec | 1000 requests (5s each) |
|-----|-----------|-------------------------|
| RTX 4090 | $0.00044 | ~$2.20 |
| A100 40GB | $0.00124 | ~$6.20 |
| H100 | $0.00199 | ~$9.95 |

## Troubleshooting

### Cold Start Too Slow
- Enable **Flash Boot**
- Use smaller GPU (faster initialization)
- Increase **Min Workers** to 1 (keeps one warm, but costs more)

### Out of Memory
- Use A100 80GB or H100
- Reduce `max_model_len` in handler

### Request Timeout
- Increase endpoint timeout in RunPod console
- Default is 300s, increase if needed

## Alternative: Use RunPod's Ready Templates

RunPod has pre-built vLLM templates:
1. Go to Serverless > Templates
2. Search for "vLLM"
3. Use template and just add your LoRA adapter

This skips Docker building entirely!
