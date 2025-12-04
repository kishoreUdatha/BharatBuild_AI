"""
API endpoints for viewing Claude API logs and project LogBus logs

Includes:
1. Claude API logs (request/response tracking)
2. Project LogBus logs (browser, build, backend, network, docker errors)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Literal
from datetime import datetime
import json
import os

from app.core.logging_config import logger

router = APIRouter(prefix="/logs", tags=["logs"])


class LogEntry(BaseModel):
    """Log entry model"""
    timestamp: str
    type: Literal["request", "response"]
    model: str
    tokens: Optional[dict] = None
    content: dict


# In-memory log storage (replace with database or file storage in production)
_log_storage: List[LogEntry] = []


def add_log_entry(entry: LogEntry):
    """Add a log entry to storage"""
    _log_storage.append(entry)

    # Keep only last 1000 entries to prevent memory issues
    if len(_log_storage) > 1000:
        _log_storage.pop(0)


@router.get("/claude", response_model=List[LogEntry])
async def get_claude_logs(
    limit: int = 100,
    log_type: Optional[Literal["request", "response"]] = None
):
    """
    Get Claude API logs

    Args:
        limit: Maximum number of logs to return
        log_type: Filter by type (request/response)

    Returns:
        List of log entries
    """
    logs = _log_storage.copy()

    # Filter by type if specified
    if log_type:
        logs = [log for log in logs if log.type == log_type]

    # Return most recent logs first
    logs.reverse()

    return logs[:limit]


@router.delete("/claude")
async def clear_claude_logs():
    """Clear all Claude API logs"""
    _log_storage.clear()
    return {"message": "Logs cleared successfully", "count": 0}


@router.get("/claude/stats")
async def get_log_stats():
    """
    Get statistics about Claude API usage

    Returns:
        Statistics about requests, responses, and token usage
    """
    total_requests = len([log for log in _log_storage if log.type == "request"])
    total_responses = len([log for log in _log_storage if log.type == "response"])

    # Calculate total tokens
    total_input_tokens = 0
    total_output_tokens = 0
    total_cost = 0.0

    for log in _log_storage:
        if log.type == "response" and log.tokens:
            total_input_tokens += log.tokens.get("input", 0)
            total_output_tokens += log.tokens.get("output", 0)

            # Calculate cost (Sonnet 4.5 pricing)
            input_cost = (log.tokens.get("input", 0) * 0.003) / 1000
            output_cost = (log.tokens.get("output", 0) * 0.015) / 1000
            total_cost += input_cost + output_cost

    return {
        "total_requests": total_requests,
        "total_responses": total_responses,
        "total_logs": len(_log_storage),
        "tokens": {
            "input": total_input_tokens,
            "output": total_output_tokens,
            "total": total_input_tokens + total_output_tokens
        },
        "estimated_cost_usd": round(total_cost, 4)
    }


@router.get("/claude/export")
async def export_logs():
    """
    Export all logs as JSON

    Returns:
        JSON file with all logs
    """
    from fastapi.responses import JSONResponse

    return JSONResponse(
        content={
            "exported_at": datetime.utcnow().isoformat(),
            "total_logs": len(_log_storage),
            "logs": [log.dict() for log in _log_storage]
        },
        headers={
            "Content-Disposition": f"attachment; filename=claude-logs-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}.json"
        }
    )


# ============================================================================
#                    PROJECT LOGBUS ENDPOINTS
# ============================================================================
# These endpoints collect logs from all 5 collectors:
# 1. Browser Console (JS errors, console.error)
# 2. Build Logs (Vite/Webpack/tsc)
# 3. Backend Runtime (Node/Python server logs)
# 4. Network Errors (fetch/XHR failures)
# 5. Docker Logs (container output)


class BrowserLogEntry(BaseModel):
    """Browser console/runtime error from frontend"""
    message: str
    source: str = "browser"  # browser, network
    level: str = "error"  # error, warning, info
    file: Optional[str] = None
    line: Optional[int] = None
    column: Optional[int] = None
    stack: Optional[str] = None
    # Network-specific
    url: Optional[str] = None
    status: Optional[int] = None
    method: Optional[str] = None


class LogBatchRequest(BaseModel):
    """Batch of logs from frontend"""
    project_id: str
    logs: List[BrowserLogEntry]


class LogBusResponse(BaseModel):
    """Response for LogBus operations"""
    success: bool
    message: str
    received: Optional[int] = None


@router.post("/project/browser", response_model=LogBusResponse)
async def submit_browser_logs(request: LogBatchRequest):
    """
    Receive browser logs from frontend.

    The frontend collects:
    - console.error() calls
    - Runtime JS errors (window.onerror)
    - Unhandled promise rejections
    - Network errors (fetch/XHR failures)

    These are batched and sent here for LogBus aggregation.
    """
    try:
        from app.services.log_bus import get_log_bus
        log_bus = get_log_bus(request.project_id)

        for log in request.logs:
            if log.source == "browser":
                log_bus.add_browser_error(
                    message=log.message,
                    file=log.file,
                    line=log.line,
                    column=log.column,
                    stack=log.stack
                )
            elif log.source == "network":
                log_bus.add_network_error(
                    message=log.message,
                    url=log.url or "",
                    status=log.status,
                    method=log.method or "GET"
                )
            else:
                log_bus.add_log(
                    source=log.source,
                    level=log.level,
                    message=log.message,
                    file=log.file,
                    line=log.line,
                    stack=log.stack
                )

        logger.debug(f"[LogBus] Received {len(request.logs)} logs for project {request.project_id}")

        return LogBusResponse(
            success=True,
            message=f"Received {len(request.logs)} logs",
            received=len(request.logs)
        )

    except Exception as e:
        logger.error(f"[LogBus] Error processing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}")
async def get_project_logs(project_id: str):
    """
    Get all collected logs for a project.

    Returns structured logs from all 5 collectors:
    - browser_errors
    - build_errors
    - backend_errors
    - network_errors
    - docker_errors
    - stack_traces
    - error_files
    """
    try:
        from app.services.log_bus import get_log_bus
        log_bus = get_log_bus(project_id)
        payload = log_bus.get_fixer_payload()

        return {
            "success": True,
            "project_id": project_id,
            "logs": payload
        }

    except Exception as e:
        logger.error(f"[LogBus] Error getting logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/project/{project_id}")
async def clear_project_logs(project_id: str):
    """Clear all logs for a project"""
    try:
        from app.services.log_bus import get_log_bus
        log_bus = get_log_bus(project_id)
        log_bus.clear()

        return {
            "success": True,
            "message": f"Cleared logs for project {project_id}"
        }

    except Exception as e:
        logger.error(f"[LogBus] Error clearing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/errors")
async def get_project_errors(project_id: str):
    """Get only error logs for a project (all sources combined)"""
    try:
        from app.services.log_bus import get_log_bus
        log_bus = get_log_bus(project_id)
        errors = log_bus.get_errors()

        return {
            "success": True,
            "project_id": project_id,
            "error_count": len(errors),
            "errors": errors
        }

    except Exception as e:
        logger.error(f"[LogBus] Error getting errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}/error-files")
async def get_error_files(project_id: str):
    """
    Get list of files mentioned in errors.

    Useful for Context Engine to determine which files to include.
    """
    try:
        from app.services.log_bus import get_log_bus
        log_bus = get_log_bus(project_id)
        files = log_bus.get_error_files()

        return {
            "success": True,
            "project_id": project_id,
            "files": files
        }

    except Exception as e:
        logger.error(f"[LogBus] Error getting error files: {e}")
        raise HTTPException(status_code=500, detail=str(e))
