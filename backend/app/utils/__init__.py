# Utilities
from app.utils.claude_client import claude_client, ClaudeClient
from app.utils.hybrid_client import hybrid_client, HybridClient

# For backwards compatibility, expose hybrid_client as the default
# When USE_LOCAL_QWEN=False, it behaves exactly like claude_client
default_client = hybrid_client

__all__ = [
    'claude_client',
    'ClaudeClient',
    'hybrid_client',
    'HybridClient',
    'default_client'
]
