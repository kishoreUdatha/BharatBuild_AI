"""
Judge0 Code Execution Service
=============================
Self-hosted HackerRank-style code execution engine supporting 60+ languages.

Features:
- Execute code with custom stdin input
- Run code against multiple test cases
- Support for 60+ programming languages
- Real execution metrics (time, memory)
- Compile error and runtime error detection

Usage:
    from app.services.judge0_executor import Judge0Executor

    executor = Judge0Executor()
    result = await executor.execute(
        code='print("Hello")',
        language='python',
        stdin='',
        time_limit_sec=2.0,
        memory_limit_kb=128000
    )
"""

import httpx
import asyncio
import base64
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

from app.core.config import settings

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Judge0 execution status codes"""
    IN_QUEUE = "in_queue"
    PROCESSING = "processing"
    ACCEPTED = "accepted"
    WRONG_ANSWER = "wrong_answer"
    TIME_LIMIT_EXCEEDED = "time_limit_exceeded"
    COMPILATION_ERROR = "compilation_error"
    RUNTIME_ERROR_SIGSEGV = "runtime_error_sigsegv"
    RUNTIME_ERROR_SIGXFSZ = "runtime_error_sigxfsz"
    RUNTIME_ERROR_SIGFPE = "runtime_error_sigfpe"
    RUNTIME_ERROR_SIGABRT = "runtime_error_sigabrt"
    RUNTIME_ERROR_NZEC = "runtime_error_nzec"
    RUNTIME_ERROR_OTHER = "runtime_error_other"
    INTERNAL_ERROR = "internal_error"
    EXEC_FORMAT_ERROR = "exec_format_error"


# Judge0 status ID to ExecutionStatus mapping
STATUS_ID_MAP = {
    1: ExecutionStatus.IN_QUEUE,
    2: ExecutionStatus.PROCESSING,
    3: ExecutionStatus.ACCEPTED,
    4: ExecutionStatus.WRONG_ANSWER,
    5: ExecutionStatus.TIME_LIMIT_EXCEEDED,
    6: ExecutionStatus.COMPILATION_ERROR,
    7: ExecutionStatus.RUNTIME_ERROR_SIGSEGV,
    8: ExecutionStatus.RUNTIME_ERROR_SIGXFSZ,
    9: ExecutionStatus.RUNTIME_ERROR_SIGFPE,
    10: ExecutionStatus.RUNTIME_ERROR_SIGABRT,
    11: ExecutionStatus.RUNTIME_ERROR_NZEC,
    12: ExecutionStatus.RUNTIME_ERROR_OTHER,
    13: ExecutionStatus.INTERNAL_ERROR,
    14: ExecutionStatus.EXEC_FORMAT_ERROR,
}


# Language name to Judge0 language ID mapping
# Full list at: https://ce.judge0.com/languages
JUDGE0_LANGUAGE_MAP = {
    # Scripting Languages
    "python": 71,           # Python (3.8.1)
    "python3": 71,          # Python (3.8.1)
    "python2": 70,          # Python (2.7.17)
    "javascript": 63,       # JavaScript (Node.js 12.14.0)
    "nodejs": 63,           # Node.js alias
    "node": 63,             # Node.js alias
    "typescript": 74,       # TypeScript (3.7.4)
    "ts": 74,               # TypeScript alias
    "ruby": 72,             # Ruby (2.7.0)
    "php": 68,              # PHP (7.4.1)
    "perl": 85,             # Perl (5.28.1)
    "lua": 64,              # Lua (5.3.5)
    "r": 80,                # R (4.0.0)

    # Compiled Languages
    "c": 50,                # C (GCC 9.2.0)
    "c99": 50,              # C99 alias
    "cpp": 54,              # C++ (GCC 9.2.0)
    "c++": 54,              # C++ alias
    "cpp14": 53,            # C++ (GCC 8.3.0) - C++14
    "cpp17": 54,            # C++ (GCC 9.2.0) - C++17
    "java": 62,             # Java (OpenJDK 13.0.1)
    "csharp": 51,           # C# (Mono 6.6.0.161)
    "c#": 51,               # C# alias
    "go": 60,               # Go (1.13.5)
    "golang": 60,           # Go alias
    "rust": 73,             # Rust (1.40.0)
    "swift": 83,            # Swift (5.2.3)
    "kotlin": 78,           # Kotlin (1.3.70)
    "scala": 81,            # Scala (2.13.2)
    "dart": 90,             # Dart (2.19.2)
    "objective-c": 79,      # Objective-C (Clang 7.0.1)
    "objc": 79,             # Objective-C alias

    # Functional Languages
    "haskell": 61,          # Haskell (GHC 8.8.1)
    "elixir": 57,           # Elixir (1.9.4)
    "erlang": 58,           # Erlang (OTP 22.2)
    "clojure": 86,          # Clojure (1.10.1)
    "fsharp": 87,           # F# (.NET Core SDK 3.1.202)
    "f#": 87,               # F# alias
    "ocaml": 65,            # OCaml (4.09.0)
    "lisp": 55,             # Common Lisp (SBCL 2.0.0)
    "commonlisp": 55,       # Common Lisp alias
    "racket": 88,           # Racket (7.7)
    "scheme": 88,           # Scheme (via Racket)

    # Systems Languages
    "assembly": 45,         # Assembly (NASM 2.14.02)
    "asm": 45,              # Assembly alias
    "nasm": 45,             # NASM alias
    "fortran": 59,          # Fortran (GFortran 9.2.0)
    "pascal": 67,           # Pascal (FPC 3.0.4)
    "cobol": 77,            # COBOL (GnuCOBOL 2.2)
    "d": 56,                # D (DMD 2.089.1)

    # Shell & Scripting
    "bash": 46,             # Bash (5.0.0)
    "shell": 46,            # Shell alias
    "sh": 46,               # Shell alias

    # Database
    "sql": 82,              # SQL (SQLite 3.27.2)
    "sqlite": 82,           # SQLite alias
    "plsql": 82,            # PL/SQL (via SQLite)

    # Esoteric & Educational
    "brainfuck": 44,        # Brainfuck
    "bf": 44,               # Brainfuck alias
    "prolog": 69,           # Prolog (GNU Prolog 1.4.5)
    "groovy": 88,           # Groovy (3.0.3) - shares ID with Racket in some versions

    # Scientific Computing
    "octave": 66,           # Octave (5.1.0)
    "matlab": 66,           # MATLAB (via Octave)

    # Text Processing
    "text": 43,             # Plain Text
    "plaintext": 43,        # Plain Text alias
}


# Code templates for each language
CODE_TEMPLATES = {
    "python": '''# Python 3
def main():
    # Your code here
    print("Hello, World!")

if __name__ == "__main__":
    main()
''',
    "javascript": '''// JavaScript (Node.js)
function main() {
    // Your code here
    console.log("Hello, World!");
}

main();
''',
    "typescript": '''// TypeScript
function main(): void {
    // Your code here
    console.log("Hello, World!");
}

main();
''',
    "c": '''// C
#include <stdio.h>

int main() {
    // Your code here
    printf("Hello, World!\\n");
    return 0;
}
''',
    "cpp": '''// C++
#include <iostream>
using namespace std;

int main() {
    // Your code here
    cout << "Hello, World!" << endl;
    return 0;
}
''',
    "java": '''// Java
public class Main {
    public static void main(String[] args) {
        // Your code here
        System.out.println("Hello, World!");
    }
}
''',
    "csharp": '''// C#
using System;

class Program {
    static void Main(string[] args) {
        // Your code here
        Console.WriteLine("Hello, World!");
    }
}
''',
    "go": '''// Go
package main

import "fmt"

func main() {
    // Your code here
    fmt.Println("Hello, World!")
}
''',
    "rust": '''// Rust
fn main() {
    // Your code here
    println!("Hello, World!");
}
''',
    "ruby": '''# Ruby
def main
  # Your code here
  puts "Hello, World!"
end

main
''',
    "php": '''<?php
// PHP
function main() {
    // Your code here
    echo "Hello, World!\\n";
}

main();
?>
''',
    "swift": '''// Swift
import Foundation

func main() {
    // Your code here
    print("Hello, World!")
}

main()
''',
    "kotlin": '''// Kotlin
fun main() {
    // Your code here
    println("Hello, World!")
}
''',
    "scala": '''// Scala
object Main extends App {
    // Your code here
    println("Hello, World!")
}
''',
    "haskell": '''-- Haskell
main :: IO ()
main = do
    -- Your code here
    putStrLn "Hello, World!"
''',
    "bash": '''#!/bin/bash
# Bash
# Your code here
echo "Hello, World!"
''',
    "sql": '''-- SQL (SQLite)
-- Your queries here
SELECT 'Hello, World!' AS message;
''',
    "r": '''# R
# Your code here
print("Hello, World!")
''',
    "dart": '''// Dart
void main() {
    // Your code here
    print("Hello, World!");
}
''',
    "perl": '''#!/usr/bin/perl
# Perl
use strict;
use warnings;

# Your code here
print "Hello, World!\\n";
''',
    "lua": '''-- Lua
-- Your code here
print("Hello, World!")
''',
}


@dataclass
class ExecutionResult:
    """Result of code execution"""
    status: str
    status_id: int
    stdout: Optional[str] = None
    stderr: Optional[str] = None
    compile_output: Optional[str] = None
    message: Optional[str] = None
    time_ms: float = 0.0
    memory_kb: int = 0
    exit_code: Optional[int] = None

    @property
    def is_success(self) -> bool:
        return self.status == ExecutionStatus.ACCEPTED

    @property
    def is_error(self) -> bool:
        return self.status in [
            ExecutionStatus.COMPILATION_ERROR,
            ExecutionStatus.RUNTIME_ERROR_SIGSEGV,
            ExecutionStatus.RUNTIME_ERROR_SIGXFSZ,
            ExecutionStatus.RUNTIME_ERROR_SIGFPE,
            ExecutionStatus.RUNTIME_ERROR_SIGABRT,
            ExecutionStatus.RUNTIME_ERROR_NZEC,
            ExecutionStatus.RUNTIME_ERROR_OTHER,
            ExecutionStatus.INTERNAL_ERROR,
            ExecutionStatus.EXEC_FORMAT_ERROR,
        ]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "status_id": self.status_id,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "compile_output": self.compile_output,
            "message": self.message,
            "time_ms": self.time_ms,
            "memory_kb": self.memory_kb,
            "exit_code": self.exit_code,
            "is_success": self.is_success,
            "is_error": self.is_error,
        }


@dataclass
class TestCaseResult:
    """Result of running code against a single test case"""
    test_case_id: int
    input: str
    expected_output: str
    actual_output: Optional[str]
    status: str
    passed: bool
    time_ms: float
    memory_kb: int
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "input": self.input,
            "expected_output": self.expected_output,
            "actual_output": self.actual_output,
            "status": self.status,
            "passed": self.passed,
            "time_ms": self.time_ms,
            "memory_kb": self.memory_kb,
            "error": self.error,
        }


@dataclass
class TestRunResult:
    """Result of running code against multiple test cases"""
    total_tests: int
    passed_tests: int
    failed_tests: int
    status: str
    results: List[TestCaseResult]
    total_time_ms: float
    max_memory_kb: int

    @property
    def all_passed(self) -> bool:
        return self.passed_tests == self.total_tests

    @property
    def pass_percentage(self) -> float:
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "status": self.status,
            "results": [r.to_dict() for r in self.results],
            "total_time_ms": self.total_time_ms,
            "max_memory_kb": self.max_memory_kb,
            "all_passed": self.all_passed,
            "pass_percentage": self.pass_percentage,
        }


class Judge0Executor:
    """
    Judge0 Code Execution Service

    Provides methods to execute code in 60+ programming languages
    using the self-hosted Judge0 instance.
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0
    ):
        self.api_url = api_url or getattr(settings, 'JUDGE0_API_URL', 'http://localhost:2358')
        self.api_key = api_key or getattr(settings, 'JUDGE0_API_KEY', '')
        self.timeout = timeout

        # Remove trailing slash
        self.api_url = self.api_url.rstrip('/')

    def _get_headers(self) -> Dict[str, str]:
        """Get headers for Judge0 API requests"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.api_key:
            headers["X-Auth-Token"] = self.api_key
        return headers

    def _encode_base64(self, text: str) -> str:
        """Encode text to base64 for Judge0 API"""
        if not text:
            return ""
        return base64.b64encode(text.encode('utf-8')).decode('utf-8')

    def _decode_base64(self, encoded: Optional[str]) -> Optional[str]:
        """Decode base64 from Judge0 API response"""
        if not encoded:
            return None
        try:
            return base64.b64decode(encoded).decode('utf-8')
        except Exception:
            return encoded

    def get_language_id(self, language: str) -> Optional[int]:
        """Get Judge0 language ID from language name"""
        language_lower = language.lower().strip()
        return JUDGE0_LANGUAGE_MAP.get(language_lower)

    def get_template(self, language: str) -> str:
        """Get code template for a language"""
        language_lower = language.lower().strip()
        return CODE_TEMPLATES.get(language_lower, f"// {language}\n// Your code here\n")

    async def get_languages(self) -> List[Dict[str, Any]]:
        """Get list of supported languages from Judge0"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.api_url}/languages",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get languages: {e}")
                # Return our known languages as fallback
                return [
                    {"id": lang_id, "name": lang_name}
                    for lang_name, lang_id in JUDGE0_LANGUAGE_MAP.items()
                ]

    async def get_about(self) -> Dict[str, Any]:
        """Get Judge0 server information"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(
                    f"{self.api_url}/about",
                    headers=self._get_headers()
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Failed to get about: {e}")
                return {"error": str(e)}

    async def execute(
        self,
        code: str,
        language: str,
        stdin: str = "",
        time_limit_sec: float = 2.0,
        memory_limit_kb: int = 128000,
        wait: bool = True
    ) -> ExecutionResult:
        """
        Execute code in the specified language.

        Args:
            code: Source code to execute
            language: Programming language name
            stdin: Standard input for the program
            time_limit_sec: Time limit in seconds
            memory_limit_kb: Memory limit in kilobytes
            wait: Whether to wait for result (uses ?wait=true parameter)

        Returns:
            ExecutionResult with stdout, stderr, and execution metrics
        """
        language_id = self.get_language_id(language)
        if not language_id:
            return ExecutionResult(
                status="unsupported_language",
                status_id=-1,
                message=f"Unsupported language: {language}. Supported: {list(JUDGE0_LANGUAGE_MAP.keys())}"
            )

        # Prepare submission data
        submission_data = {
            "source_code": self._encode_base64(code),
            "language_id": language_id,
            "stdin": self._encode_base64(stdin) if stdin else "",
            "cpu_time_limit": time_limit_sec,
            "cpu_extra_time": time_limit_sec * 0.5,  # Extra 50% for overhead
            "wall_time_limit": time_limit_sec * 3,    # 3x for wall time
            "memory_limit": memory_limit_kb,
            "stack_limit": min(memory_limit_kb, 64000),  # Stack limit
            "max_file_size": 1024,  # 1MB output limit
            "enable_per_process_and_thread_time_limit": True,
            "enable_per_process_and_thread_memory_limit": True,
            "number_of_runs": 1,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                # Create submission
                url = f"{self.api_url}/submissions"
                if wait:
                    url += "?base64_encoded=true&wait=true&fields=*"
                else:
                    url += "?base64_encoded=true&fields=token"

                response = await client.post(
                    url,
                    json=submission_data,
                    headers=self._get_headers()
                )
                response.raise_for_status()
                result = response.json()

                # If not waiting, poll for result
                if not wait:
                    token = result.get("token")
                    if not token:
                        return ExecutionResult(
                            status="internal_error",
                            status_id=13,
                            message="No token returned from Judge0"
                        )
                    result = await self._poll_submission(client, token)

                return self._parse_result(result)

            except httpx.HTTPStatusError as e:
                logger.error(f"Judge0 HTTP error: {e.response.status_code} - {e.response.text}")
                return ExecutionResult(
                    status="internal_error",
                    status_id=13,
                    message=f"Judge0 error: {e.response.status_code}"
                )
            except Exception as e:
                logger.error(f"Judge0 execution error: {e}")
                return ExecutionResult(
                    status="internal_error",
                    status_id=13,
                    message=f"Execution error: {str(e)}"
                )

    async def _poll_submission(
        self,
        client: httpx.AsyncClient,
        token: str,
        max_attempts: int = 30,
        poll_interval: float = 0.5
    ) -> Dict[str, Any]:
        """Poll for submission result"""
        for _ in range(max_attempts):
            response = await client.get(
                f"{self.api_url}/submissions/{token}?base64_encoded=true&fields=*",
                headers=self._get_headers()
            )
            response.raise_for_status()
            result = response.json()

            status_id = result.get("status", {}).get("id", 0)
            # Status 1 = In Queue, 2 = Processing
            if status_id not in [1, 2]:
                return result

            await asyncio.sleep(poll_interval)

        return {"status": {"id": 13}, "message": "Polling timeout"}

    def _parse_result(self, result: Dict[str, Any]) -> ExecutionResult:
        """Parse Judge0 API response into ExecutionResult"""
        status_info = result.get("status", {})
        status_id = status_info.get("id", 0)
        status_desc = status_info.get("description", "Unknown")

        # Map status ID to our enum
        status = STATUS_ID_MAP.get(status_id, ExecutionStatus.INTERNAL_ERROR)

        # Parse time (comes as string like "0.123")
        time_str = result.get("time", "0")
        try:
            time_ms = float(time_str) * 1000 if time_str else 0.0
        except (ValueError, TypeError):
            time_ms = 0.0

        # Parse memory (comes in KB)
        memory_kb = result.get("memory", 0) or 0

        return ExecutionResult(
            status=status,
            status_id=status_id,
            stdout=self._decode_base64(result.get("stdout")),
            stderr=self._decode_base64(result.get("stderr")),
            compile_output=self._decode_base64(result.get("compile_output")),
            message=result.get("message") or status_desc,
            time_ms=time_ms,
            memory_kb=memory_kb,
            exit_code=result.get("exit_code"),
        )

    async def execute_with_tests(
        self,
        code: str,
        language: str,
        test_cases: List[Dict[str, str]],
        time_limit_sec: float = 2.0,
        memory_limit_kb: int = 128000
    ) -> TestRunResult:
        """
        Execute code against multiple test cases.

        Args:
            code: Source code to execute
            language: Programming language name
            test_cases: List of {"input": str, "expected_output": str}
            time_limit_sec: Time limit per test case in seconds
            memory_limit_kb: Memory limit in kilobytes

        Returns:
            TestRunResult with results for each test case
        """
        results: List[TestCaseResult] = []
        total_time_ms = 0.0
        max_memory_kb = 0

        for i, test_case in enumerate(test_cases):
            input_data = test_case.get("input", "")
            expected_output = test_case.get("expected_output", "").strip()

            # Execute code with this test case's input
            exec_result = await self.execute(
                code=code,
                language=language,
                stdin=input_data,
                time_limit_sec=time_limit_sec,
                memory_limit_kb=memory_limit_kb
            )

            actual_output = (exec_result.stdout or "").strip()

            # Determine if test passed
            passed = False
            if exec_result.is_success:
                # Compare outputs (strip whitespace for comparison)
                passed = actual_output == expected_output

            # Determine status for this test case
            if exec_result.is_error:
                test_status = exec_result.status
            elif passed:
                test_status = "passed"
            else:
                test_status = "wrong_answer"

            # Build error message if applicable
            error = None
            if exec_result.compile_output:
                error = exec_result.compile_output
            elif exec_result.stderr:
                error = exec_result.stderr
            elif exec_result.message and exec_result.is_error:
                error = exec_result.message

            results.append(TestCaseResult(
                test_case_id=i + 1,
                input=input_data,
                expected_output=expected_output,
                actual_output=actual_output if exec_result.is_success else None,
                status=test_status,
                passed=passed,
                time_ms=exec_result.time_ms,
                memory_kb=exec_result.memory_kb,
                error=error,
            ))

            total_time_ms += exec_result.time_ms
            max_memory_kb = max(max_memory_kb, exec_result.memory_kb)

        # Calculate summary
        passed_tests = sum(1 for r in results if r.passed)
        failed_tests = len(results) - passed_tests

        # Determine overall status
        if passed_tests == len(results):
            overall_status = "all_passed"
        elif passed_tests > 0:
            overall_status = "partial"
        else:
            overall_status = "all_failed"

        return TestRunResult(
            total_tests=len(results),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            status=overall_status,
            results=results,
            total_time_ms=total_time_ms,
            max_memory_kb=max_memory_kb,
        )

    async def batch_execute(
        self,
        submissions: List[Dict[str, Any]],
        wait: bool = True
    ) -> List[ExecutionResult]:
        """
        Execute multiple submissions in batch.

        Args:
            submissions: List of {"code": str, "language": str, "stdin": str, ...}
            wait: Whether to wait for all results

        Returns:
            List of ExecutionResult for each submission
        """
        # Convert to Judge0 format
        judge0_submissions = []
        for sub in submissions:
            language_id = self.get_language_id(sub.get("language", "python"))
            if not language_id:
                continue

            judge0_submissions.append({
                "source_code": self._encode_base64(sub.get("code", "")),
                "language_id": language_id,
                "stdin": self._encode_base64(sub.get("stdin", "")),
                "cpu_time_limit": sub.get("time_limit_sec", 2.0),
                "memory_limit": sub.get("memory_limit_kb", 128000),
            })

        if not judge0_submissions:
            return []

        async with httpx.AsyncClient(timeout=self.timeout * 2) as client:
            try:
                # Create batch submission
                url = f"{self.api_url}/submissions/batch"
                if wait:
                    url += "?base64_encoded=true&wait=true&fields=*"

                response = await client.post(
                    url,
                    json={"submissions": judge0_submissions},
                    headers=self._get_headers()
                )
                response.raise_for_status()
                results = response.json()

                # Parse results
                if isinstance(results, list):
                    return [self._parse_result(r) for r in results]
                elif isinstance(results, dict) and "submissions" in results:
                    return [self._parse_result(r) for r in results["submissions"]]
                else:
                    return []

            except Exception as e:
                logger.error(f"Batch execution error: {e}")
                return [ExecutionResult(
                    status="internal_error",
                    status_id=13,
                    message=str(e)
                )]

    async def health_check(self) -> bool:
        """Check if Judge0 service is healthy"""
        try:
            about = await self.get_about()
            return "error" not in about
        except Exception:
            return False


# Singleton instance for convenience
_executor: Optional[Judge0Executor] = None


def get_judge0_executor() -> Judge0Executor:
    """Get or create Judge0 executor singleton"""
    global _executor
    if _executor is None:
        _executor = Judge0Executor()
    return _executor
