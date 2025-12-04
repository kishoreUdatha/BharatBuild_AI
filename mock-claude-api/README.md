# Mock Claude API Server

A lightweight mock server that mimics Anthropic's Claude API for development and testing without incurring API costs.

## Features

- Full `/v1/messages` endpoint support
- Streaming (SSE) and non-streaming responses
- Bolt-style XML artifact responses for project generation
- Configurable response delays
- Custom mock responses via API
- Token counting simulation

## Quick Start

### Windows
```bash
# Double-click or run:
start-mock-api.bat
```

### Linux/Mac
```bash
chmod +x start-mock-api.sh
./start-mock-api.sh
```

### Manual Setup
```bash
cd mock-claude-api
pip install -r requirements.txt
python server.py --port 8001
```

## Usage

### Configure Your App

Set these environment variables in your backend `.env`:

```env
# Point to mock server instead of real API
ANTHROPIC_API_KEY=mock-key-for-testing
ANTHROPIC_BASE_URL=http://localhost:8001
```

Or modify `claude_client.py` to use the mock URL during development.

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/messages` | POST | Create message (streaming/non-streaming) |
| `/v1/models` | GET | List available models |
| `/v1/messages/count_tokens` | POST | Count tokens in request |
| `/health` | GET | Health check |
| `/mock/set-response` | POST | Set custom response for keyword |
| `/mock/set-delay` | POST | Set streaming delay |
| `/mock/config` | GET | Get current configuration |

### Example Request

```bash
curl -X POST http://localhost:8001/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: mock-key" \
  -d '{
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Create a React todo app"}
    ],
    "stream": true
  }'
```

### Custom Responses

Set custom responses for specific keywords:

```bash
curl -X POST "http://localhost:8001/mock/set-response?keyword=hello&response=Hi%20there!"
```

### Adjust Streaming Speed

```bash
# Faster streaming (0.01s between chunks)
curl -X POST "http://localhost:8001/mock/set-delay?delay=0.01"

# Slower streaming (0.1s between chunks)
curl -X POST "http://localhost:8001/mock/set-delay?delay=0.1"
```

## Mock Response Types

The server automatically selects response types based on keywords:

| Keywords | Response Type |
|----------|--------------|
| "create", "build", "react", "app" | Full project with boltArtifact XML |
| "function", "implement", "code" | Code snippet |
| "api", "endpoint", "rest" | API endpoint code |
| "fix", "bug", "error" | Bug fix with explanation |
| "plan", "design", "architecture" | Project plan |
| Other | General conversational response |

## Integration with BharatBuild

### Modify claude_client.py

Add a check for development mode:

```python
import os

class ClaudeClient:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")

        # Use mock server in development
        if os.getenv("USE_MOCK_CLAUDE", "false").lower() == "true":
            self.base_url = "http://localhost:8001"
        else:
            self.base_url = "https://api.anthropic.com"
```

Then set `USE_MOCK_CLAUDE=true` in your `.env` for development.

## Command Line Options

```bash
python server.py [options]

Options:
  --port PORT     Port to run server on (default: 8001)
  --host HOST     Host to bind to (default: 0.0.0.0)
  --delay DELAY   Delay between streaming chunks in seconds (default: 0.02)
```

## Adding Custom Responses

Edit `mock_responses.py` to add new response templates:

```python
MY_CUSTOM_RESPONSE = """Your custom response here..."""

def get_response_for_prompt(prompt: str) -> str:
    if "my keyword" in prompt.lower():
        return MY_CUSTOM_RESPONSE
    # ... rest of function
```

## Limitations

- Token counting is approximate (4 chars ≈ 1 token)
- No actual AI processing (responses are template-based)
- Vision/image inputs return default text response
- Tool use not fully implemented

## Cost Savings

Using this mock server during development can save significant costs:
- Claude API: ~$3-15 per 1M tokens
- Mock server: $0

Recommended workflow:
1. Use mock server for UI development and testing
2. Switch to real API for final integration testing
3. Use mock server in CI/CD pipelines
