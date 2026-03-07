#!/bin/bash
# BharatBuild AI - Full Fine-tuning Pipeline
# Run on GPU instance with >= 24GB VRAM

set -e

echo "=============================================="
echo "BharatBuild AI - Full Fine-tuning Pipeline"
echo "=============================================="

# Check GPU
echo "Checking GPU..."
nvidia-smi || { echo "ERROR: No GPU found!"; exit 1; }

# Install dependencies
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Step 1: SFT v1 (503 gold samples only)
echo ""
echo "=============================================="
echo "STEP 1: SFT v1 (Gold Samples Only)"
echo "=============================================="
python step1_train_sft_v1.py

# Step 2: Evaluate
echo ""
echo "=============================================="
echo "STEP 2: Evaluate Model v1"
echo "=============================================="
python step2_evaluate_v1.py

# Check if evaluation passed
if [ -f "evaluation_results/v1_evaluation.json" ]; then
    PASSED=$(python -c "import json; print(json.load(open('evaluation_results/v1_evaluation.json'))['passed'])")
    if [ "$PASSED" != "True" ]; then
        echo "WARNING: Evaluation did not pass. Review results before continuing."
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi

# Step 3: Generate Silver Data
echo ""
echo "=============================================="
echo "STEP 3: Generate Silver Data"
echo "=============================================="
python step3_generate_silver.py

# Step 4: SFT v2 (Gold + Silver)
echo ""
echo "=============================================="
echo "STEP 4: SFT v2 (Gold + Silver)"
echo "=============================================="
python step4_train_sft_v2.py

# Step 5: DPO Training
echo ""
echo "=============================================="
echo "STEP 5: DPO Training"
echo "=============================================="
python step5_train_dpo.py

# Step 6: Demo Agent Loop
echo ""
echo "=============================================="
echo "STEP 6: Agent Loop Demo"
echo "=============================================="
python step6_agent_loop.py

echo ""
echo "=============================================="
echo "PIPELINE COMPLETE!"
echo "=============================================="
echo ""
echo "Models saved to:"
echo "  - models/sft_v1  (baseline)"
echo "  - models/sft_v2  (gold + silver)"
echo "  - models/dpo_v3  (final with DPO)"
echo ""
echo "To upload to Hugging Face:"
echo "  huggingface-cli login"
echo "  huggingface-cli upload your-username/qwen-bharatbuild-v5 models/dpo_v3"
