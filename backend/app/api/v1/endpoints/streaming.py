from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import AsyncGenerator
import json
import asyncio

from app.core.database import get_db
from app.models.user import User
from app.modules.auth.dependencies import get_current_user
from app.utils.claude_client import claude_client
from app.utils.token_manager import token_manager
from app.core.logging_config import logger

router = APIRouter()


class StreamingRequest(BaseModel):
    """Bolt-style streaming request"""
    prompt: str
    mode: str = "code"  # code, chat, debug


async def generate_code_stream(
    prompt: str,
    user_id: str,
    db: AsyncSession
) -> AsyncGenerator[str, None]:
    """
    Generate code in real-time like Bolt.new
    Streams each step: thinking, planning, coding, testing
    """
    try:
        # Step 1: Thinking
        yield json.dumps({
            "type": "status",
            "status": "thinking",
            "message": "Analyzing your request..."
        }) + "\n"

        await asyncio.sleep(0.5)

        # Step 2: Planning
        yield json.dumps({
            "type": "status",
            "status": "planning",
            "message": "Creating project structure..."
        }) + "\n"

        # Generate file structure first
        planning_prompt = f"""Based on this request: "{prompt}"

Create a complete file structure. Return ONLY a JSON object with this structure:
{{
  "files": [
    {{"path": "src/index.js", "description": "Main entry point"}},
    {{"path": "src/App.jsx", "description": "Root component"}},
    ...
  ]
}}"""

        planning_response = await claude_client.generate(
            prompt=planning_prompt,
            model="haiku",
            max_tokens=2048
        )

        # Parse file structure
        try:
            file_structure = json.loads(planning_response["content"])
            files_to_generate = file_structure.get("files", [])
        except (json.JSONDecodeError, TypeError, KeyError) as e:
            # Fallback to basic structure
            logger.debug(f"Could not parse file structure: {e}")
            files_to_generate = [
                {"path": "src/index.js", "description": "Main file"},
                {"path": "package.json", "description": "Dependencies"},
            ]

        yield json.dumps({
            "type": "structure",
            "files": files_to_generate
        }) + "\n"

        await asyncio.sleep(0.3)

        # Step 3: Generate each file
        for file_info in files_to_generate:
            file_path = file_info["path"]

            yield json.dumps({
                "type": "file_start",
                "path": file_path,
                "message": f"Generating {file_path}..."
            }) + "\n"

            # Generate file content
            file_prompt = f"""Generate ONLY the code for {file_path}.

Project request: {prompt}

File description: {file_info.get('description', '')}

Return ONLY the code, no explanations. No markdown, no code blocks."""

            # Stream the file content
            full_content = ""
            async for chunk in claude_client.generate_stream(
                prompt=file_prompt,
                model="sonnet",
                max_tokens=4096
            ):
                full_content += chunk
                yield json.dumps({
                    "type": "file_content",
                    "path": file_path,
                    "content": chunk
                }) + "\n"

            # File completed
            yield json.dumps({
                "type": "file_complete",
                "path": file_path,
                "full_content": full_content
            }) + "\n"

            await asyncio.sleep(0.2)

        # Step 4: Installation instructions
        yield json.dumps({
            "type": "status",
            "status": "completed",
            "message": "Project generated successfully!"
        }) + "\n"

        yield json.dumps({
            "type": "commands",
            "commands": [
                "npm install",
                "npm run dev"
            ]
        }) + "\n"

        # Final summary
        yield json.dumps({
            "type": "complete",
            "message": "✅ Your project is ready!",
            "files_count": len(files_to_generate)
        }) + "\n"

    except Exception as e:
        logger.error(f"Streaming error: {e}")
        yield json.dumps({
            "type": "error",
            "message": str(e)
        }) + "\n"


@router.post("/stream")
async def stream_code_generation(
    request: StreamingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Bolt-style streaming endpoint
    Returns Server-Sent Events (SSE) stream
    """
    # Check token balance
    balance = await token_manager.get_or_create_balance(db, str(current_user.id))
    if balance.remaining_tokens < 1000:
        raise HTTPException(
            status_code=402,
            detail="Insufficient tokens. Please purchase more tokens."
        )

    async def event_stream():
        async for data in generate_code_stream(request.prompt, str(current_user.id), db):
            yield f"data: {data}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/chat")
async def chat_stream(
    request: StreamingRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Chat-style streaming for questions/explanations
    """
    async def chat_event_stream():
        try:
            yield f"data: {json.dumps({'type': 'start', 'message': 'Processing...'})}\n\n"

            full_response = ""
            async for chunk in claude_client.generate_stream(
                prompt=request.prompt,
                model="haiku",
                max_tokens=2048
            ):
                full_response += chunk
                yield f"data: {json.dumps({'type': 'content', 'content': chunk})}\n\n"

            yield f"data: {json.dumps({'type': 'complete', 'full_content': full_response})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        chat_event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
