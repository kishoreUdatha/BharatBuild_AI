# RunPod Fine-tuning Guide (14B Model)

## Cost Estimate
- **GPU**: A100 80GB
- **Rate**: $2.49/hour
- **Training Time**: ~4 hours
- **Total Cost**: ~$10

## Quality
- **Model**: Qwen2.5-Coder-14B
- **Quality**: 95% (with RAG)
- **Trainable params**: ~300M

---

## Step-by-Step Instructions

### Step 1: Create RunPod Account
1. Go to https://www.runpod.io
2. Sign up with email
3. Add credits ($10-15 recommended)

### Step 2: Deploy GPU Pod
1. Click **Deploy** → **GPU Pods**
2. Select:
   ```
   GPU: A100 80GB (or A100 PCIe)
   Template: RunPod Pytorch 2.1
   Volume: 100GB
   ```
3. Click **Deploy**

### Step 3: Connect to Pod
1. Wait for pod to start (1-2 minutes)
2. Click **Connect** → **Start Web Terminal**
   Or use **SSH** if preferred

### Step 4: Upload Training Files
```bash
# In terminal, create directories
mkdir -p /workspace/finetuning/data

# Option A: Upload via RunPod UI
# Click "File Manager" → Upload files

# Option B: Using wget (if hosted online)
# wget -O /workspace/finetuning/data/train.jsonl YOUR_URL
```

### Step 5: Upload Scripts
Upload these files to `/workspace/finetuning/`:
- `train_14b.py`
- `setup.sh`

And upload to `/workspace/finetuning/data/`:
- `train.jsonl`

### Step 6: Run Setup
```bash
cd /workspace/finetuning
chmod +x setup.sh
./setup.sh
```

### Step 7: Start Training
```bash
cd /workspace/finetuning
python train_14b.py
```

Training will take ~4 hours. You'll see:
```
GPU: NVIDIA A100-SXM4-80GB
Memory: 80.0 GB
Loading model: Qwen/Qwen2.5-Coder-14B-Instruct
trainable params: 304,087,040 || all params: 14,770,033,664 || trainable%: 2.06%
Starting training...
```

### Step 8: Download Model
After training completes:
```bash
# Zip the model
cd /workspace/finetuning
zip -r qwen-14b-bharatbuild.zip output/qwen-bharatbuild-14b/final

# Download via RunPod File Manager
# Or use: runpodctl send qwen-14b-bharatbuild.zip
```

### Step 9: Stop Pod (Important!)
**Don't forget - you're charged per hour!**
1. Go to RunPod dashboard
2. Click **Stop** on your pod
3. Or **Terminate** if done

---

## Quick Commands

```bash
# Setup
cd /workspace/finetuning && ./setup.sh

# Train
python train_14b.py

# Check GPU
nvidia-smi

# Check training progress
# (training shows progress automatically)

# Zip model
zip -r model.zip output/qwen-bharatbuild-14b/final
```

---

## Troubleshooting

### Out of Memory
```bash
# Edit train_14b.py, reduce batch size:
BATCH_SIZE = 2  # Instead of 4
```

### Training Interrupted
```bash
# Training auto-resumes from checkpoint
python train_14b.py
```

### Slow Download
```bash
# Use HuggingFace cache
export HF_HOME=/workspace/cache
```

---

## File Structure

```
/workspace/finetuning/
├── data/
│   └── train.jsonl      # Your training data
├── output/
│   └── qwen-bharatbuild-14b/
│       └── final/       # Trained model
├── train_14b.py         # Training script
├── setup.sh             # Setup script
└── README.md            # This file
```

---

## Expected Output

After training:
```
output/qwen-bharatbuild-14b/final/
├── adapter_config.json
├── adapter_model.safetensors  # ~600MB (LoRA weights)
├── tokenizer.json
├── tokenizer_config.json
└── special_tokens_map.json
```

Total size: ~700MB (just the LoRA adapters)
