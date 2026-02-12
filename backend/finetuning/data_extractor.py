"""
Extract training data from BharatBuild AI's existing project database.
Converts successful project generations into instruction-tuning format.
"""
import os
import sys
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select, and_
from sqlalchemy.orm import sessionmaker
from app.models.project import Project, ProjectFile, ProjectStatus
from app.core.config import settings


class TrainingDataExtractor:
    """Extract and format training data from existing projects"""

    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)

    def get_successful_projects(self, limit: Optional[int] = None) -> List[Dict]:
        """
        Get all successfully completed projects with their files
        """
        session = self.Session()
        try:
            query = select(Project).where(
                and_(
                    Project.status == ProjectStatus.COMPLETED,
                    Project.deleted_at.is_(None)
                )
            ).order_by(Project.created_at.desc())

            if limit:
                query = query.limit(limit)

            projects = session.execute(query).scalars().all()

            result = []
            for project in projects:
                project_data = {
                    "id": str(project.id),
                    "title": project.title,
                    "description": project.description,
                    "requirements": project.requirements,
                    "tech_stack": project.tech_stack,
                    "mode": project.mode,
                    "files": []
                }

                # Get project files
                files_query = select(ProjectFile).where(
                    and_(
                        ProjectFile.project_id == project.id,
                        ProjectFile.deleted_at.is_(None)
                    )
                )
                files = session.execute(files_query).scalars().all()

                for file in files:
                    if self._is_code_file(file.path):
                        project_data["files"].append({
                            "path": file.path,
                            "content": file.content,
                            "language": self._detect_language(file.path)
                        })

                if project_data["files"]:  # Only include projects with code files
                    result.append(project_data)

            return result

        finally:
            session.close()

    def _is_code_file(self, path: str) -> bool:
        """Check if file is a code file worth including"""
        code_extensions = {
            '.py', '.js', '.jsx', '.ts', '.tsx', '.css', '.scss',
            '.html', '.json', '.yaml', '.yml', '.sql', '.sh',
            '.dockerfile', '.env.example'
        }
        exclude_patterns = [
            'node_modules', '__pycache__', '.git', 'dist/', 'build/',
            'package-lock.json', 'yarn.lock', '.next/'
        ]

        # Check exclusions
        for pattern in exclude_patterns:
            if pattern in path.lower():
                return False

        # Check extension
        ext = Path(path).suffix.lower()
        if ext in code_extensions:
            return True

        # Include config files
        filename = Path(path).name.lower()
        config_files = {'dockerfile', 'makefile', '.gitignore', '.env.example'}
        return filename in config_files

    def _detect_language(self, path: str) -> str:
        """Detect programming language from file extension"""
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.css': 'css',
            '.scss': 'scss',
            '.html': 'html',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.sql': 'sql',
            '.sh': 'bash',
            '.md': 'markdown'
        }
        ext = Path(path).suffix.lower()
        return ext_map.get(ext, 'text')

    def create_instruction_pairs(self, projects: List[Dict]) -> List[Dict]:
        """
        Convert projects into instruction-completion pairs for fine-tuning
        """
        training_samples = []

        for project in projects:
            # 1. Full project generation instruction
            training_samples.append(self._create_project_instruction(project))

            # 2. Individual file generation instructions
            for file in project["files"]:
                sample = self._create_file_instruction(project, file)
                if sample:
                    training_samples.append(sample)

            # 3. Component-specific instructions (React components, API endpoints, etc.)
            component_samples = self._extract_component_instructions(project)
            training_samples.extend(component_samples)

        return training_samples

    def _create_project_instruction(self, project: Dict) -> Dict:
        """Create instruction for full project generation"""
        instruction = f"""Create a {project['tech_stack']} project with the following requirements:

Title: {project['title']}
Description: {project['description']}
Requirements: {project['requirements']}

Generate the complete project structure with all necessary files."""

        # Create file structure output
        file_structure = []
        for file in project["files"]:
            file_structure.append(f"### {file['path']}\n```{file['language']}\n{file['content']}\n```")

        output = "\n\n".join(file_structure)

        return {
            "instruction": instruction,
            "input": "",
            "output": output,
            "metadata": {
                "type": "full_project",
                "tech_stack": project["tech_stack"],
                "project_id": project["id"]
            }
        }

    def _create_file_instruction(self, project: Dict, file: Dict) -> Optional[Dict]:
        """Create instruction for single file generation"""
        content = file["content"]
        if not content or len(content.strip()) < 50:
            return None

        # Determine file type and create appropriate instruction
        path = file["path"]
        language = file["language"]

        if "component" in path.lower() or path.endswith(('.jsx', '.tsx')):
            instruction = f"Create a React component for {Path(path).stem} using {project['tech_stack']}"
        elif "api" in path.lower() or "endpoint" in path.lower():
            instruction = f"Create a FastAPI endpoint for {Path(path).stem}"
        elif "model" in path.lower() and language == "python":
            instruction = f"Create a SQLAlchemy model for {Path(path).stem}"
        elif "schema" in path.lower() and language == "python":
            instruction = f"Create a Pydantic schema for {Path(path).stem}"
        elif path.endswith('.css') or path.endswith('.scss'):
            instruction = f"Create Tailwind CSS styles for {Path(path).stem}"
        else:
            instruction = f"Create the {path} file for a {project['tech_stack']} project"

        return {
            "instruction": instruction,
            "input": f"Project context: {project['description'][:200]}",
            "output": f"```{language}\n{content}\n```",
            "metadata": {
                "type": "single_file",
                "file_path": path,
                "language": language,
                "project_id": project["id"]
            }
        }

    def _extract_component_instructions(self, project: Dict) -> List[Dict]:
        """Extract specific component patterns (forms, tables, auth, etc.)"""
        samples = []

        for file in project["files"]:
            content = file["content"]
            if not content:
                continue

            # Extract React form components
            if "form" in file["path"].lower() or "Form" in content:
                if "handleSubmit" in content or "onSubmit" in content:
                    samples.append({
                        "instruction": "Create a React form component with validation and submission handling",
                        "input": f"Tech stack: {project['tech_stack']}",
                        "output": f"```{file['language']}\n{content}\n```",
                        "metadata": {"type": "form_component"}
                    })

            # Extract API CRUD endpoints
            if file["language"] == "python" and "@router" in content:
                samples.append({
                    "instruction": "Create FastAPI CRUD endpoints with proper error handling",
                    "input": f"Context: {project['description'][:150]}",
                    "output": f"```python\n{content}\n```",
                    "metadata": {"type": "api_endpoint"}
                })

            # Extract authentication logic
            if "auth" in file["path"].lower() or "login" in file["path"].lower():
                samples.append({
                    "instruction": "Create authentication logic with JWT tokens",
                    "input": "",
                    "output": f"```{file['language']}\n{content}\n```",
                    "metadata": {"type": "authentication"}
                })

        return samples

    def export_to_jsonl(self, samples: List[Dict], output_path: str):
        """Export training samples to JSONL format"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                # Format for instruction tuning
                formatted = {
                    "instruction": sample["instruction"],
                    "input": sample.get("input", ""),
                    "output": sample["output"]
                }
                f.write(json.dumps(formatted, ensure_ascii=False) + '\n')

        print(f"Exported {len(samples)} samples to {output_path}")

    def export_to_chatml(self, samples: List[Dict], output_path: str):
        """Export in ChatML format (recommended for Qwen)"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            for sample in samples:
                # ChatML format
                messages = [
                    {"role": "system", "content": "You are an expert full-stack developer. Generate clean, production-ready code."},
                    {"role": "user", "content": sample["instruction"] + ("\n" + sample.get("input", "") if sample.get("input") else "")},
                    {"role": "assistant", "content": sample["output"]}
                ]
                f.write(json.dumps({"messages": messages}, ensure_ascii=False) + '\n')

        print(f"Exported {len(samples)} samples in ChatML format to {output_path}")


def main():
    """Main extraction pipeline"""
    import argparse

    parser = argparse.ArgumentParser(description="Extract training data from BharatBuild AI")
    parser.add_argument("--output-dir", type=str, default="./data/processed")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of projects")
    parser.add_argument("--format", choices=["jsonl", "chatml", "both"], default="chatml")
    args = parser.parse_args()

    print("Starting data extraction...")
    extractor = TrainingDataExtractor()

    # Extract projects
    print("Fetching successful projects from database...")
    projects = extractor.get_successful_projects(limit=args.limit)
    print(f"Found {len(projects)} completed projects")

    # Create training samples
    print("Creating instruction-completion pairs...")
    samples = extractor.create_instruction_pairs(projects)
    print(f"Generated {len(samples)} training samples")

    # Export
    output_dir = Path(args.output_dir)
    if args.format in ["jsonl", "both"]:
        extractor.export_to_jsonl(samples, output_dir / "train_alpaca.jsonl")
    if args.format in ["chatml", "both"]:
        extractor.export_to_chatml(samples, output_dir / "train_chatml.jsonl")

    print("Data extraction complete!")


if __name__ == "__main__":
    main()
