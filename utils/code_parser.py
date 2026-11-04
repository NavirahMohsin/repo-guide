
import os
from pathlib import Path


# File types that RepoGuide can ingest
SUPPORTED_EXTENSIONS = {
    # Python and programming languages
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".java", ".c", ".cpp", ".h",

    # Web development
    ".html", ".css",

    # Data and configuration
    ".json", ".yaml", ".yml",
    ".toml", ".ini", ".sql",

    # Documentation
    ".md", ".txt",

    # Special formats
    ".pdf", ".ipynb"
}


# Directories that should not be scanned
IGNORED_DIRECTORIES = {
    ".git",
    "venv",
    ".venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    ".next",
    ".ipynb_checkpoints"
}


MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def get_all_repository_files(repo_path):
    """
    Return ALL files in the repository,
    including unsupported file formats.
    """

    repository_files = []

    for root, dirs, files in os.walk(repo_path):

        dirs[:] = [
            directory for directory in dirs
            if directory not in IGNORED_DIRECTORIES
        ]

        for file in files:

            file_path = Path(root) / file

            try:
                if file_path.stat().st_size <= MAX_FILE_SIZE:
                    repository_files.append(str(file_path))
            except OSError:
                continue

    return repository_files


def get_repository_files(repo_path):
    """
    Return files supported by our RAG pipeline.
    """

    all_files = get_all_repository_files(repo_path)

    return [
        file_path
        for file_path in all_files
        if Path(file_path).suffix.lower()
        in SUPPORTED_EXTENSIONS
    ]


def should_include_file(file_path):
    """
    Check whether a file can be processed by RepoGuide.
    """

    return (
        Path(file_path).suffix.lower()
        in SUPPORTED_EXTENSIONS
    )
