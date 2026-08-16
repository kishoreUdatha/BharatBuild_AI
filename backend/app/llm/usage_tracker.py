"""
LLM Usage Tracker - Logs every AI call with tokens, cost, model, latency.

Tracks:
- Per request: input_tokens, output_tokens, model, cost, latency
- Per user: daily/monthly totals, remaining balance
- Per project: tokens spent on each project

Used by unified_llm_client to automatically log all AI calls.
"""

import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, date
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Pricing per million tokens (input, output) in USD
MODEL_PRICING = {
    # Anthropic (updated Aug 2026 from anthropic.com/pricing)
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-5": (2.00, 10.00),
    "claude-sonnet-4.6": (3.00, 15.00),
    "claude-sonnet-4.5": (3.00, 15.00),
    "claude-sonnet-4-20250514": (3.00, 15.00),
    "claude-opus-5": (5.00, 25.00),
    "claude-opus-4.8": (5.00, 25.00),
    "claude-opus-4.7": (5.00, 25.00),
    "claude-opus-4.6": (5.00, 25.00),
    "claude-opus-4.5": (5.00, 25.00),
    "claude-fable-5": (10.00, 50.00),
    # OpenAI
    "gpt-5.6-sol": (5.00, 30.00),
    "gpt-5.6-terra": (3.00, 15.00),
    "gpt-5.6-luna": (1.00, 5.00),
    # Deepseek
    "deepseek-chat": (0.14, 0.28),
    "deepseek-coder": (0.14, 0.28),
    "deepseek-v3.2": (0.14, 0.28),
    # Google
    "gemini-2.0-flash": (0.10, 0.40),
    "gemini-1.5-pro": (1.25, 5.00),
    # Budget
    "qwen3-coder-next": (0.15, 0.60),
    "minimax-m2.5": (0.10, 0.30),
    "minimax-m2.1": (0.10, 0.30),
    "glm-5": (0.10, 0.30),
}

# Default pricing for unknown models
DEFAULT_PRICING = (2.00, 10.00)

# ============================================================
# KIRO-STYLE CREDIT SYSTEM
# $0.04 per credit (same as Kiro add-on price)
# Formula: credits = (total_tokens / 1000) * model_multiplier
# ============================================================
CREDIT_PRICE_USD = 0.04  # What user pays per credit
TOKENS_PER_CREDIT = 1000

MODEL_CREDIT_MULTIPLIER = {
    # Anthropic
    "claude-haiku-4-5": 0.4,
    "claude-sonnet-5": 1.0,
    "claude-sonnet-4.6": 1.3,
    "claude-sonnet-4.5": 1.0,
    "claude-sonnet-4-20250514": 1.3,
    "claude-opus-5": 2.5,
    "claude-opus-4.8": 2.5,
    "claude-opus-4.7": 2.5,
    "claude-opus-4.6": 2.0,
    "claude-opus-4.5": 2.0,
    "claude-fable-5": 5.0,
    # OpenAI
    "gpt-5.6-sol": 3.0,
    "gpt-5.6-terra": 1.5,
    "gpt-5.6-luna": 0.5,
    # Budget
    "deepseek-chat": 0.1,
    "deepseek-coder": 0.1,
    "deepseek-v3.2": 0.1,
    "qwen3-coder-next": 0.1,
    "minimax-m2.5": 0.1,
    "minimax-m2.1": 0.1,
    "glm-5": 0.1,
    # Google
    "gemini-2.0-flash": 0.3,
    "gemini-1.5-pro": 1.0,
}

DEFAULT_CREDIT_MULTIPLIER = 1.0


@dataclass
class UsageRecord:
    """Single AI call usage record"""
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float
    credits_used: float
    latency_ms: int
    timestamp: datetime
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    agent_type: Optional[str] = None
    operation: Optional[str] = None
    success: bool = True


class UsageTracker:
    """
    Tracks all LLM usage in-memory and persists to database.
    
    Usage:
        tracker = UsageTracker()
        
        # Start tracking a call
        ctx = tracker.start_call("claude-haiku-4-5", user_id="abc")
        
        # ... make API call ...
        
        # End tracking with token counts
        record = tracker.end_call(ctx, input_tokens=100, output_tokens=50)
    """
    
    def __init__(self):
        # In-memory buffer for batch writes
        self._buffer = []
        self._session_usage = {
            "total_tokens": 0,
            "total_cost_usd": 0.0,
            "total_credits": 0.0,
            "calls": 0,
            "models_used": set(),
        }
    
    def start_call(
        self,
        model: str,
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        operation: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Start tracking an API call. Returns context dict to pass to end_call."""
        return {
            "model": model,
            "user_id": user_id,
            "project_id": project_id,
            "agent_type": agent_type,
            "operation": operation,
            "start_time": time.time(),
        }
    
    def end_call(
        self,
        ctx: Dict[str, Any],
        input_tokens: int = 0,
        output_tokens: int = 0,
        success: bool = True,
    ) -> UsageRecord:
        """End tracking an API call. Logs the usage and credits consumed."""
        model = ctx["model"]
        latency_ms = int((time.time() - ctx["start_time"]) * 1000)
        total_tokens = input_tokens + output_tokens
        
        # Calculate cost in USD
        cost_usd = self._calculate_cost(model, input_tokens, output_tokens)
        
        # Calculate credits used: (total_tokens / 1000) * multiplier
        credits_used = self._calculate_credits(model, total_tokens)
        
        # Determine provider from model name
        provider = self._detect_provider(model)
        
        # Create record
        record = UsageRecord(
            model=model,
            provider=provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            credits_used=credits_used,
            latency_ms=latency_ms,
            timestamp=datetime.utcnow(),
            user_id=ctx.get("user_id"),
            project_id=ctx.get("project_id"),
            agent_type=ctx.get("agent_type"),
            operation=ctx.get("operation"),
            success=success,
        )
        
        # Update session totals
        self._session_usage["total_tokens"] += total_tokens
        self._session_usage["total_cost_usd"] += cost_usd
        self._session_usage["total_credits"] += credits_used
        self._session_usage["calls"] += 1
        self._session_usage["models_used"].add(model)
        
        # Buffer for batch DB write
        self._buffer.append(record)
        
        # Log
        logger.info(
            f"[Usage] {model} | {input_tokens}+{output_tokens}={total_tokens} tokens | "
            f"{credits_used:.2f} credits | ${cost_usd:.4f} | {latency_ms}ms | {ctx.get('agent_type', '-')}"
        )
        
        return record
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get usage summary for the current session"""
        return {
            "total_tokens": self._session_usage["total_tokens"],
            "total_cost_usd": round(self._session_usage["total_cost_usd"], 4),
            "total_credits": round(self._session_usage["total_credits"], 2),
            "total_calls": self._session_usage["calls"],
            "models_used": list(self._session_usage["models_used"]),
        }
    
    def get_request_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a specific request without logging"""
        return self._calculate_cost(model, input_tokens, output_tokens)
    
    def get_request_credits(self, model: str, total_tokens: int) -> float:
        """Calculate credits for a specific request without logging"""
        return self._calculate_credits(model, total_tokens)
    
    async def flush_to_database(self, db_session=None):
        """Flush buffered records to database"""
        if not self._buffer:
            return 0
        
        records_to_flush = self._buffer[:]
        self._buffer = []
        
        if db_session:
            try:
                from app.models.usage import TokenUsageLog
                for record in records_to_flush:
                    log = TokenUsageLog(
                        user_id=record.user_id or "",
                        project_id=record.project_id or "",
                        model=record.model,
                        input_tokens=record.input_tokens,
                        output_tokens=record.output_tokens,
                        total_tokens=record.total_tokens,
                        cost_usd=record.cost_usd,
                        latency_ms=record.latency_ms,
                        agent_type=record.agent_type or "",
                        operation=record.operation or "",
                        success=record.success,
                    )
                    db_session.add(log)
                await db_session.commit()
                logger.info(f"[Usage] Flushed {len(records_to_flush)} records to database")
            except Exception as e:
                logger.error(f"[Usage] Failed to flush to database: {e}")
                # Put records back in buffer
                self._buffer = records_to_flush + self._buffer
        
        return len(records_to_flush)
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate USD cost for a model call"""
        # Strip provider prefix for pricing lookup
        model_name = model.split("/")[-1] if "/" in model else model
        
        input_price, output_price = MODEL_PRICING.get(model_name, DEFAULT_PRICING)
        
        cost = (input_tokens / 1_000_000) * input_price + (output_tokens / 1_000_000) * output_price
        return round(cost, 6)
    
    def _calculate_credits(self, model: str, total_tokens: int) -> float:
        """
        Calculate credits consumed.
        
        Formula: credits = (total_tokens / TOKENS_PER_CREDIT) * credit_multiplier
        
        Examples:
          Haiku, 5000 tokens  → 5000/1000 * 0.4 = 2.0 credits
          Sonnet, 5000 tokens → 5000/1000 * 1.3 = 6.5 credits
          Deepseek, 5000 tokens → 5000/1000 * 0.1 = 0.5 credits
        """
        model_name = model.split("/")[-1] if "/" in model else model
        multiplier = MODEL_CREDIT_MULTIPLIER.get(model_name, DEFAULT_CREDIT_MULTIPLIER)
        
        credits = (total_tokens / TOKENS_PER_CREDIT) * multiplier
        return round(credits, 2)
    
    def _detect_provider(self, model: str) -> str:
        """Detect provider from model name"""
        model_lower = model.lower()
        if "/" in model_lower:
            return model_lower.split("/")[0]
        if "claude" in model_lower or "haiku" in model_lower or "sonnet" in model_lower or "opus" in model_lower:
            return "anthropic"
        if "gpt" in model_lower:
            return "openai"
        if "deepseek" in model_lower:
            return "deepseek"
        if "gemini" in model_lower:
            return "google"
        if "qwen" in model_lower:
            return "alibaba"
        if "glm" in model_lower:
            return "zhipu"
        if "minimax" in model_lower:
            return "minimax"
        return "unknown"


# Singleton instance
usage_tracker = UsageTracker()
