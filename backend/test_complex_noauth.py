"""
Complex App Test - Java Spring Boot (No Auth)

Tests a complex application with:
- Multiple entities with relationships
- Full CRUD operations
- Token tracking for cost estimation

Run: python test_complex_noauth.py
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
OUTPUT_DIR = Path(__file__).parent / "test_complex_noauth_project"


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


# Complex entity specs - Inventory Management (No Auth)
ENTITY_SPECS = """
<entity_specs>
ENTITY: Category
TABLE: categories
FIELDS:
  - id: Long (primary key)
  - name: String
  - description: String (optional)
  - active: Boolean (default true)
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/categories
RELATIONS:
  - products: List<Product> (OneToMany)

ENTITY: Product
TABLE: products
FIELDS:
  - id: Long (primary key)
  - name: String
  - description: String (optional)
  - price: BigDecimal
  - quantity: Integer
  - sku: String (unique)
  - categoryId: Long (foreign key to Category)
  - active: Boolean (default true)
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/products
RELATIONS:
  - category: Category (ManyToOne)

ENTITY: Order
TABLE: orders
FIELDS:
  - id: Long (primary key)
  - orderNumber: String (unique)
  - customerName: String
  - customerEmail: String
  - status: OrderStatus (enum)
  - totalAmount: BigDecimal
  - orderDate: LocalDateTime
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/orders
RELATIONS:
  - items: List<OrderItem> (OneToMany)

ENTITY: OrderItem
TABLE: order_items
FIELDS:
  - id: Long (primary key)
  - orderId: Long (foreign key to Order)
  - productId: Long (foreign key to Product)
  - quantity: Integer
  - unitPrice: BigDecimal
  - totalPrice: BigDecimal
  - createdAt: LocalDateTime
API_PATH: /api/order-items
RELATIONS:
  - order: Order (ManyToOne)
  - product: Product (ManyToOne)

ENUM: OrderStatus
VALUES: PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED
</entity_specs>
"""

# Files to generate in dependency order
FILES_TO_GENERATE = [
    # Config files
    ("pom.xml", "Maven POM with Spring Boot 3.x, JPA, H2, Validation"),
    ("src/main/resources/application.yml", "Application configuration with H2 database"),

    # Enums
    ("src/main/java/com/app/model/enums/OrderStatus.java", "OrderStatus enum"),

    # Entities
    ("src/main/java/com/app/model/Category.java", "Category entity"),
    ("src/main/java/com/app/model/Product.java", "Product entity with category relationship"),
    ("src/main/java/com/app/model/Order.java", "Order entity"),
    ("src/main/java/com/app/model/OrderItem.java", "OrderItem entity with order and product relationships"),

    # DTOs
    ("src/main/java/com/app/dto/CategoryDto.java", "Category DTO"),
    ("src/main/java/com/app/dto/ProductDto.java", "Product DTO"),
    ("src/main/java/com/app/dto/OrderDto.java", "Order DTO"),
    ("src/main/java/com/app/dto/OrderItemDto.java", "OrderItem DTO"),

    # Repositories
    ("src/main/java/com/app/repository/CategoryRepository.java", "Category repository"),
    ("src/main/java/com/app/repository/ProductRepository.java", "Product repository with findByCategoryId"),
    ("src/main/java/com/app/repository/OrderRepository.java", "Order repository with findByStatus"),
    ("src/main/java/com/app/repository/OrderItemRepository.java", "OrderItem repository with findByOrderId"),

    # Services
    ("src/main/java/com/app/service/CategoryService.java", "Category service interface"),
    ("src/main/java/com/app/service/ProductService.java", "Product service interface"),
    ("src/main/java/com/app/service/OrderService.java", "Order service interface"),
    ("src/main/java/com/app/service/OrderItemService.java", "OrderItem service interface"),

    # Service Implementations
    ("src/main/java/com/app/service/impl/CategoryServiceImpl.java", "Category service implementation"),
    ("src/main/java/com/app/service/impl/ProductServiceImpl.java", "Product service implementation"),
    ("src/main/java/com/app/service/impl/OrderServiceImpl.java", "Order service implementation"),
    ("src/main/java/com/app/service/impl/OrderItemServiceImpl.java", "OrderItem service implementation"),

    # Controllers
    ("src/main/java/com/app/controller/CategoryController.java", "Category CRUD controller"),
    ("src/main/java/com/app/controller/ProductController.java", "Product CRUD controller"),
    ("src/main/java/com/app/controller/OrderController.java", "Order CRUD controller"),
    ("src/main/java/com/app/controller/OrderItemController.java", "OrderItem CRUD controller"),

    # Main Application
    ("src/main/java/com/app/Application.java", "Spring Boot main application class"),
]


async def generate_file(client, system_prompt: str, file_path: str, description: str,
                        generated_files: Dict[str, str]) -> str:
    """Generate a single file with context from previously generated files."""

    # Build context from related files
    context_files = []

    # Extract entity name from file path for context matching
    file_name = file_path.split("/")[-1].replace(".java", "").replace(".yml", "").replace(".xml", "")

    # Find related files to include as context
    for path, code in generated_files.items():
        include = False

        # For repository: include entity
        if "Repository" in file_path:
            entity_name = file_name.replace("Repository", "")
            if f"model/{entity_name}.java" in path or f"model/enums/" in path:
                include = True

        # For service interface: include entity, DTO, repository
        if "service/" in file_path and "impl/" not in file_path and file_path.endswith("Service.java"):
            entity_name = file_name.replace("Service", "")
            if entity_name.lower() in path.lower() and ("model/" in path or "dto/" in path or "repository/" in path):
                include = True

        # For service impl: include service interface, entity, DTO, repository
        if "service/impl/" in file_path:
            entity_name = file_name.replace("ServiceImpl", "")
            if entity_name.lower() in path.lower():
                include = True
            # Also include the service interface
            if f"service/{entity_name}Service.java" in path:
                include = True

        # For controller: include service interface, service impl, DTO
        if "controller/" in file_path:
            entity_name = file_name.replace("Controller", "")
            if entity_name.lower() in path.lower() and ("service/" in path or "dto/" in path):
                include = True

        if include:
            context_files.append(f"--- {path} ---\n{code}")

    context = "\n\n".join(context_files) if context_files else "None"

    user_prompt = f"""Generate this file for an Inventory Management application:

FILE TO GENERATE: {file_path}
Description: {description}

{ENTITY_SPECS}

PREVIOUSLY GENERATED FILES (use EXACT method names and field names from these):
{context}

Requirements:
- Spring Boot 3.x with jakarta.* imports
- NO Lombok - write explicit getters/setters/constructors
- Use EXACT field names from entity_specs
- For service impl: ONLY call methods that exist in the Repository
- For controller: ONLY call methods that exist in the Service interface
- Match return types exactly (handle Optional properly)
- Output ONLY the file content wrapped in: <file path="{file_path}">CODE</file>"""

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

    return extract_file_content(response.content[0].text)


async def generate_project():
    """Generate a complex project with multiple entities."""
    print("=" * 70)
    print("COMPLEX APP TEST - Inventory Management (No Auth)")
    print("=" * 70)
    print("\nThis test generates:")
    print("  - 4 entities: Category, Product, Order, OrderItem")
    print("  - Entity relationships (OneToMany, ManyToOne)")
    print("  - Full CRUD operations")
    print(f"  - {len(FILES_TO_GENERATE)} files total")

    client = AsyncAnthropic()
    generated_files: Dict[str, str] = {}

    # Load prompts
    core = load_prompt("writer_core.txt")
    java = load_prompt("writer_java.txt")
    system_prompt = core + "\n\n" + java

    print(f"\n[PHASE 1] Generating {len(FILES_TO_GENERATE)} files...")

    for i, (file_path, description) in enumerate(FILES_TO_GENERATE, 1):
        file_name = file_path.split("/")[-1]
        print(f"  [{i}/{len(FILES_TO_GENERATE)}] {file_name}")

        code = await generate_file(client, system_prompt, file_path, description, generated_files)
        generated_files[file_path] = code

    return generated_files


def save_project(generated_files: Dict[str, str]):
    """Save generated files to disk."""
    print(f"\n[PHASE 2] Saving project to {OUTPUT_DIR}...")

    # Clean and create output directory
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True)

    # Save generated files
    for path, content in generated_files.items():
        full_path = OUTPUT_DIR / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    print(f"  Saved {len(generated_files)} files")


def run_maven_build() -> tuple:
    """Run Maven compile to validate Java code."""
    print(f"\n[PHASE 3] Running Maven build in Docker...")

    # Convert path for Docker
    project_path = str(OUTPUT_DIR.absolute()).replace("\\", "/")
    if len(project_path) > 1 and project_path[1] == ":":
        project_path = "/" + project_path[0].lower() + project_path[2:]

    print(f"  Project path: {project_path}")
    print("  Running: docker run maven:3.9-eclipse-temurin-17-alpine mvn compile")
    print("  (This may take a few minutes...)")

    cmd = [
        "docker", "run", "--rm",
        "-v", f"{project_path}:/app",
        "-w", "/app",
        "maven:3.9-eclipse-temurin-17-alpine",
        "mvn", "compile", "-q"
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            encoding='utf-8',
            errors='replace'
        )
        return result.returncode, result.stdout or "", result.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "Build timed out after 10 minutes"
    except Exception as e:
        return -1, "", str(e)


def analyze_errors(output: str) -> List[str]:
    """Extract compilation errors from Maven output."""
    errors = []

    # Pattern for Java compilation errors
    error_pattern = r'\[ERROR\].*\.java:\[\d+,\d+\].*'
    for match in re.finditer(error_pattern, output):
        error = match.group(0).strip()
        if error not in errors:
            errors.append(error)

    # Also capture general error messages
    general_pattern = r'\[ERROR\].*error:.*'
    for match in re.finditer(general_pattern, output, re.IGNORECASE):
        error = match.group(0).strip()
        if error not in errors:
            errors.append(error)

    # Capture "cannot find symbol" errors
    symbol_pattern = r'cannot find symbol.*'
    for match in re.finditer(symbol_pattern, output):
        error = match.group(0).strip()
        if error not in errors:
            errors.append(error)

    return errors


def count_compiled_classes() -> int:
    """Count successfully compiled .class files."""
    target_dir = OUTPUT_DIR / "target" / "classes"
    if not target_dir.exists():
        return 0

    count = 0
    for f in target_dir.rglob("*.class"):
        count += 1
    return count


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


async def main():
    """Run the complex app test."""

    # Phase 1: Generate project
    generated_files = await generate_project()

    # Phase 2: Save project
    save_project(generated_files)

    # Phase 3: Run Maven build
    returncode, stdout, stderr = run_maven_build()
    output = stdout + stderr

    # Phase 4: Analyze results
    print("\n" + "=" * 70)
    print("BUILD RESULTS")
    print("=" * 70)

    if returncode == 0:
        compiled = count_compiled_classes()
        print(f"\n[SUCCESS] Maven build completed!")
        print(f"\n  Files generated: {len(generated_files)}")
        print(f"  Classes compiled: {compiled}")

        # Print token usage and cost
        print_cost_summary()

        print("\n" + "=" * 70)
        print("[SUCCESS] Complex app compiled without errors!")
        print("=" * 70)
        return True
    else:
        errors = analyze_errors(output)
        print(f"\n[FAILED] Maven build failed!")
        print(f"\n  Files generated: {len(generated_files)}")
        print(f"  Compilation errors: {len(errors)}")

        if errors:
            print(f"\n[Errors ({len(errors)})]")
            print("-" * 50)
            for i, error in enumerate(errors[:30], 1):
                # Truncate long errors
                if len(error) > 100:
                    error = error[:100] + "..."
                print(f"  {i}. {error}")
            if len(errors) > 30:
                print(f"  ... and {len(errors) - 30} more errors")
            print("-" * 50)

        # Show last 30 lines of output
        print("\n[Build Output (last 30 lines)]")
        print("-" * 50)
        lines = output.strip().split('\n')
        for line in lines[-30:]:
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
