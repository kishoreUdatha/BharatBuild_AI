"""
Qwen Coder Client - Local Fine-tuned Model Integration
Drop-in replacement for Claude API using local Qwen model

Usage:
    1. Train the model using RunPod (see backend/finetuning/runpod_package/)
    2. Download trained model to ./finetuned_models/qwen-coder-7b/final/
    3. Set USE_LOCAL_QWEN=True in .env
    4. The hybrid_client will automatically route simple tasks to Qwen

Requirements:
    - torch>=2.0.0
    - transformers>=4.40.0
    - peft>=0.10.0
    - bitsandbytes>=0.43.0 (for 4-bit quantization)
    - CUDA-capable GPU with 8GB+ VRAM
"""
import asyncio
from typing import Optional, Dict, List, Any, AsyncGenerator
from pathlib import Path
import threading
import time

# Lazy import torch to avoid ImportError on systems without GPU
torch = None

from app.core.config import settings
from app.core.logging_config import logger


def _import_torch():
    """Lazy import torch to avoid errors on systems without GPU"""
    global torch
    if torch is None:
        try:
            import torch as _torch
            torch = _torch
        except ImportError:
            logger.warning("PyTorch not installed. Qwen client will not be available.")
            raise ImportError("PyTorch is required for Qwen client. Install with: pip install torch")
    return torch


class QwenCoderClient:
    """
    Qwen Coder client for local fine-tuned model inference.
    Mirrors ClaudeClient interface for seamless integration.
    """

    _instance = None
    _lock = threading.Lock()
    _model = None
    _tokenizer = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.model_path = getattr(settings, 'QWEN_MODEL_PATH', './finetuned_models/qwen-coder-7b/final')
        self.base_model = getattr(settings, 'QWEN_BASE_MODEL', 'Qwen/Qwen2.5-Coder-7B-Instruct')
        self.max_tokens_default = getattr(settings, 'QWEN_MAX_TOKENS', 4096)
        self.temperature_default = getattr(settings, 'QWEN_TEMPERATURE', 0.7)

        # Lazy loading - don't load model or torch until first use
        self._model_loaded = False
        self._torch_available = None  # None = not checked yet
        self.device = None  # Will be set when torch is imported

        logger.info(f"QwenCoderClient initialized (lazy loading): model_path={self.model_path}")
        self._initialized = True

    def _check_torch(self) -> bool:
        """Check if torch is available and set device"""
        if self._torch_available is not None:
            return self._torch_available

        try:
            _import_torch()
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            self._torch_available = True
            logger.info(f"PyTorch available, device={self.device}")
            return True
        except ImportError:
            self._torch_available = False
            logger.warning("PyTorch not available, Qwen client disabled")
            return False

    def _load_model(self):
        """Load model on first use (lazy loading)"""
        if self._model_loaded:
            return

        # Check torch availability first
        if not self._check_torch():
            raise RuntimeError("PyTorch is not available. Cannot load Qwen model.")

        with self._lock:
            if self._model_loaded:
                return

            logger.info(f"Loading Qwen model from {self.model_path}...")
            start_time = time.time()

            try:
                from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
                from peft import PeftModel

                # Check if model path exists
                model_path = Path(self.model_path)

                if model_path.exists() and (model_path / "adapter_config.json").exists():
                    # Load fine-tuned model (LoRA adapter)
                    logger.info("Loading fine-tuned LoRA adapter...")

                    # Quantization config for memory efficiency
                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )

                    # Load base model
                    base_model = AutoModelForCausalLM.from_pretrained(
                        self.base_model,
                        quantization_config=quantization_config,
                        device_map="auto",
                        trust_remote_code=True,
                    )

                    # Load LoRA adapter
                    self._model = PeftModel.from_pretrained(base_model, str(model_path))
                    self._tokenizer = AutoTokenizer.from_pretrained(str(model_path))

                    logger.info(f"Fine-tuned model loaded successfully")

                else:
                    # Load base model only (fallback)
                    logger.warning(f"Fine-tuned model not found at {model_path}, loading base model...")

                    quantization_config = BitsAndBytesConfig(
                        load_in_4bit=True,
                        bnb_4bit_compute_dtype=torch.float16,
                        bnb_4bit_use_double_quant=True,
                        bnb_4bit_quant_type="nf4"
                    )

                    self._model = AutoModelForCausalLM.from_pretrained(
                        self.base_model,
                        quantization_config=quantization_config,
                        device_map="auto",
                        trust_remote_code=True,
                    )
                    self._tokenizer = AutoTokenizer.from_pretrained(self.base_model)

                # Set pad token
                if self._tokenizer.pad_token is None:
                    self._tokenizer.pad_token = self._tokenizer.eos_token

                self._model_loaded = True
                load_time = time.time() - start_time
                logger.info(f"Qwen model loaded in {load_time:.2f}s")

            except Exception as e:
                logger.error(f"Failed to load Qwen model: {e}")
                raise

    def _format_prompt(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Format prompt in ChatML format for Qwen"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Use tokenizer's chat template
        if hasattr(self._tokenizer, 'apply_chat_template'):
            return self._tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True
            )

        # Fallback: manual ChatML format
        formatted = ""
        for msg in messages:
            formatted += f"<|im_start|>{msg['role']}\n{msg['content']}<|im_end|>\n"
        formatted += "<|im_start|>assistant\n"
        return formatted

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "qwen",  # Ignored, kept for compatibility
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate response from Qwen model (non-streaming)
        Compatible with ClaudeClient.generate() interface
        """
        # Load model if not loaded
        if not self._model_loaded:
            self._load_model()

        # Handle conversation history
        if messages:
            # Build full prompt from messages
            full_prompt = ""
            sys_prompt = system_prompt
            for msg in messages:
                if msg["role"] == "system":
                    sys_prompt = msg["content"]
                elif msg["role"] == "user":
                    full_prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    full_prompt += f"Assistant: {msg['content']}\n"
            full_prompt += f"User: {prompt}"
            prompt = full_prompt

        # Set defaults
        if max_tokens is None:
            max_tokens = self.max_tokens_default
        if temperature is None:
            temperature = self.temperature_default

        # Format prompt
        formatted_prompt = self._format_prompt(prompt, system_prompt)

        logger.info(f"Qwen generate: prompt_len={len(prompt)}, max_tokens={max_tokens}")

        # Run inference in thread pool to not block async
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._generate_sync,
            formatted_prompt,
            max_tokens,
            temperature
        )

        return result

    def _generate_sync(
        self,
        formatted_prompt: str,
        max_tokens: int,
        temperature: float
    ) -> Dict[str, Any]:
        """Synchronous generation (runs in thread pool)"""
        try:
            # Tokenize
            inputs = self._tokenizer(
                formatted_prompt,
                return_tensors="pt",
                truncation=True,
                max_length=8192
            ).to(self._model.device)

            input_length = inputs.input_ids.shape[1]

            # Generate
            with torch.no_grad():
                outputs = self._model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    temperature=temperature,
                    do_sample=temperature > 0,
                    top_p=0.95,
                    pad_token_id=self._tokenizer.pad_token_id,
                    eos_token_id=self._tokenizer.eos_token_id,
                )

            # Decode output (only new tokens)
            generated_tokens = outputs[0][input_length:]
            content = self._tokenizer.decode(generated_tokens, skip_special_tokens=True)

            # Clean up response
            content = content.strip()
            if "<|im_end|>" in content:
                content = content.split("<|im_end|>")[0].strip()

            output_tokens = len(generated_tokens)

            result = {
                "content": content,
                "model": "qwen-coder-7b-finetuned",
                "input_tokens": input_length,
                "output_tokens": output_tokens,
                "total_tokens": input_length + output_tokens,
                "stop_reason": "end_turn",
                "id": f"qwen-{int(time.time())}"
            }

            logger.info(f"Qwen response: tokens={result['total_tokens']}")

            return result

        except Exception as e:
            logger.error(f"Qwen generation error: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "qwen",
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from Qwen model
        Compatible with ClaudeClient.generate_stream() interface
        """
        # Load model if not loaded
        if not self._model_loaded:
            self._load_model()

        # Handle conversation history
        if messages:
            full_prompt = ""
            sys_prompt = system_prompt
            for msg in messages:
                if msg["role"] == "system":
                    sys_prompt = msg["content"]
                elif msg["role"] == "user":
                    full_prompt += f"User: {msg['content']}\n"
                elif msg["role"] == "assistant":
                    full_prompt += f"Assistant: {msg['content']}\n"
            full_prompt += f"User: {prompt}"
            prompt = full_prompt
            system_prompt = sys_prompt

        # Set defaults
        if max_tokens is None:
            max_tokens = self.max_tokens_default
        if temperature is None:
            temperature = self.temperature_default

        # Format prompt
        formatted_prompt = self._format_prompt(prompt, system_prompt)

        logger.info(f"Qwen streaming: prompt_len={len(prompt)}, max_tokens={max_tokens}")

        # Tokenize
        inputs = self._tokenizer(
            formatted_prompt,
            return_tensors="pt",
            truncation=True,
            max_length=8192
        ).to(self._model.device)

        input_length = inputs.input_ids.shape[1]

        # Use TextIteratorStreamer for streaming
        try:
            from transformers import TextIteratorStreamer

            streamer = TextIteratorStreamer(
                self._tokenizer,
                skip_prompt=True,
                skip_special_tokens=True
            )

            # Generate in background thread
            generation_kwargs = {
                **inputs,
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "do_sample": temperature > 0,
                "top_p": 0.95,
                "pad_token_id": self._tokenizer.pad_token_id,
                "eos_token_id": self._tokenizer.eos_token_id,
                "streamer": streamer,
            }

            # Start generation in thread
            thread = threading.Thread(
                target=self._model.generate,
                kwargs=generation_kwargs
            )
            thread.start()

            # Stream output
            output_tokens = 0
            for text in streamer:
                if text:
                    # Stop at end marker
                    if "<|im_end|>" in text:
                        text = text.split("<|im_end|>")[0]
                        if text:
                            yield text
                        break
                    output_tokens += len(self._tokenizer.encode(text))
                    yield text

            thread.join()

            # Yield token usage marker (compatible with ClaudeClient)
            yield f"__TOKEN_USAGE__:{input_length}:{output_tokens}:qwen-coder-7b-finetuned"

        except ImportError:
            # Fallback: non-streaming generation
            logger.warning("TextIteratorStreamer not available, falling back to non-streaming")
            result = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                temperature=temperature
            )
            yield result["content"]
            yield f"__TOKEN_USAGE__:{result['input_tokens']}:{result['output_tokens']}:qwen-coder-7b-finetuned"

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "qwen"
    ) -> float:
        """
        Calculate cost - Local model is FREE!
        """
        # Local model has no API cost
        # Only electricity/GPU cost which we don't track
        return 0.0

    def calculate_cost_in_paise(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "qwen"
    ) -> int:
        """
        Calculate cost in paise - Local model is FREE!
        """
        return 0

    def is_available(self) -> bool:
        """Check if model is available (torch + model files)"""
        try:
            # Check if torch is available
            if not self._check_torch():
                return False

            # Check if CUDA is available (required for reasonable performance)
            if self.device != "cuda":
                logger.warning("CUDA not available - Qwen requires GPU for reasonable performance")
                return False

            # Check if model files exist (either fine-tuned or base model)
            model_path = Path(self.model_path)
            if model_path.exists():
                return True

            # Base model can be downloaded from HuggingFace
            logger.info(f"Fine-tuned model not found at {model_path}, will use base model from HuggingFace")
            return True

        except Exception as e:
            logger.error(f"Error checking Qwen availability: {e}")
            return False


# Create singleton instance (lazy - won't load model until used)
qwen_client = QwenCoderClient()
