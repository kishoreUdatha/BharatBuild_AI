# BharatBuild AI - Qwen V5 Fine-tuning

## Overview
Fine-tune Qwen2.5-Coder-7B-Instruct with Claude-style output format.

**Dataset:**
- 120,542 training examples
- 6,338 evaluation examples
- 503 gold samples (Claude-style)
- 14 DPO preference pairs

**Output Format Trained:**
```
PLAN:
1) First step
2) Second step

FILES:
- path/to/file.py

PATCH:
*** Begin Patch
--- a/file.py
+++ b/file.py
@@ ... @@
*** End Patch

COMMANDS:
- pytest tests/

NOTES:
- Important notes
```

## Requirements
- GPU with >= 24GB VRAM (A100, RTX 4090, A10G)
- CUDA 11.8+
- Python 3.10+

## Quick Start

### Option 1: RunPod
1. Create a RunPod instance with A100 or RTX 4090
2. Upload the `final_v5` folder
3. Run:
```bash
cd final_v5
chmod +x start_training.sh
./start_training.sh
```

### Option 2: Manual
```bash
# Install dependencies
pip install -r requirements.txt

# Start SFT training
python train_qwen.py

# Start DPO training (after SFT)
python train_dpo.py

# Merge and prepare for deployment
python merge_and_upload.py
```

## Training Configuration

| Parameter | Value |
|-----------|-------|
| Base Model | Qwen/Qwen2.5-Coder-7B-Instruct |
| Epochs | 3 |
| Batch Size | 4 |
| Gradient Accumulation | 8 |
| Effective Batch | 32 |
| Learning Rate | 2e-4 |
| LoRA r | 64 |
| LoRA alpha | 128 |
| Max Seq Length | 4096 |

## Estimated Training Time
- A100 (40GB): ~8-12 hours
- RTX 4090 (24GB): ~12-18 hours
- A10G (24GB): ~15-20 hours

## Files
- `train.jsonl` - Training data (227 MB)
- `eval.jsonl` - Evaluation data (12 MB)
- `dpo_pairs.jsonl` - DPO preference pairs
- `train_qwen.py` - SFT training script
- `train_dpo.py` - DPO training script
- `merge_and_upload.py` - Merge LoRA weights
- `config.json` - Training configuration

## After Training
1. Upload to Hugging Face:
```bash
huggingface-cli login
huggingface-cli upload your-username/qwen-bharatbuild-v5 ./qwen-bharatbuild-v5-merged
```

2. Or copy the model files to your deployment server.
