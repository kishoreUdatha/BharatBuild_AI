"""
Data Processing Pipeline for Fine-tuning
Handles data cleaning, augmentation, and formatting
"""
import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import re
from collections import defaultdict


@dataclass
class ProcessingStats:
    """Track processing statistics"""
    total_samples: int = 0
    filtered_samples: int = 0
    augmented_samples: int = 0
    train_samples: int = 0
    eval_samples: int = 0


class DataProcessor:
    """Process and prepare data for fine-tuning"""

    def __init__(
        self,
        min_output_length: int = 50,
        max_output_length: int = 8000,
        train_split: float = 0.9,
        seed: int = 42
    ):
        self.min_output_length = min_output_length
        self.max_output_length = max_output_length
        self.train_split = train_split
        self.seed = seed
        self.stats = ProcessingStats()
        random.seed(seed)

    def load_jsonl(self, path: str) -> List[Dict]:
        """Load JSONL file"""
        samples = []
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
        return samples

    def save_jsonl(self, samples: List[Dict], path: str):
        """Save to JSONL file"""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')

    def clean_code(self, code: str) -> str:
        """Clean and normalize code"""
        # Remove excessive whitespace
        code = re.sub(r'\n{3,}', '\n\n', code)

        # Remove trailing whitespace
        lines = [line.rstrip() for line in code.split('\n')]
        code = '\n'.join(lines)

        # Remove common noise
        code = re.sub(r'# TODO:.*$', '', code, flags=re.MULTILINE)
        code = re.sub(r'// TODO:.*$', '', code, flags=re.MULTILINE)

        return code.strip()

    def filter_sample(self, sample: Dict) -> bool:
        """Check if sample should be included"""
        # Handle ChatML format
        if "messages" in sample:
            messages = sample.get("messages", [])
            output = ""
            for msg in messages:
                if msg.get("role") == "assistant":
                    output = msg.get("content", "")
                    break
        else:
            output = sample.get("output", "") or ""

        # Check length
        if len(output) < self.min_output_length:
            return False
        if len(output) > self.max_output_length:
            return False

        # Filter synthetic placeholders
        if "[TO_BE_GENERATED:" in output:
            return False

        # Check for actual code content (less strict)
        has_code = (
            "```" in output or
            any(keyword in output for keyword in ["def ", "function ", "class ", "const ", "import ", "from ", "return ", "export "])
        )
        if not has_code:
            return False

        # Filter incomplete code
        incomplete_markers = [
            "# TODO", "// TODO", "FIXME",
            "not implemented", "placeholder"
        ]
        for marker in incomplete_markers:
            if marker.lower() in output.lower():
                return False

        return True

    def process_sample(self, sample: Dict) -> Dict:
        """Process a single sample"""
        # Handle ChatML format
        if "messages" in sample:
            messages = sample["messages"]
            processed_messages = []
            for msg in messages:
                content = msg["content"]
                if msg["role"] == "assistant":
                    content = self.clean_code(content)
                processed_messages.append({
                    "role": msg["role"],
                    "content": content
                })
            return {"messages": processed_messages}

        # Handle Alpaca format
        return {
            "instruction": sample.get("instruction", "").strip(),
            "input": sample.get("input", "").strip(),
            "output": self.clean_code(sample.get("output", ""))
        }

    def augment_samples(self, samples: List[Dict]) -> List[Dict]:
        """
        Augment training data with variations
        """
        augmented = []

        for sample in samples:
            augmented.append(sample)  # Keep original

            # Create variations
            if "messages" in sample:
                # ChatML format
                messages = sample["messages"]
                user_msg = next((m for m in messages if m["role"] == "user"), None)

                if user_msg and len(user_msg["content"]) > 20:
                    # Variation 1: Add "Please" prefix
                    var1 = self._create_variation(sample, "Please " + user_msg["content"][0].lower() + user_msg["content"][1:])
                    if var1:
                        augmented.append(var1)

                    # Variation 2: Add specificity
                    var2 = self._create_variation(sample, user_msg["content"] + " Make it production-ready.")
                    if var2:
                        augmented.append(var2)

            else:
                # Alpaca format
                instruction = sample.get("instruction", "")

                if len(instruction) > 20:
                    # Variation 1: Rephrase
                    var1 = sample.copy()
                    var1["instruction"] = "Please " + instruction[0].lower() + instruction[1:]
                    augmented.append(var1)

        self.stats.augmented_samples = len(augmented) - len(samples)
        return augmented

    def _create_variation(self, sample: Dict, new_user_content: str) -> Optional[Dict]:
        """Create a variation of a ChatML sample"""
        if "messages" not in sample:
            return None

        new_messages = []
        for msg in sample["messages"]:
            if msg["role"] == "user":
                new_messages.append({"role": "user", "content": new_user_content})
            else:
                new_messages.append(msg.copy())

        return {"messages": new_messages}

    def balance_by_type(self, samples: List[Dict], max_per_type: int = 500) -> List[Dict]:
        """
        Balance samples by type to prevent overfitting to common patterns
        """
        by_type = defaultdict(list)

        for sample in samples:
            # Detect type from content
            if "messages" in sample:
                content = sample["messages"][1]["content"].lower() if len(sample["messages"]) > 1 else ""
            else:
                content = sample.get("instruction", "").lower()

            if "component" in content or "react" in content:
                sample_type = "react_component"
            elif "api" in content or "endpoint" in content:
                sample_type = "api_endpoint"
            elif "model" in content or "schema" in content:
                sample_type = "data_model"
            elif "auth" in content or "login" in content:
                sample_type = "authentication"
            elif "style" in content or "css" in content:
                sample_type = "styling"
            else:
                sample_type = "general"

            by_type[sample_type].append(sample)

        # Balance
        balanced = []
        for sample_type, type_samples in by_type.items():
            if len(type_samples) > max_per_type:
                balanced.extend(random.sample(type_samples, max_per_type))
            else:
                balanced.extend(type_samples)

        random.shuffle(balanced)
        return balanced

    def split_train_eval(self, samples: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """Split into training and evaluation sets"""
        random.shuffle(samples)
        split_idx = int(len(samples) * self.train_split)
        train = samples[:split_idx]
        eval_set = samples[split_idx:]

        self.stats.train_samples = len(train)
        self.stats.eval_samples = len(eval_set)

        return train, eval_set

    def process_dataset(
        self,
        input_path: str,
        output_dir: str,
        augment: bool = True,
        balance: bool = True
    ) -> ProcessingStats:
        """
        Full processing pipeline
        """
        print(f"Loading data from {input_path}...")
        samples = self.load_jsonl(input_path)
        self.stats.total_samples = len(samples)
        print(f"Loaded {len(samples)} samples")

        # Filter
        print("Filtering samples...")
        filtered = [s for s in samples if self.filter_sample(s)]
        self.stats.filtered_samples = len(samples) - len(filtered)
        print(f"Kept {len(filtered)} samples (filtered {self.stats.filtered_samples})")

        # Process
        print("Processing samples...")
        processed = [self.process_sample(s) for s in filtered]

        # Augment
        if augment:
            print("Augmenting data...")
            processed = self.augment_samples(processed)
            print(f"Total after augmentation: {len(processed)}")

        # Balance
        if balance:
            print("Balancing dataset...")
            processed = self.balance_by_type(processed)
            print(f"Total after balancing: {len(processed)}")

        # Split
        print("Splitting train/eval...")
        train, eval_set = self.split_train_eval(processed)

        # Save
        output_dir = Path(output_dir)
        self.save_jsonl(train, output_dir / "train.jsonl")
        self.save_jsonl(eval_set, output_dir / "eval.jsonl")

        print(f"\nProcessing complete!")
        print(f"  Train samples: {len(train)}")
        print(f"  Eval samples: {len(eval_set)}")
        print(f"  Saved to: {output_dir}")

        return self.stats


class SyntheticDataGenerator:
    """Generate synthetic training data using templates"""

    REACT_TEMPLATES = [
        {
            "instruction": "Create a {component_type} React component with {features}",
            "template": """```tsx
import React, {{ useState }} from 'react';

interface {name}Props {{
  {props}
}}

export default function {name}({{ {prop_names} }}: {name}Props) {{
  {state}

  {handlers}

  return (
    <div className="{container_classes}">
      {jsx}
    </div>
  );
}}
```"""
        }
    ]

    FASTAPI_TEMPLATES = [
        {
            "instruction": "Create a FastAPI {endpoint_type} endpoint for {resource}",
            "template": """```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.core.database import get_db
from app.models.{resource_lower} import {Resource}
from app.schemas.{resource_lower} import {Resource}Create, {Resource}Response

router = APIRouter(prefix="/{resource_plural}", tags=["{resource_plural}"])


@router.get("/", response_model=List[{Resource}Response])
async def get_{resource_plural}(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    {resource_plural} = db.query({Resource}).offset(skip).limit(limit).all()
    return {resource_plural}


@router.post("/", response_model={Resource}Response, status_code=status.HTTP_201_CREATED)
async def create_{resource_lower}(
    {resource_lower}: {Resource}Create,
    db: Session = Depends(get_db)
):
    db_{resource_lower} = {Resource}(**{resource_lower}.dict())
    db.add(db_{resource_lower})
    db.commit()
    db.refresh(db_{resource_lower})
    return db_{resource_lower}


@router.get("/{{id}}", response_model={Resource}Response)
async def get_{resource_lower}(id: int, db: Session = Depends(get_db)):
    {resource_lower} = db.query({Resource}).filter({Resource}.id == id).first()
    if not {resource_lower}:
        raise HTTPException(status_code=404, detail="{Resource} not found")
    return {resource_lower}
```"""
        }
    ]

    def generate_react_samples(self, count: int = 100) -> List[Dict]:
        """Generate synthetic React component samples"""
        components = [
            ("button", "Button", ["onClick", "disabled", "loading"]),
            ("form", "Form", ["onSubmit", "validation", "fields"]),
            ("modal", "Modal", ["isOpen", "onClose", "title"]),
            ("table", "DataTable", ["data", "columns", "pagination"]),
            ("card", "Card", ["title", "content", "actions"]),
        ]

        samples = []
        for comp_type, name, features in components:
            instruction = f"Create a {name} React component with TypeScript and Tailwind CSS"
            # Generate appropriate output based on component type
            samples.append({
                "messages": [
                    {"role": "system", "content": "You are an expert React developer."},
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": f"// {name} component would go here"}
                ]
            })

        return samples

    def generate_api_samples(self, count: int = 100) -> List[Dict]:
        """Generate synthetic FastAPI endpoint samples"""
        resources = ["User", "Product", "Order", "Comment", "Post", "Category"]

        samples = []
        for resource in resources:
            instruction = f"Create FastAPI CRUD endpoints for {resource}"
            samples.append({
                "messages": [
                    {"role": "system", "content": "You are an expert Python backend developer."},
                    {"role": "user", "content": instruction},
                    {"role": "assistant", "content": f"# {resource} API endpoints would go here"}
                ]
            })

        return samples


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Process training data")
    parser.add_argument("--input", type=str, required=True, help="Input JSONL file")
    parser.add_argument("--output-dir", type=str, default="./data/final")
    parser.add_argument("--no-augment", action="store_true")
    parser.add_argument("--no-balance", action="store_true")
    parser.add_argument("--train-split", type=float, default=0.9)
    args = parser.parse_args()

    processor = DataProcessor(train_split=args.train_split)
    stats = processor.process_dataset(
        input_path=args.input,
        output_dir=args.output_dir,
        augment=not args.no_augment,
        balance=not args.no_balance
    )

    print(f"\nFinal Statistics:")
    print(f"  Total input: {stats.total_samples}")
    print(f"  Filtered out: {stats.filtered_samples}")
    print(f"  Augmented: {stats.augmented_samples}")
    print(f"  Train set: {stats.train_samples}")
    print(f"  Eval set: {stats.eval_samples}")


if __name__ == "__main__":
    main()
