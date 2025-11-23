"""
Project Analyzer - Analyzes codebase to extract project information
for DocsPackAgent
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, List
import ast


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
        """Extract database schema from models"""

        schema = {
            "tables": [],
            "relationships": {}
        }

        models_dir = self.project_root / "backend" / "app" / "models"
        if not models_dir.exists():
            return schema

        for model_file in models_dir.glob("*.py"):
            if model_file.name.startswith('_'):
                continue

            # Extract table name from file
            table_name = model_file.stem
            if table_name != "__init__":
                schema["tables"].append(table_name)

            # Try to parse relationships (simplified)
            with open(model_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'ForeignKey' in content:
                    # Basic relationship detection
                    # This is simplified - a full implementation would use AST parsing
                    pass

        return schema

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
