# BharatBuild AI - Fine-tuning Pipeline

Fine-tune Qwen2.5-Coder for code generation, optimized for React/Next.js + FastAPI/Python stack.

## Quick Start

### 1. Install Dependencies

```bash
cd backend/finetuning
pip install -r requirements.txt
```

### 2. Run Full Pipeline

```bash
# Extract data from database, process, train, and evaluate
python run_pipeline.py --model Qwen/Qwen2.5-Coder-7B-Instruct --epochs 3
```

### 3. Run Individual Steps

```bash
# Step 1: Extract training data from BharatBuild AI database
python data_extractor.py --output-dir ./data/raw --format chatml

# Step 2: Process and prepare data
python data_processor.py --input ./data/raw/train_chatml.jsonl --output-dir ./data/processed

# Step 3: Fine-tune
python train.py \
    --train-file ./data/processed/train.jsonl \
    --eval-file ./data/processed/eval.jsonl \
    --model Qwen/Qwen2.5-Coder-7B-Instruct \
    --epochs 3 \
    --batch-size 2 \
    --lora-r 64

# Step 4: Evaluate
python evaluate.py --model-path ./finetuned_models/qwen-coder/final --benchmark
```

## Hardware Requirements

| Model | Fine-Tuning (QLoRA) | Inference |
|-------|---------------------|-----------|
| 7B | 1x RTX 4090 (24GB) | 16GB VRAM |
| 14B | 1x A100 40GB | 24GB VRAM |
| 32B | 2x A100 40GB | 48GB VRAM |

## Pipeline Components

### `data_extractor.py`
Extracts training data from BharatBuild AI's PostgreSQL database:
- Fetches successfully completed projects
- Converts to instruction-completion pairs
- Supports both Alpaca and ChatML formats

### `data_processor.py`
Prepares data for training:
- Filters low-quality samples
- Cleans and normalizes code
- Augments dataset with variations
- Balances by task type
- Splits train/eval

### `train.py`
QLoRA fine-tuning:
- 4-bit quantization (NF4)
- LoRA adapters on attention + MLP layers
- Gradient checkpointing for memory efficiency
- WandB integration for experiment tracking

### `inference.py`
Model inference:
- Load LoRA or merged models
- Streaming generation
- High-level APIs for components/endpoints
- BharatBuild AI agent interface

### `serve.py`
FastAPI server:
- REST API for code generation
- Streaming support
- Compatible with BharatBuild AI orchestrator

### `evaluate.py`
Model evaluation:
- Pattern-based metrics
- Benchmark prompts
- Syntax validation

## Configuration

Edit `config.py` to customize:

```python
# Model
model_name = "Qwen/Qwen2.5-Coder-7B-Instruct"  # or 14B, 32B

# LoRA
r = 64          # Rank
lora_alpha = 128  # Scaling

# Training
epochs = 3
batch_size = 2
learning_rate = 2e-4
max_seq_length = 4096
```

## Integration with BharatBuild AI

### Option 1: Use as Agent

```python
from app.modules.agents.qwen_coder_agent import QwenCoderAgent

agent = QwenCoderAgent()
result = await agent.generate(
    prompt="Create a login form component",
    project_context={"tech_stack": "React + TypeScript"}
)
```

### Option 2: Hybrid Agent (Qwen + Claude)

```python
from app.modules.agents.qwen_coder_agent import HybridCoderAgent

# Routes simple tasks to Qwen, complex to Claude
agent = HybridCoderAgent(complexity_threshold=0.7)
result = await agent.generate(prompt)
```

### Option 3: Direct API

```bash
# Start serving
python serve.py --model-path ./finetuned_models/qwen-coder/final --port 8001

# Call API
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a React button component"}'
```

## Cloud Training

### RunPod (Recommended)

```bash
# 1. Create A100 pod
# 2. Clone repo and install deps
# 3. Run training
python train.py \
    --train-file ./data/processed/train.jsonl \
    --model Qwen/Qwen2.5-Coder-32B-Instruct \
    --epochs 3 \
    --merge
```

### AWS SageMaker

```python
from sagemaker.huggingface import HuggingFace

estimator = HuggingFace(
    entry_point='train.py',
    source_dir='./finetuning',
    instance_type='ml.p4d.24xlarge',
    transformers_version='4.37',
    pytorch_version='2.1',
    py_version='py310',
)
estimator.fit({'training': 's3://bucket/data/'})
```

## Cost Comparison

| Provider | Claude API | Fine-tuned Qwen |
|----------|------------|-----------------|
| Per 1M tokens | ~$15 | ~$0.50 (self-hosted) |
| Monthly (100K requests) | ~$1,500 | ~$200 (GPU rental) |
| Latency | 2-5s | 0.5-2s |

**Expected savings: 70-85%** on API costs after fine-tuning.

## Troubleshooting

### Out of Memory
```bash
# Reduce batch size
python train.py --batch-size 1 --gradient-accumulation-steps 16

# Use smaller model
python train.py --model Qwen/Qwen2.5-Coder-7B-Instruct
```

### Slow Training
```bash
# Install Flash Attention
pip install flash-attn --no-build-isolation

# Enable packing
# Already enabled by default in config
```

### Model Not Loading
```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Check model path
ls ./finetuned_models/qwen-coder/final/
```

## License

Apache 2.0 (same as Qwen2.5-Coder)
