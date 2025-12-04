"""
Mock Claude API Server for Testing
===================================
A lightweight mock server that mimics Anthropic's Claude API.
Use this for development and testing to avoid API costs.

Usage:
    python server.py [--port 8001] [--delay 0.5]

Endpoints:
    POST /v1/messages - Create a message (streaming and non-streaming)
    GET /health - Health check
"""

import argparse
import asyncio
import json
import time
import uuid
import random
from datetime import datetime
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

app = FastAPI(
    title="Mock Claude API",
    description="Mock Anthropic Claude API for testing",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration
class Config:
    response_delay: float = 0.02  # Delay between streaming chunks (seconds)
    typing_speed: int = 50  # Characters per chunk for streaming
    mock_responses: Dict[str, str] = {}  # Custom responses for specific prompts

config = Config()


# ============================================
# Pydantic Models (matching Anthropic's API)
# ============================================

class ContentBlock(BaseModel):
    type: str = "text"
    text: str = ""

class Message(BaseModel):
    role: str
    content: str | List[ContentBlock]

class MessagesRequest(BaseModel):
    model: str
    max_tokens: int = 4096
    messages: List[Message]
    system: Optional[str] = None
    stream: bool = False
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = None
    top_k: Optional[int] = None
    stop_sequences: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None

class Usage(BaseModel):
    input_tokens: int
    output_tokens: int

class MessagesResponse(BaseModel):
    id: str
    type: str = "message"
    role: str = "assistant"
    content: List[ContentBlock]
    model: str
    stop_reason: str = "end_turn"
    stop_sequence: Optional[str] = None
    usage: Usage


# ============================================
# Mock Response Generator
# ============================================

# Sample mock responses for different types of prompts
MOCK_RESPONSES = {
    "plan": """I'll create a comprehensive plan for this project:

## Project Plan

### Phase 1: Setup & Foundation
1. Initialize project structure
2. Set up development environment
3. Configure dependencies

### Phase 2: Core Implementation
1. Implement main features
2. Add business logic
3. Create data models

### Phase 3: Testing & Refinement
1. Write unit tests
2. Integration testing
3. Bug fixes and optimization

### Phase 4: Deployment
1. Prepare production configuration
2. Deploy to staging
3. Final review and production release

This plan provides a solid foundation for the project.""",

    "code": """Here's the implementation:

```python
def example_function(data):
    \"\"\"Process the input data and return results.\"\"\"
    results = []

    for item in data:
        # Process each item
        processed = transform(item)
        results.append(processed)

    return results

def transform(item):
    \"\"\"Transform a single item.\"\"\"
    return {
        'id': item.get('id'),
        'value': item.get('value', 0) * 2,
        'processed': True
    }
```

This code handles the data processing efficiently.""",

    "default": """I understand your request. Let me help you with that.

Based on the information provided, here's my analysis and recommendations:

1. **First Point**: This is an important consideration that should be addressed early in the process.

2. **Second Point**: Building on the first point, we should also consider the implications for scalability and maintenance.

3. **Third Point**: Finally, it's worth noting that this approach aligns well with best practices in the industry.

Would you like me to elaborate on any of these points or provide more specific guidance?"""
}

def get_mock_response(messages: List[Message], system: Optional[str] = None) -> str:
    """Generate a mock response based on the input."""
    # Try to import BharatBuild-specific responses first
    try:
        from bharatbuild_responses import get_bharatbuild_response, get_response_for_file
        use_bharatbuild = True
    except ImportError:
        use_bharatbuild = False

    # Try to import generic mock responses
    try:
        from mock_responses import get_response_for_prompt
        use_advanced = True
    except ImportError:
        use_advanced = False

    # Get the last user message
    last_message = ""
    for msg in reversed(messages):
        content = msg.content
        if isinstance(content, list):
            content = " ".join([c.text for c in content if hasattr(c, 'text')])
        if msg.role == "user":
            last_message = content
            break

    # Check for custom responses first
    for key, response in config.mock_responses.items():
        if key.lower() in last_message.lower():
            return response

    # Use BharatBuild-specific responses if system prompt is provided
    if use_bharatbuild and system:
        return get_bharatbuild_response(system, last_message)

    # Use BharatBuild file responses for file generation requests
    if use_bharatbuild:
        # Check if this is a file generation request
        file_keywords = ["package.json", "index.html", "vite.config", "tailwind.config",
                         "tsconfig", "main.tsx", "app.tsx", "index.css", ".tsx", ".ts", ".js"]
        for keyword in file_keywords:
            if keyword in last_message.lower():
                return get_response_for_file(last_message)

    # Use advanced mock responses if available
    if use_advanced:
        return get_response_for_prompt(last_message)

    # Fallback to basic responses
    last_message_lower = last_message.lower()
    if any(word in last_message_lower for word in ["plan", "design", "architecture", "structure"]):
        return MOCK_RESPONSES["plan"]
    elif any(word in last_message_lower for word in ["code", "implement", "function", "write", "create"]):
        return MOCK_RESPONSES["code"]

    return MOCK_RESPONSES["default"]


def count_tokens(text: str) -> int:
    """Approximate token count (rough estimate: ~4 chars per token)."""
    return len(text) // 4 + 1


def generate_message_id() -> str:
    """Generate a message ID similar to Anthropic's format."""
    return f"msg_{uuid.uuid4().hex[:24]}"


# ============================================
# API Endpoints
# ============================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "mock-claude-api"}


@app.post("/v1/messages")
async def create_message(
    request: MessagesRequest,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="x-api-key"),
    anthropic_version: Optional[str] = Header(None, alias="anthropic-version")
):
    """
    Create a message - mimics Anthropic's /v1/messages endpoint.
    Supports both streaming and non-streaming responses.
    """

    # Basic auth check (accept any key for mock)
    api_key = x_api_key or (authorization.replace("Bearer ", "") if authorization else None)
    if not api_key:
        raise HTTPException(status_code=401, detail="Missing API key")

    # Generate mock response
    response_text = get_mock_response(request.messages, request.system)

    # Calculate token usage
    input_text = request.system or ""
    for msg in request.messages:
        content = msg.content
        if isinstance(content, list):
            content = " ".join([c.text for c in content if hasattr(c, 'text')])
        input_text += content

    input_tokens = count_tokens(input_text)
    output_tokens = count_tokens(response_text)

    message_id = generate_message_id()

    if request.stream:
        # Streaming response
        return StreamingResponse(
            stream_response(
                message_id=message_id,
                model=request.model,
                response_text=response_text,
                input_tokens=input_tokens,
                output_tokens=output_tokens
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    else:
        # Non-streaming response
        await asyncio.sleep(config.response_delay * 10)  # Simulate processing time

        return MessagesResponse(
            id=message_id,
            type="message",
            role="assistant",
            content=[ContentBlock(type="text", text=response_text)],
            model=request.model,
            stop_reason="end_turn",
            usage=Usage(input_tokens=input_tokens, output_tokens=output_tokens)
        )


async def stream_response(
    message_id: str,
    model: str,
    response_text: str,
    input_tokens: int,
    output_tokens: int
):
    """Generate SSE stream mimicking Anthropic's streaming format."""

    # Message start event
    yield f"event: message_start\ndata: {json.dumps({
        'type': 'message_start',
        'message': {
            'id': message_id,
            'type': 'message',
            'role': 'assistant',
            'content': [],
            'model': model,
            'stop_reason': None,
            'stop_sequence': None,
            'usage': {'input_tokens': input_tokens, 'output_tokens': 0}
        }
    })}\n\n"

    await asyncio.sleep(config.response_delay)

    # Content block start
    yield f"event: content_block_start\ndata: {json.dumps({
        'type': 'content_block_start',
        'index': 0,
        'content_block': {'type': 'text', 'text': ''}
    })}\n\n"

    await asyncio.sleep(config.response_delay)

    # Stream content in chunks
    chunk_size = config.typing_speed
    for i in range(0, len(response_text), chunk_size):
        chunk = response_text[i:i + chunk_size]

        yield f"event: content_block_delta\ndata: {json.dumps({
            'type': 'content_block_delta',
            'index': 0,
            'delta': {'type': 'text_delta', 'text': chunk}
        })}\n\n"

        await asyncio.sleep(config.response_delay)

    # Content block stop
    yield f"event: content_block_stop\ndata: {json.dumps({
        'type': 'content_block_stop',
        'index': 0
    })}\n\n"

    await asyncio.sleep(config.response_delay)

    # Message delta (with stop reason)
    yield f"event: message_delta\ndata: {json.dumps({
        'type': 'message_delta',
        'delta': {'stop_reason': 'end_turn', 'stop_sequence': None},
        'usage': {'output_tokens': output_tokens}
    })}\n\n"

    # Message stop
    yield f"event: message_stop\ndata: {json.dumps({'type': 'message_stop'})}\n\n"


# ============================================
# Additional Endpoints for Testing
# ============================================

@app.post("/v1/messages/count_tokens")
async def count_tokens_endpoint(request: MessagesRequest):
    """Count tokens in a message (mock implementation)."""
    input_text = request.system or ""
    for msg in request.messages:
        content = msg.content
        if isinstance(content, list):
            content = " ".join([c.text for c in content if hasattr(c, 'text')])
        input_text += content

    return {"input_tokens": count_tokens(input_text)}


@app.get("/v1/models")
async def list_models():
    """List available models (mock)."""
    return {
        "models": [
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
            {"id": "claude-3-opus-20240229", "name": "Claude 3 Opus"},
        ]
    }


@app.post("/mock/set-response")
async def set_mock_response(keyword: str, response: str):
    """Set a custom mock response for a specific keyword."""
    config.mock_responses[keyword] = response
    return {"status": "ok", "keyword": keyword}


@app.post("/mock/set-delay")
async def set_delay(delay: float):
    """Set the streaming delay (seconds between chunks)."""
    config.response_delay = delay
    return {"status": "ok", "delay": delay}


@app.get("/mock/config")
async def get_config():
    """Get current mock server configuration."""
    return {
        "response_delay": config.response_delay,
        "typing_speed": config.typing_speed,
        "custom_responses": list(config.mock_responses.keys())
    }


# ============================================
# Main Entry Point
# ============================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mock Claude API Server")
    parser.add_argument("--port", type=int, default=8001, help="Port to run the server on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--delay", type=float, default=0.02, help="Delay between streaming chunks")

    args = parser.parse_args()
    config.response_delay = args.delay

    print(f"""
============================================================
              Mock Claude API Server
============================================================
  Running on: http://{args.host}:{args.port}
  API Endpoint: http://localhost:{args.port}/v1/messages
  Health Check: http://localhost:{args.port}/health
------------------------------------------------------------
  To use with your app, set:
  ANTHROPIC_API_KEY=mock-key-for-testing
  ANTHROPIC_BASE_URL=http://localhost:{args.port}
============================================================
    """)

    uvicorn.run(app, host=args.host, port=args.port)
