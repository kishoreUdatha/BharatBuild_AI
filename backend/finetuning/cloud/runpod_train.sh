#!/bin/bash
# ==============================================
# RunPod Training Script
# ==============================================
# Run this after runpod_setup.sh
# Usage: bash runpod_train.sh [model_size]
# model_size: 7b (default), 14b, 32b

set -e

MODEL_SIZE=${1:-7b}
EPOCHS=${2:-3}
BATCH_SIZE=${3:-2}

echo "=============================================="
echo "Starting Fine-tuning: Qwen2.5-Coder-${MODEL_SIZE^^}"
echo "=============================================="

cd /workspace/BharatBuild_AI/backend/finetuning
source venv/bin/activate

# Set model based on size
case $MODEL_SIZE in
    7b)
        MODEL="Qwen/Qwen2.5-Coder-7B-Instruct"
        LORA_R=64
        MAX_SEQ=4096
        ;;
    14b)
        MODEL="Qwen/Qwen2.5-Coder-14B-Instruct"
        LORA_R=32
        MAX_SEQ=2048
        BATCH_SIZE=1
        ;;
    32b)
        MODEL="Qwen/Qwen2.5-Coder-32B-Instruct"
        LORA_R=16
        MAX_SEQ=2048
        BATCH_SIZE=1
        ;;
    *)
        echo "Unknown model size: $MODEL_SIZE"
        exit 1
        ;;
esac

echo "Model: $MODEL"
echo "LoRA Rank: $LORA_R"
echo "Max Sequence Length: $MAX_SEQ"
echo "Batch Size: $BATCH_SIZE"
echo "Epochs: $EPOCHS"

# Check if data exists
if [ ! -f "./data/processed/train.jsonl" ]; then
    echo "Training data not found. Generating synthetic data..."

    # Generate synthetic data
    python collect_training_data.py --no-db --output-dir ./data/collected

    # Process data
    python data_processor.py \
        --input ./data/collected/training_data.jsonl \
        --output-dir ./data/processed
fi

# Count training samples
TRAIN_COUNT=$(wc -l < ./data/processed/train.jsonl)
EVAL_COUNT=$(wc -l < ./data/processed/eval.jsonl)
echo "Training samples: $TRAIN_COUNT"
echo "Evaluation samples: $EVAL_COUNT"

# Start training
echo ""
echo "Starting training..."
echo "Monitor with: tail -f training.log"
echo "Or check WandB dashboard"
echo ""

python train.py \
    --train-file ./data/processed/train.jsonl \
    --eval-file ./data/processed/eval.jsonl \
    --output-dir ./finetuned_models/qwen-coder-${MODEL_SIZE} \
    --model $MODEL \
    --epochs $EPOCHS \
    --batch-size $BATCH_SIZE \
    --lora-r $LORA_R \
    --max-seq-length $MAX_SEQ \
    --learning-rate 2e-4 \
    --wandb-project bharatbuild-finetuning \
    2>&1 | tee training.log

echo "=============================================="
echo "Training complete!"
echo "Model saved to: ./finetuned_models/qwen-coder-${MODEL_SIZE}"
echo ""
echo "Next steps:"
echo "1. Evaluate: python evaluate.py --model-path ./finetuned_models/qwen-coder-${MODEL_SIZE}/final --benchmark"
echo "2. Test: python inference.py --model-path ./finetuned_models/qwen-coder-${MODEL_SIZE}/final --interactive"
echo "3. Download model: rsync -avz ./finetuned_models/ your-server:/path/to/models/"
echo "=============================================="
