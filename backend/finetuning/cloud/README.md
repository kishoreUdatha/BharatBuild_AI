# Cloud GPU Training Guide

Fine-tune Qwen2.5-Coder on cloud GPUs. Choose based on your budget and requirements.

## Quick Comparison

| Provider | GPU | Cost/hr | Best For |
|----------|-----|---------|----------|
| **RunPod** | RTX 4090 | $0.44 | Quick experiments, 7B model |
| **RunPod** | A100 40GB | $1.64 | Production training, 14B-32B |
| **Lambda Labs** | A100 40GB | $1.10 | Long training runs |
| **AWS SageMaker** | g5.2xlarge | $1.21 | Enterprise, managed infra |
| **AWS Spot** | p4d.24xlarge | ~$8 | Large scale, 32B+ models |

## Option 1: RunPod (Recommended for Quick Start)

### Setup

1. **Create Account**: https://runpod.io
2. **Add Credits**: $10 minimum
3. **Create Pod**:
   - Template: `RunPod Pytorch 2.1`
   - GPU: `RTX 4090` (7B) or `A100 40GB` (14B+)
   - Disk: `100 GB`
   - Region: Any with availability

4. **SSH and Run**:
```bash
# Connect via RunPod web terminal or SSH
cd /workspace
git clone https://github.com/YOUR_USERNAME/BharatBuild_AI.git
cd BharatBuild_AI/backend/finetuning

# Setup
bash cloud/runpod_setup.sh

# Train
bash cloud/runpod_train.sh 7b 3 2  # model_size, epochs, batch_size
```

### Cost Estimate
- 7B model, 3 epochs, 1000 samples: ~$2-5 (1-2 hours)
- 14B model, 3 epochs, 1000 samples: ~$10-20 (3-5 hours)

---

## Option 2: Lambda Labs

### Setup

1. **Create Account**: https://lambdalabs.com
2. **Launch Instance**:
   - 1x A100 40GB: $1.10/hr
   - Select Ubuntu 22.04 with PyTorch

3. **SSH and Run**:
```bash
ssh ubuntu@YOUR_INSTANCE_IP

# Setup
git clone https://github.com/YOUR_USERNAME/BharatBuild_AI.git
cd BharatBuild_AI/backend/finetuning
bash cloud/lambda_setup.sh

# Train in tmux (persists if SSH disconnects)
tmux new -s training
bash cloud/runpod_train.sh 7b 3 2
# Ctrl+B, D to detach
```

---

## Option 3: AWS SageMaker (Managed)

### Setup

1. **Install AWS CLI**:
```bash
pip install awscli boto3 sagemaker
aws configure  # Enter your credentials
```

2. **Create IAM Role** with SageMaker permissions

3. **Upload Data and Train**:
```bash
cd backend/finetuning

# Create entry point script
python cloud/aws_sagemaker.py --action create-script

# Upload training data
python cloud/aws_sagemaker.py --action upload --train-data ./data/processed/train.jsonl

# Start training (uses spot instances for 70% savings)
python cloud/aws_sagemaker.py --action train \
    --s3-train s3://YOUR_BUCKET/bharatbuild/training-data/train.jsonl \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --instance-type ml.g5.2xlarge \
    --epochs 3

# Download trained model
python cloud/aws_sagemaker.py --action download \
    --job-name bharatbuild-qwen-coder-TIMESTAMP \
    --output-dir ./finetuned_models
```

### Instance Types
| Type | GPU | VRAM | Cost/hr | Model Size |
|------|-----|------|---------|------------|
| ml.g5.xlarge | 1x A10G | 24GB | $1.00 | 7B |
| ml.g5.2xlarge | 1x A10G | 24GB | $1.21 | 7B (faster) |
| ml.p4d.24xlarge | 8x A100 | 320GB | $32.77 | 32B+ |

---

## Option 4: Google Colab Pro (Budget)

For testing with limited data:

```python
# In Colab notebook
!pip install transformers peft trl bitsandbytes accelerate

# Clone repo
!git clone https://github.com/YOUR_USERNAME/BharatBuild_AI.git
%cd BharatBuild_AI/backend/finetuning

# Train (limited by Colab session time)
!python train.py \
    --train-file ./data/processed/train.jsonl \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --epochs 1 \
    --batch-size 1 \
    --max-seq-length 2048
```

**Limitations**:
- Free: T4 (16GB) - can run 7B quantized
- Pro: A100 (40GB) - can run 14B quantized
- Session timeout after ~12 hours

---

## Uploading Training Data

### Option A: Generate Synthetic (No Database)
```bash
# On cloud instance
python collect_training_data.py --no-db --output-dir ./data/collected
python data_processor.py --input ./data/collected/training_data.jsonl --output-dir ./data/processed
```

### Option B: Upload from Local
```bash
# From your local machine
scp -r ./data/processed user@cloud-instance:/workspace/BharatBuild_AI/backend/finetuning/data/
```

### Option C: Export from BharatBuild DB
```bash
# On local with database access
python data_extractor.py --output-dir ./data/raw
python data_processor.py --input ./data/raw/train_chatml.jsonl --output-dir ./data/processed

# Upload to cloud
scp -r ./data/processed user@cloud-instance:/path/to/data/
```

---

## Downloading Trained Model

### From RunPod/Lambda
```bash
# On local machine
rsync -avz --progress user@cloud-instance:/workspace/BharatBuild_AI/backend/finetuning/finetuned_models/ ./finetuned_models/
```

### From S3 (SageMaker)
```bash
aws s3 cp s3://your-bucket/bharatbuild/models/model.tar.gz ./finetuned_models/
tar -xzf ./finetuned_models/model.tar.gz -C ./finetuned_models/
```

---

## Monitoring Training

### WandB Dashboard
```bash
# Login during setup
wandb login

# View at: https://wandb.ai/YOUR_USERNAME/bharatbuild-finetuning
```

### GPU Monitoring
```bash
# Real-time GPU usage
nvtop

# Or
watch -n 1 nvidia-smi
```

### Training Logs
```bash
# Follow logs
tail -f training.log

# Check for errors
grep -i error training.log
```

---

## Cost Optimization Tips

1. **Use Spot Instances** (AWS): 70% cheaper, but can be interrupted
2. **Start Small**: Test with 7B model before scaling to 32B
3. **Limit Data**: Start with 500-1000 samples to validate pipeline
4. **Use Checkpoints**: Resume training if interrupted
5. **Off-Peak Hours**: Some providers have lower prices at night

---

## Troubleshooting

### Out of Memory
```bash
# Reduce batch size and sequence length
python train.py --batch-size 1 --max-seq-length 2048
```

### Training Too Slow
```bash
# Install Flash Attention
pip install flash-attn --no-build-isolation
```

### Model Not Converging
- Check learning rate (try 1e-4 or 5e-5)
- Increase training data
- Check data quality (filter short/incomplete samples)

### Connection Lost
```bash
# Use tmux to persist sessions
tmux new -s training
# Run training
# Ctrl+B, D to detach
tmux attach -t training  # Reconnect later
```
