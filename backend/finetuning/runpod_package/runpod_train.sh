#!/bin/bash
# ============================================================
# BharatBuild AI - One-Click RunPod Training Script
# ============================================================

set -e

echo "============================================================"
echo "  BharatBuild AI - Qwen Coder Fine-tuning on RunPod"
echo "============================================================"
echo ""

# Configuration
MODEL_NAME="Qwen/Qwen2.5-Coder-7B-Instruct"
OUTPUT_DIR="/workspace/finetuned_models/qwen-coder-7b"
EPOCHS=3
BATCH_SIZE=2
LEARNING_RATE="2e-4"

# Step 1: Setup workspace
echo "[1/7] Setting up workspace..."
cd /workspace

# Step 2: Clone repository (if not exists)
if [ ! -d "BharatBuild_AI" ]; then
    echo "[2/7] Cloning repository..."
    git clone https://github.com/anthropics/BharatBuild_AI.git 2>/dev/null || {
        echo "Repository not found. Creating local structure..."
        mkdir -p BharatBuild_AI/backend/finetuning/data/ultimate
    }
else
    echo "[2/7] Repository already exists, pulling latest..."
    cd BharatBuild_AI && git pull 2>/dev/null || true
    cd /workspace
fi

cd /workspace/BharatBuild_AI/backend/finetuning

# Step 3: Install dependencies
echo "[3/7] Installing dependencies..."
pip install --upgrade pip -q
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 -q
pip install transformers>=4.40.0 datasets peft>=0.10.0 trl>=0.8.0 bitsandbytes>=0.43.0 accelerate>=0.28.0 -q
pip install wandb sentencepiece protobuf scipy -q

# Try to install flash-attention (optional, improves speed)
echo "[3/7] Installing Flash Attention (optional)..."
pip install flash-attn --no-build-isolation -q 2>/dev/null || echo "Flash Attention not available, continuing without it..."

# Step 4: Check for training data
echo "[4/7] Checking training data..."
if [ ! -f "data/ultimate/train.jsonl" ]; then
    echo "Training data not found. Please upload your data to:"
    echo "  /workspace/BharatBuild_AI/backend/finetuning/data/ultimate/"
    echo ""
    echo "Required files:"
    echo "  - train.jsonl"
    echo "  - eval.jsonl"
    echo ""
    echo "You can upload using SCP:"
    echo "  scp data/ultimate/*.jsonl root@YOUR_POD_IP:/workspace/BharatBuild_AI/backend/finetuning/data/ultimate/"
    exit 1
fi

TRAIN_SAMPLES=$(wc -l < data/ultimate/train.jsonl)
EVAL_SAMPLES=$(wc -l < data/ultimate/eval.jsonl)
echo "  Training samples: $TRAIN_SAMPLES"
echo "  Evaluation samples: $EVAL_SAMPLES"

# Step 5: Check GPU
echo "[5/7] Checking GPU..."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

# Step 6: Start training
echo "[6/7] Starting training..."
echo "  Model: $MODEL_NAME"
echo "  Epochs: $EPOCHS"
echo "  Batch Size: $BATCH_SIZE"
echo "  Learning Rate: $LEARNING_RATE"
echo "  Output: $OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p $OUTPUT_DIR

# Run training
python -u train.py \
    --train-file ./data/ultimate/train.jsonl \
    --eval-file ./data/ultimate/eval.jsonl \
    --model $MODEL_NAME \
    --epochs $EPOCHS \
    --batch-size $BATCH_SIZE \
    --learning-rate $LEARNING_RATE \
    --output-dir $OUTPUT_DIR \
    --use-flash-attention \
    --gradient-checkpointing \
    --logging-steps 10 \
    --save-steps 500 \
    --eval-steps 500 \
    2>&1 | tee $OUTPUT_DIR/training.log

# Step 7: Done
echo ""
echo "[7/7] Training complete!"
echo "============================================================"
echo "  Model saved to: $OUTPUT_DIR"
echo "============================================================"
echo ""
echo "To test the model:"
echo "  python inference.py --model-path $OUTPUT_DIR/final --interactive"
echo ""
echo "To download the model to your local machine:"
echo "  scp -r root@YOUR_POD_IP:$OUTPUT_DIR ./finetuned_models/"
