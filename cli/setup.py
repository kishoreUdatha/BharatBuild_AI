"""
BharatBuild CLI — Package Setup
"""
from setuptools import setup, find_packages
from pathlib import Path

setup(
    name="bharatbuild-cli",
    version="1.0.0",
    description="BharatBuild AI — CLI for AI-powered code generation",
    author="BharatBuild AI",
    python_requires=">=3.10",
    packages=find_packages(),
    install_requires=[
        "httpx[http2]>=0.27.0",
        "rich>=13.7.0",
        "prompt-toolkit>=3.0.47",
        "aiofiles>=23.2.1",
        "python-dotenv>=1.0.1",
        "pyyaml>=6.0.1",
    ],
    extras_require={
        "fast": ["uvloop>=0.19.0"],
    },
    entry_points={
        "console_scripts": [
            "bharatbuild=cli.main:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
)
