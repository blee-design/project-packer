#!/usr/bin/env python3
"""
Setup script for the Project Packer / Unpacker tool.
"""

from setuptools import setup, find_packages

setup(
    name="project-packer",
    version="2.0.1",
    description="Pack any Python project into a single file for AI sharing, respecting setup.py and MANIFEST.in",
    long_description=open("README.md", "r", encoding="utf-8").read() if __import__("os").path.exists("README.md") else "",
    long_description_content_type="text/markdown",
    author="Udaya Raj Joshi",
    author_email="udayarajjoshi@aol.com",
    url="https://github.com/blee-design/project-packer",
    py_modules=["packer"],  # because it's a single module
    entry_points={
        "console_scripts": [
            "packer = packer:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
