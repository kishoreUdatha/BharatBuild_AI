"""
Mock SDK Fixer Test - Demonstrates the flow without API key.

Run: python test_sdk_mock.py
"""

import asyncio
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class SDKFixResult:
    success: bool
    files_modified: List[str]
    files_created: List[str]
    message: str
    tool_calls: int
    tokens_used: int


# Mock Java files with Lombok (the problem)
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

# What Claude would return (simulated response)
MOCK_CLAUDE_RESPONSE = {
    "Order.java": """package com.example.model;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
public class Order {
    @Id
    private Long id;
    private String customerName;
    private BigDecimal totalAmount;
    private String status;

    // No-arg constructor
    public Order() {}

    // All-args constructor
    public Order(Long id, String customerName, BigDecimal totalAmount, String status) {
        this.id = id;
        this.customerName = customerName;
        this.totalAmount = totalAmount;
        this.status = status;
    }

    // Getters
    public Long getId() { return id; }
    public String getCustomerName() { return customerName; }
    public BigDecimal getTotalAmount() { return totalAmount; }
    public String getStatus() { return status; }

    // Setters
    public void setId(Long id) { this.id = id; }
    public void setCustomerName(String customerName) { this.customerName = customerName; }
    public void setTotalAmount(BigDecimal totalAmount) { this.totalAmount = totalAmount; }
    public void setStatus(String status) { this.status = status; }
}
""",
    "Product.java": """package com.example.model;

import jakarta.persistence.*;
import java.math.BigDecimal;

@Entity
public class Product {
    @Id
    private Long id;
    private String name;
    private BigDecimal price;

    // No-arg constructor
    public Product() {}

    // All-args constructor
    public Product(Long id, String name, BigDecimal price) {
        this.id = id;
        this.name = name;
        this.price = price;
    }

    // Getters
    public Long getId() { return id; }
    public String getName() { return name; }
    public BigDecimal getPrice() { return price; }

    // Setters
    public void setId(Long id) { this.id = id; }
    public void setName(String name) { this.name = name; }
    public void setPrice(BigDecimal price) { this.price = price; }
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
    """Mock sandbox for testing - stores files in memory."""

    def __init__(self, files: dict):
        self.files = dict(files)
        self.operations = []  # Track operations

    def read(self, path: str) -> str:
        path = path.replace("\\", "/")
        self.operations.append(f"READ: {path}")
        for key in self.files:
            if path.endswith(key.split("/")[-1]) or key in path or path in key:
                return self.files[key]
        return None

    def write(self, path: str, content: str) -> bool:
        path = path.replace("\\", "/")
        self.operations.append(f"WRITE: {path}")
        for key in list(self.files.keys()):
            if path.endswith(key.split("/")[-1]):
                self.files[key] = content
                return True
        self.files[path] = content
        return True

    def list(self, base: str, pattern: str) -> list:
        self.operations.append(f"LIST: {pattern}")
        return list(self.files.keys())


class MockSDKFixer:
    """Mock SDK Fixer that simulates Claude's tool-use flow."""

    TOOLS = ["list_files", "read_file", "write_file"]

    def __init__(self, sandbox_reader, sandbox_writer, sandbox_lister):
        self._sandbox_reader = sandbox_reader
        self._sandbox_writer = sandbox_writer
        self._sandbox_lister = sandbox_lister
        self._files_modified = []
        self._tool_calls = 0

    async def fix(self, project_path: Path, build_errors: str, max_iterations: int = 10) -> SDKFixResult:
        print("\n[SDK Fixer] Analyzing build errors...")
        print(f"[SDK Fixer] Detected 4 'cannot find symbol' errors")
        print(f"[SDK Fixer] Root cause: Lombok annotations not processed")

        # Simulate Claude's tool calls
        print("\n--- SIMULATED CLAUDE TOOL CALLS ---")

        # Step 1: List files
        self._tool_calls += 1
        print(f"\n[Tool Call {self._tool_calls}] list_files(pattern='**/*.java')")
        files = self._sandbox_lister("", "**/*.java")
        print(f"  Result: Found {len(files)} files")
        for f in files:
            print(f"    - {f}")

        # Step 2: Read Order.java
        self._tool_calls += 1
        print(f"\n[Tool Call {self._tool_calls}] read_file(path='Order.java')")
        order_content = self._sandbox_reader("Order.java")
        has_lombok = "@Data" in order_content if order_content else False
        print(f"  Result: {len(order_content) if order_content else 0} chars")
        print(f"  Has Lombok: {has_lombok}")

        # Step 3: Read Product.java
        self._tool_calls += 1
        print(f"\n[Tool Call {self._tool_calls}] read_file(path='Product.java')")
        product_content = self._sandbox_reader("Product.java")
        has_lombok = "@Data" in product_content if product_content else False
        print(f"  Result: {len(product_content) if product_content else 0} chars")
        print(f"  Has Lombok: {has_lombok}")

        # Step 4: Write fixed Order.java
        self._tool_calls += 1
        print(f"\n[Tool Call {self._tool_calls}] write_file(path='Order.java', content=...)")
        fixed_order = MOCK_CLAUDE_RESPONSE["Order.java"]
        self._sandbox_writer("Order.java", fixed_order)
        self._files_modified.append("Order.java")
        print(f"  Result: Written {len(fixed_order)} chars")
        print(f"  Changes: Removed @Data, @Builder, added getters/setters")

        # Step 5: Write fixed Product.java
        self._tool_calls += 1
        print(f"\n[Tool Call {self._tool_calls}] write_file(path='Product.java', content=...)")
        fixed_product = MOCK_CLAUDE_RESPONSE["Product.java"]
        self._sandbox_writer("Product.java", fixed_product)
        self._files_modified.append("Product.java")
        print(f"  Result: Written {len(fixed_product)} chars")
        print(f"  Changes: Removed @Data, added getters/setters")

        print("\n--- END TOOL CALLS ---")

        return SDKFixResult(
            success=True,
            files_modified=self._files_modified,
            files_created=[],
            message=f"Fixed {len(self._files_modified)} files",
            tool_calls=self._tool_calls,
            tokens_used=2500  # Simulated
        )


async def main():
    print("=" * 60)
    print("SDK FIXER MOCK TEST - Java Build Errors")
    print("=" * 60)

    sandbox = MockSandbox(JAVA_FILES)

    print("\n[Initial Files]")
    for path, content in sandbox.files.items():
        has_lombok = "@Data" in content
        has_getters = "getId()" in content
        status = "[LOMBOK]" if has_lombok else ("[OK]" if has_getters else "[???]")
        print(f"  {status} {path.split('/')[-1]}")

    print("\n[Build Errors]")
    print("-" * 40)
    print(BUILD_ERRORS)
    print("-" * 40)

    print("\n[Running Mock SDK Fixer...]")

    fixer = MockSDKFixer(
        sandbox_reader=sandbox.read,
        sandbox_writer=sandbox.write,
        sandbox_lister=sandbox.list
    )

    result = await fixer.fix(Path("."), BUILD_ERRORS, max_iterations=10)

    print("\n" + "=" * 60)
    print("[Results]")
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

    print("\n[Sandbox Operations]")
    for op in sandbox.operations:
        print(f"  {op}")

    if result.success:
        print("\n[Fixed Order.java - First 30 lines]")
        print("-" * 40)
        for path, content in sandbox.files.items():
            if "Order.java" in path:
                for i, line in enumerate(content.split("\n")[:30], 1):
                    print(f"{i:3}: {line}")
                break

    print("\n" + "=" * 60)
    print("[PASSED] Mock test successful" if result.success else "[FAILED] Mock test failed")
    print("=" * 60)

    print("\n[How Real SDK Fixer Works]")
    print("-" * 40)
    print("""
1. Initialize with sandbox callbacks:
   fixer = SDKFixer(sandbox_reader, sandbox_writer, sandbox_lister)

2. Call Claude with tools:
   - list_files: List project structure
   - read_file: Read files that need fixing
   - write_file: Write fixed content

3. Claude autonomously:
   - Analyzes build errors
   - Reads affected files
   - Removes Lombok annotations
   - Adds explicit getters/setters
   - Writes fixed files back

4. Result returned with:
   - files_modified list
   - tool_calls count
   - tokens_used
""")


if __name__ == "__main__":
    asyncio.run(main())
