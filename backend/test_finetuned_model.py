#!/usr/bin/env python3
"""
Test the fine-tuned Qwen model locally.

Requirements:
- GPU with 16GB+ VRAM (or 24GB for full precision)
- torch, transformers, peft, bitsandbytes installed

Usage:
    python test_finetuned_model.py
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

MODEL_PATH = Path(__file__).parent / "finetuning" / "data" / "final_v5" / "models" / "qwen-coder" / "final"


def test_model():
    print("=" * 70)
    print("TESTING FINE-TUNED QWEN MODEL")
    print("=" * 70)

    # Check model files
    print(f"\nModel path: {MODEL_PATH}")
    print(f"Exists: {MODEL_PATH.exists()}")

    if MODEL_PATH.exists():
        adapter_file = MODEL_PATH / "adapter_model.safetensors"
        config_file = MODEL_PATH / "adapter_config.json"
        print(f"Adapter file: {adapter_file.exists()}")
        print(f"Config file: {config_file.exists()}")

        if adapter_file.exists():
            size_mb = adapter_file.stat().st_size / (1024 * 1024)
            print(f"Adapter size: {size_mb:.2f} MB")
    else:
        print("ERROR: Model not found!")
        return

    # Try loading the model
    print("\n" + "=" * 70)
    print("LOADING MODEL...")
    print("=" * 70)

    try:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        from peft import PeftModel

        print(f"PyTorch version: {torch.__version__}")
        print(f"CUDA available: {torch.cuda.is_available()}")
        if torch.cuda.is_available():
            print(f"GPU: {torch.cuda.get_device_name(0)}")
            print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f} GB")

        base_model = "Qwen/Qwen2.5-Coder-7B-Instruct"

        # 4-bit quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )

        print("\nLoading base model...")
        model = AutoModelForCausalLM.from_pretrained(
            base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )

        print("Loading LoRA adapter...")
        model = PeftModel.from_pretrained(model, str(MODEL_PATH))

        print("Loading tokenizer...")
        tokenizer = AutoTokenizer.from_pretrained(base_model, trust_remote_code=True)

        print("\nModel loaded successfully!")

    except ImportError as e:
        print(f"\nERROR: Missing dependencies: {e}")
        print("Install with: pip install torch transformers peft bitsandbytes")
        return
    except Exception as e:
        print(f"\nERROR: Failed to load model: {e}")
        return

    # Test generation
    print("\n" + "=" * 70)
    print("TESTING GENERATION...")
    print("=" * 70)

    test_prompts = [
        "Create a FastAPI endpoint to get user by ID",
        "Fix the null pointer exception in this code",
        "Add unit tests for the login function",
    ]

    for prompt in test_prompts:
        print(f"\n--- Prompt: {prompt[:50]}... ---")

        messages = [
            {"role": "system", "content": "You are an expert software engineer. Use PLAN/FILES/PATCH/COMMANDS/NOTES format."},
            {"role": "user", "content": prompt}
        ]

        text = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )

        inputs = tokenizer(text, return_tensors="pt").to(model.device)

        with torch.no_grad():
            # Get proper pad token (avoid using eos as pad - causes premature stopping!)
            pad_token = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else tokenizer.eos_token_id

            outputs = model.generate(
                **inputs,
                max_new_tokens=2048,  # Increased from 512 for complete code
                min_new_tokens=100,   # Ensure minimum output
                temperature=0.7,
                repetition_penalty=1.1,  # Prevent repetitive output
                do_sample=True,
                pad_token_id=pad_token,
                eos_token_id=tokenizer.eos_token_id,
                early_stopping=False,  # Don't stop prematurely
            )

        response = tokenizer.decode(
            outputs[0][inputs.input_ids.shape[1]:],
            skip_special_tokens=True
        )

        # Check for Claude-style format
        has_plan = "PLAN:" in response
        has_files = "FILES:" in response
        has_patch = "PATCH:" in response or "*** Begin Patch" in response

        print(f"Response length: {len(response)} chars")
        print(f"Has PLAN: {has_plan}")
        print(f"Has FILES: {has_files}")
        print(f"Has PATCH: {has_patch}")
        print(f"Preview: {response[:200]}...")

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    test_model()
