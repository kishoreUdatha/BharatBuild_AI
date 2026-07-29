"""
Full Project Build Test - End-to-End Generation and Compilation

This test simulates the complete BharatBuild workflow:
1. Planner generates a project plan with entity_specs
2. Writer generates all files with cross-file context
3. Files are saved to disk
4. Maven build is executed to verify compilation

Run: python test_full_project_build.py
"""

import asyncio
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

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
OUTPUT_DIR = Path(__file__).parent / "test_output_project"


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


def extract_entity_specs(plan: str) -> str:
    """Extract entity_specs section from plan."""
    match = re.search(r'<entity_specs>(.*?)</entity_specs>', plan, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def extract_files_from_plan(plan: str) -> List[Dict[str, str]]:
    """Extract file paths and descriptions from plan."""
    files = []
    # Match <file path="..." priority="...">
    pattern = r'<file\s+path="([^"]+)"[^>]*>\s*<description>([^<]*)</description>'
    for match in re.finditer(pattern, plan, re.DOTALL):
        files.append({
            "path": match.group(1),
            "description": match.group(2).strip()
        })
    return files


class FullProjectBuildTest:
    """Full end-to-end project build test."""

    def __init__(self):
        self.client = AsyncAnthropic()
        self.generated_files: Dict[str, str] = {}
        self.entity_specs = ""
        self.errors: List[str] = []
        self.warnings: List[str] = []

    async def run_planner(self, user_request: str) -> str:
        """Run the planner to generate project plan."""
        print("\n" + "=" * 70)
        print("PHASE 1: PLANNER - Generating Project Plan")
        print("=" * 70)

        core = load_prompt("planner_core.txt")
        java = load_prompt("planner_java.txt")
        system_prompt = core + "\n\n" + java

        print(f"[OK] Loaded planner prompts (~{len(system_prompt)//4} tokens)")
        print(f"[...] Calling Claude for project plan...")

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_request}]
        )

        plan = response.content[0].text
        tokens = response.usage.input_tokens + response.usage.output_tokens
        print(f"[OK] Plan generated: {len(plan)} chars, {tokens} tokens")

        # Extract entity_specs
        self.entity_specs = extract_entity_specs(plan)
        if self.entity_specs:
            print(f"[OK] Extracted entity_specs: {len(self.entity_specs)} chars")
        else:
            self.errors.append("No entity_specs found in plan")
            print("[ERROR] No entity_specs found in plan!")

        return plan

    async def generate_file(self, file_path: str, description: str, system_prompt: str) -> str:
        """Generate a single file with cross-file context."""

        # Build context from already generated files
        files_context = []
        repo_context = ""

        # For Service files, include full Repository code
        is_service = 'Service.java' in file_path or '/service/' in file_path
        entity_name = None
        if is_service:
            file_name = file_path.split('/')[-1].replace('.java', '')
            entity_name = file_name.replace('Service', '')

        for path, content in self.generated_files.items():
            if path.endswith('.java'):
                # For Service, include full matching Repository
                if is_service and entity_name and 'Repository.java' in path and entity_name in path:
                    repo_context = f"""
🔗 REPOSITORY INTERFACE (use ONLY these methods):
📄 {path}:
```java
{content}
```
"""
                else:
                    # Include summary for other files
                    files_context.append(f"- {path}")

        context_str = "\n".join(files_context) if files_context else "None yet"

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

ENTITY_SPECS:
{self.entity_specs}
{repo_context}
FILES ALREADY CREATED (you can import from these):
{context_str}

Generate complete, production-ready code. NO LOMBOK. Use jakarta.* imports.
Output using <file path="{file_path}">CONTENT</file> format."""

        response = await self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        return extract_file_content(response.content[0].text)

    async def run_writer(self, plan: str) -> None:
        """Generate all files from the plan."""
        print("\n" + "=" * 70)
        print("PHASE 2: WRITER - Generating Project Files")
        print("=" * 70)

        core = load_prompt("writer_core.txt")
        java = load_prompt("writer_java.txt")
        system_prompt = core + "\n\n" + java

        # Get files from plan
        files = extract_files_from_plan(plan)

        if not files:
            # Fallback: generate standard Spring Boot files
            print("[WARN] No files found in plan, using standard structure")
            files = [
                {"path": "backend/src/main/java/com/store/model/enums/OrderStatus.java", "description": "Order status enum"},
                {"path": "backend/src/main/java/com/store/model/Order.java", "description": "Order JPA entity"},
                {"path": "backend/src/main/java/com/store/dto/OrderDto.java", "description": "Order DTO"},
                {"path": "backend/src/main/java/com/store/repository/OrderRepository.java", "description": "Order repository"},
                {"path": "backend/src/main/java/com/store/service/OrderService.java", "description": "Order service"},
                {"path": "backend/src/main/java/com/store/controller/OrderController.java", "description": "Order REST controller"},
                {"path": "backend/src/main/java/com/store/StoreApplication.java", "description": "Spring Boot main class"},
                {"path": "backend/src/main/resources/application.properties", "description": "Application config"},
                {"path": "backend/pom.xml", "description": "Maven build file"},
            ]

        print(f"[OK] Files to generate: {len(files)}")

        # Generate files in order (dependencies first)
        for i, file_info in enumerate(files, 1):
            path = file_info["path"]
            desc = file_info["description"]

            # Skip non-Java files for this test (we'll add them manually)
            if not path.endswith('.java') and not path.endswith('.xml') and not path.endswith('.properties'):
                continue

            print(f"\n[{i}/{len(files)}] Generating: {path}")

            try:
                content = await self.generate_file(path, desc, system_prompt)
                self.generated_files[path] = content
                print(f"    [OK] Generated {len(content)} chars")
            except Exception as e:
                self.errors.append(f"Failed to generate {path}: {e}")
                print(f"    [ERROR] {e}")

    def save_files(self) -> None:
        """Save generated files to disk."""
        print("\n" + "=" * 70)
        print("PHASE 3: SAVING FILES TO DISK")
        print("=" * 70)

        # Clean output directory
        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        OUTPUT_DIR.mkdir(parents=True)

        for path, content in self.generated_files.items():
            full_path = OUTPUT_DIR / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")
            print(f"[OK] Saved: {path}")

        # Add application.properties if not generated
        props_path = OUTPUT_DIR / "backend/src/main/resources/application.properties"
        if not props_path.exists():
            props_path.parent.mkdir(parents=True, exist_ok=True)
            props_path.write_text("""spring.application.name=store
server.port=8080
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.jpa.database-platform=org.hibernate.dialect.H2Dialect
spring.jpa.hibernate.ddl-auto=update
spring.h2.console.enabled=true
""", encoding="utf-8")
            print("[OK] Added: application.properties")

        # Add pom.xml if not generated
        pom_path = OUTPUT_DIR / "backend/pom.xml"
        if not pom_path.exists():
            pom_path.parent.mkdir(parents=True, exist_ok=True)
            pom_path.write_text("""<?xml version="1.0" encoding="UTF-8"?>
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
    <artifactId>store-backend</artifactId>
    <version>1.0.0</version>
    <name>Store Backend</name>

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
""", encoding="utf-8")
            print("[OK] Added: pom.xml")

        print(f"\n[OK] Total files saved: {len(list(OUTPUT_DIR.rglob('*')))}")

    def run_maven_build(self) -> bool:
        """Run Maven build to verify compilation."""
        print("\n" + "=" * 70)
        print("PHASE 4: MAVEN BUILD - Verifying Compilation")
        print("=" * 70)

        backend_dir = OUTPUT_DIR / "backend"

        if not (backend_dir / "pom.xml").exists():
            self.errors.append("pom.xml not found")
            print("[ERROR] pom.xml not found!")
            return False

        print("[...] Running: mvn compile -q")

        try:
            result = subprocess.run(
                ["mvn", "compile", "-q"],
                cwd=str(backend_dir),
                capture_output=True,
                text=True,
                timeout=300
            )

            if result.returncode == 0:
                print("[OK] Maven build SUCCESSFUL!")
                return True
            else:
                print("[ERROR] Maven build FAILED!")
                print("\n[Build Output]")
                print("-" * 50)
                # Extract error messages
                output = result.stdout + result.stderr
                error_lines = []
                for line in output.split('\n'):
                    if 'error:' in line.lower() or '[ERROR]' in line:
                        error_lines.append(line)
                        self.errors.append(line.strip())

                if error_lines:
                    print('\n'.join(error_lines[:20]))  # Show first 20 errors
                else:
                    print(output[:2000])  # Show raw output
                print("-" * 50)
                return False

        except FileNotFoundError:
            print("[WARN] Maven not found, skipping build verification")
            self.warnings.append("Maven not installed - build not verified")
            return True  # Don't fail if Maven not installed
        except subprocess.TimeoutExpired:
            self.errors.append("Maven build timed out")
            print("[ERROR] Maven build timed out!")
            return False

    def analyze_code_quality(self) -> None:
        """Analyze generated code for common issues."""
        print("\n" + "=" * 70)
        print("PHASE 5: CODE QUALITY ANALYSIS")
        print("=" * 70)

        checks = {
            "No Lombok": True,
            "Jakarta imports": True,
            "Explicit getters/setters": True,
            "Constructor injection": True,
            "Cross-file consistency": True,
        }

        for path, content in self.generated_files.items():
            if not path.endswith('.java'):
                continue

            # Check Lombok
            if '@Data' in content or '@Getter' in content or 'import lombok' in content:
                checks["No Lombok"] = False
                self.errors.append(f"{path}: Uses Lombok")

            # Check Jakarta
            if 'javax.persistence' in content:
                checks["Jakarta imports"] = False
                self.errors.append(f"{path}: Uses javax instead of jakarta")

            # Check getters/setters for entities
            if '/model/' in path and 'enum' not in path.lower():
                if 'getId()' not in content or 'setId(' not in content:
                    checks["Explicit getters/setters"] = False
                    self.warnings.append(f"{path}: May be missing getters/setters")

            # Check constructor injection for services
            if '/service/' in path:
                class_name = path.split('/')[-1].replace('.java', '')
                if f'public {class_name}(' not in content:
                    checks["Constructor injection"] = False
                    self.warnings.append(f"{path}: May be missing constructor injection")

        for check, passed in checks.items():
            status = "[OK]" if passed else "[FAIL]"
            print(f"  {status} {check}")

    async def run(self, user_request: str) -> bool:
        """Run the full test."""
        print("=" * 70)
        print("FULL PROJECT BUILD TEST")
        print("=" * 70)
        print(f"Request: {user_request[:100]}...")

        # Phase 1: Plan
        plan = await self.run_planner(user_request)

        # Phase 2: Generate files
        await self.run_writer(plan)

        # Phase 3: Save files
        self.save_files()

        # Phase 4: Build
        build_success = self.run_maven_build()

        # Phase 5: Analyze
        self.analyze_code_quality()

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print(f"Files Generated: {len(self.generated_files)}")
        print(f"Errors: {len(self.errors)}")
        print(f"Warnings: {len(self.warnings)}")

        if self.errors:
            print("\n[ERRORS]")
            for error in self.errors[:10]:
                print(f"  - {error}")

        if self.warnings:
            print("\n[WARNINGS]")
            for warning in self.warnings[:10]:
                print(f"  - {warning}")

        print("\n" + "=" * 70)
        if build_success and len(self.errors) == 0:
            print("[SUCCESS] Full project build test PASSED!")
        else:
            print("[FAILED] Full project build test failed")
        print("=" * 70)

        return build_success and len(self.errors) == 0


async def main():
    user_request = """Create a simple Order Management backend with Spring Boot:
- Order entity: customerName, customerEmail, totalAmount (BigDecimal), status (enum: PENDING/CONFIRMED/SHIPPED/DELIVERED), orderDate
- Full CRUD REST API at /api/orders
- Use Spring Boot 3.x with H2 database
- NO LOMBOK - explicit getters and setters"""

    test = FullProjectBuildTest()
    success = await test.run(user_request)
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
