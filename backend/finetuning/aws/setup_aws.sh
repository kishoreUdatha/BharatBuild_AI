#!/bin/bash
# AWS EC2 Setup Script for Qwen Fine-tuning
# Instance: g5.xlarge or g5.2xlarge (A10G GPU)

echo "=========================================="
echo "BharatBuild Qwen Fine-tuning Setup (AWS)"
echo "=========================================="

# Update system
sudo apt-get update -y
sudo apt-get install -y git wget curl

# Install Python 3.10 if not present
python3 --version || sudo apt-get install -y python3.10 python3.10-venv python3-pip

# Create virtual environment
python3 -m venv ~/qwen-env
source ~/qwen-env/bin/activate

# Install PyTorch with CUDA
pip install --upgrade pip
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install training dependencies
pip install transformers>=4.37.0
pip install datasets>=2.16.0
pip install accelerate>=0.25.0
pip install peft>=0.7.0
pip install bitsandbytes>=0.41.0
pip install trl>=0.7.0
pip install wandb
pip install scipy
pip install sentencepiece

# Install Flash Attention (optional, for faster training)
pip install flash-attn --no-build-isolation || echo "Flash attention not installed (optional)"

# Verify GPU
echo ""
echo "GPU Status:"
nvidia-smi

echo ""
echo "=========================================="
echo "Setup complete! Run training with:"
echo "  source ~/qwen-env/bin/activate"
echo "  python train.py"
echo "=========================================="
