"""
Fine-tuning Configuration for Qwen2.5-Coder
"""
from dataclasses import dataclass, field
from typing import Optional, List
from pathlib import Path


@dataclass
class ModelConfig:
    """Model configuration"""
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct"  # Start with 7B, scale to 32B
    model_revision: str = "main"
    torch_dtype: str = "bfloat16"  # or "float16" for older GPUs
    trust_remote_code: bool = True
    use_flash_attention: bool = True  # Requires flash-attn package


@dataclass
class QuantizationConfig:
    """QLoRA quantization settings"""
    load_in_4bit: bool = True
    bnb_4bit_quant_type: str = "nf4"
    bnb_4bit_compute_dtype: str = "bfloat16"
    bnb_4bit_use_double_quant: bool = True


@dataclass
class LoraConfig:
    """LoRA adapter configuration"""
    r: int = 64  # Rank - higher = more capacity but slower
    lora_alpha: int = 128  # Scaling factor
    lora_dropout: float = 0.05
    target_modules: List[str] = field(default_factory=lambda: [
        "q_proj", "k_proj", "v_proj", "o_proj",  # Attention
        "gate_proj", "up_proj", "down_proj"  # MLP
    ])
    bias: str = "none"
    task_type: str = "CAUSAL_LM"


@dataclass
class TrainingConfig:
    """Training hyperparameters"""
    # Output
    output_dir: str = "./finetuned_models/qwen-coder-bharatbuild"

    # Training
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 2
    per_device_eval_batch_size: int = 2
    gradient_accumulation_steps: int = 8  # Effective batch = 2 * 8 = 16
    gradient_checkpointing: bool = True

    # Optimizer
    learning_rate: float = 2e-4
    weight_decay: float = 0.01
    warmup_ratio: float = 0.03
    lr_scheduler_type: str = "cosine"
    optim: str = "paged_adamw_8bit"

    # Precision
    fp16: bool = False
    bf16: bool = True  # Use bf16 if GPU supports it

    # Logging
    logging_steps: int = 10
    save_steps: int = 100
    eval_steps: int = 100
    save_total_limit: int = 3

    # Misc
    max_seq_length: int = 4096
    packing: bool = True  # Pack multiple samples into one sequence
    seed: int = 42

    # Wandb
    report_to: str = "wandb"
    run_name: str = "qwen-coder-bharatbuild"


@dataclass
class DataConfig:
    """Dataset configuration"""
    # Paths
    raw_data_dir: str = "./data/raw"
    processed_data_dir: str = "./data/processed"
    train_file: str = "train.jsonl"
    eval_file: str = "eval.jsonl"

    # Processing
    train_split: float = 0.9
    max_samples: Optional[int] = None  # None = use all
    min_code_length: int = 50  # Filter very short code snippets

    # Tech stack focus
    include_frameworks: List[str] = field(default_factory=lambda: [
        "react", "nextjs", "typescript", "tailwind",
        "fastapi", "python", "sqlalchemy", "pydantic"
    ])


@dataclass
class InferenceConfig:
    """Inference configuration"""
    model_path: str = "./finetuned_models/qwen-coder-bharatbuild"
    device_map: str = "auto"
    max_new_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 50
    repetition_penalty: float = 1.1
    do_sample: bool = True


# Default configs
DEFAULT_MODEL_CONFIG = ModelConfig()
DEFAULT_QUANT_CONFIG = QuantizationConfig()
DEFAULT_LORA_CONFIG = LoraConfig()
DEFAULT_TRAINING_CONFIG = TrainingConfig()
DEFAULT_DATA_CONFIG = DataConfig()
DEFAULT_INFERENCE_CONFIG = InferenceConfig()
