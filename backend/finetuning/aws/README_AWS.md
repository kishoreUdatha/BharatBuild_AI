# AWS Fine-tuning Guide for BharatBuild

## Cost Estimate
- **Instance**: g5.xlarge (A10G 24GB)
- **Rate**: $1.01/hour
- **Training Time**: ~5-6 hours
- **Total Cost**: ~$6

## Step-by-Step Instructions

### Step 1: Launch EC2 Instance

1. Go to AWS Console → EC2 → Launch Instance

2. Configure:
   ```
   Name: qwen-finetuning
   AMI: Deep Learning AMI GPU PyTorch 2.0 (Ubuntu 20.04)
   Instance Type: g5.xlarge (or g5.2xlarge for faster)
   Storage: 100 GB gp3
   ```

3. Security Group:
   ```
   SSH (port 22) - Your IP
   ```

4. Create/select key pair and launch

### Step 2: Connect to Instance

```bash
# Connect via SSH
ssh -i your-key.pem ubuntu@<your-instance-ip>
```

### Step 3: Upload Training Files

Option A: Using SCP
```bash
# From your local machine
scp -i your-key.pem -r backend/finetuning ubuntu@<instance-ip>:~/
```

Option B: Using Git
```bash
# On EC2 instance
git clone <your-repo-url>
cd BharatBuild_AI/backend/finetuning
```

### Step 4: Setup Environment

```bash
# Run setup script
cd ~/finetuning/aws
chmod +x setup_aws.sh
./setup_aws.sh

# Activate environment
source ~/qwen-env/bin/activate
```

### Step 5: Prepare Training Data

```bash
# Create data directory
mkdir -p ~/finetuning/aws/data

# Copy training data
cp ~/finetuning/data/training_data.jsonl ~/finetuning/aws/data/
```

### Step 6: Start Training

```bash
cd ~/finetuning/aws
python train_aws.py
```

Training will take approximately 5-6 hours.

### Step 7: Monitor Training

```bash
# Check GPU usage
watch -n 1 nvidia-smi

# Check training logs
tail -f output/qwen-bharatbuild/training.log
```

### Step 8: Save Model to S3

```bash
# After training completes
aws s3 cp ./output/qwen-bharatbuild/final s3://your-bucket/qwen-finetuned/ --recursive
```

### Step 9: Stop Instance (Important!)

```bash
# Don't forget to stop the instance to avoid charges!
# AWS Console → EC2 → Instances → Stop
```

## Quick Commands Summary

```bash
# 1. SSH into instance
ssh -i key.pem ubuntu@<ip>

# 2. Setup (first time only)
cd ~/finetuning/aws && ./setup_aws.sh

# 3. Activate environment
source ~/qwen-env/bin/activate

# 4. Start training
python train_aws.py

# 5. Upload to S3
aws s3 cp ./output/qwen-bharatbuild/final s3://bucket/model/ --recursive

# 6. STOP INSTANCE when done!
```

## Troubleshooting

### Out of Memory Error
```bash
# Reduce batch size in train_aws.py
BATCH_SIZE = 1  # Instead of 2
```

### CUDA Error
```bash
# Restart and clear GPU memory
sudo fuser -v /dev/nvidia* 2>&1 | grep python | awk '{print $2}' | xargs kill -9
```

### Training Interrupted
```bash
# Resume from checkpoint
# Training auto-resumes from last checkpoint in output/
python train_aws.py
```

## Cost Optimization Tips

1. **Use Spot Instances**: Up to 70% cheaper
   - g5.xlarge spot: ~$0.30/hour
   - Risk: Can be interrupted

2. **Stop when not training**: Don't leave instance running

3. **Use smaller instance for setup**:
   - Setup on t3.medium
   - Switch to g5.xlarge for training only
