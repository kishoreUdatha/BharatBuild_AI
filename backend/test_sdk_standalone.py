"""
Standalone SDK Fixer Test - No app dependencies.

Run: python test_sdk_standalone.py
"""

import asyncio
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable, List, Dict, Any

# Check for API key - try multiple sources
api_key = os.environ.get("ANTHROPIC_API_KEY")
if not api_key:
    # Try loading from .env file
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        for line in env_path.read_text().split("\n"):
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                os.environ["ANTHROPIC_API_KEY"] = api_key
                break

if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not found")
    print("Set it with: set ANTHROPIC_API_KEY=your-key")
    exit(1)

print(f"[OK] API key found: {api_key[:10]}...")

from anthropic import AsyncAnthropic


@dataclass
class SDKFixResult:
    success: bool
    files_modified: List[str]
    files_created: List[str]
    message: str
    tool_calls: int
    tokens_used: int


class SDKFixer:
    """Claude SDK Agent-based fixer - standalone version."""

    SYSTEM_PROMPT = """You are an expert code fixer. Fix build/compilation errors.

RULES:
1. First, use list_files to see project structure
2. Use read_file to read files that have errors or need fixing
3. Use write_file to write the fixed content

JAVA RULES (CRITICAL):
- NO LOMBOK: Remove @Data, @Getter, @Setter, @Builder, @NoArgsConstructor, @AllArgsConstructor
- Remove: import lombok.*;
- Add explicit getter for EVERY field: public Type getField() { return field; }
- Add explicit setter for EVERY field: public void setField(Type val) { this.field = val; }
- Add no-arg constructor and all-args constructor
- Use constructor injection for services (not @RequiredArgsConstructor)

FIX ROOT CAUSE:
- If error says "cannot find symbol: method getX() in class Order"
  → Read Order.java and add the missing getter
- If error says "location: class Product"
  → Fix Product.java, not the file that uses it
"""

    TOOLS = [
        {
            "name": "list_files",
            "description": "List files matching a pattern",
            "input_schema": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern like '**/*.java'"}
                },
                "required": ["pattern"]
            }
        },
        {
            "name": "read_file",
            "description": "Read a file's content",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"}
                },
                "required": ["path"]
            }
        },
        {
            "name": "write_file",
            "description": "Write content to a file",
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path"},
                    "content": {"type": "string", "description": "File content"}
                },
                "required": ["path", "content"]
            }
        }
    ]

    def __init__(self, sandbox_reader, sandbox_writer, sandbox_lister):
        self._client = AsyncAnthropic()
        self._sandbox_reader = sandbox_reader
        self._sandbox_writer = sandbox_writer
        self._sandbox_lister = sandbox_lister
        self._files_modified = []
        self._files_created = []

    async def fix(self, project_path: Path, build_errors: str, max_iterations: int = 10) -> SDKFixResult:
        self._project_path = project_path
        self._files_modified = []
        self._files_created = []
        tool_calls = 0
        total_tokens = 0

        messages = [{
            "role": "user",
            "content": f"""Fix these build errors:

```
{build_errors[:8000]}
```

Steps:
1. List Java files to understand structure
2. Read files that have errors (check "location:" in errors)
3. Fix each file - remove Lombok, add explicit getters/setters
4. Write the fixed files
"""
        }]

        try:
            for iteration in range(max_iterations):
                print(f"  [Iteration {iteration + 1}] Calling Claude...")

                response = await self._client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=16384,
                    system=self.SYSTEM_PROMPT,
                    tools=self.TOOLS,
                    messages=messages
                )

                total_tokens += response.usage.input_tokens + response.usage.output_tokens

                if response.stop_reason == "end_turn":
                    print(f"  [Iteration {iteration + 1}] Claude finished")
                    break

                if response.stop_reason == "tool_use":
                    messages.append({"role": "assistant", "content": response.content})

                    tool_results = []
                    for block in response.content:
                        if block.type == "tool_use":
                            tool_calls += 1
                            print(f"  [Tool] {block.name}({block.input})")
                            result = await self._execute_tool(block.name, block.input, block.id)
                            tool_results.append(result)

                    messages.append({"role": "user", "content": tool_results})

            return SDKFixResult(
                success=len(self._files_modified) > 0,
                files_modified=self._files_modified,
                files_created=self._files_created,
                message=f"Fixed {len(self._files_modified)} files",
                tool_calls=tool_calls,
                tokens_used=total_tokens
            )

        except Exception as e:
            return SDKFixResult(
                success=False, files_modified=[], files_created=[],
                message=str(e), tool_calls=tool_calls, tokens_used=total_tokens
            )

    async def _execute_tool(self, name: str, input: dict, tool_id: str) -> dict:
        try:
            if name == "list_files":
                result = self._sandbox_lister("", input.get("pattern", ""))
                result = f"Found {len(result)} files:\n" + "\n".join(result[:50])
            elif name == "read_file":
                result = self._sandbox_reader(input.get("path", ""))
                if not result:
                    result = f"File not found: {input.get('path')}"
            elif name == "write_file":
                path = input.get("path", "")
                content = input.get("content", "")
                self._sandbox_writer(path, content)
                self._files_modified.append(path)
                result = f"Written: {path} ({len(content)} chars)"
            else:
                result = f"Unknown tool: {name}"

            return {"type": "tool_result", "tool_use_id": tool_id, "content": str(result)[:5000]}
        except Exception as e:
            return {"type": "tool_result", "tool_use_id": tool_id, "content": f"Error: {e}", "is_error": True}


# Mock files with Lombok
JAVA_FILES = {
    "backend/src/main/java/com/example/model/Order.java": """package com.example.model;

import lombok.Data;
import lombok.Builder;
import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
@Data
@Builder
public class Order {
    @Id
    private Long id;
    private String customerName;
    private BigDecimal totalAmount;
    private String status;
}
""",
    "backend/src/main/java/com/example/model/Product.java": """package com.example.model;

import lombok.Data;
import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
@Data
public class Product {
    @Id
    private Long id;
    private String name;
    private BigDecimal price;
}
"""
}

BUILD_ERRORS = """[ERROR] /app/src/main/java/com/example/service/OrderService.java:[25,52] cannot find symbol
[ERROR]   symbol:   method getId()
[ERROR]   location: class com.example.model.Order
[ERROR] /app/src/main/java/com/example/service/OrderService.java:[26,50] cannot find symbol
[ERROR]   symbol:   method getStatus()
[ERROR]   location: class com.example.model.Order
[ERROR] /app/src/main/java/com/example/service/OrderService.java:[33,48] cannot find symbol
[ERROR]   symbol:   method getName()
[ERROR]   location: class com.example.model.Product
[ERROR] /app/src/main/java/com/example/service/OrderService.java:[34,49] cannot find symbol
[ERROR]   symbol:   method getPrice()
[ERROR]   location: class com.example.model.Product
[INFO] BUILD FAILURE - 4 errors
"""


class MockSandbox:
    def __init__(self, files: dict):
        self.files = dict(files)

    def read(self, path: str) -> str:
        path = path.replace("\\", "/")
        for key in self.files:
            if path.endswith(key.split("/")[-1]) or key in path or path in key:
                return self.files[key]
        return None

    def write(self, path: str, content: str) -> bool:
        path = path.replace("\\", "/")
        for key in list(self.files.keys()):
            if path.endswith(key.split("/")[-1]):
                self.files[key] = content
                print(f"    → Updated: {key}")
                return True
        self.files[path] = content
        print(f"    → Created: {path}")
        return True

    def list(self, base: str, pattern: str) -> list:
        return list(self.files.keys())


async def main():
    print("=" * 60)
    print("SDK FIXER TEST - Java Build Errors")
    print("=" * 60)

    sandbox = MockSandbox(JAVA_FILES)

    print("\n[Initial Files]")
    for path, content in sandbox.files.items():
        has_lombok = "@Data" in content
        status = "[LOMBOK]" if has_lombok else "[OK]"
        print(f"  {status} {path.split('/')[-1]}")

    print("\n[Running SDK Fixer...]")
    print("-" * 40)

    fixer = SDKFixer(
        sandbox_reader=sandbox.read,
        sandbox_writer=sandbox.write,
        sandbox_lister=sandbox.list
    )

    result = await fixer.fix(Path("."), BUILD_ERRORS, max_iterations=10)

    print("-" * 40)
    print(f"\n[Results]")
    print(f"  Success: {result.success}")
    print(f"  Files Modified: {result.files_modified}")
    print(f"  Tool Calls: {result.tool_calls}")
    print(f"  Tokens: {result.tokens_used}")

    print("\n[Final Files]")
    for path, content in sandbox.files.items():
        has_lombok = "@Data" in content or "import lombok" in content
        has_getters = "getId()" in content
        if has_lombok:
            status = "[LOMBOK] Still has Lombok"
        elif has_getters:
            status = "[FIXED] Has getters"
        else:
            status = "[???] Unknown"
        print(f"  {status}: {path.split('/')[-1]}")

    if result.success:
        print("\n[Fixed Order.java]")
        print("-" * 40)
        for path, content in sandbox.files.items():
            if "Order.java" in path:
                for i, line in enumerate(content.split("\n")[:40], 1):
                    print(f"{i:3}: {line}")
                break

    print("\n" + "=" * 60)
    print("[PASSED] Test successful" if result.success else "[FAILED] Test failed")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
