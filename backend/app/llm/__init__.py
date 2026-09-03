"""
BharatBuild AI - Unified Multi-Provider LLM Client

Usage:
    from app.llm import unified_llm_client
    
    # Generate completion
    result = await unified_llm_client.generate("claude-sonnet-5", "Hello!")
    
    # Stream completion
    async for chunk in unified_llm_client.generate_stream("gpt-4o", "Write a story"):
        print(chunk, end="")
    
    # Explicit provider prefix
    result = await unified_llm_client.generate("deepseek/deepseek-coder", "Write Python code")
    
    # Check available providers
    providers = unified_llm_client.list_available_providers()
"""

from app.llm.unified_client import unified_llm_client

__all__ = ['unified_llm_client']
