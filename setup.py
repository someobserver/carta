"""Package configuration for CARTA."""

from setuptools import setup, find_packages
from pathlib import Path

readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

requirements_path = Path(__file__).parent / "requirements.txt"
if requirements_path.exists():
    with open(requirements_path, encoding="utf-8") as f:
        requirements = [
            line.strip() for line in f 
            if line.strip() and not line.startswith("#")
        ]
else:
    requirements = ["openai>=1.0.0", "numpy>=1.24.0"]

setup(
    name="carta",
    version="0.1.0",
    author="Inside The Black Box LLC",
    description="Conversation analysis with recursive thought mapping",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/someobserver/carta",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8+",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "carta-parse=carta.cli:parse_cli",
            "carta-embed=carta.cli:embed_cli",
        ],
    },
    include_package_data=True,
    zip_safe=False,
)