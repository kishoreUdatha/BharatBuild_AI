#!/usr/bin/env python3
"""
Setup script for BharatBuild AI CLI

Install with:
    pip install -e .

Or install CLI only:
    pip install -e ".[cli]"
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = ""
if readme_path.exists():
    long_description = readme_path.read_text(encoding="utf-8")

# CLI dependencies
cli_requirements = [
    "anthropic>=0.18.0",
    "httpx>=0.26.0",
    "rich>=13.7.0",
    "prompt-toolkit>=3.0.43",
    "aiofiles>=23.2.1",
    "python-dotenv>=1.0.0",
]

setup(
    name="bharatbuild",
    version="1.0.0",
    description="BharatBuild AI - Claude Code Style CLI for AI-driven development",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="BharatBuild AI Team",
    author_email="team@bharatbuild.ai",
    url="https://github.com/bharatbuild/bharatbuild-ai",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=cli_requirements,
    extras_require={
        "cli": cli_requirements,
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.23.0",
            "black>=24.1.0",
            "isort>=5.13.0",
            "mypy>=1.8.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "bharatbuild=cli.main:main",
            "bb=cli.main:main",  # Short alias
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
    ],
    keywords="ai cli code-generation claude anthropic developer-tools",
    project_urls={
        "Documentation": "https://docs.bharatbuild.ai",
        "Source": "https://github.com/bharatbuild/bharatbuild-ai",
        "Bug Tracker": "https://github.com/bharatbuild/bharatbuild-ai/issues",
    },
)
