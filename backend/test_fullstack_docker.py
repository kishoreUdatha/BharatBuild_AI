"""
Full Stack Docker Build Tests

Tests three full stack combinations:
1. React + Java Spring Boot
2. React + Python FastAPI
3. React + Node.js Express

Each test:
- Generates backend + frontend code via Claude API
- Builds with Docker to validate compilation/imports
- Reports any cross-file consistency errors

Run: python test_fullstack_docker.py [java|python|node|all]
"""

import asyncio
import os
import re
import shutil
import subprocess
import sys
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
OUTPUT_BASE = Path(__file__).parent / "test_fullstack_projects"


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


# =============================================================================
# ENTITY SPECS (shared across all tests)
# =============================================================================
ENTITY_SPECS = """
ENTITY_SPECS:
ENTITY: Product
TABLE: products
FIELDS:
  - id: int/long (primary key, auto-generated)
  - name: str/String
  - description: str/String (optional)
  - price: float/double/Decimal
  - quantity: int/Integer
  - category: str/String
  - createdAt: datetime/LocalDateTime
  - updatedAt: datetime/LocalDateTime
API_PATH: /api/products
"""


# =============================================================================
# REACT FRONTEND (shared across all backends)
# =============================================================================
REACT_FILES = [
    ("src/types/product.ts", "TypeScript interface for Product matching ENTITY_SPECS"),
    ("src/services/api.ts", "Axios API service for /api/products endpoints"),
    ("src/components/ProductList.tsx", "React component to list products"),
    ("src/components/ProductForm.tsx", "React form to create/edit products"),
    ("src/App.tsx", "Main App component with routing"),
]


# =============================================================================
# JAVA SPRING BOOT BACKEND
# =============================================================================
JAVA_FILES = [
    ("src/main/java/com/example/demo/entity/Product.java", "JPA Entity for Product"),
    ("src/main/java/com/example/demo/dto/ProductDto.java", "DTO for Product"),
    ("src/main/java/com/example/demo/repository/ProductRepository.java", "Spring Data JPA Repository"),
    ("src/main/java/com/example/demo/service/ProductService.java", "Service with CRUD operations"),
    ("src/main/java/com/example/demo/controller/ProductController.java", "REST Controller for /api/products"),
    ("src/main/java/com/example/demo/DemoApplication.java", "Spring Boot main class"),
]

JAVA_POM = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>
    <parent>
        <groupId>org.springframework.boot</groupId>
        <artifactId>spring-boot-starter-parent</artifactId>
        <version>3.2.0</version>
    </parent>
    <groupId>com.example</groupId>
    <artifactId>demo</artifactId>
    <version>0.0.1-SNAPSHOT</version>
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
            <groupId>com.h2database</groupId>
            <artifactId>h2</artifactId>
            <scope>runtime</scope>
        </dependency>
        <dependency>
            <groupId>org.projectlombok</groupId>
            <artifactId>lombok</artifactId>
            <optional>true</optional>
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

JAVA_DOCKERFILE = """FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml .
RUN mvn dependency:go-offline -B
COPY src ./src
RUN mvn compile -B

FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
CMD ["java", "-jar", "app.jar"]
"""


# =============================================================================
# PYTHON FASTAPI BACKEND
# =============================================================================
PYTHON_FILES = [
    ("app/core/config.py", "Settings configuration with Pydantic"),
    ("app/core/database.py", "SQLAlchemy async database setup"),
    ("app/models/product.py", "SQLAlchemy Product model"),
    ("app/schemas/product.py", "Pydantic schemas: ProductCreate, ProductUpdate, ProductResponse"),
    ("app/services/product_service.py", "Product service with async CRUD"),
    ("app/api/routes/products.py", "FastAPI router for /api/products"),
    ("app/main.py", "FastAPI application entry point"),
]

PYTHON_REQUIREMENTS = """fastapi
uvicorn
sqlalchemy
aiosqlite
pydantic
pydantic-settings
python-multipart
"""

PYTHON_DOCKERFILE = """FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Syntax check
RUN python -m py_compile app/main.py && \\
    python -m py_compile app/core/config.py && \\
    python -m py_compile app/core/database.py && \\
    python -m py_compile app/models/product.py && \\
    python -m py_compile app/schemas/product.py && \\
    python -m py_compile app/services/product_service.py && \\
    python -m py_compile app/api/routes/products.py

# Import check
RUN python -c "from app.main import app; print('Import check passed!')"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""


# =============================================================================
# NODE.JS EXPRESS BACKEND
# =============================================================================
NODE_FILES = [
    ("src/config/database.js", "Database connection setup with Sequelize"),
    ("src/models/Product.js", "Sequelize Product model"),
    ("src/services/productService.js", "Product service with CRUD operations"),
    ("src/controllers/productController.js", "Express controller for products"),
    ("src/routes/productRoutes.js", "Express router for /api/products"),
    ("src/app.js", "Express application setup"),
    ("src/index.js", "Server entry point"),
]

NODE_PACKAGE_JSON = """{
  "name": "product-api",
  "version": "1.0.0",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js"
  },
  "dependencies": {
    "express": "^4.18.2",
    "sequelize": "^6.35.0",
    "sqlite3": "^5.1.6",
    "cors": "^2.8.5",
    "dotenv": "^16.3.1"
  }
}
"""

NODE_DOCKERFILE = """FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# Syntax check all JS files
RUN node --check src/index.js && \\
    node --check src/app.js && \\
    node --check src/config/database.js && \\
    node --check src/models/Product.js && \\
    node --check src/services/productService.js && \\
    node --check src/controllers/productController.js && \\
    node --check src/routes/productRoutes.js

# Import/require check
RUN node -e "require('./src/app.js'); console.log('Import check passed!')"

EXPOSE 3000
CMD ["npm", "start"]
"""


# =============================================================================
# REACT FRONTEND BUILD FILES
# =============================================================================
REACT_PACKAGE_JSON = """{
  "name": "product-frontend",
  "version": "0.1.0",
  "private": true,
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "axios": "^1.6.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "typescript": "^5.3.0"
  },
  "scripts": {
    "start": "react-scripts start",
    "build": "react-scripts build",
    "typecheck": "tsc --noEmit"
  },
  "browserslist": {
    "production": [">0.2%", "not dead"],
    "development": ["last 1 chrome version"]
  }
}
"""

REACT_TSCONFIG = """{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": true,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "noFallthroughCasesInSwitch": true,
    "module": "ESNext",
    "moduleResolution": "node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src"]
}
"""

REACT_DOCKERFILE = """FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

# TypeScript check
RUN npx tsc --noEmit

# Build check (ensures no import/export errors)
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
"""


# =============================================================================
# CODE GENERATION
# =============================================================================
async def generate_files(
    client: AsyncAnthropic,
    files: List[Tuple[str, str]],
    system_prompt: str,
    tech_context: str,
    generated_files: Dict[str, str]
) -> Dict[str, str]:
    """Generate files with cross-file context passing."""

    for i, (file_path, description) in enumerate(files, 1):
        print(f"    [{i}/{len(files)}] {file_path.split('/')[-1]}")

        # Build dependency context based on file type
        dependency_context = ""

        # Java: Repository → Service, Service → Controller
        if file_path.endswith('.java'):
            if 'Service.java' in file_path and 'Controller' not in file_path:
                for path, code in generated_files.items():
                    if 'Repository.java' in path:
                        dependency_context = f"""
REPOSITORY INTERFACE (use ONLY these methods):
```java
{code}
```
CRITICAL: Only call methods that exist in the Repository above.
"""
            elif 'Controller.java' in file_path:
                for path, code in generated_files.items():
                    if 'Service.java' in path and 'Impl' not in path:
                        dependency_context = f"""
SERVICE CLASS (use ONLY these methods with EXACT return types):
```java
{code}
```
CRITICAL: Match Service method signatures exactly.
- If Service returns Optional<T>, handle with .map()/.orElse()
- Only call methods that exist in the Service above
"""

        # Python: config → database, database → main, schema+service → routes
        elif file_path.endswith('.py'):
            if 'database.py' in file_path:
                for path, code in generated_files.items():
                    if 'config.py' in path:
                        dependency_context = f"""
CONFIG CLASS (use EXACT attribute names):
```python
{code}
```
CRITICAL: Use settings.database_url NOT settings.DATABASE_URL
"""
            elif 'main.py' in file_path:
                for path, code in generated_files.items():
                    if 'database.py' in path:
                        dependency_context = f"""
DATABASE MODULE (use EXACT function names):
```python
{code}
```
CRITICAL: Import exact function names (init_db vs create_tables)
"""
            elif 'routes/' in file_path or '/api/' in file_path:
                schema_ctx = ""
                service_ctx = ""
                for path, code in generated_files.items():
                    if 'schemas/' in path:
                        schema_ctx = f"""
SCHEMA CLASSES (import ONLY these exact class names):
```python
{code}
```
CRITICAL: Only import schemas that EXIST above.
"""
                    if 'service' in path.lower():
                        service_ctx = f"""
SERVICE CLASS (use ONLY these methods):
```python
{code}
```
CRITICAL: Only call methods that exist in the Service.
"""
                dependency_context = schema_ctx + service_ctx

        # Node.js: model → service, service → controller, controller → routes
        elif file_path.endswith('.js'):
            if 'service' in file_path.lower():
                for path, code in generated_files.items():
                    if 'model' in path.lower() or 'Model' in path:
                        dependency_context = f"""
MODEL (use EXACT model name and methods):
```javascript
{code}
```
CRITICAL: Use the exact model name exported above.
"""
            elif 'controller' in file_path.lower():
                for path, code in generated_files.items():
                    if 'service' in path.lower():
                        dependency_context = f"""
SERVICE (use ONLY these exported functions):
```javascript
{code}
```
CRITICAL: Only call functions that are exported from the service.
"""
            elif 'route' in file_path.lower():
                for path, code in generated_files.items():
                    if 'controller' in path.lower():
                        dependency_context = f"""
CONTROLLER (use ONLY these exported functions):
```javascript
{code}
```
CRITICAL: Only use controller functions that are exported above.
"""

        # React: types → api → components
        elif file_path.endswith('.ts') or file_path.endswith('.tsx'):
            if 'api.ts' in file_path or 'service' in file_path.lower():
                for path, code in generated_files.items():
                    if 'types/' in path or 'type' in path.lower():
                        dependency_context = f"""
TYPESCRIPT TYPES (use EXACT type names):
```typescript
{code}
```
CRITICAL: Import exact type names as defined above.
"""
            elif file_path.endswith('.tsx'):
                types_ctx = ""
                api_ctx = ""
                for path, code in generated_files.items():
                    if 'types/' in path:
                        types_ctx = f"""
TYPES:
```typescript
{code}
```
"""
                    if 'api.ts' in path or 'service' in path.lower():
                        api_ctx = f"""
API SERVICE (use EXACT function names):
```typescript
{code}
```
"""
                dependency_context = types_ctx + api_ctx

        # Build context of created files
        context = [f"- {p}" for p in generated_files.keys()]

        user_prompt = f"""Generate this file:

FILE TO GENERATE: {file_path}
Description: {description}

{ENTITY_SPECS}

{tech_context}

{dependency_context}

FILES ALREADY CREATED:
{chr(10).join(context) if context else "None"}

Requirements:
- Use modern syntax and best practices
- Type hints/annotations where applicable
- Output: <file path="{file_path}">CODE</file>"""

        response = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=8192,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

        code = extract_file_content(response.content[0].text)
        generated_files[file_path] = code

    return generated_files


# =============================================================================
# TEST RUNNERS
# =============================================================================
async def test_java_fullstack():
    """Test React + Java Spring Boot full stack."""
    print("\n" + "=" * 70)
    print("FULLSTACK TEST: React + Java Spring Boot")
    print("=" * 70)

    client = AsyncAnthropic()
    output_dir = OUTPUT_BASE / "java-fullstack"

    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    backend_dir = output_dir / "backend"
    frontend_dir = output_dir / "frontend"
    backend_dir.mkdir()
    frontend_dir.mkdir()

    # Load prompts
    core_prompt = load_prompt("writer_core.txt")
    java_prompt = load_prompt("writer_java.txt")
    react_prompt = load_prompt("writer_react.txt")

    generated_files: Dict[str, str] = {}

    # Generate backend
    print("\n[PHASE 1] Generating Java backend...")
    java_system = core_prompt + "\n\n" + java_prompt
    java_context = "Tech: Java 17, Spring Boot 3.2, Spring Data JPA, H2 Database, Lombok"
    await generate_files(client, JAVA_FILES, java_system, java_context, generated_files)

    # Save backend files
    for path, content in generated_files.items():
        if path.startswith("src/main/java"):
            full_path = backend_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

    (backend_dir / "pom.xml").write_text(JAVA_POM, encoding="utf-8")
    (backend_dir / "Dockerfile").write_text(JAVA_DOCKERFILE, encoding="utf-8")

    # Add application.properties
    props_dir = backend_dir / "src" / "main" / "resources"
    props_dir.mkdir(parents=True, exist_ok=True)
    (props_dir / "application.properties").write_text(
        "spring.datasource.url=jdbc:h2:mem:testdb\n"
        "spring.datasource.driver-class-name=org.h2.Driver\n"
        "spring.jpa.hibernate.ddl-auto=create-drop\n"
        "spring.h2.console.enabled=true\n",
        encoding="utf-8"
    )
    print("  Backend files saved")

    # Generate frontend
    print("\n[PHASE 2] Generating React frontend...")
    react_system = core_prompt + "\n\n" + react_prompt
    react_context = "Tech: React 18, TypeScript, React Router, Axios"
    frontend_files: Dict[str, str] = {}
    await generate_files(client, REACT_FILES, react_system, react_context, frontend_files)

    # Save frontend files
    for path, content in frontend_files.items():
        full_path = frontend_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    (frontend_dir / "package.json").write_text(REACT_PACKAGE_JSON, encoding="utf-8")
    (frontend_dir / "tsconfig.json").write_text(REACT_TSCONFIG, encoding="utf-8")
    (frontend_dir / "Dockerfile").write_text(REACT_DOCKERFILE, encoding="utf-8")

    # Add index.html for React
    public_dir = frontend_dir / "public"
    public_dir.mkdir(exist_ok=True)
    (public_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head><title>Products</title></head>'
        '<body><div id="root"></div></body></html>',
        encoding="utf-8"
    )

    # Add index.tsx
    (frontend_dir / "src" / "index.tsx").write_text(
        'import React from "react";\n'
        'import ReactDOM from "react-dom/client";\n'
        'import App from "./App";\n\n'
        'const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);\n'
        'root.render(<React.StrictMode><App /></React.StrictMode>);\n',
        encoding="utf-8"
    )
    print("  Frontend files saved")

    # Build backend with Docker
    print("\n[PHASE 3] Docker build - Java backend...")
    backend_result = run_docker_build(backend_dir, "java-backend-test")

    # Build frontend with Docker
    print("\n[PHASE 4] Docker build - React frontend...")
    frontend_result = run_docker_build(frontend_dir, "react-frontend-test")

    return backend_result[0] == 0 and frontend_result[0] == 0, backend_result, frontend_result


async def test_python_fullstack():
    """Test React + Python FastAPI full stack."""
    print("\n" + "=" * 70)
    print("FULLSTACK TEST: React + Python FastAPI")
    print("=" * 70)

    client = AsyncAnthropic()
    output_dir = OUTPUT_BASE / "python-fullstack"

    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    backend_dir = output_dir / "backend"
    frontend_dir = output_dir / "frontend"
    backend_dir.mkdir()
    frontend_dir.mkdir()

    # Load prompts
    core_prompt = load_prompt("writer_core.txt")
    python_prompt = load_prompt("writer_python.txt")
    react_prompt = load_prompt("writer_react.txt")

    generated_files: Dict[str, str] = {}

    # Generate backend
    print("\n[PHASE 1] Generating Python backend...")
    python_system = core_prompt + "\n\n" + python_prompt
    python_context = "Tech: Python 3.11, FastAPI, SQLAlchemy 2.0 async, Pydantic v2, aiosqlite"
    await generate_files(client, PYTHON_FILES, python_system, python_context, generated_files)

    # Save backend files
    for path, content in generated_files.items():
        if path.startswith("app/"):
            full_path = backend_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

    # Add __init__.py files
    for init_dir in ["app", "app/core", "app/models", "app/schemas", "app/services", "app/api", "app/api/routes"]:
        init_path = backend_dir / init_dir / "__init__.py"
        init_path.parent.mkdir(parents=True, exist_ok=True)
        init_path.write_text("", encoding="utf-8")

    (backend_dir / "requirements.txt").write_text(PYTHON_REQUIREMENTS, encoding="utf-8")
    (backend_dir / "Dockerfile").write_text(PYTHON_DOCKERFILE, encoding="utf-8")
    print("  Backend files saved")

    # Generate frontend
    print("\n[PHASE 2] Generating React frontend...")
    react_system = core_prompt + "\n\n" + react_prompt
    react_context = "Tech: React 18, TypeScript, React Router, Axios"
    frontend_files: Dict[str, str] = {}
    await generate_files(client, REACT_FILES, react_system, react_context, frontend_files)

    # Save frontend files
    for path, content in frontend_files.items():
        full_path = frontend_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    (frontend_dir / "package.json").write_text(REACT_PACKAGE_JSON, encoding="utf-8")
    (frontend_dir / "tsconfig.json").write_text(REACT_TSCONFIG, encoding="utf-8")
    (frontend_dir / "Dockerfile").write_text(REACT_DOCKERFILE, encoding="utf-8")

    # Add index.html and index.tsx
    public_dir = frontend_dir / "public"
    public_dir.mkdir(exist_ok=True)
    (public_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head><title>Products</title></head>'
        '<body><div id="root"></div></body></html>',
        encoding="utf-8"
    )
    (frontend_dir / "src" / "index.tsx").write_text(
        'import React from "react";\n'
        'import ReactDOM from "react-dom/client";\n'
        'import App from "./App";\n\n'
        'const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);\n'
        'root.render(<React.StrictMode><App /></React.StrictMode>);\n',
        encoding="utf-8"
    )
    print("  Frontend files saved")

    # Build backend with Docker
    print("\n[PHASE 3] Docker build - Python backend...")
    backend_result = run_docker_build(backend_dir, "python-backend-test")

    # Build frontend with Docker
    print("\n[PHASE 4] Docker build - React frontend...")
    frontend_result = run_docker_build(frontend_dir, "react-frontend-test")

    return backend_result[0] == 0 and frontend_result[0] == 0, backend_result, frontend_result


async def test_node_fullstack():
    """Test React + Node.js Express full stack."""
    print("\n" + "=" * 70)
    print("FULLSTACK TEST: React + Node.js Express")
    print("=" * 70)

    client = AsyncAnthropic()
    output_dir = OUTPUT_BASE / "node-fullstack"

    # Clean output directory
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)

    backend_dir = output_dir / "backend"
    frontend_dir = output_dir / "frontend"
    backend_dir.mkdir()
    frontend_dir.mkdir()

    # Load prompts
    core_prompt = load_prompt("writer_core.txt")
    node_prompt = load_prompt("writer_node.txt") if (PROMPTS_DIR / "writer_node.txt").exists() else ""
    react_prompt = load_prompt("writer_react.txt")

    generated_files: Dict[str, str] = {}

    # Generate backend
    print("\n[PHASE 1] Generating Node.js backend...")
    node_system = core_prompt + "\n\n" + node_prompt if node_prompt else core_prompt + """

NODE.JS/EXPRESS RULES:
- Use ES6+ syntax (const, arrow functions, async/await)
- Use CommonJS modules (require/module.exports)
- Sequelize for ORM with proper model definitions
- Express Router for routes
- Proper error handling with try/catch
"""
    node_context = "Tech: Node.js 18, Express 4, Sequelize 6, SQLite3"
    await generate_files(client, NODE_FILES, node_system, node_context, generated_files)

    # Save backend files
    for path, content in generated_files.items():
        if path.startswith("src/"):
            full_path = backend_dir / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding="utf-8")

    (backend_dir / "package.json").write_text(NODE_PACKAGE_JSON, encoding="utf-8")
    (backend_dir / "Dockerfile").write_text(NODE_DOCKERFILE, encoding="utf-8")
    print("  Backend files saved")

    # Generate frontend
    print("\n[PHASE 2] Generating React frontend...")
    react_system = core_prompt + "\n\n" + react_prompt
    react_context = "Tech: React 18, TypeScript, React Router, Axios"
    frontend_files: Dict[str, str] = {}
    await generate_files(client, REACT_FILES, react_system, react_context, frontend_files)

    # Save frontend files
    for path, content in frontend_files.items():
        full_path = frontend_dir / path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")

    (frontend_dir / "package.json").write_text(REACT_PACKAGE_JSON, encoding="utf-8")
    (frontend_dir / "tsconfig.json").write_text(REACT_TSCONFIG, encoding="utf-8")
    (frontend_dir / "Dockerfile").write_text(REACT_DOCKERFILE, encoding="utf-8")

    # Add index.html and index.tsx
    public_dir = frontend_dir / "public"
    public_dir.mkdir(exist_ok=True)
    (public_dir / "index.html").write_text(
        '<!DOCTYPE html><html><head><title>Products</title></head>'
        '<body><div id="root"></div></body></html>',
        encoding="utf-8"
    )
    (frontend_dir / "src" / "index.tsx").write_text(
        'import React from "react";\n'
        'import ReactDOM from "react-dom/client";\n'
        'import App from "./App";\n\n'
        'const root = ReactDOM.createRoot(document.getElementById("root") as HTMLElement);\n'
        'root.render(<React.StrictMode><App /></React.StrictMode>);\n',
        encoding="utf-8"
    )
    print("  Frontend files saved")

    # Build backend with Docker
    print("\n[PHASE 3] Docker build - Node.js backend...")
    backend_result = run_docker_build(backend_dir, "node-backend-test")

    # Build frontend with Docker
    print("\n[PHASE 4] Docker build - React frontend...")
    frontend_result = run_docker_build(frontend_dir, "react-frontend-test")

    return backend_result[0] == 0 and frontend_result[0] == 0, backend_result, frontend_result


def run_docker_build(project_dir: Path, image_name: str) -> Tuple[int, str, str]:
    """Run Docker build and return results."""
    cmd = ["docker", "build", "-t", image_name, str(project_dir.absolute())]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,
            encoding='utf-8',
            errors='replace'
        )

        if result.returncode == 0:
            print(f"  [SUCCESS] {image_name} built successfully")
        else:
            print(f"  [FAILED] {image_name} build failed")
            # Show last 20 lines of error
            lines = (result.stdout + result.stderr).strip().split('\n')
            for line in lines[-20:]:
                print(f"    {line}")

        return result.returncode, result.stdout or "", result.stderr or ""

    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {image_name} build timed out")
        return -1, "", "Build timed out"
    except Exception as e:
        print(f"  [ERROR] {image_name}: {str(e)}")
        return -1, "", str(e)


def print_summary(results: Dict[str, Tuple[bool, any, any]]):
    """Print test summary."""
    print("\n" + "=" * 70)
    print("FULLSTACK TEST SUMMARY")
    print("=" * 70)

    all_passed = True
    for name, (success, backend, frontend) in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"\n{status} {name}")
        if not success:
            all_passed = False
            print(f"  Backend: {'OK' if backend[0] == 0 else 'FAILED'}")
            print(f"  Frontend: {'OK' if frontend[0] == 0 else 'FAILED'}")

    print("\n" + "=" * 70)
    if all_passed:
        print("[SUCCESS] All fullstack tests passed!")
    else:
        print("[FAILED] Some tests failed - see details above")
    print("=" * 70)

    return all_passed


async def main():
    """Run fullstack tests based on command line args."""
    args = sys.argv[1:] if len(sys.argv) > 1 else ["all"]

    results = {}

    if "java" in args or "all" in args:
        success, backend, frontend = await test_java_fullstack()
        results["React + Java Spring Boot"] = (success, backend, frontend)

    if "python" in args or "all" in args:
        success, backend, frontend = await test_python_fullstack()
        results["React + Python FastAPI"] = (success, backend, frontend)

    if "node" in args or "all" in args:
        success, backend, frontend = await test_node_fullstack()
        results["React + Node.js Express"] = (success, backend, frontend)

    all_passed = print_summary(results)
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
