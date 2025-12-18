"""
Project Import API - Upload existing projects for analysis, bug fixing, and documentation
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List, Dict, Any
from datetime import datetime
import zipfile
import io
import os
import json
import asyncio

from app.core.database import get_db
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.feature_flags import require_feature
from app.models.user import User
from app.models.project import Project
from app.models.project_file import ProjectFile
from app.modules.agents.import_analyzer_agent import import_analyzer_agent
from app.core.types import generate_uuid

router = APIRouter()

# File extensions to process (text-based files)
TEXT_EXTENSIONS = {
    '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.h', '.hpp',
    '.cs', '.go', '.rs', '.rb', '.php', '.swift', '.kt', '.scala', '.html',
    '.css', '.scss', '.less', '.json', '.xml', '.yaml', '.yml', '.md', '.txt',
    '.sql', '.sh', '.bat', '.ps1', '.env', '.gitignore', '.dockerignore',
    '.dockerfile', '.makefile', '.gradle', '.properties', '.ini', '.cfg',
    '.vue', '.svelte', '.astro', '.prisma', '.graphql', '.proto'
}

# Directories to skip
SKIP_DIRS = {
    'node_modules', '.git', '__pycache__', '.venv', 'venv', 'env',
    '.idea', '.vscode', 'dist', 'build', 'target', '.next', '.nuxt',
    'coverage', '.pytest_cache', '.mypy_cache', 'vendor', 'packages'
}

# Maximum file size to process (in bytes)
MAX_FILE_SIZE = 100 * 1024  # 100KB per file
MAX_TOTAL_SIZE = 10 * 1024 * 1024  # 10MB total


@router.post("/upload")
async def upload_project(
    file: UploadFile = File(...),
    project_name: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a ZIP file containing an existing project.
    Returns project ID and file structure.
    """
    if not file.filename.endswith('.zip'):
        raise HTTPException(status_code=400, detail="Only ZIP files are supported")

    try:
        # Read ZIP file
        content = await file.read()
        if len(content) > MAX_TOTAL_SIZE:
            raise HTTPException(status_code=400, detail=f"File too large. Maximum size is {MAX_TOTAL_SIZE // (1024*1024)}MB")

        # Extract files from ZIP
        files_data = []
        total_size = 0

        with zipfile.ZipFile(io.BytesIO(content), 'r') as zip_ref:
            for zip_info in zip_ref.infolist():
                # Skip directories
                if zip_info.is_dir():
                    continue

                # Get relative path
                file_path = zip_info.filename

                # Skip hidden and excluded directories
                path_parts = file_path.split('/')
                if any(part in SKIP_DIRS or part.startswith('.') for part in path_parts[:-1]):
                    continue

                # Skip if file is too large
                if zip_info.file_size > MAX_FILE_SIZE:
                    continue

                # Get file extension
                _, ext = os.path.splitext(file_path.lower())

                # Only process text files
                if ext not in TEXT_EXTENSIONS and not file_path.endswith('Dockerfile'):
                    continue

                # Read file content
                try:
                    with zip_ref.open(zip_info) as f:
                        file_content = f.read().decode('utf-8', errors='ignore')
                        total_size += len(file_content)

                        # Stop if total size exceeds limit
                        if total_size > MAX_TOTAL_SIZE:
                            break

                        # Determine language from extension
                        language = get_language_from_extension(ext)

                        files_data.append({
                            'path': file_path,
                            'content': file_content,
                            'language': language,
                            'size': len(file_content)
                        })
                except Exception as e:
                    # Skip files that can't be decoded
                    continue

        if not files_data:
            raise HTTPException(status_code=400, detail="No valid source files found in ZIP")

        # Extract project name from ZIP filename if not provided
        if not project_name:
            project_name = os.path.splitext(file.filename)[0]

        # Create project in database
        project_id = str(generate_uuid())
        project = Project(
            id=project_id,
            name=project_name,
            description=f"Imported project: {project_name}",
            user_id=current_user.id,
            status="imported"
        )
        db.add(project)

        # Create project files in database
        for file_data in files_data:
            project_file = ProjectFile(
                id=str(generate_uuid()),
                project_id=project_id,
                path=file_data['path'],
                content=file_data['content'],
                language=file_data['language'],
                file_type='file',
                size_bytes=file_data['size']
            )
            db.add(project_file)

        await db.commit()

        # Build file tree structure
        file_tree = build_file_tree(files_data)

        return {
            "success": True,
            "project_id": project_id,
            "project_name": project_name,
            "total_files": len(files_data),
            "total_size": total_size,
            "file_tree": file_tree,
            "files": [{"path": f['path'], "language": f['language'], "size": f['size']} for f in files_data]
        }

    except zipfile.BadZipFile:
        raise HTTPException(status_code=400, detail="Invalid ZIP file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze/{project_id}")
async def analyze_project(
    project_id: str,
    analysis_type: str = Form("full"),  # full, bugs, security, performance, docs
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze an imported project for bugs, security issues, and generate recommendations.
    Streams the analysis results.
    """
    # Verify project exists and belongs to user
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get project files
    files_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = files_result.scalars().all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found in project")

    async def stream_analysis():
        try:
            # Convert files to dict format for agent
            files_data = [
                {'path': f.path, 'content': f.content, 'language': f.language}
                for f in files
            ]

            yield f"data: {json.dumps({'type': 'status', 'message': f'Starting {analysis_type} analysis with Import Analyzer Agent...'})}\n\n"

            # Use Import Analyzer Agent
            async for text in import_analyzer_agent.analyze_project(
                files=files_data,
                project_name=project.name,
                analysis_type=analysis_type
            ):
                yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_analysis(),
        media_type="text/event-stream"
    )


@router.post("/fix-bugs/{project_id}")
async def fix_bugs(
    project_id: str,
    bug_description: str = Form(...),
    file_paths: Optional[str] = Form(None),  # Comma-separated file paths
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Fix bugs in specific files based on bug description.
    Returns fixed code with explanations.
    """
    # Verify project
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get relevant files
    query = select(ProjectFile).where(ProjectFile.project_id == project_id)
    if file_paths:
        paths = [p.strip() for p in file_paths.split(',')]
        query = query.where(ProjectFile.path.in_(paths))

    files_result = await db.execute(query)
    files = files_result.scalars().all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found")

    async def stream_fixes():
        try:
            # Convert files to dict format for agent
            files_data = [
                {'path': f.path, 'content': f.content, 'language': f.language}
                for f in files
            ]

            yield f"data: {json.dumps({'type': 'status', 'message': 'Import Analyzer Agent is analyzing and fixing the bug...'})}\n\n"

            # Use Import Analyzer Agent for bug fixing
            async for text in import_analyzer_agent.fix_bugs(
                files=files_data,
                bug_description=bug_description
            ):
                yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_fixes(),
        media_type="text/event-stream"
    )


@router.post("/generate-docs/{project_id}")
async def generate_documentation(
    project_id: str,
    doc_type: str = Form("all"),  # all, readme, srs, api, architecture
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_feature("document_generation"))
):
    """
    Generate documentation from existing code.
    Supports: README, SRS, API docs, Architecture docs

    Requires: Premium plan (document_generation feature)
    """
    # Verify project
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get project files
    files_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = files_result.scalars().all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found in project")

    async def stream_docs():
        try:
            # Convert files to dict format for agent
            files_data = [
                {'path': f.path, 'content': f.content, 'language': f.language}
                for f in files
            ]

            yield f"data: {json.dumps({'type': 'status', 'message': f'Import Analyzer Agent is generating {doc_type} documentation...'})}\n\n"

            # Use Import Analyzer Agent for documentation generation
            async for text in import_analyzer_agent.generate_documentation(
                files=files_data,
                project_name=project.name,
                doc_type=doc_type
            ):
                yield f"data: {json.dumps({'type': 'content', 'text': text})}\n\n"

            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        stream_docs(),
        media_type="text/event-stream"
    )


@router.get("/token-estimate/{project_id}")
async def get_token_estimate(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get token estimate for a project before analysis.
    Helps users understand potential cost/time.
    """
    # Verify project
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get project files
    files_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = files_result.scalars().all()

    if not files:
        raise HTTPException(status_code=404, detail="No files found in project")

    # Convert to dict format
    files_data = [
        {'path': f.path, 'content': f.content, 'language': f.language}
        for f in files
    ]

    # Get token stats from agent
    stats = import_analyzer_agent._get_token_stats(files_data)
    needs_chunking = import_analyzer_agent._needs_chunking(files_data)

    # Estimate model selection
    model_for_full = import_analyzer_agent._get_model_for_task('full', len(files_data))
    model_for_bugs = import_analyzer_agent._get_model_for_task('bugs', len(files_data))

    return {
        "success": True,
        "project_id": project_id,
        "project_name": project.name,
        "token_stats": {
            "total_tokens": stats['total_tokens'],
            "file_count": stats['file_count'],
            "avg_tokens_per_file": stats['avg_tokens_per_file'],
            "estimated_input_cost_usd": stats['estimated_cost_input'],
            "needs_chunking": needs_chunking,
            "recommended_model_full": model_for_full,
            "recommended_model_bugs": model_for_bugs,
        },
        "optimization_tips": [
            "Large files will be truncated automatically",
            "Priority files (py, js, ts) are analyzed first",
            f"{'Chunked analysis will be used (multiple API calls)' if needs_chunking else 'Single API call will be used'}",
            f"Haiku model selected for simple tasks to reduce cost" if model_for_bugs == 'haiku' else "Sonnet model selected for comprehensive analysis"
        ]
    }


@router.get("/files/{project_id}")
async def get_project_files(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all files for an imported project"""
    # Verify project
    result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.user_id == current_user.id
        )
    )
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get files
    files_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = files_result.scalars().all()

    return {
        "success": True,
        "project_id": project_id,
        "project_name": project.name,
        "files": [
            {
                "path": f.path,
                "content": f.content,
                "language": f.language,
                "size": f.size_bytes
            }
            for f in files
        ]
    }


# Helper functions

def get_language_from_extension(ext: str) -> str:
    """Map file extension to language"""
    mapping = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescriptreact',
        '.jsx': 'javascriptreact',
        '.java': 'java',
        '.cpp': 'cpp',
        '.c': 'c',
        '.h': 'c',
        '.hpp': 'cpp',
        '.cs': 'csharp',
        '.go': 'go',
        '.rs': 'rust',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.html': 'html',
        '.css': 'css',
        '.scss': 'scss',
        '.less': 'less',
        '.json': 'json',
        '.xml': 'xml',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.md': 'markdown',
        '.txt': 'plaintext',
        '.sql': 'sql',
        '.sh': 'bash',
        '.bat': 'batch',
        '.ps1': 'powershell',
        '.vue': 'vue',
        '.svelte': 'svelte',
        '.graphql': 'graphql',
        '.prisma': 'prisma',
    }
    return mapping.get(ext, 'plaintext')


def build_file_tree(files: List[Dict]) -> Dict:
    """Build a hierarchical file tree from flat file list"""
    tree = {"name": "root", "type": "folder", "children": []}

    for file_data in files:
        parts = file_data['path'].split('/')
        current = tree

        for i, part in enumerate(parts[:-1]):
            # Find or create folder
            found = None
            for child in current.get('children', []):
                if child['name'] == part and child['type'] == 'folder':
                    found = child
                    break

            if not found:
                found = {"name": part, "type": "folder", "children": []}
                current.setdefault('children', []).append(found)

            current = found

        # Add file
        current.setdefault('children', []).append({
            "name": parts[-1],
            "type": "file",
            "path": file_data['path'],
            "language": file_data['language']
        })

    return tree


# Note: build_code_context, create_analysis_prompt, and create_doc_prompt
# have been moved to the ImportAnalyzerAgent class
