"""
Real Compilation Test - Generate related files and check for cross-file errors.

This test generates a complete set of related Java files and checks for:
1. Cross-file method consistency
2. Import correctness
3. Type matching
4. Repository method existence
5. DTO field mapping completeness
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

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


def load_prompt(filename: str) -> str:
    filepath = PROMPTS_DIR / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def extract_file_content(response: str) -> str:
    """Extract code from <file>...</file> tags."""
    match = re.search(r'<file[^>]*>(.*?)</file>', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response


class JavaAnalyzer:
    """Analyze Java code for common errors."""

    @staticmethod
    def extract_class_name(code: str) -> str:
        match = re.search(r'public\s+(?:class|interface|enum)\s+(\w+)', code)
        return match.group(1) if match else ""

    @staticmethod
    def extract_imports(code: str) -> List[str]:
        return re.findall(r'import\s+([\w.]+);', code)

    @staticmethod
    def extract_fields(code: str) -> List[Tuple[str, str]]:
        """Extract (type, name) pairs for fields."""
        fields = []
        for match in re.finditer(r'private\s+(\w+(?:<[\w<>,\s]+>)?)\s+(\w+);', code):
            fields.append((match.group(1), match.group(2)))
        return fields

    @staticmethod
    def extract_methods(code: str) -> List[Tuple[str, str, List[str]]]:
        """Extract (return_type, name, param_types) for methods."""
        methods = []
        # Match both 'public Type method()' and 'Type method()' (interface methods)
        pattern = r'(?:public\s+)?(\w+(?:<[\w<>,\s]+>)?)\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(pattern, code):
            return_type = match.group(1)
            name = match.group(2)
            params = match.group(3)
            # Skip constructors and common non-method patterns
            if return_type in ['if', 'for', 'while', 'switch', 'catch', 'class', 'interface', 'enum']:
                continue
            param_types = []
            if params.strip():
                for param in params.split(','):
                    param = param.strip()
                    if param:
                        parts = param.split()
                        if len(parts) >= 2:
                            param_types.append(parts[0])
            methods.append((return_type, name, param_types))
        return methods

    @staticmethod
    def extract_getters(code: str) -> List[str]:
        """Extract getter method names."""
        return re.findall(r'public\s+\w+\s+(get\w+)\s*\(\)', code)

    @staticmethod
    def extract_setters(code: str) -> List[str]:
        """Extract setter method names."""
        return re.findall(r'public\s+void\s+(set\w+)\s*\(', code)

    @staticmethod
    def has_lombok(code: str) -> bool:
        return '@Data' in code or '@Getter' in code or '@Setter' in code or 'import lombok' in code

    @staticmethod
    def uses_jakarta(code: str) -> bool:
        return 'jakarta.' in code

    @staticmethod
    def uses_javax(code: str) -> bool:
        return 'javax.persistence' in code or 'javax.validation' in code


async def generate_file(client, system_prompt: str, user_prompt: str) -> str:
    """Generate a single file using Claude."""
    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=8192,
        system=system_prompt,
        messages=[{"role": "user", "content": user_prompt}]
    )
    return extract_file_content(response.content[0].text)


async def main():
    print("=" * 70)
    print("REAL COMPILATION TEST - Cross-File Consistency Check")
    print("=" * 70)

    core = load_prompt("writer_core.txt")
    java = load_prompt("writer_java.txt")
    system_prompt = core + "\n\n" + java

    client = AsyncAnthropic()

    # Common context for all files
    entity_specs = """
ENTITY_SPECS:
ENTITY: Order
TABLE: orders
FIELDS:
  - id: Long (primary key)
  - customerName: String
  - customerEmail: String
  - totalAmount: BigDecimal
  - status: OrderStatus (enum)
  - orderDate: LocalDateTime
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/orders

ENTITY: OrderItem
TABLE: order_items
FIELDS:
  - id: Long (primary key)
  - order: Order (ManyToOne)
  - productName: String
  - quantity: Integer
  - unitPrice: BigDecimal
  - createdAt: LocalDateTime
API_PATH: /api/order-items

ENUM: OrderStatus
VALUES: PENDING, CONFIRMED, SHIPPED, DELIVERED, CANCELLED
"""

    generated_files: Dict[str, str] = {}
    errors: List[str] = []
    warnings: List[str] = []

    # =========================================================================
    # STEP 1: Generate Entity
    # =========================================================================
    print("\n[1/6] Generating Order Entity...")
    entity_prompt = f"""Generate this file:

FILE TO GENERATE: backend/src/main/java/com/store/model/Order.java

{entity_specs}

Generate complete JPA entity with:
- All fields with proper JPA annotations
- @OneToMany relationship to OrderItem
- NO LOMBOK - explicit getters and setters for ALL fields
- @PrePersist and @PreUpdate for timestamps"""

    entity_code = await generate_file(client, system_prompt, entity_prompt)
    generated_files["Order.java"] = entity_code
    print(f"    Generated {len(entity_code)} chars")

    # =========================================================================
    # STEP 2: Generate DTO
    # =========================================================================
    print("\n[2/6] Generating OrderDto...")
    dto_prompt = f"""Generate this file:

FILE TO GENERATE: backend/src/main/java/com/store/dto/OrderDto.java

{entity_specs}

FILES ALREADY CREATED:
- backend/src/main/java/com/store/model/Order.java (has: id, customerName, customerEmail, totalAmount, status, orderDate, createdAt, updatedAt)

Generate DTO with:
- Same fields as Order entity
- NO LOMBOK - explicit getters and setters for ALL fields
- Include a list of OrderItemDto for the items"""

    dto_code = await generate_file(client, system_prompt, dto_prompt)
    generated_files["OrderDto.java"] = dto_code
    print(f"    Generated {len(dto_code)} chars")

    # =========================================================================
    # STEP 3: Generate Repository
    # =========================================================================
    print("\n[3/6] Generating OrderRepository...")
    repo_prompt = f"""Generate this file:

FILE TO GENERATE: backend/src/main/java/com/store/repository/OrderRepository.java

{entity_specs}

FILES ALREADY CREATED:
- backend/src/main/java/com/store/model/Order.java

Generate repository interface with:
- Extend JpaRepository<Order, Long>
- findByStatus(OrderStatus status)
- findByCustomerEmail(String email)
- findByOrderDateBetween(LocalDateTime start, LocalDateTime end)
- findByTotalAmountGreaterThan(BigDecimal amount)"""

    repo_code = await generate_file(client, system_prompt, repo_prompt)
    generated_files["OrderRepository.java"] = repo_code
    print(f"    Generated {len(repo_code)} chars")

    # =========================================================================
    # STEP 4: Generate Service (WITH FULL REPOSITORY CODE - like orchestrator does)
    # =========================================================================
    print("\n[4/6] Generating OrderService...")
    # CRITICAL: Include FULL Repository code so Claude knows exactly what methods exist
    repo_code = generated_files.get("OrderRepository.java", "")
    service_prompt = f"""Generate this file:

FILE TO GENERATE: backend/src/main/java/com/store/service/OrderService.java

{entity_specs}

🔗 REPOSITORY INTERFACE (use ONLY these methods):
📄 backend/src/main/java/com/store/repository/OrderRepository.java:
```java
{repo_code}
```

FILES ALREADY CREATED:
- backend/src/main/java/com/store/model/Order.java (entity with getters/setters)
- backend/src/main/java/com/store/dto/OrderDto.java (DTO with getters/setters)
- backend/src/main/java/com/store/repository/OrderRepository.java

Generate service with:
- Constructor injection for OrderRepository
- ONLY call methods that exist in the Repository interface above
- findAll() returning List<OrderDto>
- findById(Long id) returning OrderDto
- findByStatus(OrderStatus status) returning List<OrderDto> - ONLY if findByStatus exists in repo
- findByCustomerEmail(String email) returning List<OrderDto> - ONLY if findByCustomerEmail exists in repo
- create(OrderDto dto) returning OrderDto
- update(Long id, OrderDto dto) returning OrderDto
- delete(Long id) returning void
- updateStatus(Long id, OrderStatus status) returning OrderDto
- convertToDto and convertToEntity methods
- Map ALL fields in convertToDto/convertToEntity"""

    service_code = await generate_file(client, system_prompt, service_prompt)
    generated_files["OrderService.java"] = service_code
    print(f"    Generated {len(service_code)} chars")

    # =========================================================================
    # STEP 5: Generate Controller
    # =========================================================================
    print("\n[5/6] Generating OrderController...")
    controller_prompt = """Generate this file:

FILE TO GENERATE: backend/src/main/java/com/store/controller/OrderController.java

""" + entity_specs + """

FILES ALREADY CREATED:
- backend/src/main/java/com/store/dto/OrderDto.java
- backend/src/main/java/com/store/service/OrderService.java (has: findAll, findById, findByStatus, findByCustomerEmail, create, update, delete, updateStatus)

Generate controller with:
- @RestController and @RequestMapping("/api/orders")
- Constructor injection for OrderService
- GET / - getAll()
- GET /{id} - getById(Long id)
- GET /status/{status} - getByStatus(OrderStatus status)
- GET /customer/{email} - getByCustomerEmail(String email)
- POST / - create(OrderDto dto)
- PUT /{id} - update(Long id, OrderDto dto)
- DELETE /{id} - delete(Long id)
- PATCH /{id}/status - updateStatus(Long id, OrderStatus status)
- Proper ResponseEntity return types"""

    controller_code = await generate_file(client, system_prompt, controller_prompt)
    generated_files["OrderController.java"] = controller_code
    print(f"    Generated {len(controller_code)} chars")

    # =========================================================================
    # STEP 6: Generate Enum
    # =========================================================================
    print("\n[6/6] Generating OrderStatus Enum...")
    enum_prompt = f"""Generate this file:

FILE TO GENERATE: backend/src/main/java/com/store/model/enums/OrderStatus.java

{entity_specs}

Generate enum with all status values."""

    enum_code = await generate_file(client, system_prompt, enum_prompt)
    generated_files["OrderStatus.java"] = enum_code
    print(f"    Generated {len(enum_code)} chars")

    # =========================================================================
    # ANALYSIS: Check for cross-file errors
    # =========================================================================
    print("\n" + "=" * 70)
    print("CROSS-FILE ANALYSIS")
    print("=" * 70)

    analyzer = JavaAnalyzer()

    # Check 1: Lombok usage
    print("\n[Check 1] Lombok Usage:")
    for filename, code in generated_files.items():
        if analyzer.has_lombok(code):
            errors.append(f"{filename}: Contains Lombok annotations")
            print(f"  [ERROR] {filename}: Contains Lombok")
        else:
            print(f"  [OK] {filename}: No Lombok")

    # Check 2: Jakarta vs Javax
    print("\n[Check 2] Jakarta vs Javax:")
    for filename, code in generated_files.items():
        if analyzer.uses_javax(code):
            errors.append(f"{filename}: Uses javax instead of jakarta")
            print(f"  [ERROR] {filename}: Uses javax")
        elif analyzer.uses_jakarta(code) or filename == "OrderStatus.java":
            print(f"  [OK] {filename}: Uses jakarta or N/A")

    # Check 3: Entity fields vs DTO fields
    print("\n[Check 3] Entity-DTO Field Consistency:")
    entity_fields = set(f[1] for f in analyzer.extract_fields(generated_files.get("Order.java", "")))
    dto_fields = set(f[1] for f in analyzer.extract_fields(generated_files.get("OrderDto.java", "")))

    # Fields in entity but not in DTO
    missing_in_dto = entity_fields - dto_fields - {'items'}  # items might be named differently
    if missing_in_dto:
        for field in missing_in_dto:
            warnings.append(f"OrderDto missing field from Order: {field}")
            print(f"  [WARN] DTO missing field: {field}")
    else:
        print(f"  [OK] DTO has all entity fields")

    # Check 4: Entity getters for all fields
    print("\n[Check 4] Entity Getters/Setters:")
    entity_code = generated_files.get("Order.java", "")
    entity_getters = set(g.lower() for g in analyzer.extract_getters(entity_code))
    entity_setters = set(s.lower() for s in analyzer.extract_setters(entity_code))

    required_accessors = ['id', 'customername', 'customeremail', 'totalamount', 'status', 'orderdate', 'createdat', 'updatedat']
    for field in required_accessors:
        getter = f"get{field}"
        setter = f"set{field}"
        if getter not in entity_getters:
            errors.append(f"Order.java missing getter: get{field.title()}")
            print(f"  [ERROR] Missing getter: get{field.title()}")
        if setter not in entity_setters:
            errors.append(f"Order.java missing setter: set{field.title()}")
            print(f"  [ERROR] Missing setter: set{field.title()}")

    if not any(f"get{f}" not in entity_getters for f in required_accessors):
        print(f"  [OK] Entity has all getters")
    if not any(f"set{f}" not in entity_setters for f in required_accessors):
        print(f"  [OK] Entity has all setters")

    # Check 5: Service calls methods that exist in Repository
    print("\n[Check 5] Service-Repository Method Consistency:")
    repo_code = generated_files.get("OrderRepository.java", "")
    service_code = generated_files.get("OrderService.java", "")

    repo_methods = [m[1] for m in analyzer.extract_methods(repo_code)]

    # Check if service uses repo methods that exist
    service_repo_calls = re.findall(r'orderRepository\.(\w+)\(', service_code)
    for call in set(service_repo_calls):
        # Standard JpaRepository methods
        standard_methods = ['findAll', 'findById', 'save', 'delete', 'deleteById', 'existsById']
        if call not in repo_methods and call not in standard_methods:
            errors.append(f"Service calls orderRepository.{call}() but method not in Repository")
            print(f"  [ERROR] Service calls {call}() - not in Repository")

    if not errors:
        print(f"  [OK] All service->repository calls are valid")

    # Check 6: Controller calls methods that exist in Service
    print("\n[Check 6] Controller-Service Method Consistency:")
    controller_code = generated_files.get("OrderController.java", "")

    service_methods = [m[1] for m in analyzer.extract_methods(service_code)]
    controller_service_calls = re.findall(r'orderService\.(\w+)\(', controller_code)

    for call in set(controller_service_calls):
        if call not in service_methods:
            errors.append(f"Controller calls orderService.{call}() but method not in Service")
            print(f"  [ERROR] Controller calls {call}() - not in Service")

    if not any(call not in service_methods for call in set(controller_service_calls)):
        print(f"  [OK] All controller->service calls are valid")

    # Check 7: ConvertToDto maps all fields
    print("\n[Check 7] ConvertToDto Field Mapping:")
    if 'convertToDto' in service_code:
        # Check if convertToDto uses getters for all fields
        convert_section = service_code[service_code.find('convertToDto'):service_code.find('convertToDto')+1500]
        for field in ['Id', 'CustomerName', 'CustomerEmail', 'TotalAmount', 'Status', 'OrderDate']:
            if f'get{field}()' not in convert_section:
                warnings.append(f"convertToDto may not map field: {field}")
                print(f"  [WARN] convertToDto may miss: {field}")
        print(f"  [OK] convertToDto appears to map fields")
    else:
        errors.append("Service missing convertToDto method")
        print(f"  [ERROR] Missing convertToDto method")

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)

    print(f"\nFiles Generated: {len(generated_files)}")
    print(f"Errors Found: {len(errors)}")
    print(f"Warnings Found: {len(warnings)}")

    if errors:
        print("\n[ERRORS]")
        for err in errors:
            print(f"  - {err}")

    if warnings:
        print("\n[WARNINGS]")
        for warn in warnings:
            print(f"  - {warn}")

    print("\n" + "=" * 70)
    if len(errors) == 0:
        print("[SUCCESS] No critical cross-file errors detected!")
    elif len(errors) <= 3:
        print("[MOSTLY OK] Few minor errors - simplified prompts work well")
    else:
        print(f"[ISSUES] {len(errors)} errors found - may need prompt adjustments")
    print("=" * 70)

    # Show sample of generated code
    print("\n[Sample: Order.java getters/setters section]")
    print("-" * 50)
    entity_code = generated_files.get("Order.java", "")
    # Find getter section
    getter_start = entity_code.find("public Long getId()")
    if getter_start > 0:
        print(entity_code[getter_start:getter_start+800])
    print("-" * 50)

    return len(errors) == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
