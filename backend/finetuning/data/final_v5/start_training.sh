#!/bin/bash
# BharatBuild AI - Qwen SFT Training Script
# Run on GPU instance with >= 24GB VRAM (A100, RTX 4090, etc.)

set -e

echo "=============================================="
echo "BharatBuild AI - Qwen V5 Fine-tuning"
echo "=============================================="

# Check GPU
echo "Checking GPU..."
nvidia-smi || { echo "ERROR: No GPU found!"; exit 1; }

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check data files
echo "Checking data files..."
if [ ! -f "train.jsonl" ]; then
    echo "ERROR: train.jsonl not found!"
    exit 1
fi

TRAIN_COUNT=$(wc -l < train.jsonl)
EVAL_COUNT=$(wc -l < eval.jsonl)
echo "Train examples: $TRAIN_COUNT"
echo "Eval examples: $EVAL_COUNT"

# Start training
echo ""
echo "Starting SFT training..."
echo "=============================================="
python train_qwen.py

# Check if DPO should run
if [ -f "dpo_pairs.jsonl" ]; then
    DPO_COUNT=$(wc -l < dpo_pairs.jsonl)
    if [ "$DPO_COUNT" -gt 0 ]; then
        echo ""
        echo "Starting DPO training..."
        echo "=============================================="
        python train_dpo.py
    fi
fi

echo ""
echo "=============================================="
echo "Training Complete!"
echo "=============================================="
echo "Model saved to: qwen-bharatbuild-v5/"
echo ""
echo "To upload to Hugging Face:"
echo "  huggingface-cli login"
echo "  python merge_and_upload.py"
