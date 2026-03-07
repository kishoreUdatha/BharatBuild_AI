#!/usr/bin/env python3
"""
RunPod Inference Server for Fine-tuned Qwen Model

Usage on RunPod:
    1. Copy this file to /workspace/server.py
    2. Run: python server.py
    3. API will be available at port 8000
"""

import os
import torch
from pathlib import Path
from typing import Optional, List, Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# ============================================================================
# CONFIGURATION
# ============================================================================

# Find model path - check common locations
MODEL_PATHS = [
    "/workspace/qwen-coder/final",
    "/workspace/models/qwen-coder/final",
    "/workspace/model",
    "/workspace/qwen-coder-finetuned",
    "/runpod-volume/models/qwen-coder/final",
]

BASE_MODEL = "Qwen/Qwen2.5-Coder-7B-Instruct"
PORT = 8000

# ============================================================================
# FIND MODEL
# ============================================================================

def find_model_path():
    """Find the fine-tuned model path."""
    for path in MODEL_PATHS:
        adapter_file = Path(path) / "adapter_config.json"
        if adapter_file.exists():
            print(f"Found model at: {path}")
            return path

    # Search for adapter_config.json
    import subprocess
    result = subprocess.run(
        ["find", "/workspace", "-name", "adapter_config.json", "-type", "f"],
        capture_output=True, text=True
    )
    if result.stdout.strip():
        found_path = Path(result.stdout.strip().split('\n')[0]).parent
        print(f"Found model at: {found_path}")
        return str(found_path)

    return None

MODEL_PATH = find_model_path()

# ============================================================================
# LOAD MODEL
# ============================================================================

print("=" * 60)
print("LOADING FINE-TUNED QWEN MODEL")
print("=" * 60)

if MODEL_PATH is None:
    print("ERROR: Model not found!")
    print("Please ensure the fine-tuned model is in /workspace/")
    print("Expected files: adapter_config.json, adapter_model.safetensors")
    exit(1)

print(f"Model path: {MODEL_PATH}")
print(f"Base model: {BASE_MODEL}")

from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import PeftModel

# 4-bit quantization for lower VRAM
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
)

print("Loading LoRA adapter...")
model = PeftModel.from_pretrained(model, MODEL_PATH)

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)

print("Model loaded successfully!")
print("=" * 60)

# ============================================================================
# FASTAPI SERVER
# ============================================================================

app = FastAPI(title="Qwen Coder Fine-tuned API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    max_new_tokens: int = 8192  # Increased from 2048 for complete code generation
    temperature: float = 0.7
    top_p: float = 0.9
    repetition_penalty: float = 1.1  # Prevent repetitive output
    min_new_tokens: int = 100  # Ensure minimum output
    stream: bool = False


class GenerateResponse(BaseModel):
    content: str
    model: str = "qwen-coder-7b-finetuned"
    input_tokens: int
    output_tokens: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_path: str
    gpu: str


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "No GPU"
    return HealthResponse(
        status="healthy",
        model_loaded=True,
        model_path=MODEL_PATH,
        gpu=gpu_name
    )


@app.post("/generate", response_model=GenerateResponse)
async def generate(request: GenerateRequest):
    """Generate text from prompt."""
    try:
        # Build messages
        messages = []
        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})
        messages.append({"role": "user", "content": request.prompt})

        # Apply chat template
        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = tokenizer(text, return_tensors="pt").to(model.device)
        input_len = inputs.input_ids.shape[1]

        # Generate with improved parameters for complete code output
        with torch.no_grad():
            # Get proper pad token (avoid using eos as pad)
            pad_token = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

            outputs = model.generate(
                **inputs,
                max_new_tokens=request.max_new_tokens,
                min_new_tokens=request.min_new_tokens,
                temperature=request.temperature,
                top_p=request.top_p,
                repetition_penalty=request.repetition_penalty,
                do_sample=True,
                pad_token_id=pad_token,
                # Don't stop on eos too early - let model complete naturally
                eos_token_id=tokenizer.eos_token_id,
                # Prevent premature stopping
                early_stopping=False,
            )

        # Decode response
        response = tokenizer.decode(
            outputs[0][input_len:],
            skip_special_tokens=True
        )

        output_len = outputs.shape[1] - input_len

        return GenerateResponse(
            content=response,
            input_tokens=input_len,
            output_tokens=output_len
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Qwen Coder Fine-tuned API",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "generate": "/generate (POST)"
        }
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print(f"\nStarting server on port {PORT}...")
    print(f"Health check: http://localhost:{PORT}/health")
    print(f"Generate: POST http://localhost:{PORT}/generate")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=PORT)
