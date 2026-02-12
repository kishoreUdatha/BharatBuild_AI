#!/bin/bash
# ==============================================
# RunPod GPU Setup Script for Fine-tuning
# ==============================================
# Usage: bash runpod_setup.sh
#
# Prerequisites:
# 1. Create RunPod account: https://runpod.io
# 2. Add credits ($10 minimum)
# 3. Create a GPU pod with:
#    - Template: RunPod Pytorch 2.1
#    - GPU: RTX 4090 (24GB) for 7B, A100 40GB for 14B+
#    - Disk: 100GB minimum
# 4. SSH into the pod and run this script

set -e

echo "=============================================="
echo "BharatBuild AI - Fine-tuning Setup on RunPod"
echo "=============================================="

# Update system
echo "Updating system packages..."
apt-get update && apt-get install -y git wget curl htop nvtop

# Check GPU
echo "Checking GPU..."
nvidia-smi

# Clone repository (replace with your repo URL)
echo "Cloning BharatBuild AI repository..."
if [ ! -d "/workspace/BharatBuild_AI" ]; then
    cd /workspace
    git clone https://github.com/YOUR_USERNAME/BharatBuild_AI.git
fi

cd /workspace/BharatBuild_AI/backend/finetuning

# Create virtual environment
echo "Setting up Python environment..."
python -m venv venv
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Install Flash Attention (optional but recommended)
echo "Installing Flash Attention..."
pip install flash-attn --no-build-isolation || echo "Flash Attention install failed, continuing without it"

# Install wandb for experiment tracking
pip install wandb
echo "Please login to Weights & Biases:"
wandb login

# Create directories
mkdir -p data/collected data/processed finetuned_models

# Download model weights (pre-cache)
echo "Pre-downloading model weights..."
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
print('Downloading Qwen2.5-Coder-7B-Instruct...')
AutoTokenizer.from_pretrained('Qwen/Qwen2.5-Coder-7B-Instruct', trust_remote_code=True)
# Don't download full model yet, just tokenizer for now
print('Tokenizer downloaded!')
"

echo "=============================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "1. Upload your training data to: /workspace/BharatBuild_AI/backend/finetuning/data/collected/"
echo "2. Or generate synthetic data: python collect_training_data.py --no-db"
echo "3. Process data: python data_processor.py --input ./data/collected/training_data.jsonl --output-dir ./data/processed"
echo "4. Start training: python train.py --train-file ./data/processed/train.jsonl --epochs 3"
echo ""
echo "Monitor training:"
echo "  - GPU: nvtop"
echo "  - WandB: https://wandb.ai/YOUR_USERNAME/bharatbuild-finetuning"
echo "=============================================="
