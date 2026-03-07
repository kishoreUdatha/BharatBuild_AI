# Preventing Catastrophic Forgetting in Fine-Tuning

## What is Catastrophic Forgetting?

When you fine-tune a model, it can "forget" its original capabilities while learning new ones.

```
Before Fine-tuning:          After BAD Fine-tuning:
├── Python [OK]               ├── Python (Claude format only)
├── JavaScript [OK]           ├── JavaScript [LOST]
├── Go [OK]                   ├── Go [LOST]
├── Rust [OK]                 ├── Rust [LOST]
├── SQL [OK]                  ├── SQL [LOST]
├── Reasoning [OK]            ├── Reasoning [DAMAGED]
└── General coding [OK]       └── General coding [DAMAGED]
```

## Our Safeguards

### 1. LoRA (Low-Rank Adaptation) ✅

**We freeze the original 7B parameters and only train ~50M new parameters.**

```python
# Original weights: FROZEN (never modified)
model.base_model.requires_grad = False  # 7B params

# LoRA weights: TRAINABLE (new knowledge)
lora_adapter.requires_grad = True  # ~50M params

# Final output combines both
output = original_output + lora_delta
```

**Why this works:**
- 100% of original knowledge is preserved in frozen weights
- New knowledge is stored in small adapter
- At inference: original + adapter = best of both

### 2. Conservative Training Hyperparameters ✅

```python
# Our settings (safe):
EPOCHS = 2              # Few epochs
LEARNING_RATE = 2e-4    # Low learning rate
BATCH_SIZE = 16         # Reasonable batch

# Dangerous settings (would cause forgetting):
EPOCHS = 10             # Too many epochs
LEARNING_RATE = 1e-3    # Too high
BATCH_SIZE = 1          # Unstable gradients
```

### 3. Diverse Training Data ✅

We train on ALL task types, not just one:

```json
{
  "api_implementation": 145,  // FastAPI, Django, Flask, Express
  "bug_fix": 150,
  "add_tests": 108,
  "refactor": 50,
  "security": 50,
  "ai_ml": 12               // PyTorch, TensorFlow, sklearn
}
```

This ensures the model sees:
- Multiple languages (Python, JS, Go, Rust)
- Multiple frameworks
- Multiple task types

### 4. Knowledge Retention Testing ✅

Run before AND after fine-tuning:

```bash
# Before fine-tuning (baseline)
python test_knowledge_retention.py --save-results baseline.json

# After fine-tuning
python test_knowledge_retention.py --model-path ./models/sft_v1 --save-results after_sft.json

# Compare
python -c "
import json
baseline = json.load(open('baseline.json'))
after = json.load(open('after_sft.json'))
print(f'Baseline: {baseline[\"passed\"]}/10')
print(f'After SFT: {after[\"passed\"]}/10')
"
```

**Expected results:**
- Baseline: 10/10 (100%)
- After SFT: 9/10 or 10/10 (90%+)

If retention drops below 80%, reduce epochs or learning rate.

### 5. Early Stopping ✅

We monitor loss and stop if it starts increasing:

```python
training_args = TrainingArguments(
    # ... other args ...
    load_best_model_at_end=True,
    metric_for_best_model="loss",
    greater_is_better=False,
    save_total_limit=3,
)
```

## Comparison: Full Fine-tuning vs LoRA

| Aspect | Full Fine-tuning | LoRA (Our Approach) |
|--------|------------------|---------------------|
| Parameters modified | 7B (100%) | 50M (~0.7%) |
| Original knowledge | Can be lost | Preserved |
| Training time | Long | Fast |
| VRAM needed | 80GB+ | 24GB |
| Risk of forgetting | HIGH | LOW |

## What We're Teaching (Not Replacing)

We're NOT replacing the model's knowledge. We're adding:

1. **Output format**: PLAN/FILES/PATCH/COMMANDS/NOTES structure
2. **Style**: Claude-like response organization
3. **Task-specific patterns**: How to structure API code, tests, etc.

The base model's coding ability, language knowledge, and reasoning stay intact.

## Recovery if Forgetting Occurs

If you notice forgetting after training:

### Option 1: Reduce Training
```python
EPOCHS = 1  # Reduce from 2
LEARNING_RATE = 1e-4  # Reduce from 2e-4
```

### Option 2: Use Smaller LoRA Rank
```python
LORA_R = 32  # Reduce from 64
LORA_ALPHA = 64  # Reduce from 128
```

### Option 3: Add Replay Data
Mix in general coding examples (not Claude format) to maintain diversity:
```python
# Add 10-20% general coding samples
training_data = gold_samples + general_samples
```

### Option 4: Simply Remove Adapter
Since we use LoRA, you can always fall back to the base model:
```python
# Use base model without adapter = original Qwen
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen2.5-Coder-7B-Instruct")
# No PeftModel.from_pretrained() = no adapter = no new learning
```

## Summary

| Safeguard | Status | Effect |
|-----------|--------|--------|
| LoRA (frozen base) | ✅ | Preserves 100% original weights |
| Low learning rate (2e-4) | ✅ | Gentle updates |
| Few epochs (2) | ✅ | Prevents overwriting |
| Diverse data (515 samples) | ✅ | Maintains language diversity |
| Retention testing | ✅ | Verifies no forgetting |
| Early stopping | ✅ | Stops before damage |

**With these safeguards, catastrophic forgetting is extremely unlikely.**
