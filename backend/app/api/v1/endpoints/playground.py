"""
Code Playground API Endpoints
=============================
HackerRank-style code execution playground using Judge0.

Endpoints:
- POST /playground/run - Execute code and return result
- POST /playground/run-with-tests - Run code against test cases
- GET /playground/languages - List supported languages
- GET /playground/templates/{language} - Get starter code template

Rate Limiting:
- /playground/run: 30 requests/minute per IP
- /playground/run-with-tests: 10 requests/minute per IP
"""

import time
import hashlib
from typing import Dict, List, Optional, Any
from collections import defaultdict

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.services.judge0_executor import (
    Judge0Executor,
    get_judge0_executor,
    JUDGE0_LANGUAGE_MAP,
    CODE_TEMPLATES,
    ExecutionResult,
    TestRunResult,
)

router = APIRouter(prefix="/playground", tags=["Code Playground"])

# =============================================
# Rate Limiting (Simple in-memory implementation)
# =============================================
# In production, use Redis-based rate limiting

_rate_limit_store: Dict[str, List[float]] = defaultdict(list)
RATE_LIMIT_RUN = 30  # requests per minute
RATE_LIMIT_RUN_TESTS = 10  # requests per minute
RATE_LIMIT_WINDOW = 60  # seconds


def _get_client_ip(request: Request) -> str:
    """Get client IP address from request"""
    # Check for forwarded headers (behind proxy/load balancer)
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_rate_limit(key: str, limit: int) -> bool:
    """Check if request is within rate limit"""
    now = time.time()
    window_start = now - RATE_LIMIT_WINDOW

    # Clean old entries
    _rate_limit_store[key] = [
        t for t in _rate_limit_store[key]
        if t > window_start
    ]

    # Check limit
    if len(_rate_limit_store[key]) >= limit:
        return False

    # Record this request
    _rate_limit_store[key].append(now)
    return True


# =============================================
# Request/Response Models
# =============================================

class PlaygroundRunRequest(BaseModel):
    """Request model for code execution"""
    source_code: str = Field(
        ...,
        description="Source code to execute",
        min_length=1,
        max_length=100000
    )
    language: str = Field(
        ...,
        description="Programming language (e.g., 'python', 'javascript', 'cpp')"
    )
    stdin: Optional[str] = Field(
        default="",
        description="Standard input for the program",
        max_length=10000
    )
    time_limit_sec: float = Field(
        default=2.0,
        description="Time limit in seconds (max 10)",
        ge=0.1,
        le=10.0
    )
    memory_limit_mb: int = Field(
        default=128,
        description="Memory limit in MB (max 512)",
        ge=16,
        le=512
    )


class TestCase(BaseModel):
    """Single test case definition"""
    input: str = Field(
        default="",
        description="Input to provide via stdin"
    )
    expected_output: str = Field(
        ...,
        description="Expected output from stdout"
    )


class PlaygroundRunWithTestsRequest(BaseModel):
    """Request model for running code against test cases"""
    source_code: str = Field(
        ...,
        description="Source code to execute",
        min_length=1,
        max_length=100000
    )
    language: str = Field(
        ...,
        description="Programming language"
    )
    test_cases: List[TestCase] = Field(
        ...,
        description="List of test cases to run",
        min_length=1,
        max_length=20
    )
    time_limit_sec: float = Field(
        default=2.0,
        description="Time limit per test case in seconds",
        ge=0.1,
        le=10.0
    )
    memory_limit_mb: int = Field(
        default=128,
        description="Memory limit in MB",
        ge=16,
        le=512
    )


class ExecutionResponse(BaseModel):
    """Response model for code execution"""
    status: str = Field(description="Execution status")
    status_id: int = Field(description="Status ID code")
    stdout: Optional[str] = Field(description="Standard output")
    stderr: Optional[str] = Field(description="Standard error")
    compile_output: Optional[str] = Field(description="Compilation output/errors")
    message: Optional[str] = Field(description="Status message")
    time_ms: float = Field(description="Execution time in milliseconds")
    memory_kb: int = Field(description="Memory used in kilobytes")
    exit_code: Optional[int] = Field(description="Process exit code")
    is_success: bool = Field(description="Whether execution succeeded")
    is_error: bool = Field(description="Whether there was an error")

    class Config:
        from_attributes = True


class TestCaseResponse(BaseModel):
    """Response model for single test case result"""
    test_case_id: int
    input: str
    expected_output: str
    actual_output: Optional[str]
    status: str
    passed: bool
    time_ms: float
    memory_kb: int
    error: Optional[str]


class TestRunResponse(BaseModel):
    """Response model for test run"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    status: str
    results: List[TestCaseResponse]
    total_time_ms: float
    max_memory_kb: int
    all_passed: bool
    pass_percentage: float


class LanguageInfo(BaseModel):
    """Language information"""
    id: int
    name: str
    aliases: List[str] = []
    has_template: bool = False


class TemplateResponse(BaseModel):
    """Code template response"""
    language: str
    template: str


# =============================================
# Endpoints
# =============================================

@router.post(
    "/run",
    response_model=ExecutionResponse,
    summary="Execute code",
    description="Execute source code in the specified language and return the result."
)
async def run_code(
    request: Request,
    body: PlaygroundRunRequest
) -> ExecutionResponse:
    """
    Execute code in the playground.

    - **source_code**: The source code to execute
    - **language**: Programming language (python, javascript, cpp, java, etc.)
    - **stdin**: Optional input to provide to the program
    - **time_limit_sec**: Maximum execution time (default 2 seconds, max 10)
    - **memory_limit_mb**: Maximum memory usage (default 128 MB, max 512)

    Returns execution result with stdout, stderr, time, and memory metrics.
    """
    # Rate limiting
    client_ip = _get_client_ip(request)
    rate_key = f"run:{client_ip}"
    if not _check_rate_limit(rate_key, RATE_LIMIT_RUN):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_RUN} requests per minute."
        )

    # Validate language
    language = body.language.lower().strip()
    if language not in JUDGE0_LANGUAGE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {body.language}. Supported languages: {list(JUDGE0_LANGUAGE_MAP.keys())}"
        )

    # Execute code
    executor = get_judge0_executor()
    result = await executor.execute(
        code=body.source_code,
        language=language,
        stdin=body.stdin or "",
        time_limit_sec=body.time_limit_sec,
        memory_limit_kb=body.memory_limit_mb * 1024
    )

    return ExecutionResponse(
        status=result.status,
        status_id=result.status_id,
        stdout=result.stdout,
        stderr=result.stderr,
        compile_output=result.compile_output,
        message=result.message,
        time_ms=result.time_ms,
        memory_kb=result.memory_kb,
        exit_code=result.exit_code,
        is_success=result.is_success,
        is_error=result.is_error,
    )


@router.post(
    "/run-with-tests",
    response_model=TestRunResponse,
    summary="Run code against test cases",
    description="Execute code against multiple test cases and return pass/fail results."
)
async def run_with_tests(
    request: Request,
    body: PlaygroundRunWithTestsRequest
) -> TestRunResponse:
    """
    Run code against multiple test cases.

    - **source_code**: The source code to execute
    - **language**: Programming language
    - **test_cases**: List of test cases with input and expected_output
    - **time_limit_sec**: Maximum execution time per test case
    - **memory_limit_mb**: Maximum memory usage

    Returns results for each test case including pass/fail status.
    """
    # Rate limiting (more restrictive)
    client_ip = _get_client_ip(request)
    rate_key = f"tests:{client_ip}"
    if not _check_rate_limit(rate_key, RATE_LIMIT_RUN_TESTS):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {RATE_LIMIT_RUN_TESTS} requests per minute."
        )

    # Validate language
    language = body.language.lower().strip()
    if language not in JUDGE0_LANGUAGE_MAP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported language: {body.language}"
        )

    # Convert test cases to dict format
    test_cases = [
        {"input": tc.input, "expected_output": tc.expected_output}
        for tc in body.test_cases
    ]

    # Execute tests
    executor = get_judge0_executor()
    result = await executor.execute_with_tests(
        code=body.source_code,
        language=language,
        test_cases=test_cases,
        time_limit_sec=body.time_limit_sec,
        memory_limit_kb=body.memory_limit_mb * 1024
    )

    return TestRunResponse(
        total_tests=result.total_tests,
        passed_tests=result.passed_tests,
        failed_tests=result.failed_tests,
        status=result.status,
        results=[
            TestCaseResponse(
                test_case_id=r.test_case_id,
                input=r.input,
                expected_output=r.expected_output,
                actual_output=r.actual_output,
                status=r.status,
                passed=r.passed,
                time_ms=r.time_ms,
                memory_kb=r.memory_kb,
                error=r.error,
            )
            for r in result.results
        ],
        total_time_ms=result.total_time_ms,
        max_memory_kb=result.max_memory_kb,
        all_passed=result.all_passed,
        pass_percentage=result.pass_percentage,
    )


@router.get(
    "/languages",
    response_model=List[LanguageInfo],
    summary="List supported languages",
    description="Get list of all supported programming languages."
)
async def get_languages() -> List[LanguageInfo]:
    """
    Get list of supported programming languages.

    Returns language ID, name, aliases, and whether a template is available.
    """
    # Build language info with aliases
    language_map: Dict[int, LanguageInfo] = {}

    for name, lang_id in JUDGE0_LANGUAGE_MAP.items():
        if lang_id not in language_map:
            language_map[lang_id] = LanguageInfo(
                id=lang_id,
                name=name,
                aliases=[],
                has_template=name in CODE_TEMPLATES
            )
        else:
            # Add as alias
            language_map[lang_id].aliases.append(name)

    # Sort by name
    return sorted(language_map.values(), key=lambda x: x.name)


@router.get(
    "/templates/{language}",
    response_model=TemplateResponse,
    summary="Get code template",
    description="Get starter code template for a language."
)
async def get_template(language: str) -> TemplateResponse:
    """
    Get starter code template for a programming language.

    Returns a basic "Hello World" template to get started.
    """
    language_lower = language.lower().strip()

    # Check if language is supported
    if language_lower not in JUDGE0_LANGUAGE_MAP:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unsupported language: {language}"
        )

    # Get template (or generate a generic one)
    template = CODE_TEMPLATES.get(
        language_lower,
        f"// {language}\n// Your code here\n"
    )

    return TemplateResponse(
        language=language_lower,
        template=template
    )


@router.get(
    "/health",
    summary="Check Judge0 health",
    description="Check if the Judge0 code execution service is available."
)
async def check_health() -> Dict[str, Any]:
    """
    Check Judge0 service health.

    Returns service status and information.
    """
    executor = get_judge0_executor()
    healthy = await executor.health_check()

    if healthy:
        about = await executor.get_about()
        return {
            "status": "healthy",
            "service": "judge0",
            "info": about
        }
    else:
        return {
            "status": "unhealthy",
            "service": "judge0",
            "message": "Judge0 service is not responding"
        }
