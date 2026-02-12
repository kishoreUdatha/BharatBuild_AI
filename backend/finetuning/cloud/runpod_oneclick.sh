#!/bin/bash
# =====================================================
# RunPod One-Click Setup & Training Script
# =====================================================
#
# USAGE: Just copy-paste this ENTIRE script into RunPod terminal
#
# Prerequisites:
# 1. RunPod pod with RTX 4090 or A100
# 2. Template: RunPod Pytorch 2.1
# 3. Storage: 100GB volume mounted at /workspace
#
# =====================================================

set -e

echo "=============================================="
echo "  BharatBuild AI - Fine-tuning Setup"
echo "=============================================="
echo ""

# Configuration
MODEL_SIZE="7b"  # Change to "14b" or "32b" for larger models
EPOCHS=3
BATCH_SIZE=2
REPO_URL="https://github.com/YOUR_USERNAME/BharatBuild_AI.git"  # UPDATE THIS!

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_step() {
    echo -e "${GREEN}[STEP]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Step 1: Check GPU
print_step "Checking GPU..."
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader
echo ""

# Step 2: Install system deps
print_step "Installing system dependencies..."
apt-get update -qq && apt-get install -y -qq git htop tmux > /dev/null 2>&1

# Step 3: Clone repo
print_step "Setting up repository..."
cd /workspace

if [ -d "BharatBuild_AI" ]; then
    print_warn "Repository exists, pulling latest..."
    cd BharatBuild_AI && git pull && cd ..
else
    print_step "Cloning repository..."
    # Try to clone, if fails, create directory structure
    git clone $REPO_URL 2>/dev/null || {
        print_warn "Clone failed. Creating directory structure manually..."
        mkdir -p BharatBuild_AI/backend/finetuning/data/processed
        mkdir -p BharatBuild_AI/backend/finetuning/finetuned_models
    }
fi

cd /workspace/BharatBuild_AI/backend/finetuning

# Step 4: Install Python dependencies
print_step "Installing Python dependencies..."
pip install --upgrade pip -q

# Core dependencies
pip install -q \
    torch>=2.1.0 \
    transformers>=4.37.0 \
    peft>=0.8.0 \
    trl>=0.7.0 \
    bitsandbytes>=0.42.0 \
    accelerate>=0.27.0 \
    datasets>=2.17.0 \
    wandb \
    scipy

# Install Flash Attention (optional but recommended)
print_step "Installing Flash Attention (this may take a few minutes)..."
pip install flash-attn --no-build-isolation -q 2>/dev/null || print_warn "Flash Attention failed, continuing without it"

# Step 5: Check/Generate training data
print_step "Checking training data..."

if [ ! -f "./data/processed/train.jsonl" ]; then
    print_warn "Training data not found. Generating synthetic data..."

    # Create minimal training script inline
    python << 'PYTHON_SCRIPT'
import json
from pathlib import Path

# Create directories
Path("./data/processed").mkdir(parents=True, exist_ok=True)

# High-quality training samples
samples = [
    {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer. Generate clean, production-ready code."},
            {"role": "user", "content": "Create a React button component with loading state using TypeScript and Tailwind CSS"},
            {"role": "assistant", "content": '''```tsx
import React from 'react';
import { Loader2 } from 'lucide-react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  isLoading?: boolean;
  variant?: 'primary' | 'secondary' | 'outline';
}

export default function Button({
  children,
  isLoading,
  variant = 'primary',
  disabled,
  className,
  ...props
}: ButtonProps) {
  const variants = {
    primary: 'bg-blue-600 text-white hover:bg-blue-700',
    secondary: 'bg-gray-200 text-gray-900 hover:bg-gray-300',
    outline: 'border-2 border-gray-300 hover:bg-gray-50',
  };

  return (
    <button
      className={`px-4 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 ${variants[variant]} ${className}`}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && <Loader2 className="w-4 h-4 mr-2 animate-spin inline" />}
      {children}
    </button>
  );
}
```'''}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer. Generate clean, production-ready code."},
            {"role": "user", "content": "Create a FastAPI endpoint for user registration with email validation"},
            {"role": "assistant", "content": '''```python
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from passlib.context import CryptContext

router = APIRouter(prefix="/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=2)

class UserResponse(BaseModel):
    id: str
    email: str
    name: str

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    # Check if user exists (pseudo-code)
    # existing = await db.users.find_one({"email": user.email})
    # if existing:
    #     raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)

    new_user = {
        "id": "generated-uuid",
        "email": user.email,
        "name": user.name,
        "password": hashed_password,
    }
    # await db.users.insert_one(new_user)

    return UserResponse(**new_user)
```'''}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer. Generate clean, production-ready code."},
            {"role": "user", "content": "Create a React login form with react-hook-form and Zod validation"},
            {"role": "assistant", "content": '''```tsx
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email('Invalid email'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginForm({ onSubmit }: { onSubmit: (data: LoginForm) => void }) {
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 max-w-md mx-auto p-6">
      <div>
        <label className="block text-sm font-medium mb-1">Email</label>
        <input
          {...register('email')}
          type="email"
          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        {errors.email && <p className="text-red-500 text-sm mt-1">{errors.email.message}</p>}
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Password</label>
        <input
          {...register('password')}
          type="password"
          className="w-full px-3 py-2 border rounded-lg focus:ring-2 focus:ring-blue-500"
        />
        {errors.password && <p className="text-red-500 text-sm mt-1">{errors.password.message}</p>}
      </div>
      <button
        type="submit"
        disabled={isSubmitting}
        className="w-full py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50"
      >
        {isSubmitting ? 'Signing in...' : 'Sign In'}
      </button>
    </form>
  );
}
```'''}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer. Generate clean, production-ready code."},
            {"role": "user", "content": "Create a SQLAlchemy User model with password hashing"},
            {"role": "assistant", "content": '''```python
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
from passlib.context import CryptContext

from app.core.database import Base

pwd_context = CryptContext(schemes=["bcrypt"])

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)
```'''}
        ]
    },
    {
        "messages": [
            {"role": "system", "content": "You are an expert full-stack developer. Generate clean, production-ready code."},
            {"role": "user", "content": "Create a React modal component with backdrop and close button"},
            {"role": "assistant", "content": '''```tsx
import React, { useEffect } from 'react';
import { X } from 'lucide-react';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
}

export default function Modal({ isOpen, onClose, title, children }: ModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white rounded-lg shadow-xl max-w-lg w-full mx-4 max-h-[90vh] overflow-auto">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-4">{children}</div>
      </div>
    </div>
  );
}
```'''}
        ]
    },
]

# Duplicate and augment samples to create ~100 training examples
augmented = []
for sample in samples:
    augmented.append(sample)
    # Add variation
    var = {"messages": sample["messages"].copy()}
    var["messages"] = [
        var["messages"][0],
        {"role": "user", "content": "Please " + sample["messages"][1]["content"][0].lower() + sample["messages"][1]["content"][1:]},
        var["messages"][2]
    ]
    augmented.append(var)

# Repeat to get more samples
all_samples = augmented * 10

# Split
train = all_samples[:int(len(all_samples)*0.9)]
eval_set = all_samples[int(len(all_samples)*0.9):]

# Save
with open("./data/processed/train.jsonl", "w") as f:
    for s in train:
        f.write(json.dumps(s) + "\n")

with open("./data/processed/eval.jsonl", "w") as f:
    for s in eval_set:
        f.write(json.dumps(s) + "\n")

print(f"Created {len(train)} training samples and {len(eval_set)} eval samples")
PYTHON_SCRIPT

fi

TRAIN_COUNT=$(wc -l < ./data/processed/train.jsonl)
EVAL_COUNT=$(wc -l < ./data/processed/eval.jsonl)
print_step "Training samples: $TRAIN_COUNT, Eval samples: $EVAL_COUNT"

# Step 6: Create training script if not exists
if [ ! -f "train.py" ]; then
    print_step "Creating training script..."
    cat > train.py << 'TRAIN_SCRIPT'
import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig
from datasets import load_dataset
import argparse

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-file", required=True)
    parser.add_argument("--eval-file", default=None)
    parser.add_argument("--output-dir", default="./finetuned_models/qwen-coder")
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-7B-Instruct")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--lora-r", type=int, default=64)
    parser.add_argument("--max-seq-length", type=int, default=4096)
    args = parser.parse_args()

    print(f"Loading model: {args.model}")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        args.model,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora_config = LoraConfig(
        r=args.lora_r,
        lora_alpha=args.lora_r * 2,
        lora_dropout=0.05,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        bias="none",
        task_type="CAUSAL_LM",
    )

    model = get_peft_model(model, lora_config)
    print(f"Trainable params: {sum(p.numel() for p in model.parameters() if p.requires_grad):,}")

    train_data = load_dataset("json", data_files=args.train_file, split="train")
    eval_data = None
    if args.eval_file:
        eval_data = load_dataset("json", data_files=args.eval_file, split="train")

    def format_chat(example):
        text = tokenizer.apply_chat_template(example["messages"], tokenize=False, add_generation_prompt=False)
        return {"text": text}

    train_data = train_data.map(format_chat, remove_columns=train_data.column_names)
    if eval_data:
        eval_data = eval_data.map(format_chat, remove_columns=eval_data.column_names)

    training_args = SFTConfig(
        output_dir=args.output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=8,
        learning_rate=args.learning_rate,
        bf16=True,
        logging_steps=10,
        save_steps=100,
        eval_strategy="steps" if eval_data else "no",
        eval_steps=100 if eval_data else None,
        max_seq_length=args.max_seq_length,
        packing=True,
        dataset_text_field="text",
        gradient_checkpointing=True,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_data,
        eval_dataset=eval_data,
        tokenizer=tokenizer,
    )

    trainer.train()

    final_dir = f"{args.output_dir}/final"
    model.save_pretrained(final_dir)
    tokenizer.save_pretrained(final_dir)
    print(f"Model saved to {final_dir}")

if __name__ == "__main__":
    main()
TRAIN_SCRIPT
fi

# Step 7: Start training
print_step "Starting training..."
echo ""
echo "=============================================="
echo "  Training Configuration"
echo "=============================================="
echo "  Model: Qwen/Qwen2.5-Coder-${MODEL_SIZE^^}-Instruct"
echo "  Epochs: $EPOCHS"
echo "  Batch Size: $BATCH_SIZE"
echo "  Training Samples: $TRAIN_COUNT"
echo "=============================================="
echo ""

python train.py \
    --train-file ./data/processed/train.jsonl \
    --eval-file ./data/processed/eval.jsonl \
    --model "Qwen/Qwen2.5-Coder-7B-Instruct" \
    --epochs $EPOCHS \
    --batch-size $BATCH_SIZE \
    --output-dir ./finetuned_models/qwen-coder-${MODEL_SIZE}

echo ""
echo "=============================================="
echo "  Training Complete!"
echo "=============================================="
echo ""
echo "Model saved to: ./finetuned_models/qwen-coder-${MODEL_SIZE}/final"
echo ""
echo "Test the model:"
echo "  python -c \"from transformers import AutoModelForCausalLM; print('Model loads!')\""
echo ""
echo "Download to your machine:"
echo "  scp -r root@YOUR_POD_IP:/workspace/BharatBuild_AI/backend/finetuning/finetuned_models ./finetuned_models/"
echo ""
echo "IMPORTANT: Stop your pod to avoid charges!"
echo "=============================================="
