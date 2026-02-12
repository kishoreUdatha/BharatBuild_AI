"""
Model Serving API
FastAPI server for the fine-tuned model
"""
import os
import asyncio
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn

from inference import QwenCoderInference, QwenCoderAgent


# Global model instance
model: Optional[QwenCoderInference] = None
agent: Optional[QwenCoderAgent] = None


class GenerationRequest(BaseModel):
    """Request model for code generation"""
    prompt: str = Field(..., description="The code generation prompt")
    system_prompt: Optional[str] = Field(None, description="Optional system prompt")
    max_new_tokens: int = Field(2048, ge=1, le=8192)
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    top_k: int = Field(50, ge=1, le=100)
    stream: bool = Field(False, description="Enable streaming response")


class GenerationResponse(BaseModel):
    """Response model for code generation"""
    generated_code: str
    tokens_generated: int
    model: str


class ComponentRequest(BaseModel):
    """Request for React component generation"""
    component_name: str
    component_type: str = "functional"
    props: Optional[List[str]] = None
    features: Optional[List[str]] = None


class APIEndpointRequest(BaseModel):
    """Request for FastAPI endpoint generation"""
    resource: str
    methods: List[str] = ["GET", "POST", "PUT", "DELETE"]
    auth_required: bool = True


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    model_loaded: bool
    model_name: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model on startup"""
    global model, agent

    model_path = os.environ.get("MODEL_PATH", "./finetuned_models/qwen-coder/final")

    print(f"Loading model from {model_path}...")
    model = QwenCoderInference(model_path)
    agent = QwenCoderAgent(model_path)
    print("Model loaded successfully!")

    yield

    # Cleanup
    model = None
    agent = None


app = FastAPI(
    title="BharatBuild AI - Code Generation API",
    description="Fine-tuned Qwen2.5-Coder for code generation",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if model else "unhealthy",
        model_loaded=model is not None,
        model_name="Qwen2.5-Coder-BharatBuild"
    )


@app.post("/generate", response_model=GenerationResponse)
async def generate_code(request: GenerationRequest):
    """Generate code from prompt"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if request.stream:
        return StreamingResponse(
            stream_generate(request),
            media_type="text/event-stream"
        )

    generated = model.generate(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
        top_p=request.top_p,
        top_k=request.top_k,
    )

    return GenerationResponse(
        generated_code=generated,
        tokens_generated=len(model.tokenizer.encode(generated)),
        model="qwen2.5-coder-bharatbuild"
    )


async def stream_generate(request: GenerationRequest):
    """Stream generation response"""
    for token in model.generate_stream(
        prompt=request.prompt,
        system_prompt=request.system_prompt,
        max_new_tokens=request.max_new_tokens,
        temperature=request.temperature,
    ):
        yield f"data: {token}\n\n"
        await asyncio.sleep(0)  # Allow other tasks to run

    yield "data: [DONE]\n\n"


@app.post("/generate/component")
async def generate_component(request: ComponentRequest):
    """Generate a React component"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    generated = model.generate_component(
        component_name=request.component_name,
        component_type=request.component_type,
        props=request.props,
        features=request.features,
    )

    return {
        "component": generated,
        "component_name": request.component_name,
    }


@app.post("/generate/endpoint")
async def generate_endpoint(request: APIEndpointRequest):
    """Generate a FastAPI endpoint"""
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")

    generated = model.generate_api_endpoint(
        resource=request.resource,
        methods=request.methods,
        auth_required=request.auth_required,
    )

    return {
        "endpoint": generated,
        "resource": request.resource,
    }


@app.post("/agent/generate")
async def agent_generate(request: GenerationRequest, background_tasks: BackgroundTasks):
    """
    Agent-style generation compatible with BharatBuild AI orchestrator
    Returns structured response with parsed files
    """
    if not agent:
        raise HTTPException(status_code=503, detail="Agent not loaded")

    result = await agent.generate_code(
        prompt=request.prompt,
        project_context=None  # Can be extended
    )

    return result


def main():
    """Run the server"""
    import argparse

    parser = argparse.ArgumentParser(description="Run code generation server")
    parser.add_argument("--model-path", type=str, required=True)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--workers", type=int, default=1)
    args = parser.parse_args()

    os.environ["MODEL_PATH"] = args.model_path

    uvicorn.run(
        "serve:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=False,
    )


if __name__ == "__main__":
    main()
