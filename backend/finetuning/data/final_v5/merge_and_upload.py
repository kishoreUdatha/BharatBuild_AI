#!/usr/bin/env python3
"""
Merge LoRA weights and prepare for deployment
"""

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
import json

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

BASE_MODEL = config["training_config"]["base_model"]
LORA_MODEL = "./qwen-bharatbuild-v5"
OUTPUT_DIR = "./qwen-bharatbuild-v5-merged"

print("Loading base model...")
model = AutoModelForCausalLM.from_pretrained(
    BASE_MODEL,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

print("Loading LoRA weights...")
model = PeftModel.from_pretrained(model, LORA_MODEL)

print("Merging weights...")
model = model.merge_and_unload()

print(f"Saving merged model to {OUTPUT_DIR}...")
model.save_pretrained(OUTPUT_DIR)

tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL, trust_remote_code=True)
tokenizer.save_pretrained(OUTPUT_DIR)

print("Done! Model ready for deployment.")
print("\nTo upload to Hugging Face:")
print("  huggingface-cli login")
print("  huggingface-cli upload your-username/qwen-bharatbuild-v5 ./qwen-bharatbuild-v5-merged")
print("\nClaude-Style Output Format trained:")
print("  PLAN -> FILES -> PATCH -> COMMANDS -> NOTES")
