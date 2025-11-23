from anthropic import AsyncAnthropic, Anthropic
from typing import Optional, Dict, List, Any, AsyncGenerator
import asyncio
from app.core.config import settings
from app.core.logging_config import logger


class ClaudeClient:
    """Claude API client wrapper for both streaming and non-streaming requests"""

    def __init__(self):
        self.async_client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.sync_client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.haiku_model = settings.CLAUDE_HAIKU_MODEL
        self.sonnet_model = settings.CLAUDE_SONNET_MODEL

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Generate response from Claude (non-streaming)

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: "haiku" or "sonnet"
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            messages: Optional list of previous messages for conversation

        Returns:
            Dict with response and metadata
        """
        try:
            # Select model
            model_name = self.sonnet_model if model == "sonnet" else self.haiku_model

            # Build messages
            if messages is None:
                messages = []

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Set defaults
            if max_tokens is None:
                max_tokens = settings.CLAUDE_MAX_TOKENS
            if temperature is None:
                temperature = settings.CLAUDE_TEMPERATURE

            # Make API call
            response = await self.async_client.messages.create(
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=messages
            )

            # Extract response
            content = response.content[0].text if response.content else ""

            result = {
                "content": content,
                "model": model_name,
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
                "stop_reason": response.stop_reason,
                "id": response.id
            }

            logger.info(f"Claude API call: {model_name}, tokens: {result['total_tokens']}")

            return result

        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def generate_stream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None,
        messages: Optional[List[Dict[str, str]]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generate streaming response from Claude

        Args:
            prompt: User prompt
            system_prompt: System prompt
            model: "haiku" or "sonnet"
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation
            messages: Optional list of previous messages for conversation

        Yields:
            Chunks of text as they arrive
        """
        try:
            # Select model
            model_name = self.sonnet_model if model == "sonnet" else self.haiku_model

            # Build messages
            if messages is None:
                messages = []

            messages.append({
                "role": "user",
                "content": prompt
            })

            # Set defaults
            if max_tokens is None:
                max_tokens = settings.CLAUDE_MAX_TOKENS
            if temperature is None:
                temperature = settings.CLAUDE_TEMPERATURE

            # Make streaming API call
            async with self.async_client.messages.stream(
                model=model_name,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt if system_prompt else "",
                messages=messages
            ) as stream:
                async for text in stream.text_stream:
                    yield text

            # Get final message with usage stats
            final_message = await stream.get_final_message()

            logger.info(
                f"Claude streaming call: {model_name}, "
                f"tokens: {final_message.usage.input_tokens + final_message.usage.output_tokens}"
            )

        except Exception as e:
            logger.error(f"Claude streaming API error: {e}")
            raise

    async def batch_generate(
        self,
        prompts: List[str],
        system_prompt: Optional[str] = None,
        model: str = "haiku",
        max_tokens: int = None,
        temperature: float = None
    ) -> List[Dict[str, Any]]:
        """
        Generate responses for multiple prompts concurrently

        Args:
            prompts: List of prompts
            system_prompt: System prompt
            model: "haiku" or "sonnet"
            max_tokens: Maximum tokens to generate
            temperature: Temperature for generation

        Returns:
            List of response dictionaries
        """
        tasks = [
            self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature
            )
            for prompt in prompts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Batch generate error for prompt {i}: {result}")
                processed_results.append({
                    "content": "",
                    "error": str(result)
                })
            else:
                processed_results.append(result)

        return processed_results

    def calculate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "haiku"
    ) -> float:
        """
        Calculate cost in USD based on token usage

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: "haiku" or "sonnet"

        Returns:
            Cost in USD
        """
        # Claude 3.5 Haiku pricing (as of Jan 2025)
        # Input: $0.80 / MTok, Output: $4.00 / MTok

        # Claude 3.5 Sonnet pricing (as of Jan 2025)
        # Input: $3.00 / MTok, Output: $15.00 / MTok

        if model == "sonnet":
            input_cost = (input_tokens / 1_000_000) * 3.00
            output_cost = (output_tokens / 1_000_000) * 15.00
        else:  # haiku
            input_cost = (input_tokens / 1_000_000) * 0.80
            output_cost = (output_tokens / 1_000_000) * 4.00

        return input_cost + output_cost

    def calculate_cost_in_paise(
        self,
        input_tokens: int,
        output_tokens: int,
        model: str = "haiku"
    ) -> int:
        """
        Calculate cost in Indian Paise (for database storage)

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            model: "haiku" or "sonnet"

        Returns:
            Cost in paise (1 USD ≈ 83 INR = 8300 paise as of Jan 2025)
        """
        usd_cost = self.calculate_cost(input_tokens, output_tokens, model)
        # Convert to INR, then to paise
        return int(usd_cost * 83 * 100)


# Create singleton instance
claude_client = ClaudeClient()
