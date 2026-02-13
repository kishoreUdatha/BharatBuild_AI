#!/bin/bash
# RunPod Setup Script for Qwen-14B Fine-tuning
# GPU Required: A100 80GB

echo "=========================================="
echo "BharatBuild 14B Fine-tuning Setup (RunPod)"
echo "=========================================="

# Update system
apt-get update -y
apt-get install -y git wget curl

# Install Python packages
pip install --upgrade pip
pip install torch torchvision torchaudio

# Install training dependencies
pip install transformers>=4.40.0
pip install datasets>=2.16.0
pip install accelerate>=0.25.0
pip install peft>=0.7.0
pip install bitsandbytes>=0.41.0
pip install trl>=0.8.0
pip install scipy
pip install sentencepiece

# Verify GPU
echo ""
echo "GPU Status:"
nvidia-smi

echo ""
echo "=========================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Upload train.jsonl to ./data/"
echo "  2. Run: python train_14b.py"
echo "=========================================="
