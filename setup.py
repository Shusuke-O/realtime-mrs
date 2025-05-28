#!/usr/bin/env python3
"""
Setup script for realtime-mrs package.
Makes the package installable and reusable in other projects.
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    readme_path = os.path.join(os.path.dirname(__file__), 'README.md')
    if os.path.exists(readme_path):
        with open(readme_path, 'r', encoding='utf-8') as f:
            return f.read()
    return "Real-time MRS visualization system with FSL-MRS and Lab Streaming Layer integration"

# Read requirements from requirements.txt
def read_requirements():
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    if os.path.exists(req_path):
        with open(req_path, 'r') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    return [
        'pyyaml>=6.0',
        'pylsl>=1.16.0',
        'numpy>=1.21.0',
        'scipy>=1.7.0',
        'matplotlib>=3.5.0',
        'pandas>=1.3.0',
        'seaborn>=0.13.2',
        'pygame>=2.0.0',
    ]

setup(
    name="realtime-mrs",
    version="0.2.0",
    description="Real-time MRS visualization system with FSL-MRS and Lab Streaming Layer integration",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/realtime-mrs",
    packages=find_packages(include=['realtime_mrs', 'realtime_mrs.*']),
    package_data={
        'realtime_mrs': ['config/*.yaml', 'config/*.yml'],
    },
    include_package_data=True,
    install_requires=read_requirements(),
    extras_require={
        'dev': [
            'pytest>=7.0',
            'black>=23.0',
            'flake8>=6.0',
            'mypy>=1.0',
        ],
        'psychopy': [
            'psychopy>=2023.1.0',
        ],
        'fsl': [
            # FSL-MRS should be installed separately
            # 'fsl-mrs',  # Uncomment if available via PyPI
        ],
    },
    entry_points={
        'console_scripts': [
            'realtime-mrs=realtime_mrs.cli:main',
            'realtime-mrs-menu=realtime_mrs.menu:main',
            'realtime-mrs-lsl-publisher=realtime_mrs.lsl.fsl_mrs_publisher:main',
            'realtime-mrs-lsl-receiver=realtime_mrs.lsl.receiver:main',
            'realtime-mrs-test-lsl=realtime_mrs.testing.test_lsl_system:main',
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Scientific/Engineering :: Medical Science Apps.",
        "Topic :: Scientific/Engineering :: Visualization",
    ],
    python_requires=">=3.8",
    keywords="MRS, real-time, visualization, neuroscience, LSL, FSL-MRS, PsychoPy",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/realtime-mrs/issues",
        "Source": "https://github.com/yourusername/realtime-mrs",
        "Documentation": "https://github.com/yourusername/realtime-mrs/wiki",
    },
) 