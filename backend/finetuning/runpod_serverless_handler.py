"""
RunPod Serverless Handler for Fine-tuned Qwen Model

This handler is invoked by RunPod serverless infrastructure.
Deploy this as a serverless endpoint for auto-scaling inference.

Setup:
1. Build Docker image with this handler
2. Push to Docker Hub or RunPod registry
3. Create serverless endpoint on RunPod
4. Update QWEN_API_URL in BharatBuild .env

The LoRA adapter is automatically downloaded from HuggingFace on first run.
"""

import runpod
from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
import os

# Global model instance (loaded once, reused across requests)
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

        # Download the LoRA adapter
        snapshot_download(
            repo_id=LORA_HF_REPO,
            local_dir=LORA_PATH,
            local_dir_use_symlinks=False
        )

        # Verify required files exist
        required_files = ["adapter_config.json", "adapter_model.safetensors"]
        for f in required_files:
            if not os.path.exists(os.path.join(LORA_PATH, f)):
                # Try alternate filename
                if f == "adapter_model.safetensors" and os.path.exists(os.path.join(LORA_PATH, "adapter_model.bin")):
                    continue
                print(f"Warning: {f} not found in LoRA adapter")

        lora_loaded = True
        print(f"LoRA adapter downloaded successfully to {LORA_PATH}")
        print(f"Files: {os.listdir(LORA_PATH)}")
        return True

    except Exception as e:
        print(f"Failed to download LoRA adapter: {e}")
        print("Falling back to base model without fine-tuning")
        return False

def load_model():
    """Load model once when container starts"""
    global llm
    if llm is None:
        # Download LoRA adapter first
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
    """
    RunPod serverless handler function.

    Input format:
    {
        "input": {
            "prompt": "Create a React button component",
            "system_prompt": "You are an expert developer.",
            "max_tokens": 8192,
            "temperature": 0.7,
            "stream": false
        }
    }

    Output format:
    {
        "content": "generated code...",
        "input_tokens": 123,
        "output_tokens": 456,
        "model": "qwen-coder-serverless"
    }
    """
    job_input = job["input"]

    # Extract parameters
    prompt = job_input.get("prompt", "")
    system_prompt = job_input.get("system_prompt", "You are an expert full-stack developer.")
    max_tokens = job_input.get("max_tokens", 8192)
    max_new_tokens = job_input.get("max_new_tokens", max_tokens)
    temperature = job_input.get("temperature", 0.7)

    if not prompt:
        return {"error": "No prompt provided"}

    # Load model (cached after first load)
    model = load_model()

    # Format prompt with chat template
    messages = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    # Configure sampling
    sampling_params = SamplingParams(
        temperature=temperature,
        max_tokens=max_new_tokens,
        repetition_penalty=1.1,
        stop=["<|im_end|>"]
    )

    # Use LoRA adapter if available
    lora_request = None
    if os.path.exists(LORA_PATH):
        lora_request = LoRARequest("qwen-coder", 1, LORA_PATH)

    # Generate
    outputs = model.generate([messages], sampling_params, lora_request=lora_request)

    content = outputs[0].outputs[0].text
    input_tokens = len(outputs[0].prompt_token_ids)
    output_tokens = len(outputs[0].outputs[0].token_ids)

    return {
        "content": content,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "model": "qwen-coder-serverless"
    }


# For streaming support (optional)
def generator_handler(job):
    """
    Streaming handler for RunPod serverless.
    Returns chunks as they're generated.
    """
    job_input = job["input"]

    prompt = job_input.get("prompt", "")
    system_prompt = job_input.get("system_prompt", "You are an expert full-stack developer.")
    max_tokens = job_input.get("max_tokens", 8192)
    temperature = job_input.get("temperature", 0.7)

    if not prompt:
        yield {"error": "No prompt provided"}
        return

    model = load_model()

    messages = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n"

    sampling_params = SamplingParams(
        temperature=temperature,
        max_tokens=max_tokens,
        repetition_penalty=1.1,
        stop=["<|im_end|>"]
    )

    lora_request = None
    if os.path.exists(LORA_PATH):
        lora_request = LoRARequest("qwen-coder", 1, LORA_PATH)

    # Generate and yield chunks
    outputs = model.generate([messages], sampling_params, lora_request=lora_request)
    content = outputs[0].outputs[0].text

    # Simulate streaming by chunking
    chunk_size = 100
    for i in range(0, len(content), chunk_size):
        yield {"chunk": content[i:i+chunk_size]}

    yield {
        "done": True,
        "input_tokens": len(outputs[0].prompt_token_ids),
        "output_tokens": len(outputs[0].outputs[0].token_ids)
    }


# Start serverless worker
runpod.serverless.start({
    "handler": handler,
    "generator_handler": generator_handler  # Optional streaming
})
