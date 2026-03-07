#!/bin/bash
# RunPod Serverless Deployment Script
# Run this on a RunPod GPU Pod

echo "=== BharatBuild Qwen Serverless Deployment ==="

# Step 1: Create workspace
cd /workspace
mkdir -p qwen-serverless
cd qwen-serverless

# Step 2: Create the handler file
cat > handler.py << 'HANDLER_EOF'
"""
RunPod Serverless Handler for Fine-tuned Qwen Model
Auto-downloads LoRA adapter from HuggingFace on first run.
"""

import runpod
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
import os

# Global model instance
llm = None
lora_loaded = False

# LoRA adapter settings
LORA_HF_REPO = "kishoreudatha/qwen-coder-lora"
LORA_PATH = "/workspace/lora_adapter"

def download_lora_adapter():
    """Download LoRA adapter from HuggingFace if not already present"""
    global lora_loaded

    if lora_loaded and os.path.exists(LORA_PATH):
        return True

    try:
        print(f"Downloading LoRA adapter from {LORA_HF_REPO}...")
        from huggingface_hub import snapshot_download

        snapshot_download(
            repo_id=LORA_HF_REPO,
            local_dir=LORA_PATH,
            local_dir_use_symlinks=False
        )

        lora_loaded = True
        print(f"LoRA adapter downloaded successfully to {LORA_PATH}")
        print(f"Files: {os.listdir(LORA_PATH)}")
        return True

    except Exception as e:
        print(f"Failed to download LoRA adapter: {e}")
        return False

def load_model():
    """Load model once when container starts"""
    global llm
    if llm is None:
        download_lora_adapter()

        print("Loading Qwen model with vLLM...")
        llm = LLM(
            model="Qwen/Qwen2.5-Coder-7B-Instruct",
            enable_lora=True,
            max_lora_rank=64,
            gpu_memory_utilization=0.90,
            max_model_len=16384,
            trust_remote_code=True,
        )
        print("Model loaded successfully!")
    return llm

def handler(job):
    """RunPod serverless handler function."""
    job_input = job["input"]

    prompt = job_input.get("prompt", "")
    system_prompt = job_input.get("system_prompt", "You are an expert full-stack developer. Generate code in the exact format requested.")
    max_tokens = job_input.get("max_tokens", 8192)
    max_new_tokens = job_input.get("max_new_tokens", max_tokens)
    temperature = job_input.get("temperature", 0.7)

    if not prompt:
        return {"error": "No prompt provided"}

    model = load_model()

    # Format prompt with chat template
    messages = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    sampling_params = SamplingParams(
        temperature=temperature,
        max_tokens=max_new_tokens,
        repetition_penalty=1.1,
        stop=["<|im_end|>"]
    )

    # Use LoRA adapter if available
    lora_request = None
    if os.path.exists(LORA_PATH) and os.path.exists(os.path.join(LORA_PATH, "adapter_config.json")):
        lora_request = LoRARequest("qwen-coder", 1, LORA_PATH)
        print("Using LoRA adapter for generation")

    outputs = model.generate([messages], sampling_params, lora_request=lora_request)

    content = outputs[0].outputs[0].text
    input_tokens = len(outputs[0].prompt_token_ids)
    output_tokens = len(outputs[0].outputs[0].token_ids)

    return {
        "content": content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": "qwen-coder-finetuned"
    }

# Start serverless worker
runpod.serverless.start({"handler": handler})
HANDLER_EOF

echo "Created handler.py"

# Step 3: Create Dockerfile
cat > Dockerfile << 'DOCKERFILE_EOF'
FROM runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04

WORKDIR /workspace

# Install dependencies
RUN pip install --upgrade pip && \
    pip install vllm>=0.3.0 runpod transformers accelerate sentencepiece protobuf huggingface_hub

# Copy handler
COPY handler.py /workspace/handler.py

# Pre-download base model (reduces cold start)
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('Qwen/Qwen2.5-Coder-7B-Instruct')"

# Pre-download LoRA adapter
RUN python -c "from huggingface_hub import snapshot_download; snapshot_download('kishoreudatha/qwen-coder-lora', local_dir='/workspace/lora_adapter')"

ENV PYTHONUNBUFFERED=1
ENV HF_HOME=/workspace/hf_cache

CMD ["python", "-u", "/workspace/handler.py"]
DOCKERFILE_EOF

echo "Created Dockerfile"

# Step 4: Build Docker image
echo ""
echo "=== Building Docker Image ==="
docker build -t kishoreudatha/qwen-serverless:v2 .

# Step 5: Login to Docker Hub
echo ""
echo "=== Docker Hub Login ==="
echo "Please enter your Docker Hub credentials:"
docker login

# Step 6: Push to Docker Hub
echo ""
echo "=== Pushing to Docker Hub ==="
docker push kishoreudatha/qwen-serverless:v2

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo ""
echo "Next steps:"
echo "1. Go to RunPod Serverless: https://www.runpod.io/console/serverless"
echo "2. Edit your endpoint: gmpr31tckmu0rj"
echo "3. Change Docker image to: kishoreudatha/qwen-serverless:v2"
echo "4. Save and wait for deployment"
echo ""
echo "The LoRA adapter is pre-downloaded in the image, so cold starts will be faster!"
