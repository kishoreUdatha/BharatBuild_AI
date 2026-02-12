# RunPod Quick Start Guide

## Step 1: Create RunPod Account

1. Go to **https://runpod.io**
2. Sign up with email or Google
3. Add credits: **$10 minimum** (Settings → Billing → Add Credits)

---

## Step 2: Create GPU Pod

1. Click **"+ Deploy"** or **"Pods"** → **"+ New Pod"**

2. **Select GPU:**
   - For 7B model: **RTX 4090** ($0.44/hr) ← Recommended
   - For 14B model: **A100 40GB** ($1.64/hr)

3. **Select Template:**
   - Search for: `RunPod Pytorch 2.1`
   - Or use: `runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04`

4. **Configure:**
   - Container Disk: **50 GB**
   - Volume Disk: **100 GB** (persistent storage)
   - Volume Mount: `/workspace`

5. Click **"Deploy On-Demand"**

---

## Step 3: Connect to Pod

### Option A: Web Terminal (Easiest)
- Click on your pod → **"Connect"** → **"Start Web Terminal"**

### Option B: SSH
```bash
# Get SSH command from pod details
ssh root@YOUR_POD_IP -i ~/.ssh/id_rsa
```

---

## Step 4: Setup Environment

Copy and paste this entire block into the terminal:

```bash
# Clone repository
cd /workspace
git clone https://github.com/YOUR_USERNAME/BharatBuild_AI.git
cd BharatBuild_AI/backend/finetuning

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install Flash Attention (faster training)
pip install flash-attn --no-build-isolation

# Login to Weights & Biases (optional but recommended)
pip install wandb
wandb login
```

---

## Step 5: Upload Training Data

### Option A: From your local machine
```bash
# On your LOCAL machine, run:
scp -r ./data/processed root@YOUR_POD_IP:/workspace/BharatBuild_AI/backend/finetuning/data/
```

### Option B: Generate fresh data on RunPod
```bash
# On RunPod:
cd /workspace/BharatBuild_AI/backend/finetuning
python collect_training_data.py --no-db
python data_processor.py --input ./data/collected/training_data.jsonl --output-dir ./data/processed
```

---

## Step 6: Start Training

```bash
cd /workspace/BharatBuild_AI/backend/finetuning

# Train 7B model (recommended first)
python train.py \
    --train-file ./data/processed/train.jsonl \
    --eval-file ./data/processed/eval.jsonl \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --epochs 3 \
    --batch-size 2 \
    --learning-rate 2e-4 \
    --output-dir ./finetuned_models/qwen-coder-7b
```

**Expected time:** ~1-2 hours for 672 samples

---

## Step 7: Monitor Training

### GPU Usage
```bash
nvtop
# Or: watch -n 1 nvidia-smi
```

### Training Logs
```bash
tail -f ./finetuned_models/qwen-coder-7b/training.log
```

### WandB Dashboard
- Go to: https://wandb.ai/YOUR_USERNAME/bharatbuild-finetuning

---

## Step 8: Test the Model

```bash
python inference.py \
    --model-path ./finetuned_models/qwen-coder-7b/final \
    --interactive
```

Try prompts like:
- "Create a React login form with validation"
- "Create a FastAPI endpoint for user registration"

---

## Step 9: Download Trained Model

### From your LOCAL machine:
```bash
# Download the LoRA adapter (small, ~100MB)
scp -r root@YOUR_POD_IP:/workspace/BharatBuild_AI/backend/finetuning/finetuned_models/qwen-coder-7b/final ./finetuned_models/

# Or download everything
rsync -avz --progress root@YOUR_POD_IP:/workspace/BharatBuild_AI/backend/finetuning/finetuned_models/ ./finetuned_models/
```

---

## Step 10: Stop Pod (Save Money!)

⚠️ **IMPORTANT:** Stop your pod when done to avoid charges!

1. Go to RunPod dashboard
2. Click on your pod
3. Click **"Stop"** (keeps data) or **"Terminate"** (deletes everything)

---

## Cost Summary

| Item | Cost |
|------|------|
| RTX 4090 × 2 hours | $0.88 |
| Storage 100GB | ~$0.10 |
| **Total** | **~$1.00** |

---

## Troubleshooting

### Out of Memory
```bash
# Reduce batch size
python train.py --batch-size 1 --gradient-accumulation-steps 16
```

### Connection Lost
```bash
# Use tmux to keep training running
tmux new -s training
python train.py ...
# Ctrl+B, D to detach
# tmux attach -t training to reconnect
```

### Model Download Failed
```bash
# Pre-download model
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('Qwen/Qwen2.5-Coder-7B-Instruct', trust_remote_code=True)"
```
