"""
Project Analyzer - Scans and analyzes project codebase for dynamic document generation

This module analyzes the actual project structure, code, models, APIs, and components
to generate project-specific IEEE documentation.
"""

import os
import re
import json
import ast
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class APIEndpoint:
    """Represents an API endpoint"""
    method: str  # GET, POST, PUT, DELETE
    path: str
    description: str = ""
    parameters: List[Dict] = field(default_factory=list)
    request_body: Dict = field(default_factory=dict)
    response: Dict = field(default_factory=dict)
    module: str = ""


@dataclass
class DatabaseModel:
    """Represents a database model/table"""
    name: str
    fields: List[Dict] = field(default_factory=list)  # {name, type, constraints}
    relationships: List[Dict] = field(default_factory=list)
    description: str = ""


@dataclass
class Component:
    """Represents a UI component"""
    name: str
    file_path: str
    type: str = "component"  # component, page, layout
    props: List[Dict] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    description: str = ""


@dataclass
class FunctionalRequirement:
    """Represents a functional requirement derived from code"""
    id: str
    name: str
    description: str
    module: str
    priority: str = "Medium"
    source: str = ""  # file/function where this was derived from
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    actors: List[str] = field(default_factory=list)


@dataclass
class UseCase:
    """Represents a use case derived from code"""
    id: str
    name: str
    actor: str
    description: str
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    main_flow: List[str] = field(default_factory=list)
    alternative_flows: List[Dict] = field(default_factory=list)
    related_requirements: List[str] = field(default_factory=list)


@dataclass
class TestCase:
    """Represents a test case derived from code"""
    id: str
    name: str
    module: str
    description: str
    preconditions: List[str] = field(default_factory=list)
    steps: List[str] = field(default_factory=list)
    expected_result: str = ""
    priority: str = "Medium"
    type: str = "Functional"  # Functional, Integration, Unit, API


@dataclass
class ProjectAnalysis:
    """Complete project analysis result"""
    project_name: str
    project_type: str  # web, api, cli, mobile, etc.
    tech_stack: Dict[str, str] = field(default_factory=dict)

    # Structure
    directories: List[str] = field(default_factory=list)
    files: Dict[str, List[str]] = field(default_factory=dict)  # {extension: [files]}

    # Backend
    models: List[DatabaseModel] = field(default_factory=list)
    api_endpoints: List[APIEndpoint] = field(default_factory=list)
    services: List[Dict] = field(default_factory=list)
    middlewares: List[str] = field(default_factory=list)

    # Frontend
    components: List[Component] = field(default_factory=list)
    pages: List[Component] = field(default_factory=list)
    routes: List[Dict] = field(default_factory=list)

    # Dependencies
    dependencies: Dict[str, str] = field(default_factory=dict)
    dev_dependencies: Dict[str, str] = field(default_factory=dict)

    # Derived requirements
    functional_requirements: List[FunctionalRequirement] = field(default_factory=list)
    use_cases: List[UseCase] = field(default_factory=list)
    test_cases: List[TestCase] = field(default_factory=list)

    # Actors
    actors: List[Dict] = field(default_factory=list)

    # Modules
    modules: List[Dict] = field(default_factory=list)


class ProjectAnalyzer:
    """Analyzes project codebase to extract structure and generate documentation"""

    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.analysis = ProjectAnalysis(
            project_name=self.project_path.name,
            project_type="unknown"
        )

        # Patterns for different frameworks
        self.patterns = {
            'python_model': r'class\s+(\w+)\s*\([^)]*(?:Model|Base|db\.Model)[^)]*\)',
            'python_route': r'@(?:app|router|bp)\.(?:route|get|post|put|delete|patch)\s*\([\'"]([^\'"]+)[\'"]',
            'python_function': r'(?:async\s+)?def\s+(\w+)\s*\([^)]*\)',
            'python_class': r'class\s+(\w+)\s*(?:\([^)]*\))?:',
            'js_component': r'(?:function|const|class)\s+(\w+).*(?:React|Component|=>)',
            'js_route': r'(?:router|app)\.(get|post|put|delete|patch)\s*\([\'"]([^\'"]+)[\'"]',
            'sql_table': r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?',
        }

        # File type mappings
        self.file_types = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx', '.ts', '.tsx'],
            'html': ['.html', '.htm'],
            'css': ['.css', '.scss', '.sass', '.less'],
            'sql': ['.sql'],
            'config': ['.json', '.yaml', '.yml', '.toml', '.env'],
            'docs': ['.md', '.rst', '.txt'],
        }

    def analyze(self) -> ProjectAnalysis:
        """Run complete project analysis"""
        print(f"Analyzing project: {self.project_path}")

        # Step 1: Scan directory structure
        self._scan_structure()

        # Step 2: Detect project type and tech stack
        self._detect_tech_stack()

        # Step 3: Parse dependencies
        self._parse_dependencies()

        # Step 4: Analyze backend code
        self._analyze_backend()

        # Step 5: Analyze frontend code
        self._analyze_frontend()

        # Step 6: Extract database models
        self._extract_models()

        # Step 7: Extract API endpoints
        self._extract_api_endpoints()

        # Step 8: Generate functional requirements
        self._generate_requirements()

        # Step 9: Generate use cases
        self._generate_use_cases()

        # Step 10: Generate test cases
        self._generate_test_cases()

        # Step 11: Identify actors
        self._identify_actors()

        # Step 12: Identify modules
        self._identify_modules()

        return self.analysis

    def _scan_structure(self):
        """Scan project directory structure"""
        ignore_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv',
                       'dist', 'build', '.next', '.nuxt', 'coverage', '.idea'}
        ignore_files = {'.gitignore', '.env', '.DS_Store'}

        for root, dirs, files in os.walk(self.project_path):
            # Filter out ignored directories
            dirs[:] = [d for d in dirs if d not in ignore_dirs]

            rel_path = Path(root).relative_to(self.project_path)
            if str(rel_path) != '.':
                self.analysis.directories.append(str(rel_path))

            for file in files:
                if file in ignore_files:
                    continue

                ext = Path(file).suffix.lower()
                if ext not in self.analysis.files:
                    self.analysis.files[ext] = []

                file_path = str(rel_path / file) if str(rel_path) != '.' else file
                self.analysis.files[ext].append(file_path)

    def _detect_tech_stack(self):
        """Detect project type and technology stack"""
        files = self.analysis.files

        # Check for package.json (Node.js/JavaScript)
        if '.json' in files and any('package.json' in f for f in files['.json']):
            self._parse_package_json()

        # Check for requirements.txt or pyproject.toml (Python)
        if '.txt' in files and any('requirements' in f for f in files.get('.txt', [])):
            self.analysis.tech_stack['backend'] = 'Python'
            self._parse_requirements_txt()

        if '.toml' in files and any('pyproject.toml' in f for f in files.get('.toml', [])):
            self.analysis.tech_stack['backend'] = 'Python'

        # Detect frontend framework
        if '.jsx' in files or '.tsx' in files:
            self.analysis.tech_stack['frontend'] = 'React'
        elif any('vue' in str(f).lower() for ext in files for f in files.get(ext, [])):
            self.analysis.tech_stack['frontend'] = 'Vue.js'
        elif any('angular' in str(f).lower() for ext in files for f in files.get(ext, [])):
            self.analysis.tech_stack['frontend'] = 'Angular'

        # Detect backend framework
        py_files = files.get('.py', [])
        if py_files:
            for py_file in py_files:
                try:
                    content = self._read_file(py_file)
                    if 'fastapi' in content.lower():
                        self.analysis.tech_stack['backend_framework'] = 'FastAPI'
                        break
                    elif 'flask' in content.lower():
                        self.analysis.tech_stack['backend_framework'] = 'Flask'
                        break
                    elif 'django' in content.lower():
                        self.analysis.tech_stack['backend_framework'] = 'Django'
                        break
                except:
                    pass

        # Detect database
        all_content = ""
        for ext in ['.py', '.js', '.ts', '.env', '.yaml', '.yml']:
            for f in files.get(ext, [])[:10]:  # Check first 10 files
                try:
                    all_content += self._read_file(f)
                except:
                    pass

        if 'postgresql' in all_content.lower() or 'postgres' in all_content.lower():
            self.analysis.tech_stack['database'] = 'PostgreSQL'
        elif 'mongodb' in all_content.lower() or 'mongoose' in all_content.lower():
            self.analysis.tech_stack['database'] = 'MongoDB'
        elif 'mysql' in all_content.lower():
            self.analysis.tech_stack['database'] = 'MySQL'
        elif 'sqlite' in all_content.lower():
            self.analysis.tech_stack['database'] = 'SQLite'

        # Determine project type
        if self.analysis.tech_stack.get('frontend') and self.analysis.tech_stack.get('backend'):
            self.analysis.project_type = 'Full-Stack Web Application'
        elif self.analysis.tech_stack.get('frontend'):
            self.analysis.project_type = 'Frontend Web Application'
        elif self.analysis.tech_stack.get('backend'):
            self.analysis.project_type = 'Backend API Service'
        elif '.py' in files:
            self.analysis.project_type = 'Python Application'
        else:
            self.analysis.project_type = 'Software Application'

    def _parse_package_json(self):
        """Parse package.json for dependencies"""
        try:
            package_path = self.project_path / 'package.json'
            if not package_path.exists():
                # Check in subdirectories
                for subdir in ['frontend', 'client', 'web']:
                    package_path = self.project_path / subdir / 'package.json'
                    if package_path.exists():
                        break

            if package_path.exists():
                with open(package_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.analysis.dependencies.update(data.get('dependencies', {}))
                self.analysis.dev_dependencies.update(data.get('devDependencies', {}))

                # Detect frameworks from dependencies
                deps = list(self.analysis.dependencies.keys())
                if 'react' in deps:
                    self.analysis.tech_stack['frontend'] = 'React'
                if 'next' in deps:
                    self.analysis.tech_stack['frontend_framework'] = 'Next.js'
                if 'vue' in deps:
                    self.analysis.tech_stack['frontend'] = 'Vue.js'
                if 'express' in deps:
                    self.analysis.tech_stack['backend_framework'] = 'Express.js'
                if 'nestjs' in deps or '@nestjs/core' in deps:
                    self.analysis.tech_stack['backend_framework'] = 'NestJS'
                if 'tailwindcss' in deps or 'tailwindcss' in self.analysis.dev_dependencies:
                    self.analysis.tech_stack['css'] = 'Tailwind CSS'
        except Exception as e:
            print(f"Error parsing package.json: {e}")

    def _parse_requirements_txt(self):
        """Parse requirements.txt for Python dependencies"""
        try:
            req_path = self.project_path / 'requirements.txt'
            if not req_path.exists():
                for subdir in ['backend', 'server', 'api']:
                    req_path = self.project_path / subdir / 'requirements.txt'
                    if req_path.exists():
                        break

            if req_path.exists():
                with open(req_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#'):
                            # Parse package==version or package>=version
                            match = re.match(r'^([a-zA-Z0-9_-]+)', line)
                            if match:
                                pkg = match.group(1)
                                self.analysis.dependencies[pkg] = line
        except Exception as e:
            print(f"Error parsing requirements.txt: {e}")

    def _parse_dependencies(self):
        """Parse all dependency files"""
        # Already handled in detect_tech_stack
        pass

    def _read_file(self, relative_path: str) -> str:
        """Read file content"""
        full_path = self.project_path / relative_path
        try:
            with open(full_path, 'r', encoding='utf-8') as f:
                return f.read()
        except:
            return ""

    def _analyze_backend(self):
        """Analyze backend code"""
        py_files = self.analysis.files.get('.py', [])

        for py_file in py_files:
            content = self._read_file(py_file)

            # Find services/business logic
            if 'service' in py_file.lower():
                classes = re.findall(self.patterns['python_class'], content)
                for cls in classes:
                    self.analysis.services.append({
                        'name': cls,
                        'file': py_file,
                        'methods': re.findall(self.patterns['python_function'], content)
                    })

            # Find middlewares
            if 'middleware' in py_file.lower():
                self.analysis.middlewares.append(py_file)

    def _analyze_frontend(self):
        """Analyze frontend code"""
        jsx_files = self.analysis.files.get('.jsx', []) + self.analysis.files.get('.tsx', [])
        js_files = self.analysis.files.get('.js', []) + self.analysis.files.get('.ts', [])

        for file in jsx_files + js_files:
            content = self._read_file(file)
            file_lower = file.lower()

            # Determine component type
            if 'page' in file_lower or 'pages/' in file_lower:
                comp_type = 'page'
            elif 'layout' in file_lower:
                comp_type = 'layout'
            else:
                comp_type = 'component'

            # Extract component name from file
            comp_name = Path(file).stem
            if comp_name in ['index', 'page']:
                comp_name = Path(file).parent.name

            # Find React component definitions
            component_patterns = [
                r'(?:export\s+)?(?:default\s+)?function\s+(\w+)',
                r'(?:export\s+)?const\s+(\w+)\s*[=:]\s*(?:\([^)]*\)|)\s*=>',
                r'(?:export\s+)?class\s+(\w+)\s+extends\s+(?:React\.)?Component',
            ]

            comp_names = []
            for pattern in component_patterns:
                matches = re.findall(pattern, content)
                comp_names.extend(matches)

            if comp_names:
                comp_name = comp_names[0] if comp_names[0] not in ['default', 'function'] else comp_name

            # Extract imports/dependencies
            imports = re.findall(r'import\s+.*?\s+from\s+[\'"]([^\'"]+)[\'"]', content)

            component = Component(
                name=comp_name.replace('-', ' ').replace('_', ' ').title().replace(' ', ''),
                file_path=file,
                type=comp_type,
                dependencies=imports
            )

            if comp_type == 'page':
                self.analysis.pages.append(component)
            else:
                self.analysis.components.append(component)

    def _extract_models(self):
        """Extract database models from code"""
        py_files = self.analysis.files.get('.py', [])

        for py_file in py_files:
            if 'model' in py_file.lower() or 'schema' in py_file.lower():
                content = self._read_file(py_file)

                # SQLAlchemy models
                model_matches = re.findall(
                    r'class\s+(\w+)\s*\([^)]*(?:Base|Model|db\.Model)[^)]*\):\s*\n((?:\s+.*\n)*)',
                    content
                )

                for model_name, model_body in model_matches:
                    fields = []

                    # Extract Column definitions
                    column_matches = re.findall(
                        r'(\w+)\s*=\s*(?:Column|db\.Column)\s*\(\s*(\w+)',
                        model_body
                    )

                    for field_name, field_type in column_matches:
                        if field_name != '__tablename__':
                            fields.append({
                                'name': field_name,
                                'type': field_type,
                                'constraints': []
                            })

                    # Extract relationships
                    relationships = []
                    rel_matches = re.findall(
                        r'(\w+)\s*=\s*relationship\s*\([\'"](\w+)[\'"]',
                        model_body
                    )
                    for rel_name, rel_target in rel_matches:
                        relationships.append({
                            'name': rel_name,
                            'target': rel_target,
                            'type': 'relationship'
                        })

                    self.analysis.models.append(DatabaseModel(
                        name=model_name,
                        fields=fields,
                        relationships=relationships
                    ))

                # Pydantic models
                pydantic_matches = re.findall(
                    r'class\s+(\w+)\s*\((?:BaseModel|Schema)[^)]*\):\s*\n((?:\s+.*\n)*)',
                    content
                )

                for model_name, model_body in pydantic_matches:
                    fields = []
                    field_matches = re.findall(
                        r'(\w+)\s*:\s*([^\n=]+)',
                        model_body
                    )
                    for field_name, field_type in field_matches:
                        if not field_name.startswith('_') and 'class' not in field_name:
                            fields.append({
                                'name': field_name.strip(),
                                'type': field_type.strip().split('=')[0].strip(),
                                'constraints': []
                            })

                    if fields:
                        self.analysis.models.append(DatabaseModel(
                            name=model_name,
                            fields=fields
                        ))

        # Also check TypeScript/JavaScript files for models
        ts_files = self.analysis.files.get('.ts', []) + self.analysis.files.get('.js', [])
        for ts_file in ts_files:
            if 'model' in ts_file.lower() or 'schema' in ts_file.lower() or 'entity' in ts_file.lower():
                content = self._read_file(ts_file)

                # Mongoose schemas
                mongoose_matches = re.findall(
                    r'(?:const|let)\s+(\w+)Schema\s*=\s*new\s+(?:mongoose\.)?Schema\s*\(\s*\{([^}]+)\}',
                    content, re.DOTALL
                )

                for model_name, schema_body in mongoose_matches:
                    fields = []
                    field_matches = re.findall(r'(\w+)\s*:\s*\{?\s*type\s*:\s*(\w+)', schema_body)
                    for field_name, field_type in field_matches:
                        fields.append({
                            'name': field_name,
                            'type': field_type,
                            'constraints': []
                        })

                    if fields:
                        self.analysis.models.append(DatabaseModel(
                            name=model_name,
                            fields=fields
                        ))

    def _extract_api_endpoints(self):
        """Extract API endpoints from code"""
        # Python (FastAPI, Flask, Django)
        py_files = self.analysis.files.get('.py', [])

        for py_file in py_files:
            content = self._read_file(py_file)

            # FastAPI routes
            fastapi_routes = re.findall(
                r'@(?:app|router)\.(\w+)\s*\([\'"]([^\'"]+)[\'"](?:[^)]*response_model\s*=\s*(\w+))?[^)]*\)\s*\n(?:async\s+)?def\s+(\w+)',
                content
            )

            for method, path, response_model, func_name in fastapi_routes:
                self.analysis.api_endpoints.append(APIEndpoint(
                    method=method.upper(),
                    path=path,
                    description=self._func_name_to_description(func_name),
                    module=py_file,
                    response={'model': response_model} if response_model else {}
                ))

            # Flask routes
            flask_routes = re.findall(
                r'@(?:app|bp|blueprint)\.route\s*\([\'"]([^\'"]+)[\'"](?:[^)]*methods\s*=\s*\[([^\]]+)\])?[^)]*\)\s*\ndef\s+(\w+)',
                content
            )

            for path, methods, func_name in flask_routes:
                method_list = re.findall(r'[\'"](\w+)[\'"]', methods) if methods else ['GET']
                for method in method_list:
                    self.analysis.api_endpoints.append(APIEndpoint(
                        method=method.upper(),
                        path=path,
                        description=self._func_name_to_description(func_name),
                        module=py_file
                    ))

        # JavaScript/TypeScript (Express, NestJS)
        js_files = self.analysis.files.get('.js', []) + self.analysis.files.get('.ts', [])

        for js_file in js_files:
            if 'route' in js_file.lower() or 'controller' in js_file.lower():
                content = self._read_file(js_file)

                # Express routes
                express_routes = re.findall(
                    r'(?:router|app)\.(get|post|put|patch|delete)\s*\([\'"]([^\'"]+)[\'"]',
                    content, re.IGNORECASE
                )

                for method, path in express_routes:
                    self.analysis.api_endpoints.append(APIEndpoint(
                        method=method.upper(),
                        path=path,
                        description=self._path_to_description(path),
                        module=js_file
                    ))

    def _func_name_to_description(self, func_name: str) -> str:
        """Convert function name to human-readable description"""
        # Convert snake_case or camelCase to words
        words = re.sub(r'([a-z])([A-Z])', r'\1 \2', func_name)
        words = words.replace('_', ' ')
        return words.strip().title()

    def _path_to_description(self, path: str) -> str:
        """Convert API path to description"""
        parts = path.strip('/').split('/')
        # Remove path parameters
        parts = [p for p in parts if not p.startswith(':') and not p.startswith('{')]
        return ' '.join(parts).replace('-', ' ').replace('_', ' ').title()

    def _generate_requirements(self):
        """Generate functional requirements from analyzed code"""
        req_counter = 1

        # Generate requirements from API endpoints
        for endpoint in self.analysis.api_endpoints:
            method_action = {
                'GET': 'retrieve',
                'POST': 'create',
                'PUT': 'update',
                'PATCH': 'modify',
                'DELETE': 'delete'
            }

            action = method_action.get(endpoint.method, 'process')
            resource = endpoint.path.strip('/').split('/')[-1].replace('-', ' ').replace('_', ' ')
            if resource.startswith('{') or resource.startswith(':'):
                parts = endpoint.path.strip('/').split('/')
                resource = parts[-2] if len(parts) > 1 else 'resource'

            self.analysis.functional_requirements.append(FunctionalRequirement(
                id=f"FR-{req_counter:03d}",
                name=f"{action.title()} {resource.title()}",
                description=f"The system shall allow authorized users to {action} {resource} via {endpoint.method} {endpoint.path}",
                module=endpoint.module.split('/')[-1].replace('.py', '').replace('.js', '').title(),
                priority="High" if endpoint.method in ['POST', 'GET'] else "Medium",
                source=endpoint.module
            ))
            req_counter += 1

        # Generate requirements from models (CRUD for each model)
        for model in self.analysis.models:
            model_name = model.name.lower()

            # Create
            self.analysis.functional_requirements.append(FunctionalRequirement(
                id=f"FR-{req_counter:03d}",
                name=f"Create {model.name}",
                description=f"The system shall allow users to create new {model_name} records with required fields",
                module=f"{model.name} Management",
                priority="High",
                inputs=[f['name'] for f in model.fields[:5]]
            ))
            req_counter += 1

            # Read
            self.analysis.functional_requirements.append(FunctionalRequirement(
                id=f"FR-{req_counter:03d}",
                name=f"View {model.name}",
                description=f"The system shall allow users to view {model_name} details and list all {model_name}s",
                module=f"{model.name} Management",
                priority="High",
                outputs=[f['name'] for f in model.fields[:5]]
            ))
            req_counter += 1

            # Update
            self.analysis.functional_requirements.append(FunctionalRequirement(
                id=f"FR-{req_counter:03d}",
                name=f"Update {model.name}",
                description=f"The system shall allow users to update existing {model_name} records",
                module=f"{model.name} Management",
                priority="Medium"
            ))
            req_counter += 1

            # Delete
            self.analysis.functional_requirements.append(FunctionalRequirement(
                id=f"FR-{req_counter:03d}",
                name=f"Delete {model.name}",
                description=f"The system shall allow authorized users to delete {model_name} records",
                module=f"{model.name} Management",
                priority="Medium"
            ))
            req_counter += 1

        # Generate requirements from pages/components
        for page in self.analysis.pages:
            page_name = page.name.replace('Page', '').strip()
            if page_name:
                self.analysis.functional_requirements.append(FunctionalRequirement(
                    id=f"FR-{req_counter:03d}",
                    name=f"{page_name} Page",
                    description=f"The system shall provide a {page_name} page for users to interact with related features",
                    module="User Interface",
                    priority="Medium",
                    source=page.file_path
                ))
                req_counter += 1

        # Add common requirements if authentication is detected
        deps = list(self.analysis.dependencies.keys())
        if any(auth in str(deps).lower() for auth in ['jwt', 'auth', 'passport', 'session']):
            auth_reqs = [
                ("User Registration", "The system shall allow new users to register with email and password"),
                ("User Login", "The system shall authenticate users using email and password"),
                ("Password Reset", "The system shall allow users to reset their password via email"),
                ("Session Management", "The system shall maintain user sessions securely"),
            ]
            for name, desc in auth_reqs:
                self.analysis.functional_requirements.append(FunctionalRequirement(
                    id=f"FR-{req_counter:03d}",
                    name=name,
                    description=desc,
                    module="Authentication",
                    priority="High"
                ))
                req_counter += 1

    def _generate_use_cases(self):
        """Generate use cases from requirements and code analysis"""
        uc_counter = 1

        # Group requirements by module
        modules = {}
        for req in self.analysis.functional_requirements:
            if req.module not in modules:
                modules[req.module] = []
            modules[req.module].append(req)

        # Generate use cases for major features
        for model in self.analysis.models:
            # CRUD use case
            self.analysis.use_cases.append(UseCase(
                id=f"UC-{uc_counter:03d}",
                name=f"Manage {model.name}",
                actor="User",
                description=f"User manages {model.name.lower()} records in the system",
                preconditions=["User is logged in", "User has appropriate permissions"],
                postconditions=[f"{model.name} record is created/updated/deleted"],
                main_flow=[
                    f"User navigates to {model.name} management section",
                    "System displays list of existing records",
                    "User selects action (Create/View/Edit/Delete)",
                    "System processes the request",
                    "System displays confirmation/result"
                ],
                related_requirements=[r.id for r in self.analysis.functional_requirements
                                     if model.name in r.name]
            ))
            uc_counter += 1

        # Authentication use cases if detected
        if any('auth' in m.lower() for m in modules.keys()):
            auth_use_cases = [
                ("User Registration", "Guest", "New user creates an account",
                 ["User is not logged in"], ["User account is created"],
                 ["User opens registration page", "User enters details", "System validates input",
                  "System creates account", "System sends verification email"]),
                ("User Login", "Registered User", "User logs into the system",
                 ["User has an account", "User is not logged in"], ["User is authenticated"],
                 ["User opens login page", "User enters credentials", "System validates credentials",
                  "System creates session", "System redirects to dashboard"]),
            ]

            for name, actor, desc, pre, post, flow in auth_use_cases:
                self.analysis.use_cases.append(UseCase(
                    id=f"UC-{uc_counter:03d}",
                    name=name,
                    actor=actor,
                    description=desc,
                    preconditions=pre,
                    postconditions=post,
                    main_flow=flow
                ))
                uc_counter += 1

    def _generate_test_cases(self):
        """Generate test cases from requirements and code"""
        tc_counter = 1

        # Generate test cases for each functional requirement
        for req in self.analysis.functional_requirements:
            # Positive test case
            self.analysis.test_cases.append(TestCase(
                id=f"TC-{tc_counter:03d}",
                name=f"{req.name} - Valid Input",
                module=req.module,
                description=f"Verify that {req.description.lower()}",
                preconditions=["User is logged in", "System is accessible"],
                steps=[
                    f"Navigate to {req.module} section",
                    "Provide valid input data",
                    "Submit the request",
                    "Verify the response"
                ],
                expected_result="Operation completes successfully",
                priority=req.priority,
                type="Functional"
            ))
            tc_counter += 1

            # Negative test case for critical requirements
            if req.priority == "High":
                self.analysis.test_cases.append(TestCase(
                    id=f"TC-{tc_counter:03d}",
                    name=f"{req.name} - Invalid Input",
                    module=req.module,
                    description=f"Verify system handles invalid input for {req.name.lower()}",
                    preconditions=["User is logged in", "System is accessible"],
                    steps=[
                        f"Navigate to {req.module} section",
                        "Provide invalid/empty input data",
                        "Submit the request",
                        "Verify error handling"
                    ],
                    expected_result="System displays appropriate error message",
                    priority="Medium",
                    type="Negative"
                ))
                tc_counter += 1

        # Generate API test cases
        for endpoint in self.analysis.api_endpoints:
            self.analysis.test_cases.append(TestCase(
                id=f"TC-{tc_counter:03d}",
                name=f"API: {endpoint.method} {endpoint.path}",
                module="API",
                description=f"Verify {endpoint.method} {endpoint.path} endpoint",
                preconditions=["API server is running", "Valid authentication token"],
                steps=[
                    f"Send {endpoint.method} request to {endpoint.path}",
                    "Include required headers and body",
                    "Verify response status code",
                    "Verify response body structure"
                ],
                expected_result="API returns expected response",
                priority="High",
                type="API"
            ))
            tc_counter += 1

    def _identify_actors(self):
        """Identify system actors from code analysis"""
        actors = set()

        # Check for role-based access
        all_content = ""
        for ext in ['.py', '.js', '.ts']:
            for f in self.analysis.files.get(ext, [])[:20]:
                try:
                    all_content += self._read_file(f).lower()
                except:
                    pass

        # Common actor patterns
        actor_patterns = [
            ('admin', 'Administrator', 'Full system access and configuration privileges'),
            ('user', 'Registered User', 'Standard system user with basic privileges'),
            ('guest', 'Guest', 'Unauthenticated user with limited access'),
            ('manager', 'Manager', 'User with elevated privileges for oversight'),
            ('customer', 'Customer', 'End user who uses the system services'),
            ('staff', 'Staff', 'Internal user with operational access'),
        ]

        for pattern, name, desc in actor_patterns:
            if pattern in all_content:
                self.analysis.actors.append({
                    'name': name,
                    'description': desc,
                    'type': 'primary' if pattern in ['user', 'customer', 'admin'] else 'secondary'
                })

        # Always add System as an actor
        self.analysis.actors.append({
            'name': 'System',
            'description': 'Automated system processes and scheduled tasks',
            'type': 'system'
        })

        # Default actors if none found
        if len(self.analysis.actors) <= 1:
            self.analysis.actors.insert(0, {
                'name': 'User',
                'description': 'Standard system user',
                'type': 'primary'
            })

    def _identify_modules(self):
        """Identify system modules from code structure"""
        modules = set()

        # From directory structure
        for dir_path in self.analysis.directories:
            parts = dir_path.split('/')
            if len(parts) >= 1:
                module_candidates = ['modules', 'features', 'components', 'pages',
                                   'services', 'controllers', 'api', 'routes']
                for i, part in enumerate(parts):
                    if part.lower() in module_candidates and i + 1 < len(parts):
                        modules.add(parts[i + 1])
                    elif part.lower() not in ['src', 'app', 'lib', 'utils', 'common', 'shared']:
                        if not part.startswith('.') and not part.startswith('_'):
                            modules.add(part)

        # From models
        for model in self.analysis.models:
            modules.add(f"{model.name} Management")

        # Create module entries
        for module in modules:
            if module and len(module) > 2:
                self.analysis.modules.append({
                    'name': module.replace('-', ' ').replace('_', ' ').title(),
                    'description': f"Handles {module.replace('-', ' ').replace('_', ' ').lower()} related functionality"
                })

        # Add common modules
        common_modules = [
            ('Authentication', 'User authentication and authorization'),
            ('User Management', 'User account management'),
            ('Dashboard', 'Main dashboard and analytics'),
        ]

        existing_names = [m['name'].lower() for m in self.analysis.modules]
        for name, desc in common_modules:
            if name.lower() not in existing_names:
                self.analysis.modules.append({
                    'name': name,
                    'description': desc
                })


def analyze_project(project_path: str) -> ProjectAnalysis:
    """Convenience function to analyze a project"""
    analyzer = ProjectAnalyzer(project_path)
    return analyzer.analyze()
