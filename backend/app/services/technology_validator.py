"""
Technology Validator - Comprehensive pre-build validation for ALL supported technologies

This module ensures all required files exist and are correctly configured
BEFORE the build starts, preventing cascading errors.

SUPPORTED TECHNOLOGIES:
- React/Vite/TypeScript
- Angular
- Vue.js
- Python (FastAPI, Django, Flask)
- Python AI/ML (TensorFlow, PyTorch, Scikit-learn)
- Node.js (Express, NestJS)
- Java (Spring Boot, Maven, Gradle)
- Go (Golang)
- Rust
- Blockchain (Solidity, Hardhat, Truffle, Web3)
- Cyber Security tools
- Full-stack (any combination)
"""

import os
import json
import re
from typing import Dict, List, Tuple, Optional, Callable
from dataclasses import dataclass, field

from app.core.logging_config import logger


@dataclass
class ValidationResult:
    """Result of technology validation"""
    is_valid: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    files_fixed: List[str] = field(default_factory=list)


# =============================================================================
# DEFAULT FILE TEMPLATES - REACT/VITE
# =============================================================================

TSCONFIG_NODE_JSON = """{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts", "vite.config.js"]
}"""

POSTCSS_CONFIG_JS = """export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}"""

VITE_CONFIG_TS = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})"""

INDEX_HTML = """<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>App</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>"""

MAIN_TSX = """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)"""

APP_TSX = """function App() {
  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center">
      <h1 className="text-3xl font-bold">Hello World</h1>
    </div>
  )
}

export default App"""

INDEX_CSS = """@tailwind base;
@tailwind components;
@tailwind utilities;
"""

TAILWIND_CONFIG_JS = """/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}"""

# =============================================================================
# DEFAULT FILE TEMPLATES - ANGULAR
# =============================================================================

ANGULAR_JSON_MINIMAL = """{
  "$schema": "./node_modules/@angular/cli/lib/config/schema.json",
  "version": 1,
  "newProjectRoot": "projects",
  "projects": {
    "app": {
      "projectType": "application",
      "root": "",
      "sourceRoot": "src",
      "architect": {
        "build": {
          "builder": "@angular-devkit/build-angular:browser",
          "options": {
            "outputPath": "dist",
            "index": "src/index.html",
            "main": "src/main.ts",
            "polyfills": ["zone.js"],
            "tsConfig": "tsconfig.app.json"
          }
        },
        "serve": {
          "builder": "@angular-devkit/build-angular:dev-server",
          "options": {
            "buildTarget": "app:build",
            "host": "0.0.0.0",
            "port": 4200
          }
        }
      }
    }
  }
}"""

TSCONFIG_APP_JSON = """{
  "extends": "./tsconfig.json",
  "compilerOptions": {
    "outDir": "./out-tsc/app",
    "types": []
  },
  "files": ["src/main.ts"],
  "include": ["src/**/*.d.ts"]
}"""

# =============================================================================
# DEFAULT FILE TEMPLATES - JAVA/SPRING BOOT
# =============================================================================

APPLICATION_PROPERTIES = """# Server Configuration
server.port=8080
server.servlet.context-path=/api

# Database Configuration (H2 for development)
spring.datasource.url=jdbc:h2:mem:testdb
spring.datasource.driverClassName=org.h2.Driver
spring.datasource.username=sa
spring.datasource.password=
spring.h2.console.enabled=true

# JPA Configuration
spring.jpa.hibernate.ddl-auto=update
spring.jpa.show-sql=true

# Logging
logging.level.root=INFO
logging.level.com.example=DEBUG
"""

MAVEN_WRAPPER_PROPERTIES = """distributionUrl=https://repo.maven.apache.org/maven2/org/apache/maven/apache-maven/3.9.6/apache-maven-3.9.6-bin.zip
wrapperUrl=https://repo.maven.apache.org/maven2/org/apache/maven/wrapper/maven-wrapper/3.2.0/maven-wrapper-3.2.0.jar
"""

# =============================================================================
# DEFAULT FILE TEMPLATES - BLOCKCHAIN
# =============================================================================

HARDHAT_CONFIG_JS = """require("@nomicfoundation/hardhat-toolbox");

/** @type import('hardhat/config').HardhatUserConfig */
module.exports = {
  solidity: "0.8.19",
  networks: {
    hardhat: {
      chainId: 1337
    },
    localhost: {
      url: "http://127.0.0.1:8545"
    }
  },
  paths: {
    sources: "./contracts",
    tests: "./test",
    cache: "./cache",
    artifacts: "./artifacts"
  }
};
"""

TRUFFLE_CONFIG_JS = """module.exports = {
  networks: {
    development: {
      host: "127.0.0.1",
      port: 8545,
      network_id: "*"
    }
  },
  compilers: {
    solc: {
      version: "0.8.19"
    }
  }
};
"""

# =============================================================================
# DEFAULT FILE TEMPLATES - AI/ML
# =============================================================================

JUPYTER_CONFIG = """{
  "NotebookApp": {
    "ip": "0.0.0.0",
    "port": 8888,
    "open_browser": false,
    "allow_root": true,
    "token": ""
  }
}"""

# =============================================================================
# DEFAULT FILE TEMPLATES - GO
# =============================================================================

GO_MOD_TEMPLATE = """module app

go 1.21
"""

GO_MAIN_TEMPLATE = """package main

import (
    "fmt"
    "net/http"
)

func main() {
    http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
        fmt.Fprintf(w, "Hello, World!")
    })

    fmt.Println("Server starting on :8080")
    http.ListenAndServe(":8080", nil)
}
"""

# =============================================================================
# DEFAULT FILE TEMPLATES - RUST
# =============================================================================

CARGO_TOML_TEMPLATE = """[package]
name = "app"
version = "0.1.0"
edition = "2021"

[dependencies]
actix-web = "4"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
"""


class TechnologyValidator:
    """
    Comprehensive validator for all supported technologies.

    Validates and auto-fixes missing files before build.
    """

    def __init__(self):
        self.file_reader: Optional[Callable] = None
        self.file_writer: Optional[Callable] = None

    def validate_and_fix(
        self,
        project_path: str,
        file_reader: Callable,
        file_writer: Callable
    ) -> ValidationResult:
        """
        Validate project and auto-fix missing files.

        Args:
            project_path: Path to project root
            file_reader: Function to read files (for sandbox support)
            file_writer: Function to write files (for sandbox support)

        Returns:
            ValidationResult with errors, warnings, and files created/fixed
        """
        self.file_reader = file_reader
        self.file_writer = file_writer

        result = ValidationResult()

        # Detect project type(s) - check both root and subdirectories
        detections = self._detect_technologies(project_path)

        logger.info(f"[TechnologyValidator] Detected technologies: {detections}")

        # Validate each detected technology
        if detections.get("react_vite"):
            self._validate_react_vite(detections["react_vite"], result)

        if detections.get("angular"):
            self._validate_angular(detections["angular"], result)

        if detections.get("vue"):
            self._validate_vue(detections["vue"], result)

        if detections.get("python"):
            self._validate_python(detections["python"], result)

        if detections.get("python_ml"):
            self._validate_python_ml(detections["python_ml"], result)

        if detections.get("java"):
            self._validate_java(detections["java"], result)

        if detections.get("go"):
            self._validate_go(detections["go"], result)

        if detections.get("rust"):
            self._validate_rust(detections["rust"], result)

        if detections.get("blockchain"):
            self._validate_blockchain(detections["blockchain"], result)

        if detections.get("node"):
            self._validate_node(detections["node"], result)

        # Validate Docker files if present
        if self._check_exists(project_path, "docker-compose.yml") or \
           self._check_exists(project_path, "docker-compose.yaml"):
            self._validate_docker_compose(project_path, result)

        # Set overall validity
        result.is_valid = len(result.errors) == 0

        return result

    def _detect_technologies(self, project_path: str) -> Dict[str, str]:
        """Detect all technologies in the project"""
        detections = {}

        # Check root and common subdirectories
        paths_to_check = [
            project_path,
            os.path.join(project_path, "frontend"),
            os.path.join(project_path, "backend"),
            os.path.join(project_path, "web"),
            os.path.join(project_path, "api"),
            os.path.join(project_path, "app"),
            os.path.join(project_path, "client"),
            os.path.join(project_path, "server"),
        ]

        for check_path in paths_to_check:
            # React/Vite detection
            if self._check_exists(check_path, "package.json"):
                pkg_content = self._read_file(check_path, "package.json")
                if pkg_content:
                    if "vite" in pkg_content or "react" in pkg_content:
                        if "react_vite" not in detections:
                            detections["react_vite"] = check_path

                    # Angular detection
                    if "@angular/core" in pkg_content:
                        if "angular" not in detections:
                            detections["angular"] = check_path

                    # Vue detection
                    if "vue" in pkg_content and "@angular" not in pkg_content:
                        if "vue" not in detections:
                            detections["vue"] = check_path

                    # Blockchain detection
                    if "hardhat" in pkg_content or "truffle" in pkg_content or \
                       "ethers" in pkg_content or "web3" in pkg_content:
                        if "blockchain" not in detections:
                            detections["blockchain"] = check_path

                    # Node.js backend detection
                    if "express" in pkg_content or "fastify" in pkg_content or \
                       "nestjs" in pkg_content or "koa" in pkg_content:
                        if "node" not in detections:
                            detections["node"] = check_path

            # Python detection
            if self._check_exists(check_path, "requirements.txt"):
                req_content = self._read_file(check_path, "requirements.txt")
                if req_content:
                    # AI/ML detection
                    ml_keywords = ["tensorflow", "torch", "pytorch", "keras", "scikit-learn",
                                   "sklearn", "pandas", "numpy", "jupyter", "notebook",
                                   "transformers", "langchain", "openai"]
                    if any(kw in req_content.lower() for kw in ml_keywords):
                        if "python_ml" not in detections:
                            detections["python_ml"] = check_path
                    else:
                        if "python" not in detections:
                            detections["python"] = check_path

            # Java detection
            if self._check_exists(check_path, "pom.xml") or \
               self._check_exists(check_path, "build.gradle") or \
               self._check_exists(check_path, "build.gradle.kts"):
                if "java" not in detections:
                    detections["java"] = check_path

            # Go detection
            if self._check_exists(check_path, "go.mod"):
                if "go" not in detections:
                    detections["go"] = check_path

            # Rust detection
            if self._check_exists(check_path, "Cargo.toml"):
                if "rust" not in detections:
                    detections["rust"] = check_path

            # Solidity detection (additional blockchain check)
            if self._check_exists(check_path, "contracts") or \
               self._check_exists(check_path, "hardhat.config.js") or \
               self._check_exists(check_path, "truffle-config.js"):
                if "blockchain" not in detections:
                    detections["blockchain"] = check_path

        return detections

    def _check_exists(self, base_path: str, rel_path: str) -> bool:
        """Check if a file exists"""
        try:
            full_path = os.path.join(base_path, rel_path)
            content = self.file_reader(full_path)
            return content is not None and len(content) > 0
        except:
            return False

    def _read_file(self, base_path: str, rel_path: str) -> Optional[str]:
        """Read file content"""
        try:
            full_path = os.path.join(base_path, rel_path)
            return self.file_reader(full_path)
        except:
            return None

    def _write_file(self, base_path: str, rel_path: str, content: str) -> bool:
        """Write file content"""
        try:
            full_path = os.path.join(base_path, rel_path)
            self.file_writer(full_path, content)
            return True
        except Exception as e:
            logger.error(f"[TechnologyValidator] Failed to write {rel_path}: {e}")
            return False

    # =========================================================================
    # REACT / VITE / TYPESCRIPT VALIDATION
    # =========================================================================

    def _validate_react_vite(self, frontend_path: str, result: ValidationResult):
        """Validate React/Vite/TypeScript project"""
        logger.info(f"[TechnologyValidator] Validating React/Vite project: {frontend_path}")

        # 1. Check package.json exists and is valid
        pkg_content = self._read_file(frontend_path, "package.json")
        if not pkg_content:
            result.errors.append("Missing package.json")
            return

        try:
            pkg_json = json.loads(pkg_content)
        except json.JSONDecodeError as e:
            result.errors.append(f"Invalid package.json: {e}")
            return

        # 2. Check for TypeScript project
        is_typescript = self._check_exists(frontend_path, "tsconfig.json")

        if is_typescript:
            # Check tsconfig.json references
            tsconfig_content = self._read_file(frontend_path, "tsconfig.json")
            if tsconfig_content and "tsconfig.node.json" in tsconfig_content:
                if not self._check_exists(frontend_path, "tsconfig.node.json"):
                    if self._write_file(frontend_path, "tsconfig.node.json", TSCONFIG_NODE_JSON):
                        result.files_created.append("tsconfig.node.json")
                    else:
                        result.errors.append("Missing tsconfig.node.json")

            # Check tsconfig.app.json if referenced
            if tsconfig_content and "tsconfig.app.json" in tsconfig_content:
                if not self._check_exists(frontend_path, "tsconfig.app.json"):
                    if self._write_file(frontend_path, "tsconfig.app.json", TSCONFIG_APP_JSON):
                        result.files_created.append("tsconfig.app.json")

        # 3. Check for Vite config
        has_vite_config = self._check_exists(frontend_path, "vite.config.ts") or \
                         self._check_exists(frontend_path, "vite.config.js") or \
                         self._check_exists(frontend_path, "vite.config.mjs")
        if not has_vite_config and "vite" in pkg_content:
            ext = "ts" if is_typescript else "js"
            if self._write_file(frontend_path, f"vite.config.{ext}", VITE_CONFIG_TS):
                result.files_created.append(f"vite.config.{ext}")

        # 4. Check for index.html
        if not self._check_exists(frontend_path, "index.html"):
            if self._write_file(frontend_path, "index.html", INDEX_HTML):
                result.files_created.append("index.html")

        # 5. Check Tailwind setup
        deps = {**pkg_json.get("dependencies", {}), **pkg_json.get("devDependencies", {})}
        if "tailwindcss" in deps:
            # Need postcss.config.js
            if not self._check_exists(frontend_path, "postcss.config.js") and \
               not self._check_exists(frontend_path, "postcss.config.cjs") and \
               not self._check_exists(frontend_path, "postcss.config.mjs"):
                if self._write_file(frontend_path, "postcss.config.js", POSTCSS_CONFIG_JS):
                    result.files_created.append("postcss.config.js")

            # Need tailwind.config.js
            if not self._check_exists(frontend_path, "tailwind.config.js") and \
               not self._check_exists(frontend_path, "tailwind.config.ts"):
                if self._write_file(frontend_path, "tailwind.config.js", TAILWIND_CONFIG_JS):
                    result.files_created.append("tailwind.config.js")

            # Need CSS with @tailwind directives
            if not self._check_exists(frontend_path, "src/index.css"):
                if self._write_file(frontend_path, "src/index.css", INDEX_CSS):
                    result.files_created.append("src/index.css")

        # 6. Fix Dockerfile issues
        self._fix_dockerfile_in_path(frontend_path, result)

    # =========================================================================
    # ANGULAR VALIDATION
    # =========================================================================

    def _validate_angular(self, angular_path: str, result: ValidationResult):
        """Validate Angular project"""
        logger.info(f"[TechnologyValidator] Validating Angular project: {angular_path}")

        # 1. Check angular.json exists
        if not self._check_exists(angular_path, "angular.json"):
            if self._write_file(angular_path, "angular.json", ANGULAR_JSON_MINIMAL):
                result.files_created.append("angular.json")
            else:
                result.errors.append("Missing angular.json")

        # 2. Check tsconfig files
        if self._check_exists(angular_path, "tsconfig.json"):
            tsconfig_content = self._read_file(angular_path, "tsconfig.json")
            if tsconfig_content and "tsconfig.app.json" in tsconfig_content:
                if not self._check_exists(angular_path, "tsconfig.app.json"):
                    if self._write_file(angular_path, "tsconfig.app.json", TSCONFIG_APP_JSON):
                        result.files_created.append("tsconfig.app.json")

        # 3. Fix Dockerfile issues
        self._fix_dockerfile_in_path(angular_path, result)

    # =========================================================================
    # VUE VALIDATION
    # =========================================================================

    def _validate_vue(self, vue_path: str, result: ValidationResult):
        """Validate Vue.js project"""
        logger.info(f"[TechnologyValidator] Validating Vue.js project: {vue_path}")

        # Check for Vite config (Vue 3 with Vite)
        has_vite_config = self._check_exists(vue_path, "vite.config.ts") or \
                         self._check_exists(vue_path, "vite.config.js")

        pkg_content = self._read_file(vue_path, "package.json")
        if pkg_content and "vite" in pkg_content and not has_vite_config:
            vue_vite_config = """import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    port: 5173,
  },
})"""
            if self._write_file(vue_path, "vite.config.js", vue_vite_config):
                result.files_created.append("vite.config.js")

        # Fix Dockerfile issues
        self._fix_dockerfile_in_path(vue_path, result)

    # =========================================================================
    # PYTHON VALIDATION
    # =========================================================================

    def _validate_python(self, backend_path: str, result: ValidationResult):
        """Validate Python project"""
        logger.info(f"[TechnologyValidator] Validating Python project: {backend_path}")

        # 1. Check requirements.txt
        req_content = self._read_file(backend_path, "requirements.txt")
        if not req_content:
            result.errors.append("Missing requirements.txt")
            return

        # 2. Check for invalid package names (python- prefix)
        self._fix_python_requirements(backend_path, req_content, result)

        # 3. Check for main entry point
        has_main = self._check_exists(backend_path, "main.py") or \
                   self._check_exists(backend_path, "app.py") or \
                   self._check_exists(backend_path, "app/__init__.py") or \
                   self._check_exists(backend_path, "manage.py")  # Django
        if not has_main:
            result.warnings.append("No main.py or app.py found")

        # 4. Fix Dockerfile issues
        self._fix_dockerfile_in_path(backend_path, result)

    # =========================================================================
    # PYTHON AI/ML VALIDATION
    # =========================================================================

    def _validate_python_ml(self, ml_path: str, result: ValidationResult):
        """Validate Python AI/ML project"""
        logger.info(f"[TechnologyValidator] Validating AI/ML project: {ml_path}")

        # 1. Check requirements.txt and fix package names
        req_content = self._read_file(ml_path, "requirements.txt")
        if req_content:
            self._fix_python_requirements(ml_path, req_content, result)

        # 2. Check for Jupyter notebook support
        if "jupyter" in (req_content or "").lower() or "notebook" in (req_content or "").lower():
            # May need jupyter config
            pass

        # 3. Check for common ML project structure
        # notebooks/, models/, data/, src/
        dirs_to_check = ["notebooks", "models", "data", "src"]
        for dir_name in dirs_to_check:
            if not self._check_exists(ml_path, dir_name):
                result.warnings.append(f"Consider creating {dir_name}/ directory for ML project organization")
                break  # Only warn once

        # 4. Fix Dockerfile issues
        self._fix_dockerfile_in_path(ml_path, result)

    # =========================================================================
    # JAVA VALIDATION
    # =========================================================================

    def _validate_java(self, java_path: str, result: ValidationResult):
        """Validate Java project"""
        logger.info(f"[TechnologyValidator] Validating Java project: {java_path}")

        is_maven = self._check_exists(java_path, "pom.xml")
        is_gradle = self._check_exists(java_path, "build.gradle") or \
                    self._check_exists(java_path, "build.gradle.kts")

        if is_maven:
            # Check for Maven wrapper
            if not self._check_exists(java_path, ".mvn/wrapper/maven-wrapper.properties"):
                # Create .mvn/wrapper directory structure
                if self._write_file(java_path, ".mvn/wrapper/maven-wrapper.properties", MAVEN_WRAPPER_PROPERTIES):
                    result.files_created.append(".mvn/wrapper/maven-wrapper.properties")

            # Check for application.properties
            if not self._check_exists(java_path, "src/main/resources/application.properties") and \
               not self._check_exists(java_path, "src/main/resources/application.yml"):
                if self._write_file(java_path, "src/main/resources/application.properties", APPLICATION_PROPERTIES):
                    result.files_created.append("src/main/resources/application.properties")

        if is_gradle:
            # Check for gradle wrapper
            if not self._check_exists(java_path, "gradle/wrapper/gradle-wrapper.properties"):
                result.warnings.append("Missing Gradle wrapper - run 'gradle wrapper' to generate")

        # Fix Dockerfile issues
        self._fix_dockerfile_in_path(java_path, result)

    # =========================================================================
    # GO VALIDATION
    # =========================================================================

    def _validate_go(self, go_path: str, result: ValidationResult):
        """Validate Go project"""
        logger.info(f"[TechnologyValidator] Validating Go project: {go_path}")

        # 1. Check go.mod exists
        if not self._check_exists(go_path, "go.mod"):
            if self._write_file(go_path, "go.mod", GO_MOD_TEMPLATE):
                result.files_created.append("go.mod")

        # 2. Check for main.go
        if not self._check_exists(go_path, "main.go") and \
           not self._check_exists(go_path, "cmd/main.go"):
            if self._write_file(go_path, "main.go", GO_MAIN_TEMPLATE):
                result.files_created.append("main.go")

        # Fix Dockerfile issues
        self._fix_dockerfile_in_path(go_path, result)

    # =========================================================================
    # RUST VALIDATION
    # =========================================================================

    def _validate_rust(self, rust_path: str, result: ValidationResult):
        """Validate Rust project"""
        logger.info(f"[TechnologyValidator] Validating Rust project: {rust_path}")

        # 1. Check Cargo.toml exists
        if not self._check_exists(rust_path, "Cargo.toml"):
            if self._write_file(rust_path, "Cargo.toml", CARGO_TOML_TEMPLATE):
                result.files_created.append("Cargo.toml")

        # 2. Check for src/main.rs
        if not self._check_exists(rust_path, "src/main.rs"):
            rust_main = """fn main() {
    println!("Hello, world!");
}
"""
            if self._write_file(rust_path, "src/main.rs", rust_main):
                result.files_created.append("src/main.rs")

        # Fix Dockerfile issues
        self._fix_dockerfile_in_path(rust_path, result)

    # =========================================================================
    # BLOCKCHAIN VALIDATION
    # =========================================================================

    def _validate_blockchain(self, blockchain_path: str, result: ValidationResult):
        """Validate Blockchain/Web3 project"""
        logger.info(f"[TechnologyValidator] Validating Blockchain project: {blockchain_path}")

        pkg_content = self._read_file(blockchain_path, "package.json")

        # Detect if Hardhat or Truffle
        is_hardhat = pkg_content and "hardhat" in pkg_content
        is_truffle = pkg_content and "truffle" in pkg_content

        if is_hardhat:
            # Check for hardhat.config.js
            if not self._check_exists(blockchain_path, "hardhat.config.js") and \
               not self._check_exists(blockchain_path, "hardhat.config.ts"):
                if self._write_file(blockchain_path, "hardhat.config.js", HARDHAT_CONFIG_JS):
                    result.files_created.append("hardhat.config.js")

            # Check for contracts directory
            if not self._check_exists(blockchain_path, "contracts"):
                result.warnings.append("Missing contracts/ directory for Solidity files")

        if is_truffle:
            # Check for truffle-config.js
            if not self._check_exists(blockchain_path, "truffle-config.js"):
                if self._write_file(blockchain_path, "truffle-config.js", TRUFFLE_CONFIG_JS):
                    result.files_created.append("truffle-config.js")

        # Fix Dockerfile issues
        self._fix_dockerfile_in_path(blockchain_path, result)

    # =========================================================================
    # NODE.JS BACKEND VALIDATION
    # =========================================================================

    def _validate_node(self, node_path: str, result: ValidationResult):
        """Validate Node.js backend project"""
        logger.info(f"[TechnologyValidator] Validating Node.js project: {node_path}")

        # Check for TypeScript config if using TS
        pkg_content = self._read_file(node_path, "package.json")
        if pkg_content and "typescript" in pkg_content:
            if not self._check_exists(node_path, "tsconfig.json"):
                node_tsconfig = """{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["ES2020"],
    "outDir": "./dist",
    "rootDir": "./src",
    "strict": true,
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true,
    "resolveJsonModule": true
  },
  "include": ["src/**/*"],
  "exclude": ["node_modules", "dist"]
}"""
                if self._write_file(node_path, "tsconfig.json", node_tsconfig):
                    result.files_created.append("tsconfig.json")

        # Fix Dockerfile issues
        self._fix_dockerfile_in_path(node_path, result)

    # =========================================================================
    # DOCKER COMPOSE VALIDATION
    # =========================================================================

    def _validate_docker_compose(self, project_path: str, result: ValidationResult):
        """Validate Docker Compose configuration"""
        logger.info(f"[TechnologyValidator] Validating Docker Compose: {project_path}")

        compose_content = self._read_file(project_path, "docker-compose.yml")
        if not compose_content:
            compose_content = self._read_file(project_path, "docker-compose.yaml")

        if not compose_content:
            return

        # Check for referenced Dockerfiles
        dockerfile_refs = re.findall(r'dockerfile:\s*(\S+)', compose_content)
        context_refs = re.findall(r'context:\s*(\S+)', compose_content)

        for i, dockerfile in enumerate(dockerfile_refs):
            context = context_refs[i] if i < len(context_refs) else "."
            dockerfile_path = os.path.join(context, dockerfile)
            dockerfile_path = dockerfile_path.replace("./", "")

            if not self._check_exists(project_path, dockerfile_path):
                result.errors.append(f"Missing Dockerfile: {dockerfile_path}")

        # Fix Dockerfiles in all contexts
        for context in context_refs:
            context_clean = context.replace("./", "").strip()
            context_path = os.path.join(project_path, context_clean) if context_clean else project_path
            self._fix_dockerfile_in_path(context_path, result)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _fix_python_requirements(self, base_path: str, req_content: str, result: ValidationResult):
        """Fix invalid Python package names in requirements.txt"""
        invalid_packages = []
        valid_python_prefixed = ["python-dotenv", "python-dateutil", "python-multipart",
                                  "python-jose", "python-magic", "python-slugify"]

        for line in req_content.split("\n"):
            line = line.strip()
            if line.startswith("python-") and not any(line.startswith(p) for p in valid_python_prefixed):
                # Extract package name
                pkg_name = line.split("==")[0].split(">=")[0].split("<=")[0].split(">")[0].split("<")[0].split("[")[0]
                correct_name = pkg_name.replace("python-", "")
                invalid_packages.append((pkg_name, correct_name))

        if invalid_packages:
            # Fix the requirements.txt
            fixed_content = req_content
            for wrong, correct in invalid_packages:
                fixed_content = fixed_content.replace(wrong, correct)

            if self._write_file(base_path, "requirements.txt", fixed_content):
                result.files_fixed.append(f"requirements.txt (fixed {len(invalid_packages)} package names)")

    def _fix_dockerfile_in_path(self, base_path: str, result: ValidationResult):
        """Fix Dockerfile issues in the given path"""
        dockerfile_content = self._read_file(base_path, "Dockerfile")
        if not dockerfile_content:
            return

        original_content = dockerfile_content
        fixes = []

        # Check if build step exists
        has_npm_build = "npm run build" in dockerfile_content or \
                        "yarn build" in dockerfile_content or \
                        "pnpm build" in dockerfile_content

        # 1. Replace npm ci with npm install
        if "npm ci" in dockerfile_content:
            dockerfile_content = dockerfile_content.replace("npm ci", "npm install")
            fixes.append("npm ci → npm install")

        # 2. Handle --only=production and --omit=dev
        if has_npm_build:
            # Remove production-only flags if build step exists
            if "--only=production" in dockerfile_content:
                dockerfile_content = re.sub(r'\s*--only=production\s*', ' ', dockerfile_content)
                fixes.append("Removed --only=production")
            if "--omit=dev" in dockerfile_content:
                dockerfile_content = re.sub(r'\s*--omit=dev\s*', ' ', dockerfile_content)
                fixes.append("Removed --omit=dev")
        else:
            # Just modernize the flag
            if "--only=production" in dockerfile_content:
                dockerfile_content = dockerfile_content.replace("--only=production", "--omit=dev")
                fixes.append("--only=production → --omit=dev")

        # Write back if changed
        if dockerfile_content != original_content:
            if self._write_file(base_path, "Dockerfile", dockerfile_content):
                rel_path = os.path.basename(base_path) or "root"
                result.files_fixed.append(f"{rel_path}/Dockerfile ({', '.join(fixes)})")


# Singleton instance
technology_validator = TechnologyValidator()
