#!/bin/bash
# ==============================================
# Lambda Labs GPU Setup Script
# ==============================================
# Usage: bash lambda_setup.sh
#
# Prerequisites:
# 1. Create Lambda Labs account: https://lambdalabs.com
# 2. Launch an instance:
#    - 1x A100 40GB for 7B-14B models
#    - 2x A100 40GB for 32B model
# 3. SSH into instance and run this script

set -e

echo "=============================================="
echo "BharatBuild AI - Fine-tuning Setup on Lambda"
echo "=============================================="

# Lambda instances come with CUDA pre-installed
echo "Checking GPU..."
nvidia-smi

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y git htop nvtop tmux

# Clone repository
echo "Cloning repository..."
cd ~
if [ ! -d "BharatBuild_AI" ]; then
    git clone https://github.com/YOUR_USERNAME/BharatBuild_AI.git
fi

cd ~/BharatBuild_AI/backend/finetuning

# Use system Python with venv
python3 -m venv venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Install PyTorch (Lambda has CUDA 12.x)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Install other dependencies
pip install -r requirements.txt

# Install Flash Attention
pip install flash-attn --no-build-isolation

# Install experiment tracking
pip install wandb tensorboard

# Login to wandb
echo "Login to Weights & Biases:"
wandb login

# Create directories
mkdir -p data/collected data/processed finetuned_models

echo "=============================================="
echo "Lambda Labs setup complete!"
echo ""
echo "Start training in tmux session:"
echo "  tmux new -s training"
echo "  bash cloud/runpod_train.sh 7b 3 2"
echo ""
echo "Detach with: Ctrl+B, then D"
echo "Reattach with: tmux attach -t training"
echo "=============================================="
