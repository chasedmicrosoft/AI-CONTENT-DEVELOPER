#!/usr/bin/env python3
"""Setup script for AI Content Developer"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="ai-content-developer",
    version="1.0.0",
    author="AI Content Developer Team",
    description="AI-powered content developer for technical documentation",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/your-org/ai-content-developer",
    packages=find_packages(exclude=["tests", "tests.*", "llm_outputs", "work", "inputs"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Documentation",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "ai-content-dev=content_developer.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["*.json"],
    },
) 