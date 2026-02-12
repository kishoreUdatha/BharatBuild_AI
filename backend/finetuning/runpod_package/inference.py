"""
Inference module for fine-tuned Qwen2.5-Coder
Provides easy-to-use API for code generation
"""
import os
import json
import torch
from pathlib import Path
from typing import Optional, List, Dict, Generator
import logging

from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TextIteratorStreamer,
)
from peft import PeftModel
from threading import Thread

from config import DEFAULT_INFERENCE_CONFIG, InferenceConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QwenCoderInference:
    """Inference wrapper for fine-tuned Qwen2.5-Coder"""

    def __init__(
        self,
        model_path: str,
        config: InferenceConfig = DEFAULT_INFERENCE_CONFIG,
        load_in_4bit: bool = True,
        device_map: str = "auto",
    ):
        self.model_path = Path(model_path)
        self.config = config
        self.load_in_4bit = load_in_4bit
        self.device_map = device_map

        self.model = None
        self.tokenizer = None
        self.is_lora = False

        self._load_model()

    def _load_model(self):
        """Load the fine-tuned model"""
        logger.info(f"Loading model from {self.model_path}")

        # Check if this is a LoRA adapter or merged model
        adapter_config_path = self.model_path / "adapter_config.json"
        self.is_lora = adapter_config_path.exists()

        # Setup quantization
        bnb_config = None
        if self.load_in_4bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
                bnb_4bit_use_double_quant=True,
            )

        if self.is_lora:
            # Load base model + LoRA adapter
            with open(self.model_path / "training_config.json") as f:
                training_config = json.load(f)
            base_model_name = training_config.get("base_model", "Qwen/Qwen2.5-Coder-7B-Instruct")

            logger.info(f"Loading base model: {base_model_name}")
            base_model = AutoModelForCausalLM.from_pretrained(
                base_model_name,
                quantization_config=bnb_config,
                device_map=self.device_map,
                trust_remote_code=True,
            )

            logger.info("Loading LoRA adapter...")
            self.model = PeftModel.from_pretrained(base_model, self.model_path)
            self.tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
        else:
            # Load merged model directly
            logger.info("Loading merged model...")
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_path,
                quantization_config=bnb_config,
                device_map=self.device_map,
                trust_remote_code=True,
            )
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_path, trust_remote_code=True)

        # Set pad token
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        self.model.eval()
        logger.info("Model loaded successfully")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_new_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
        repetition_penalty: Optional[float] = None,
        stop_sequences: Optional[List[str]] = None,
    ) -> str:
        """
        Generate code from a prompt

        Args:
            prompt: The user's code generation request
            system_prompt: Optional system prompt (defaults to code generation prompt)
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling probability
            top_k: Top-k sampling
            repetition_penalty: Penalty for repetition
            stop_sequences: Sequences that stop generation

        Returns:
            Generated code as string
        """
        # Build messages
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": "You are an expert full-stack developer specializing in React, Next.js, TypeScript, FastAPI, and Python. Generate clean, production-ready code with proper error handling and best practices."
            })

        messages.append({"role": "user", "content": prompt})

        # Apply chat template
        input_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Tokenize
        inputs = self.tokenizer(input_text, return_tensors="pt").to(self.model.device)

        # Generation config
        gen_kwargs = {
            "max_new_tokens": max_new_tokens or self.config.max_new_tokens,
            "temperature": temperature or self.config.temperature,
            "top_p": top_p or self.config.top_p,
            "top_k": top_k or self.config.top_k,
            "repetition_penalty": repetition_penalty or self.config.repetition_penalty,
            "do_sample": self.config.do_sample,
            "pad_token_id": self.tokenizer.pad_token_id,
            "eos_token_id": self.tokenizer.eos_token_id,
        }

        # Add stop sequences
        if stop_sequences:
            stop_ids = [self.tokenizer.encode(seq, add_special_tokens=False) for seq in stop_sequences]
            gen_kwargs["stopping_criteria"] = self._create_stopping_criteria(stop_ids)

        # Generate
        with torch.no_grad():
            outputs = self.model.generate(**inputs, **gen_kwargs)

        # Decode
        generated_ids = outputs[0][inputs.input_ids.shape[1]:]
        response = self.tokenizer.decode(generated_ids, skip_special_tokens=True)

        return response.strip()

    def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        **kwargs
    ) -> Generator[str, None, None]:
        """
        Stream generated code token by token

        Yields:
            Generated tokens one at a time
        """
        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        else:
            messages.append({
                "role": "system",
                "content": "You are an expert full-stack developer. Generate clean, production-ready code."
            })
        messages.append({"role": "user", "content": prompt})

        # Apply chat template
        input_text = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        # Tokenize
        inputs = self.tokenizer(input_text, return_tensors="pt").to(self.model.device)

        # Setup streamer
        streamer = TextIteratorStreamer(
            self.tokenizer,
            skip_prompt=True,
            skip_special_tokens=True
        )

        # Generation config
        gen_kwargs = {
            **inputs,
            "max_new_tokens": kwargs.get("max_new_tokens", self.config.max_new_tokens),
            "temperature": kwargs.get("temperature", self.config.temperature),
            "top_p": kwargs.get("top_p", self.config.top_p),
            "do_sample": True,
            "streamer": streamer,
        }

        # Run generation in thread
        thread = Thread(target=self.model.generate, kwargs=gen_kwargs)
        thread.start()

        # Yield tokens
        for token in streamer:
            yield token

        thread.join()

    def generate_code(
        self,
        task: str,
        language: str = "typescript",
        framework: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        High-level code generation with structured prompting

        Args:
            task: What to generate (e.g., "login form component")
            language: Programming language
            framework: Framework to use (e.g., "react", "fastapi")
            context: Additional context about the project

        Returns:
            Generated code
        """
        # Build structured prompt
        prompt_parts = [f"Create a {task}"]

        if framework:
            prompt_parts.append(f"using {framework}")
        prompt_parts.append(f"in {language}")

        if context:
            prompt_parts.append(f"\n\nContext: {context}")

        prompt_parts.append("\n\nRequirements:")
        prompt_parts.append("- Production-ready code with proper error handling")
        prompt_parts.append("- Follow best practices and conventions")
        prompt_parts.append("- Include necessary imports")
        prompt_parts.append("- Add TypeScript types if applicable")

        prompt = " ".join(prompt_parts[:3]) + "\n".join(prompt_parts[3:])

        return self.generate(prompt)

    def generate_component(
        self,
        component_name: str,
        component_type: str = "functional",
        props: Optional[List[str]] = None,
        features: Optional[List[str]] = None,
    ) -> str:
        """
        Generate a React component

        Args:
            component_name: Name of the component
            component_type: "functional" or "class"
            props: List of prop names
            features: Features to include (e.g., ["state", "effects", "form"])

        Returns:
            Generated React component code
        """
        prompt = f"Create a {component_type} React component called {component_name}"

        if props:
            prompt += f" with props: {', '.join(props)}"

        if features:
            prompt += f"\n\nInclude the following features: {', '.join(features)}"

        prompt += "\n\nUse TypeScript and Tailwind CSS for styling."

        return self.generate(prompt)

    def generate_api_endpoint(
        self,
        resource: str,
        methods: List[str] = None,
        auth_required: bool = True,
    ) -> str:
        """
        Generate FastAPI endpoint

        Args:
            resource: Resource name (e.g., "users", "products")
            methods: HTTP methods to include
            auth_required: Whether to include authentication

        Returns:
            Generated FastAPI code
        """
        methods = methods or ["GET", "POST", "PUT", "DELETE"]

        prompt = f"Create FastAPI CRUD endpoints for {resource}"
        prompt += f"\n\nMethods to implement: {', '.join(methods)}"

        if auth_required:
            prompt += "\nInclude JWT authentication dependency"

        prompt += "\n\nUse Pydantic schemas for request/response validation"
        prompt += "\nInclude proper error handling with HTTPException"

        return self.generate(prompt)

    def _create_stopping_criteria(self, stop_ids):
        """Create stopping criteria for generation"""
        from transformers import StoppingCriteria, StoppingCriteriaList

        class StopOnTokens(StoppingCriteria):
            def __init__(self, stop_ids):
                self.stop_ids = stop_ids

            def __call__(self, input_ids, scores, **kwargs):
                for stop_id in self.stop_ids:
                    if input_ids[0][-len(stop_id):].tolist() == stop_id:
                        return True
                return False

        return StoppingCriteriaList([StopOnTokens(stop_ids)])


class QwenCoderAgent:
    """
    Agent wrapper for integration with BharatBuild AI orchestrator
    Drop-in replacement for Claude-based code agent
    """

    def __init__(self, model_path: str, **kwargs):
        self.inference = QwenCoderInference(model_path, **kwargs)
        self.name = "QwenCoderAgent"

    async def generate_code(
        self,
        prompt: str,
        project_context: Optional[Dict] = None,
    ) -> Dict:
        """
        Generate code compatible with BharatBuild AI agent interface

        Returns:
            Dict with 'code', 'files', 'explanation' keys
        """
        # Build context-aware prompt
        full_prompt = prompt
        if project_context:
            tech_stack = project_context.get("tech_stack", "")
            requirements = project_context.get("requirements", "")
            full_prompt = f"Tech Stack: {tech_stack}\nRequirements: {requirements}\n\n{prompt}"

        # Generate
        response = self.inference.generate(full_prompt)

        # Parse response into files
        files = self._parse_files(response)

        return {
            "code": response,
            "files": files,
            "explanation": "",
            "tokens_used": len(self.inference.tokenizer.encode(response)),
        }

    def _parse_files(self, response: str) -> List[Dict]:
        """Parse generated response into file objects"""
        import re

        files = []
        # Match ```language or ### filename patterns
        pattern = r'(?:###\s*([^\n]+)\n)?```(\w+)?\n(.*?)```'

        for match in re.finditer(pattern, response, re.DOTALL):
            filename = match.group(1) or f"file.{match.group(2) or 'txt'}"
            language = match.group(2) or "text"
            content = match.group(3).strip()

            files.append({
                "path": filename.strip(),
                "content": content,
                "language": language,
            })

        return files


# Convenience function
def load_model(model_path: str, **kwargs) -> QwenCoderInference:
    """Load fine-tuned model for inference"""
    return QwenCoderInference(model_path, **kwargs)


def main():
    """Interactive testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Test fine-tuned Qwen2.5-Coder")
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--prompt", type=str, help="Single prompt to run")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    args = parser.parse_args()

    # Load model
    print("Loading model...")
    inference = QwenCoderInference(args.model_path)
    print("Model loaded!")

    if args.prompt:
        # Single prompt
        response = inference.generate(args.prompt)
        print("\n" + "="*50)
        print(response)
        print("="*50)

    elif args.interactive:
        # Interactive mode
        print("\nInteractive mode. Type 'quit' to exit.\n")
        while True:
            prompt = input("You: ").strip()
            if prompt.lower() in ['quit', 'exit', 'q']:
                break

            print("\nGenerating...")
            response = inference.generate(prompt)
            print(f"\nAssistant:\n{response}\n")

    else:
        # Demo
        print("\nRunning demo prompts...\n")

        demos = [
            "Create a React button component with loading state using TypeScript and Tailwind",
            "Create a FastAPI endpoint for user registration with email validation",
        ]

        for prompt in demos:
            print(f"Prompt: {prompt}")
            print("-" * 40)
            response = inference.generate(prompt)
            print(response[:500] + "..." if len(response) > 500 else response)
            print("\n")


if __name__ == "__main__":
    main()
