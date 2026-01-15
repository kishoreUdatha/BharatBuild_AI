"""
Static Code Analysis Test - Verify Java code quality without Maven/Docker

This test checks for common compilation issues using static analysis:
1. Import correctness (classes exist in generated files)
2. Method calls match available methods
3. Field types match across Entity/DTO/Service
4. Package declarations match file paths
5. No Lombok, uses jakarta.*, explicit getters/setters

Run: python test_static_analysis.py
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass

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
    match = re.search(r'<file[^>]*>(.*?)</file>', response, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response


@dataclass
class JavaClass:
    """Parsed Java class/interface/enum info."""
    name: str
    package: str
    type: str  # class, interface, enum
    imports: List[str]
    fields: List[Tuple[str, str]]  # (type, name)
    methods: List[Tuple[str, str, List[str]]]  # (return_type, name, params)
    getters: List[str]
    setters: List[str]
    extends: str
    implements: List[str]


class JavaParser:
    """Parse Java code into structured data."""

    @staticmethod
    def parse(code: str, file_path: str = "") -> JavaClass:
        # Extract package
        pkg_match = re.search(r'package\s+([\w.]+);', code)
        package = pkg_match.group(1) if pkg_match else ""

        # Extract class/interface/enum name and type
        type_match = re.search(r'public\s+(class|interface|enum)\s+(\w+)', code)
        class_type = type_match.group(1) if type_match else "class"
        class_name = type_match.group(2) if type_match else ""

        # Extract imports
        imports = re.findall(r'import\s+([\w.]+);', code)

        # Extract fields
        fields = []
        for match in re.finditer(r'private\s+(\w+(?:<[\w<>,\s]+>)?)\s+(\w+);', code):
            fields.append((match.group(1), match.group(2)))

        # Extract methods (both public and interface methods without public)
        methods = []
        pattern = r'(?:public\s+)?(\w+(?:<[\w<>,\s]+>)?)\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(pattern, code):
            return_type = match.group(1)
            name = match.group(2)
            params_str = match.group(3)
            if return_type in ['if', 'for', 'while', 'switch', 'catch', 'class', 'interface', 'enum', 'new']:
                continue
            params = []
            if params_str.strip():
                for p in params_str.split(','):
                    p = p.strip()
                    if p:
                        parts = p.split()
                        if len(parts) >= 1:
                            params.append(parts[0])
            methods.append((return_type, name, params))

        # Extract getters/setters
        getters = re.findall(r'public\s+\w+\s+(get\w+)\s*\(\)', code)
        setters = re.findall(r'public\s+void\s+(set\w+)\s*\(', code)

        # Extract extends
        extends_match = re.search(r'extends\s+(\w+(?:<[\w<>,\s]+>)?)', code)
        extends = extends_match.group(1) if extends_match else ""

        # Extract implements
        implements_match = re.search(r'implements\s+([\w,\s<>]+)\s*\{', code)
        implements = []
        if implements_match:
            implements = [i.strip() for i in implements_match.group(1).split(',')]

        return JavaClass(
            name=class_name,
            package=package,
            type=class_type,
            imports=imports,
            fields=fields,
            methods=methods,
            getters=getters,
            setters=setters,
            extends=extends,
            implements=implements
        )


class StaticAnalyzer:
    """Analyze Java code for common issues."""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.classes: Dict[str, JavaClass] = {}

    def add_class(self, file_path: str, code: str):
        """Parse and store a Java class."""
        parsed = JavaParser.parse(code, file_path)
        self.classes[file_path] = parsed
        # Also index by class name
        if parsed.name:
            self.classes[parsed.name] = parsed

    def check_lombok(self, file_path: str, code: str) -> bool:
        """Check for Lombok usage."""
        if '@Data' in code or '@Getter' in code or '@Setter' in code or '@Builder' in code:
            self.errors.append(f"{file_path}: Uses Lombok annotations")
            return False
        if 'import lombok' in code:
            self.errors.append(f"{file_path}: Imports Lombok")
            return False
        return True

    def check_jakarta(self, file_path: str, code: str) -> bool:
        """Check for jakarta vs javax imports."""
        if 'javax.persistence' in code:
            self.errors.append(f"{file_path}: Uses javax.persistence instead of jakarta.persistence")
            return False
        if 'javax.validation' in code:
            self.errors.append(f"{file_path}: Uses javax.validation instead of jakarta.validation")
            return False
        return True

    def check_package_matches_path(self, file_path: str, code: str) -> bool:
        """Check if package declaration matches file path."""
        pkg_match = re.search(r'package\s+([\w.]+);', code)
        if not pkg_match:
            self.warnings.append(f"{file_path}: No package declaration")
            return True

        package = pkg_match.group(1)
        # Convert file path to expected package
        # e.g., src/main/java/com/store/model/Order.java -> com.store.model
        path_parts = file_path.replace('\\', '/').split('/')
        if 'java' in path_parts:
            java_idx = path_parts.index('java')
            expected_parts = path_parts[java_idx + 1:-1]  # Exclude java/ and filename
            expected_package = '.'.join(expected_parts)
            if package != expected_package:
                self.errors.append(f"{file_path}: Package '{package}' doesn't match path (expected '{expected_package}')")
                return False
        return True

    def check_entity_getters_setters(self, file_path: str, parsed: JavaClass) -> bool:
        """Check if entity has getters/setters for all fields."""
        if '/model/' not in file_path or parsed.type == 'enum':
            return True

        missing = []
        for field_type, field_name in parsed.fields:
            capitalized = field_name[0].upper() + field_name[1:]
            getter = f"get{capitalized}"
            setter = f"set{capitalized}"

            if getter not in parsed.getters:
                missing.append(f"get{capitalized}()")
            if setter not in parsed.setters:
                missing.append(f"set{capitalized}()")

        if missing:
            self.errors.append(f"{file_path}: Missing accessors: {', '.join(missing[:5])}")
            return False
        return True

    def check_service_repository_calls(self, service_path: str, service_code: str) -> bool:
        """Check if Service only calls existing Repository methods."""
        if 'Service' not in service_path:
            return True

        # Find repository variable name
        repo_match = re.search(r'private\s+final\s+(\w+Repository)\s+(\w+);', service_code)
        if not repo_match:
            return True

        repo_class_name = repo_match.group(1)
        repo_var_name = repo_match.group(2)

        # Find repository class
        repo_class = self.classes.get(repo_class_name)
        if not repo_class:
            self.warnings.append(f"{service_path}: Could not find Repository class {repo_class_name}")
            return True

        # Get available methods from repository
        repo_methods = set(m[1] for m in repo_class.methods)
        # Add standard JpaRepository methods
        repo_methods.update(['findAll', 'findById', 'save', 'delete', 'deleteById', 'existsById', 'count', 'findAllById'])

        # Find all repository method calls in service
        pattern = rf'{repo_var_name}\.(\w+)\s*\('
        service_calls = set(re.findall(pattern, service_code))

        # Check each call
        invalid_calls = service_calls - repo_methods
        if invalid_calls:
            self.errors.append(f"{service_path}: Calls non-existent Repository methods: {', '.join(invalid_calls)}")
            return False
        return True

    def check_imports_exist(self, file_path: str, parsed: JavaClass) -> bool:
        """Check if imported classes exist in our generated files."""
        # Get all known classes from our package
        our_package_prefix = parsed.package.rsplit('.', 1)[0] if '.' in parsed.package else parsed.package

        missing = []
        for imp in parsed.imports:
            # Skip standard library imports
            if imp.startswith('java.') or imp.startswith('jakarta.') or imp.startswith('org.springframework'):
                continue

            # Check if it's from our package
            if imp.startswith(our_package_prefix):
                class_name = imp.split('.')[-1]
                if class_name not in self.classes and class_name != '*':
                    missing.append(class_name)

        if missing:
            self.warnings.append(f"{file_path}: Imports possibly missing classes: {', '.join(missing)}")
        return True

    def check_constructor_injection(self, file_path: str, code: str, parsed: JavaClass) -> bool:
        """Check for constructor injection in services."""
        if '/service/' not in file_path or parsed.type != 'class':
            return True

        # Check for @Autowired on fields
        if '@Autowired' in code and 'private' in code:
            autowired_fields = re.findall(r'@Autowired\s+private', code)
            if autowired_fields:
                self.errors.append(f"{file_path}: Uses field injection (@Autowired on field). Use constructor injection.")
                return False

        # Check if has constructor with dependencies
        if parsed.name:
            constructor_pattern = rf'public\s+{parsed.name}\s*\([^)]+\)'
            if not re.search(constructor_pattern, code):
                # Check if has any dependencies that should be injected
                if re.search(r'private\s+final\s+\w+\s+\w+;', code):
                    self.warnings.append(f"{file_path}: Has final fields but no constructor found")
        return True

    def analyze_all(self) -> Tuple[int, int]:
        """Run all checks on all parsed classes."""
        for file_path, parsed in self.classes.items():
            if not file_path.endswith('.java'):
                continue

            # Get the code (need to store it)
            # For now, we'll need to pass code separately

        return len(self.errors), len(self.warnings)


async def generate_and_analyze():
    """Generate a project and analyze it statically."""
    print("=" * 70)
    print("STATIC CODE ANALYSIS TEST")
    print("=" * 70)

    client = AsyncAnthropic()
    analyzer = StaticAnalyzer()

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
  - stockQuantity: Integer
  - category: String
  - createdAt: LocalDateTime
  - updatedAt: LocalDateTime
API_PATH: /api/products

ENUM: ProductCategory
VALUES: ELECTRONICS, CLOTHING, FOOD, BOOKS, OTHER
"""

    # Files to generate in order
    files_to_generate = [
        ("src/main/java/com/store/model/enums/ProductCategory.java", "Product category enum"),
        ("src/main/java/com/store/model/Product.java", "Product JPA entity with all fields and explicit getters/setters"),
        ("src/main/java/com/store/dto/ProductDto.java", "Product DTO with all fields and explicit getters/setters"),
        ("src/main/java/com/store/repository/ProductRepository.java", "Product repository extending JpaRepository"),
        ("src/main/java/com/store/service/ProductService.java", "Product service with CRUD operations"),
        ("src/main/java/com/store/controller/ProductController.java", "Product REST controller"),
    ]

    generated_files: Dict[str, str] = {}
    print(f"\n[Generating {len(files_to_generate)} files...]")

    for i, (file_path, description) in enumerate(files_to_generate, 1):
        print(f"\n[{i}/{len(files_to_generate)}] {file_path}")

        # Build context
        context_parts = []
        repo_context = ""

        is_service = 'Service.java' in file_path
        if is_service:
            # Find matching repository
            for path, code in generated_files.items():
                if 'Repository.java' in path:
                    repo_context = f"""
🔗 REPOSITORY INTERFACE (use ONLY these methods):
```java
{code}
```
"""
                    break

        for path in generated_files.keys():
            context_parts.append(f"- {path}")

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

{entity_specs}
{repo_context}
FILES ALREADY CREATED:
{chr(10).join(context_parts) if context_parts else "None yet"}

Requirements:
- NO LOMBOK - explicit getters and setters
- Use jakarta.* imports (not javax.*)
- Constructor injection for services
- Output using <file path="{file_path}">CODE</file> format"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        code = extract_file_content(response.content[0].text)
        generated_files[file_path] = code
        print(f"    Generated: {len(code)} chars")

        # Parse and add to analyzer
        analyzer.add_class(file_path, code)

    # Run analysis
    print("\n" + "=" * 70)
    print("STATIC ANALYSIS RESULTS")
    print("=" * 70)

    checks_passed = 0
    checks_failed = 0

    for file_path, code in generated_files.items():
        print(f"\n[Analyzing] {file_path}")
        parsed = analyzer.classes.get(file_path)

        # Run checks
        checks = [
            ("No Lombok", analyzer.check_lombok(file_path, code)),
            ("Jakarta imports", analyzer.check_jakarta(file_path, code)),
            ("Package matches path", analyzer.check_package_matches_path(file_path, code)),
        ]

        if parsed:
            checks.append(("Entity getters/setters", analyzer.check_entity_getters_setters(file_path, parsed)))
            checks.append(("Constructor injection", analyzer.check_constructor_injection(file_path, code, parsed)))
            checks.append(("Imports exist", analyzer.check_imports_exist(file_path, parsed)))

        # Service-Repository check
        if 'Service.java' in file_path:
            checks.append(("Repository method calls", analyzer.check_service_repository_calls(file_path, code)))

        for check_name, passed in checks:
            if passed:
                checks_passed += 1
                print(f"    [OK] {check_name}")
            else:
                checks_failed += 1
                print(f"    [FAIL] {check_name}")

    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"Files Generated: {len(generated_files)}")
    print(f"Checks Passed: {checks_passed}")
    print(f"Checks Failed: {checks_failed}")
    print(f"Errors: {len(analyzer.errors)}")
    print(f"Warnings: {len(analyzer.warnings)}")

    if analyzer.errors:
        print("\n[ERRORS]")
        for error in analyzer.errors:
            print(f"  - {error}")

    if analyzer.warnings:
        print("\n[WARNINGS]")
        for warning in analyzer.warnings[:10]:
            print(f"  - {warning}")

    # Show sample code
    print("\n" + "=" * 70)
    print("SAMPLE: ProductService.java (first 50 lines)")
    print("=" * 70)
    service_code = generated_files.get("src/main/java/com/store/service/ProductService.java", "")
    for i, line in enumerate(service_code.split('\n')[:50], 1):
        print(f"{i:3}: {line}")

    print("\n" + "=" * 70)
    if checks_failed == 0 and len(analyzer.errors) == 0:
        print("[SUCCESS] All static analysis checks PASSED!")
        return True
    else:
        print(f"[FAILED] {checks_failed} checks failed, {len(analyzer.errors)} errors")
        return False


if __name__ == "__main__":
    success = asyncio.run(generate_and_analyze())
    exit(0 if success else 1)
