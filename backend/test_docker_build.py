"""
Docker Build Test - Full compilation verification using Maven in Docker

This test:
1. Generates a complete Spring Boot project
2. Builds it with Maven in Docker container
3. Reports any compilation errors
4. Tracks token usage and cost

Run: python test_docker_build.py
"""

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

# Claude Sonnet pricing (per 1M tokens)
INPUT_PRICE = 3.0   # $3 per 1M input tokens
OUTPUT_PRICE = 15.0  # $15 per 1M output tokens

# Global token tracker
total_input_tokens = 0
total_output_tokens = 0

# Load API key
api_key = os.environ.get("ANTHROPIC_API_KEY")
for env_file in [".env.test", ".env"]:
    if api_key:
        break
    env_path = Path(__file__).parent / env_file
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("ANTHROPIC_API_KEY="):
                api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                os.environ["ANTHROPIC_API_KEY"] = api_key
                break

if not api_key:
    print("[ERROR] ANTHROPIC_API_KEY not found")
    exit(1)

from anthropic import AsyncAnthropic

PROMPTS_DIR = Path(__file__).parent / "app" / "config" / "prompts"
OUTPUT_DIR = Path(__file__).parent / "test_docker_project"


def load_prompt(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def extract_file_content(response: str) -> str:
    match = re.search(r'<file[^>]*>(.*?)</file>', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response


async def generate_project():
    """Generate a complete Spring Boot project."""
    print("=" * 70)
    print("DOCKER BUILD TEST - Java Spring Boot")
    print("=" * 70)

    client = AsyncAnthropic()
    generated_files: Dict[str, str] = {}

    # Load prompts
    core = load_prompt("writer_core.txt")
    java = load_prompt("writer_java.txt")
    system_prompt = core + "\n\n" + java

    entity_specs = """
ENTITY_SPECS:
ENTITY: Product
TABLE: products
FIELDS:
  - id: Long (primary key)
  - name: String
  - description: String
  - price: BigDecimal
  - quantity: Integer
  - category: ProductCategory (enum)
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/products

ENUM: ProductCategory
VALUES: ELECTRONICS, CLOTHING, FOOD, BOOKS
"""

    # Files to generate in dependency order
    files = [
        ("src/main/java/com/store/model/enums/ProductCategory.java", "Product category enum"),
        ("src/main/java/com/store/model/Product.java", "Product JPA entity"),
        ("src/main/java/com/store/dto/ProductDto.java", "Product DTO"),
        ("src/main/java/com/store/repository/ProductRepository.java", "Product repository"),
        ("src/main/java/com/store/service/ProductService.java", "Product service"),
        ("src/main/java/com/store/controller/ProductController.java", "Product REST controller"),
        ("src/main/java/com/store/StoreApplication.java", "Spring Boot main class"),
    ]

    print(f"\n[PHASE 1] Generating {len(files)} Java files...")

    for i, (file_path, description) in enumerate(files, 1):
        print(f"  [{i}/{len(files)}] {file_path.split('/')[-1]}")

        # Build context
        context = [f"- {p}" for p in generated_files.keys()]
        dependency_context = ""

        # For Service: include Repository code
        if 'Service.java' in file_path:
            for path, code in generated_files.items():
                if 'Repository.java' in path:
                    dependency_context = f"""
🔗 REPOSITORY INTERFACE (use ONLY these methods):
```java
{code}
```
"""

        # For Controller: include Service code
        if 'Controller.java' in file_path:
            for path, code in generated_files.items():
                if 'Service.java' in path:
                    dependency_context = f"""
🔗 SERVICE CLASS (use ONLY these methods with EXACT return types):
```java
{code}
```

CRITICAL: Match the Service method signatures exactly:
- If Service returns Optional<T>, handle it with .orElse() or .isPresent()
- Only call methods that exist in the Service
"""

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

{entity_specs}
{dependency_context}
FILES ALREADY CREATED:
{chr(10).join(context) if context else "None"}

Requirements:
- NO LOMBOK - explicit getters/setters
- Use jakarta.* imports
- Constructor injection
- Output: <file path="{file_path}">CODE</file>"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        # Track tokens
        global total_input_tokens, total_output_tokens
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        code = extract_file_content(response.content[0].text)
        generated_files[file_path] = code

    return generated_files


def print_cost_summary():
    """Print token usage and cost summary."""
    print("\n" + "-" * 50)
    print("TOKEN USAGE & COST (Claude Sonnet)")
    print("-" * 50)
    print(f"  Input tokens:  {total_input_tokens:,}")
    print(f"  Output tokens: {total_output_tokens:,}")
    print(f"  Total tokens:  {total_input_tokens + total_output_tokens:,}")

    input_cost = (total_input_tokens / 1_000_000) * INPUT_PRICE
    output_cost = (total_output_tokens / 1_000_000) * OUTPUT_PRICE
    total_cost = input_cost + output_cost

    print(f"\n  Input cost:  ${input_cost:.4f}")
    print(f"  Output cost: ${output_cost:.4f}")
    print(f"  TOTAL COST:  ${total_cost:.4f}")
    print("-" * 50)


def save_project(generated_files: Dict[str, str]):
    """Save generated files and add build files."""
    print(f"\n[PHASE 2] Saving project to {OUTPUT_DIR}...")

    # Clean and create output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Save generated Java files
    for path, content in generated_files.items():
        full_path = OUTPUT_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        print(f"  Saved: {path.split('/')[-1]}")

    # Add pom.xml
    pom_content = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>

    <groupId>com.store</groupId>
    <artifactId>store-api</artifactId>
    <version>1.0.0</version>
    <name>Store API</name>

    <properties>
        <java.version>17</java.version>
    </properties>

    <dependencies>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-web</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-data-jpa</artifactId>
        </dependency>
        <dependency>
            <groupId>org.springframework.boot</groupId>
            <artifactId>spring-boot-starter-validation</artifactId>
        </dependency>
        <dependency>
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>
    </dependencies>

    <build>
        <plugins>
            <plugin>
                <groupId>org.springframework.boot</groupId>
                <artifactId>spring-boot-maven-plugin</artifactId>
            </plugin>
        </plugins>
    </build>
</project>
"""
    (OUTPUT_DIR / "pom.xml").write_text(pom_content, encoding="utf-8")
    print("  Saved: pom.xml")

    # Add application.properties
    props_dir = OUTPUT_DIR / "src/main/resources"
    props_dir.mkdir(parents=True, exist_ok=True)
    (props_dir / "application.properties").write_text("""
spring.application.name=store-api
server.port=8080
spring.datasource.url=jdbc:h2:mem:storedb
spring.datasource.driverClassName=org.h2.Driver
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=update
spring.h2.console.enabled=true
""", encoding="utf-8")
    print("  Saved: application.properties")


def run_docker_build() -> tuple:
    """Run Maven build in Docker container."""
    print(f"\n[PHASE 3] Running Maven build in Docker...")

    # Convert Windows path to Docker-compatible path
    project_path = str(OUTPUT_DIR.absolute()).replace("\\", "/")

    # For Windows, convert C:/... to /c/...
    if project_path[1] == ":":
        project_path = "/" + project_path[0].lower() + project_path[2:]

    print(f"  Project path: {project_path}")

    # Run Maven compile in Docker
    cmd = [
        "docker", "run", "--rm",
        "-v", f"{project_path}:/app",
        "-w", "/app",
        "maven:3.9-eclipse-temurin-17-alpine",
        "mvn", "compile", "-B"
    ]

    print(f"  Running: docker run maven:3.9-eclipse-temurin-17-alpine mvn compile")
    print("  (This may take a minute for first run to download dependencies...)\n")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        return result.returncode, result.stdout, result.stderr

    except subprocess.TimeoutExpired:
        return -1, "", "Build timed out after 5 minutes"
    except Exception as e:
        return -1, "", str(e)


def analyze_build_output(returncode: int, stdout: str, stderr: str) -> List[str]:
    """Analyze build output for errors."""
    errors = []
    output = stdout + stderr

    if returncode == 0:
        return errors

    # Extract compilation errors
    error_patterns = [
        r'\[ERROR\].*\.java:\[\d+,\d+\].*',
        r'error:.*',
        r'cannot find symbol.*',
        r'incompatible types.*',
        r'package .* does not exist.*',
    ]

    for pattern in error_patterns:
        for match in re.finditer(pattern, output, re.IGNORECASE):
            error = match.group(0).strip()
            if error and error not in errors:
                errors.append(error)

    # If no specific errors found but build failed
    if not errors and returncode != 0:
        # Get last few lines that might contain error info
        lines = output.strip().split('\n')
        for line in lines[-20:]:
            if 'error' in line.lower() or 'failed' in line.lower():
                errors.append(line.strip())

    return errors


async def main():
    """Run the full Docker build test."""

    # Phase 1: Generate project
    generated_files = await generate_project()
    print(f"\n  Generated {len(generated_files)} files")

    # Phase 2: Save project
    save_project(generated_files)

    # Phase 3: Run Docker build
    returncode, stdout, stderr = run_docker_build()

    # Phase 4: Analyze results
    print("=" * 70)
    print("BUILD RESULTS")
    print("=" * 70)

    if returncode == 0:
        print("\n[SUCCESS] Maven build completed successfully!")
        print("\nBuild output (last 20 lines):")
        print("-" * 50)
        lines = stdout.strip().split('\n')
        for line in lines[-20:]:
            print(line)
        print("-" * 50)

        # Show what was compiled
        print("\n[Compiled Files]")
        target_dir = OUTPUT_DIR / "target" / "classes" / "com" / "store"
        if target_dir.exists():
            for f in target_dir.rglob("*.class"):
                print(f"  [OK] {f.name}")

        # Print token usage and cost
        print_cost_summary()

        print("\n" + "=" * 70)
        print("[SUCCESS] All Java files compiled without errors!")
        print("=" * 70)
        return True

    else:
        print("\n[FAILED] Maven build failed!")

        errors = analyze_build_output(returncode, stdout, stderr)

        if errors:
            print(f"\n[Compilation Errors: {len(errors)}]")
            print("-" * 50)
            for i, error in enumerate(errors[:15], 1):
                print(f"  {i}. {error}")
            print("-" * 50)

        print("\n[Full Build Output]")
        print("-" * 50)
        output = stdout + stderr
        # Show relevant portion
        lines = output.strip().split('\n')
        for line in lines[-40:]:
            print(line)
        print("-" * 50)

        # Print token usage and cost even on failure
        print_cost_summary()

        print("\n" + "=" * 70)
        print(f"[FAILED] Build failed with {len(errors)} errors")
        print("=" * 70)
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
