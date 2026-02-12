"""
Evaluation Script for Fine-tuned Model
Measures code generation quality
"""
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict
import logging
from tqdm import tqdm

from inference import QwenCoderInference

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModelEvaluator:
    """Evaluate fine-tuned model on code generation tasks"""

    def __init__(self, model_path: str):
        logger.info("Loading model for evaluation...")
        self.inference = QwenCoderInference(model_path)

    def load_eval_data(self, eval_file: str) -> List[Dict]:
        """Load evaluation dataset"""
        samples = []
        with open(eval_file, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    samples.append(json.loads(line))
        return samples

    def evaluate_sample(self, sample: Dict) -> Dict:
        """Evaluate a single sample"""
        # Extract prompt and expected output
        if "messages" in sample:
            messages = sample["messages"]
            user_msg = next((m["content"] for m in messages if m["role"] == "user"), "")
            expected = next((m["content"] for m in messages if m["role"] == "assistant"), "")
        else:
            user_msg = sample.get("instruction", "") + " " + sample.get("input", "")
            expected = sample.get("output", "")

        # Generate
        generated = self.inference.generate(user_msg, max_new_tokens=1024)

        # Calculate metrics
        metrics = self._calculate_metrics(expected, generated)

        return {
            "prompt": user_msg[:200],
            "expected_length": len(expected),
            "generated_length": len(generated),
            "metrics": metrics,
        }

    def _calculate_metrics(self, expected: str, generated: str) -> Dict:
        """Calculate evaluation metrics"""
        metrics = {}

        # Length ratio
        if len(expected) > 0:
            metrics["length_ratio"] = len(generated) / len(expected)
        else:
            metrics["length_ratio"] = 0

        # Code block detection
        metrics["has_code_block"] = "```" in generated

        # Common patterns detection
        patterns = {
            "has_imports": any(kw in generated for kw in ["import ", "from ", "require("]),
            "has_function": any(kw in generated for kw in ["def ", "function ", "const ", "=>"]),
            "has_class": "class " in generated,
            "has_types": any(kw in generated for kw in [": str", ": int", ": string", ": number", "interface ", "type "]),
        }
        metrics.update(patterns)

        # Syntax indicators
        syntax_errors = []
        # Check for incomplete code
        if generated.count("{") != generated.count("}"):
            syntax_errors.append("unbalanced_braces")
        if generated.count("(") != generated.count(")"):
            syntax_errors.append("unbalanced_parens")
        if generated.count("[") != generated.count("]"):
            syntax_errors.append("unbalanced_brackets")

        metrics["syntax_errors"] = syntax_errors
        metrics["syntax_valid"] = len(syntax_errors) == 0

        # Token overlap (simple)
        expected_tokens = set(expected.split())
        generated_tokens = set(generated.split())
        if expected_tokens:
            metrics["token_overlap"] = len(expected_tokens & generated_tokens) / len(expected_tokens)
        else:
            metrics["token_overlap"] = 0

        return metrics

    def evaluate_dataset(
        self,
        eval_file: str,
        max_samples: int = 100,
        output_file: str = None
    ) -> Dict:
        """Evaluate on full dataset"""
        samples = self.load_eval_data(eval_file)

        if max_samples and len(samples) > max_samples:
            import random
            random.seed(42)
            samples = random.sample(samples, max_samples)

        logger.info(f"Evaluating {len(samples)} samples...")

        results = []
        for sample in tqdm(samples, desc="Evaluating"):
            result = self.evaluate_sample(sample)
            results.append(result)

        # Aggregate metrics
        aggregated = self._aggregate_metrics(results)

        # Save results
        if output_file:
            with open(output_file, 'w') as f:
                json.dump({
                    "aggregated": aggregated,
                    "samples": results
                }, f, indent=2)
            logger.info(f"Results saved to {output_file}")

        return aggregated

    def _aggregate_metrics(self, results: List[Dict]) -> Dict:
        """Aggregate metrics across all samples"""
        n = len(results)
        if n == 0:
            return {}

        aggregated = {
            "total_samples": n,
            "avg_length_ratio": sum(r["metrics"]["length_ratio"] for r in results) / n,
            "has_code_block_rate": sum(r["metrics"]["has_code_block"] for r in results) / n,
            "has_imports_rate": sum(r["metrics"]["has_imports"] for r in results) / n,
            "has_function_rate": sum(r["metrics"]["has_function"] for r in results) / n,
            "has_types_rate": sum(r["metrics"]["has_types"] for r in results) / n,
            "syntax_valid_rate": sum(r["metrics"]["syntax_valid"] for r in results) / n,
            "avg_token_overlap": sum(r["metrics"]["token_overlap"] for r in results) / n,
        }

        return aggregated

    def run_benchmark_prompts(self) -> Dict:
        """Run on standard benchmark prompts"""
        benchmarks = [
            {
                "name": "React Component",
                "prompt": "Create a React button component with loading state, disabled state, and onClick handler using TypeScript and Tailwind CSS",
                "expected_patterns": ["interface", "useState", "className", "onClick", "disabled"],
            },
            {
                "name": "FastAPI Endpoint",
                "prompt": "Create a FastAPI POST endpoint for user registration with email and password validation",
                "expected_patterns": ["@router.post", "async def", "HTTPException", "BaseModel"],
            },
            {
                "name": "Database Model",
                "prompt": "Create a SQLAlchemy model for a Product with id, name, price, and description fields",
                "expected_patterns": ["class Product", "Column", "Integer", "String", "Float"],
            },
            {
                "name": "Pydantic Schema",
                "prompt": "Create Pydantic schemas for User with create, update, and response variants",
                "expected_patterns": ["BaseModel", "class User", "Optional", "Field"],
            },
            {
                "name": "React Hook",
                "prompt": "Create a custom React hook called useLocalStorage that persists state to localStorage",
                "expected_patterns": ["useState", "useEffect", "localStorage", "export"],
            },
        ]

        results = []
        for bench in benchmarks:
            logger.info(f"Running benchmark: {bench['name']}")
            generated = self.inference.generate(bench["prompt"])

            # Check patterns
            matches = sum(1 for p in bench["expected_patterns"] if p in generated)
            score = matches / len(bench["expected_patterns"])

            results.append({
                "name": bench["name"],
                "score": score,
                "patterns_matched": matches,
                "patterns_total": len(bench["expected_patterns"]),
                "generated_length": len(generated),
            })

            logger.info(f"  Score: {score:.2%} ({matches}/{len(bench['expected_patterns'])} patterns)")

        # Summary
        avg_score = sum(r["score"] for r in results) / len(results)
        logger.info(f"\nOverall Benchmark Score: {avg_score:.2%}")

        return {
            "benchmark_score": avg_score,
            "results": results,
        }


def main():
    parser = argparse.ArgumentParser(description="Evaluate fine-tuned model")
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--eval-file", type=str, help="Evaluation JSONL file")
    parser.add_argument("--max-samples", type=int, default=100)
    parser.add_argument("--output", type=str, help="Output file for results")
    parser.add_argument("--benchmark", action="store_true", help="Run benchmark prompts")
    args = parser.parse_args()

    evaluator = ModelEvaluator(args.model_path)

    if args.benchmark:
        results = evaluator.run_benchmark_prompts()
        print(json.dumps(results, indent=2))

    if args.eval_file:
        results = evaluator.evaluate_dataset(
            args.eval_file,
            max_samples=args.max_samples,
            output_file=args.output
        )
        print("\nAggregated Results:")
        for key, value in results.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.4f}")
            else:
                print(f"  {key}: {value}")


if __name__ == "__main__":
    main()
