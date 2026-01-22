"""
Project Analyzer - Analyzes codebase to extract project information
for DocsPackAgent and UML diagram generation.

This module performs deep code analysis to extract:
- Database schema with columns, types, and relationships
- API endpoints with methods and parameters
- Class structures with attributes and methods
- Project features and modules
"""

import os
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import ast


class SQLAlchemyModelVisitor(ast.NodeVisitor):
    """AST visitor to extract SQLAlchemy model information."""

    # SQLAlchemy type mappings
    TYPE_MAPPINGS = {
        'String': 'String',
        'Integer': 'Integer',
        'BigInteger': 'BigInteger',
        'Float': 'Float',
        'Numeric': 'Decimal',
        'Boolean': 'Boolean',
        'DateTime': 'DateTime',
        'Date': 'Date',
        'Time': 'Time',
        'Text': 'Text',
        'LargeBinary': 'Binary',
        'JSON': 'JSON',
        'JSONB': 'JSONB',
        'UUID': 'UUID',
        'Enum': 'Enum',
        'ARRAY': 'Array',
    }

    def __init__(self):
        self.models = []
        self.current_model = None

    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definitions to find SQLAlchemy models."""
        # Check if this class inherits from Base or Model
        base_names = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                base_names.append(base.attr)

        is_model = any(name in ['Base', 'Model', 'BaseModel', 'DeclarativeBase'] for name in base_names)

        if is_model:
            self.current_model = {
                'name': node.name,
                'columns': [],
                'relationships': [],
                'primary_key': 'id',
                'table_name': None,
                'methods': []
            }

            # Process class body
            for item in node.body:
                if isinstance(item, ast.Assign):
                    self._process_assignment(item)
                elif isinstance(item, ast.AnnAssign):
                    self._process_annotated_assignment(item)
                elif isinstance(item, ast.FunctionDef):
                    if not item.name.startswith('_'):
                        self.current_model['methods'].append(item.name)

            # Only add if we found columns
            if self.current_model['columns']:
                self.models.append(self.current_model)

            self.current_model = None

        self.generic_visit(node)

    def _process_assignment(self, node: ast.Assign):
        """Process simple assignments like: id = Column(UUID, ...)"""
        if not self.current_model:
            return

        for target in node.targets:
            if isinstance(target, ast.Name):
                col_name = target.id

                # Check for __tablename__
                if col_name == '__tablename__' and isinstance(node.value, ast.Constant):
                    self.current_model['table_name'] = node.value.value
                    continue

                # Check for Column() call
                if isinstance(node.value, ast.Call):
                    col_info = self._extract_column_info(col_name, node.value)
                    if col_info:
                        self.current_model['columns'].append(col_info)

                    # Check for relationship()
                    rel_info = self._extract_relationship_info(col_name, node.value)
                    if rel_info:
                        self.current_model['relationships'].append(rel_info)

    def _process_annotated_assignment(self, node: ast.AnnAssign):
        """Process annotated assignments like: id: Mapped[UUID] = mapped_column(...)"""
        if not self.current_model or not isinstance(node.target, ast.Name):
            return

        col_name = node.target.id

        # Extract type from annotation
        col_type = self._extract_type_from_annotation(node.annotation)

        # Check for mapped_column() or Column()
        if node.value and isinstance(node.value, ast.Call):
            col_info = self._extract_column_info(col_name, node.value, default_type=col_type)
            if col_info:
                self.current_model['columns'].append(col_info)

            rel_info = self._extract_relationship_info(col_name, node.value)
            if rel_info:
                self.current_model['relationships'].append(rel_info)
        elif col_type:
            # Just annotated without value
            self.current_model['columns'].append({
                'name': col_name,
                'type': col_type,
                'nullable': True,
                'primary_key': False,
                'foreign_key': None
            })

    def _extract_type_from_annotation(self, annotation) -> Optional[str]:
        """Extract type from type annotation like Mapped[UUID]."""
        if isinstance(annotation, ast.Subscript):
            # Mapped[SomeType] or Optional[SomeType]
            if isinstance(annotation.slice, ast.Name):
                return self.TYPE_MAPPINGS.get(annotation.slice.id, annotation.slice.id)
            elif isinstance(annotation.slice, ast.Subscript):
                # Nested like Mapped[Optional[UUID]]
                return self._extract_type_from_annotation(annotation.slice)
        elif isinstance(annotation, ast.Name):
            return self.TYPE_MAPPINGS.get(annotation.id, annotation.id)
        return None

    def _extract_column_info(self, col_name: str, call_node: ast.Call, default_type: str = None) -> Optional[Dict]:
        """Extract column information from Column() or mapped_column() call."""
        func_name = None
        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            func_name = call_node.func.attr

        if func_name not in ['Column', 'mapped_column']:
            return None

        col_info = {
            'name': col_name,
            'type': default_type or 'String',
            'nullable': True,
            'primary_key': False,
            'foreign_key': None
        }

        # Process positional arguments
        for i, arg in enumerate(call_node.args):
            if i == 0:
                # First arg is usually the type
                col_type = self._extract_column_type(arg)
                if col_type:
                    col_info['type'] = col_type

            # Check for ForeignKey
            if isinstance(arg, ast.Call):
                fk_info = self._extract_foreign_key(arg)
                if fk_info:
                    col_info['foreign_key'] = fk_info

        # Process keyword arguments
        for kw in call_node.keywords:
            if kw.arg == 'primary_key' and isinstance(kw.value, ast.Constant):
                col_info['primary_key'] = kw.value.value
                if kw.value.value:
                    self.current_model['primary_key'] = col_name
            elif kw.arg == 'nullable' and isinstance(kw.value, ast.Constant):
                col_info['nullable'] = kw.value.value

        return col_info

    def _extract_column_type(self, node) -> Optional[str]:
        """Extract column type from AST node."""
        if isinstance(node, ast.Name):
            return self.TYPE_MAPPINGS.get(node.id, node.id)
        elif isinstance(node, ast.Call):
            # Type with parameters like String(255)
            if isinstance(node.func, ast.Name):
                return self.TYPE_MAPPINGS.get(node.func.id, node.func.id)
            elif isinstance(node.func, ast.Attribute):
                return self.TYPE_MAPPINGS.get(node.func.attr, node.func.attr)
        elif isinstance(node, ast.Attribute):
            return self.TYPE_MAPPINGS.get(node.attr, node.attr)
        return None

    def _extract_foreign_key(self, call_node: ast.Call) -> Optional[str]:
        """Extract ForeignKey reference."""
        func_name = None
        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            func_name = call_node.func.attr

        if func_name == 'ForeignKey' and call_node.args:
            if isinstance(call_node.args[0], ast.Constant):
                # ForeignKey('users.id') -> 'users'
                fk_ref = call_node.args[0].value
                if '.' in fk_ref:
                    return fk_ref.split('.')[0]
                return fk_ref
        return None

    def _extract_relationship_info(self, attr_name: str, call_node: ast.Call) -> Optional[Dict]:
        """Extract relationship information from relationship() call."""
        func_name = None
        if isinstance(call_node.func, ast.Name):
            func_name = call_node.func.id
        elif isinstance(call_node.func, ast.Attribute):
            func_name = call_node.func.attr

        if func_name != 'relationship':
            return None

        rel_info = {
            'name': attr_name,
            'target': None,
            'type': 'one_to_many',
            'back_populates': None
        }

        # First argument is the target model
        if call_node.args and isinstance(call_node.args[0], ast.Constant):
            rel_info['target'] = call_node.args[0].value

        # Check keywords
        for kw in call_node.keywords:
            if kw.arg == 'back_populates' and isinstance(kw.value, ast.Constant):
                rel_info['back_populates'] = kw.value.value
            elif kw.arg == 'uselist' and isinstance(kw.value, ast.Constant):
                if not kw.value.value:
                    rel_info['type'] = 'one_to_one'

        return rel_info if rel_info['target'] else None


class ProjectAnalyzer:
    """
    Analyzes a project codebase to extract structured information
    for academic document generation.
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete project analysis.

        Returns:
            Dict with project_name, purpose, tech_stack, architecture, etc.
        """

        analysis = {
            "project_name": self._get_project_name(),
            "project_purpose": self._get_project_purpose(),
            "domain": self._infer_domain(),
            "technology_stack": self._analyze_tech_stack(),
            "architecture": self._infer_architecture(),
            "database_schema": self._analyze_database_schema(),
            "modules": self._analyze_modules(),
            "features": self._extract_features(),
            "file_structure": self._get_file_structure()
        }

        return analysis

    def _get_project_name(self) -> str:
        """Extract project name from directory or README"""

        # Try README first
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                first_line = f.readline().strip()
                if first_line.startswith('#'):
                    return first_line.lstrip('#').strip()

        # Fallback to directory name
        return self.project_root.name

    def _get_project_purpose(self) -> str:
        """Extract project purpose/description from README"""

        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for description after title
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if line.startswith('#') and i + 1 < len(lines):
                        # Get next non-empty line
                        for j in range(i + 1, len(lines)):
                            if lines[j].strip():
                                return lines[j].strip()

        return "Purpose not specified in README"

    def _infer_domain(self) -> str:
        """Infer project domain from name, README, or files"""

        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read().lower()

                # Domain keywords
                if any(word in content for word in ['ecommerce', 'e-commerce', 'shop', 'cart', 'product']):
                    return "E-Commerce"
                elif any(word in content for word in ['hospital', 'patient', 'doctor', 'medical']):
                    return "Healthcare"
                elif any(word in content for word in ['student', 'course', 'learning', 'education']):
                    return "Education / EdTech"
                elif any(word in content for word in ['ai', 'ml', 'agent', 'llm']):
                    return "Artificial Intelligence"
                elif any(word in content for word in ['finance', 'banking', 'payment', 'transaction']):
                    return "Finance / FinTech"

        return "Web Application"

    def _analyze_tech_stack(self) -> Dict[str, Any]:
        """Analyze technology stack from package files"""

        tech_stack = {
            "backend": {},
            "frontend": {},
            "database": {},
            "other": []
        }

        # Backend (Python)
        requirements_txt = self.project_root / "backend" / "requirements.txt"
        if requirements_txt.exists():
            with open(requirements_txt, 'r', encoding='utf-8') as f:
                packages = [line.split('==')[0].strip() for line in f if line.strip() and not line.startswith('#')]

                if 'fastapi' in packages:
                    tech_stack["backend"]["framework"] = "FastAPI"
                    tech_stack["backend"]["language"] = "Python 3.11+"
                elif 'django' in packages:
                    tech_stack["backend"]["framework"] = "Django"
                    tech_stack["backend"]["language"] = "Python 3.x"
                elif 'flask' in packages:
                    tech_stack["backend"]["framework"] = "Flask"
                    tech_stack["backend"]["language"] = "Python 3.x"

                if 'sqlalchemy' in packages:
                    tech_stack["backend"]["orm"] = "SQLAlchemy"
                if 'celery' in packages:
                    tech_stack["backend"]["task_queue"] = "Celery"
                if 'redis' in packages:
                    tech_stack["backend"]["cache"] = "Redis"

        # Frontend (Node.js)
        package_json = self.project_root / "frontend" / "package.json"
        if package_json.exists():
            with open(package_json, 'r', encoding='utf-8') as f:
                pkg_data = json.load(f)
                dependencies = pkg_data.get('dependencies', {})

                if 'next' in dependencies:
                    tech_stack["frontend"]["framework"] = "Next.js 14"
                    tech_stack["frontend"]["language"] = "TypeScript 5"
                elif 'react' in dependencies:
                    tech_stack["frontend"]["framework"] = "React 18"
                elif 'vue' in dependencies:
                    tech_stack["frontend"]["framework"] = "Vue.js"

                if 'tailwindcss' in dependencies or '@tailwindcss' in str(dependencies):
                    tech_stack["frontend"]["styling"] = "Tailwind CSS 3"

        # Database (from environment or config files)
        env_example = self.project_root / "backend" / ".env.example"
        if env_example.exists():
            with open(env_example, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                if 'postgresql' in content or 'postgres' in content:
                    tech_stack["database"]["primary"] = "PostgreSQL 15"
                elif 'mongodb' in content or 'mongo' in content:
                    tech_stack["database"]["primary"] = "MongoDB"
                elif 'mysql' in content:
                    tech_stack["database"]["primary"] = "MySQL"

                if 'redis' in content:
                    tech_stack["database"]["cache"] = "Redis 7"

        return tech_stack

    def _infer_architecture(self) -> str:
        """Infer system architecture from directory structure"""

        has_frontend = (self.project_root / "frontend").exists()
        has_backend = (self.project_root / "backend").exists()
        has_docker = (self.project_root / "docker-compose.yml").exists()
        has_api_folder = (self.project_root / "backend" / "app" / "api").exists()

        if has_frontend and has_backend:
            if has_api_folder:
                return "Microservices-oriented architecture with separate frontend and backend layers, API gateway, and data layer"
            return "Client-Server architecture with React frontend and Python backend"
        elif has_backend:
            return "Backend API service with RESTful architecture"

        return "Monolithic architecture"

    def _analyze_database_schema(self) -> Dict[str, Any]:
        """
        Extract complete database schema from models using AST parsing.

        Returns:
            Dict with:
            - tables: List of table dicts with name, columns, relationships
            - relationships: Dict mapping table pairs to relationship type
        """
        schema = {
            "tables": [],
            "relationships": {}
        }

        # Try multiple possible model locations
        model_paths = [
            self.project_root / "backend" / "app" / "models",
            self.project_root / "app" / "models",
            self.project_root / "models",
            self.project_root / "src" / "models",
        ]

        models_dir = None
        for path in model_paths:
            if path.exists():
                models_dir = path
                break

        if not models_dir:
            # Try to find models in generated project files
            return self._analyze_schema_from_files()

        # Parse each model file with AST
        for model_file in models_dir.glob("*.py"):
            if model_file.name.startswith('_') or model_file.name == '__init__.py':
                continue

            try:
                with open(model_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Use AST to parse Python models
                tree = ast.parse(content)
                visitor = SQLAlchemyModelVisitor()
                visitor.visit(tree)

                # Add extracted models to schema
                for model in visitor.models:
                    table_info = {
                        'name': model['name'],
                        'table_name': model.get('table_name') or self._to_snake_case(model['name']),
                        'columns': model['columns'],
                        'primary_key': model['primary_key'],
                        'relationships': [],
                        'methods': model.get('methods', [])
                    }

                    # Process relationships
                    for rel in model['relationships']:
                        table_info['relationships'].append({
                            'column': rel['name'],
                            'references': rel['target'],
                            'type': rel['type']
                        })

                    # Also check columns for foreign keys
                    for col in model['columns']:
                        if col.get('foreign_key'):
                            fk_table = col['foreign_key']
                            table_info['relationships'].append({
                                'column': col['name'],
                                'references': self._snake_to_pascal(fk_table),
                                'type': 'many_to_one'
                            })
                            # Add to global relationships
                            rel_key = f"{model['name']}_{self._snake_to_pascal(fk_table)}"
                            schema['relationships'][rel_key] = {
                                'from': model['name'],
                                'to': self._snake_to_pascal(fk_table),
                                'type': 'many_to_one'
                            }

                    schema['tables'].append(table_info)

            except SyntaxError as e:
                # If AST parsing fails, try regex fallback
                tables_from_regex = self._parse_model_with_regex(model_file)
                schema['tables'].extend(tables_from_regex)
            except Exception as e:
                # Log but continue
                pass

        # If no tables found, try alternative parsing
        if not schema['tables']:
            schema = self._analyze_schema_from_files()

        return schema

    def _analyze_schema_from_files(self) -> Dict[str, Any]:
        """Fallback: Extract schema from various file types using regex."""
        schema = {"tables": [], "relationships": {}}

        # Search for model files in the entire project
        search_patterns = [
            ('*.py', self._parse_python_models),
            ('*.prisma', self._parse_prisma_schema),
            ('*.ts', self._parse_typeorm_models),
            ('*.java', self._parse_java_entities),
            ('*.sql', self._parse_sql_schema),
        ]

        for pattern, parser in search_patterns:
            for file_path in self.project_root.rglob(pattern):
                # Skip node_modules, venv, etc.
                if any(skip in str(file_path) for skip in ['node_modules', 'venv', '.venv', '__pycache__', 'dist', 'build']):
                    continue
                try:
                    tables = parser(file_path)
                    schema['tables'].extend(tables)
                except Exception:
                    continue

        # Remove duplicates
        seen = set()
        unique_tables = []
        for table in schema['tables']:
            name = table.get('name', '')
            if name and name not in seen:
                seen.add(name)
                unique_tables.append(table)
        schema['tables'] = unique_tables

        return schema

    def _parse_python_models(self, file_path: Path) -> List[Dict]:
        """Parse Python file for SQLAlchemy/Django models."""
        tables = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Check if this looks like a model file
            if 'Column' not in content and 'models.Model' not in content:
                return tables

            tree = ast.parse(content)
            visitor = SQLAlchemyModelVisitor()
            visitor.visit(tree)

            for model in visitor.models:
                tables.append({
                    'name': model['name'],
                    'columns': model['columns'],
                    'primary_key': model['primary_key'],
                    'relationships': [
                        {'column': col['name'], 'references': col['foreign_key'], 'type': 'many_to_one'}
                        for col in model['columns'] if col.get('foreign_key')
                    ]
                })

        except Exception:
            pass

        return tables

    def _parse_model_with_regex(self, file_path: Path) -> List[Dict]:
        """Parse model file using regex when AST fails."""
        tables = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find class definitions that inherit from Base/Model
            class_pattern = r'class\s+(\w+)\s*\([^)]*(?:Base|Model)[^)]*\)'
            for match in re.finditer(class_pattern, content):
                class_name = match.group(1)

                # Find columns
                columns = []
                col_pattern = r'(\w+)\s*[=:]\s*(?:Column|mapped_column)\s*\(\s*(\w+)'
                for col_match in re.finditer(col_pattern, content):
                    col_name, col_type = col_match.groups()
                    if col_name not in ['__tablename__', '__table_args__']:
                        columns.append({
                            'name': col_name,
                            'type': col_type,
                            'nullable': True,
                            'primary_key': col_name == 'id',
                            'foreign_key': None
                        })

                # Find foreign keys
                fk_pattern = r'(\w+)\s*=\s*Column\s*\([^)]*ForeignKey\s*\(\s*[\'"](\w+)\.(\w+)[\'"]'
                for fk_match in re.finditer(fk_pattern, content):
                    col_name, ref_table, ref_col = fk_match.groups()
                    for col in columns:
                        if col['name'] == col_name:
                            col['foreign_key'] = ref_table
                            break

                if columns:
                    tables.append({
                        'name': class_name,
                        'columns': columns,
                        'primary_key': 'id',
                        'relationships': [
                            {'column': c['name'], 'references': c['foreign_key'], 'type': 'many_to_one'}
                            for c in columns if c.get('foreign_key')
                        ]
                    })

        except Exception:
            pass

        return tables

    def _parse_prisma_schema(self, file_path: Path) -> List[Dict]:
        """Parse Prisma schema file."""
        tables = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find model definitions
            model_pattern = r'model\s+(\w+)\s*\{([^}]+)\}'
            for match in re.finditer(model_pattern, content, re.DOTALL):
                model_name = match.group(1)
                model_body = match.group(2)

                columns = []
                relationships = []

                # Parse fields
                field_pattern = r'(\w+)\s+(\w+)(\[\])?\s*(@[^\n]+)?'
                for field_match in re.finditer(field_pattern, model_body):
                    field_name = field_match.group(1)
                    field_type = field_match.group(2)
                    is_array = field_match.group(3)
                    decorators = field_match.group(4) or ''

                    # Skip relation fields (they're model names, not types)
                    if field_type[0].isupper() and field_type not in ['String', 'Int', 'Float', 'Boolean', 'DateTime', 'Json']:
                        relationships.append({
                            'column': field_name,
                            'references': field_type,
                            'type': 'one_to_many' if is_array else 'many_to_one'
                        })
                    else:
                        columns.append({
                            'name': field_name,
                            'type': field_type,
                            'nullable': '?' in decorators,
                            'primary_key': '@id' in decorators,
                            'foreign_key': None
                        })

                tables.append({
                    'name': model_name,
                    'columns': columns,
                    'primary_key': next((c['name'] for c in columns if c['primary_key']), 'id'),
                    'relationships': relationships
                })

        except Exception:
            pass

        return tables

    def _parse_typeorm_models(self, file_path: Path) -> List[Dict]:
        """Parse TypeORM entity files."""
        tables = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if '@Entity' not in content:
                return tables

            # Find entity classes
            entity_pattern = r'@Entity\s*\([^)]*\)\s*(?:export\s+)?class\s+(\w+)'
            for match in re.finditer(entity_pattern, content):
                entity_name = match.group(1)

                columns = []
                relationships = []

                # Find columns
                col_pattern = r'@(?:PrimaryGeneratedColumn|Column)\s*\([^)]*\)\s*(\w+)\s*[?:]?\s*(\w+)?'
                for col_match in re.finditer(col_pattern, content):
                    col_name = col_match.group(1)
                    col_type = col_match.group(2) or 'string'
                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'nullable': True,
                        'primary_key': 'PrimaryGeneratedColumn' in col_match.group(0),
                        'foreign_key': None
                    })

                # Find relationships
                rel_pattern = r'@(?:ManyToOne|OneToMany|OneToOne|ManyToMany)\s*\([^)]*\)\s*(\w+)\s*[?:]?\s*(\w+)?'
                for rel_match in re.finditer(rel_pattern, content):
                    rel_name = rel_match.group(1)
                    rel_type = rel_match.group(2)
                    if rel_type:
                        relationships.append({
                            'column': rel_name,
                            'references': rel_type.replace('[]', ''),
                            'type': 'one_to_many' if 'OneToMany' in rel_match.group(0) else 'many_to_one'
                        })

                tables.append({
                    'name': entity_name,
                    'columns': columns,
                    'primary_key': next((c['name'] for c in columns if c['primary_key']), 'id'),
                    'relationships': relationships
                })

        except Exception:
            pass

        return tables

    def _parse_java_entities(self, file_path: Path) -> List[Dict]:
        """Parse Java JPA/Hibernate entity files."""
        tables = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            if '@Entity' not in content:
                return tables

            # Find entity classes
            entity_pattern = r'@Entity\s*(?:@Table\s*\([^)]*\))?\s*public\s+class\s+(\w+)'
            for match in re.finditer(entity_pattern, content):
                entity_name = match.group(1)

                columns = []
                relationships = []

                # Find fields with @Column or @Id
                field_pattern = r'(?:@(?:Id|Column|GeneratedValue)[^;]*\s+)?private\s+(\w+)\s+(\w+)\s*;'
                for field_match in re.finditer(field_pattern, content):
                    field_type = field_match.group(1)
                    field_name = field_match.group(2)
                    columns.append({
                        'name': field_name,
                        'type': field_type,
                        'nullable': True,
                        'primary_key': '@Id' in content[:field_match.start()].split('\n')[-1],
                        'foreign_key': None
                    })

                # Find relationships
                rel_pattern = r'@(?:ManyToOne|OneToMany|OneToOne|ManyToMany)[^;]*private\s+(?:List<)?(\w+)>?\s+(\w+)\s*;'
                for rel_match in re.finditer(rel_pattern, content):
                    rel_type = rel_match.group(1)
                    rel_name = rel_match.group(2)
                    relationships.append({
                        'column': rel_name,
                        'references': rel_type,
                        'type': 'one_to_many' if 'OneToMany' in rel_match.group(0) else 'many_to_one'
                    })

                tables.append({
                    'name': entity_name,
                    'columns': columns,
                    'primary_key': next((c['name'] for c in columns if c['primary_key']), 'id'),
                    'relationships': relationships
                })

        except Exception:
            pass

        return tables

    def _parse_sql_schema(self, file_path: Path) -> List[Dict]:
        """Parse SQL CREATE TABLE statements."""
        tables = []

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Find CREATE TABLE statements
            table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"\']?(\w+)[`"\']?\s*\(([^;]+)\)'
            for match in re.finditer(table_pattern, content, re.IGNORECASE | re.DOTALL):
                table_name = match.group(1)
                table_body = match.group(2)

                columns = []
                relationships = []

                # Parse columns
                col_pattern = r'[`"\']?(\w+)[`"\']?\s+([\w\(\)]+)(?:\s+(?:NOT\s+)?NULL)?(?:\s+PRIMARY\s+KEY)?'
                for col_match in re.finditer(col_pattern, table_body, re.IGNORECASE):
                    col_name = col_match.group(1)
                    col_type = col_match.group(2)

                    # Skip constraints
                    if col_name.upper() in ['PRIMARY', 'FOREIGN', 'UNIQUE', 'INDEX', 'CONSTRAINT', 'KEY']:
                        continue

                    columns.append({
                        'name': col_name,
                        'type': col_type,
                        'nullable': 'NOT NULL' not in col_match.group(0).upper(),
                        'primary_key': 'PRIMARY KEY' in col_match.group(0).upper(),
                        'foreign_key': None
                    })

                # Find foreign keys
                fk_pattern = r'FOREIGN\s+KEY\s*\([`"\']?(\w+)[`"\']?\)\s*REFERENCES\s+[`"\']?(\w+)[`"\']?'
                for fk_match in re.finditer(fk_pattern, table_body, re.IGNORECASE):
                    fk_col = fk_match.group(1)
                    ref_table = fk_match.group(2)
                    for col in columns:
                        if col['name'] == fk_col:
                            col['foreign_key'] = ref_table
                    relationships.append({
                        'column': fk_col,
                        'references': ref_table,
                        'type': 'many_to_one'
                    })

                tables.append({
                    'name': self._snake_to_pascal(table_name),
                    'columns': columns,
                    'primary_key': next((c['name'] for c in columns if c['primary_key']), 'id'),
                    'relationships': relationships
                })

        except Exception:
            pass

        return tables

    def _to_snake_case(self, name: str) -> str:
        """Convert PascalCase to snake_case."""
        return re.sub(r'(?<!^)(?=[A-Z])', '_', name).lower()

    def _snake_to_pascal(self, name: str) -> str:
        """Convert snake_case to PascalCase."""
        return ''.join(word.title() for word in name.split('_'))

    def _analyze_modules(self) -> List[Dict[str, str]]:
        """Analyze project modules from API endpoints or directory structure"""

        modules = []

        # Check API endpoints
        api_dir = self.project_root / "backend" / "app" / "api" / "v1" / "endpoints"
        if api_dir.exists():
            for endpoint_file in api_dir.glob("*.py"):
                if endpoint_file.name.startswith('_'):
                    continue

                module_name = endpoint_file.stem.replace('_', ' ').title()
                modules.append({
                    "name": module_name,
                    "description": f"{module_name} management and operations"
                })

        # If no API endpoints, check main app modules
        if not modules:
            modules_dir = self.project_root / "backend" / "app" / "modules"
            if modules_dir.exists():
                for module_dir in modules_dir.iterdir():
                    if module_dir.is_dir() and not module_dir.name.startswith('_'):
                        modules.append({
                            "name": module_dir.name.replace('_', ' ').title(),
                            "description": f"{module_dir.name} functionality"
                        })

        return modules

    def _extract_features(self) -> List[str]:
        """Extract key features from README or infer from modules"""

        features = []

        # Try README first
        readme_path = self.project_root / "README.md"
        if readme_path.exists():
            with open(readme_path, 'r', encoding='utf-8') as f:
                content = f.read()

                # Look for Features section
                if '## Features' in content or '### Features' in content:
                    in_features = False
                    for line in content.split('\n'):
                        if '## Features' in line or '### Features' in line:
                            in_features = True
                            continue
                        if in_features:
                            if line.startswith('##') or line.startswith('###'):
                                break
                            if line.strip().startswith('-') or line.strip().startswith('*'):
                                features.append(line.strip().lstrip('-*').strip())

        # If no features found, infer from modules
        if not features:
            modules = self._analyze_modules()
            features = [f"{module['name']}" for module in modules]

        return features

    def _get_file_structure(self) -> Dict[str, List[str]]:
        """Get high-level file structure"""

        structure = {}

        for subdir in ['backend', 'frontend', 'database', 'docs']:
            subdir_path = self.project_root / subdir
            if subdir_path.exists():
                structure[subdir] = [str(p.relative_to(subdir_path)) for p in subdir_path.rglob('*') if p.is_dir()][:10]  # Limit to 10

        return structure


# Example usage
if __name__ == "__main__":
    import asyncio
    from docspack_agent import DocsPackAgent

    async def generate_docs_for_project(project_root: str):
        """
        Complete workflow: Analyze project → Generate documents
        """

        # Step 1: Analyze project
        print("📊 Analyzing project...")
        analyzer = ProjectAnalyzer(project_root)
        analysis = analyzer.analyze()

        print(f"\n✅ Analysis complete:")
        print(f"   Project: {analysis['project_name']}")
        print(f"   Domain: {analysis['domain']}")
        print(f"   Modules: {len(analysis['modules'])}")
        print(f"   Features: {len(analysis['features'])}")

        # Step 2: Generate documents
        print("\n📝 Generating academic documents...")
        agent = DocsPackAgent()
        documents = await agent.generate_documents(analysis)

        # Step 3: Save to files
        output_dir = Path(project_root) / "academic_documents"
        output_dir.mkdir(exist_ok=True)

        file_mapping = {
            "abstract": "01_ABSTRACT.md",
            "srs": "02_SRS_DOCUMENT.md",
            "uml": "03_UML_DIAGRAMS.md",
            "erd": "04_ER_DIAGRAM.md",
            "report": "05_PROJECT_REPORT.md",
            "ppt_slides": "06_PPT_SLIDES.md",
            "viva": "07_VIVA_QUESTIONS.md",
            "output_explanation": "08_OUTPUT_EXPLANATION.md"
        }

        for doc_type, filename in file_mapping.items():
            filepath = output_dir / filename
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(documents[doc_type])
            print(f"   ✅ {filename}")

        print(f"\n🎉 All documents generated in '{output_dir}/'")

        return documents

    # Run for current project
    project_root = r"C:\Users\KishoreUdatha\IdeaProjects\BharatBuild_AI"
    asyncio.run(generate_docs_for_project(project_root))
