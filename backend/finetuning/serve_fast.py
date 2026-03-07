from vllm import LLM, SamplingParams
from vllm.lora.request import LoRARequest
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import uvicorn
import json

app = FastAPI(title="Qwen Fast API")

print("Loading model with vLLM...")
llm = LLM(
    model="Qwen/Qwen2.5-Coder-7B-Instruct",
    enable_lora=True,
    max_lora_rank=64,
    gpu_memory_utilization=0.90,
    max_model_len=16384,
    trust_remote_code=True,
)
print("Model loaded!")

LORA_PATH = "./finetuned_models/qwen-coder/final"

class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = "You are an expert full-stack developer."
    max_tokens: int = 8192
    max_new_tokens: Optional[int] = None
    temperature: float = 0.7
    stream: bool = False

class GenerateResponse(BaseModel):
    content: str
    input_tokens: int
    output_tokens: int
    model: str

@app.get("/health")
async def health():
    return {"status": "healthy", "engine": "vllm"}

@app.post("/generate")
async def generate(request: GenerateRequest):
    messages = f"<|im_start|>system\n{request.system_prompt}<|im_end|>\n<|im_start|>user\n{request.prompt}<|im_end|>\n<|im_start|>assistant\n"

    max_tokens = request.max_new_tokens or request.max_tokens

    sampling_params = SamplingParams(
        temperature=request.temperature,
        max_tokens=max_tokens,
        repetition_penalty=1.1,
        stop=["<|im_end|>"]
    )
    lora_request = LoRARequest("qwen-coder", 1, LORA_PATH)

    if request.stream:
        async def stream_generator():
            outputs = llm.generate([messages], sampling_params, lora_request=lora_request)
            content = outputs[0].outputs[0].text
            # Simulate streaming by chunking
            chunk_size = 50
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield f"data: {json.dumps({'content': chunk})}\n\n"
            yield f"data: {json.dumps({'done': True, 'input_tokens': len(outputs[0].prompt_token_ids), 'output_tokens': len(outputs[0].outputs[0].token_ids)})}\n\n"

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    outputs = llm.generate([messages], sampling_params, lora_request=lora_request)
    content = outputs[0].outputs[0].text
    return GenerateResponse(
        content=content,
        input_tokens=len(outputs[0].prompt_token_ids),
        output_tokens=len(outputs[0].outputs[0].token_ids),
        model="qwen-coder-vllm"
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8888)
