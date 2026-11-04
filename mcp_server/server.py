
import os
import json
from pathlib import Path
from collections import Counter

from pypdf import PdfReader

from mcp.server.fastmcp import FastMCP

from utils.code_parser import (
    get_repository_files,
    get_all_repository_files
)

# Initialize MCP server
mcp = FastMCP("RepoGuide")

# Get repository path from environment variable (set by the agent)
BASE_DIR = Path(__file__).resolve().parents[1]
REPO_PATH_ENV = os.getenv("REPOGUIDE_REPO_PATH")

if REPO_PATH_ENV:
    REPO_PATH = Path(REPO_PATH_ENV).resolve()
else:
    # Fallback to sample_repo if not set
    REPO_PATH = (BASE_DIR / "sample_repo").resolve()


def validate_path(relative_path):
    """
    Ensure requested files remain inside the repository.
    """

    target = (REPO_PATH / relative_path).resolve()

    if not target.is_relative_to(REPO_PATH):
        raise ValueError("Access outside repository is not allowed")

    return target


@mcp.tool()
def list_files() -> str:
    """
    List all supported source files in the repository.
    """

    files = get_all_repository_files(str(REPO_PATH))
    
    if not files:
        return "No files found in the repository."

    file_list = sorted([
        str(Path(file).relative_to(REPO_PATH))
        for file in files
    ])
    
    return "\n".join(file_list)

@mcp.tool()
def count_files() -> str:
    """
    Count the number of files by type in the repository.
    """

    files = get_all_repository_files(str(REPO_PATH))

    if not files:
        return "No files found in the repository."

    file_types = [
        Path(file).suffix.lower() for file in files
    ]

    counts = Counter(file_types)
    
    # Format as readable string
    result = "File counts by type:\n"
    for ext, count in sorted(counts.items(), key=lambda x: x[1], reverse=True):
        ext_display = ext if ext else "(no extension)"
        result += f"  {ext_display}: {count}\n"
    
    return result.strip()

@mcp.tool()
def get_file_structure() -> str:
    """
    Return the directory structure of the repository.
    """

    files = get_all_repository_files(str(REPO_PATH))

    folders = set()

    for file in files:

        relative_path = Path(file).relative_to(REPO_PATH)

        for parent in relative_path.parents:

            if str(parent) != ".":
                folders.add(str(parent))

    structure = [f"{REPO_PATH.name}/"]

    for folder in sorted(folders):
        structure.append(f"  {folder}/")

    for file in sorted(files):
        relative = Path(file).relative_to(REPO_PATH)
        structure.append(f"  {relative}")

    return "\n".join(structure)        


@mcp.tool()
def read_file(file_path: str, max_chars: int = 3000) -> str:
    """
    Read the contents of a particular repository file.

    Args:
        file_path: Relative path of the file.
        max_chars: Maximum characters to return (default 3000 for Groq's token limit).
    """

    target = validate_path(file_path)

    if not target.is_file():
        return "File not found."

    if not any(
        target.suffix.lower() == ext
        for ext in {
            ".py", ".js", ".jsx", ".ts", ".tsx",
            ".java", ".c", ".cpp", ".h",
            ".html", ".css", ".json", ".yaml",
            ".yml", ".md", ".txt", ".sql",
            ".toml", ".ini",".pdf", ".ipynb"
        }
    ):
        return "Unsupported file type."

    try:
        content = target.read_text(
            encoding="utf-8",
            errors="replace"
        )
        
        # Truncate to avoid exceeding Groq's token limit
        if len(content) > max_chars:
            return content[:max_chars] + f"\n\n... [Truncated. File has {len(content)} chars total]"
        
        return content
    except OSError as error:
        return f"Unable to read file: {error}"


@mcp.tool()
def search_code(keyword: str, max_results: int = 20) -> str:
    """
    Search for a keyword in repository source files.

    Args:
        keyword: Function name, variable, or text to search.
        max_results: Maximum number of results (default 20 for Groq's token limit).
    """

    if not keyword.strip():
        return "Please provide a keyword to search."

    files = get_repository_files(str(REPO_PATH))
    matches = []

    for file in files:

        try:
            with open(
                file,
                "r",
                encoding="utf-8",
                errors="replace"
            ) as f:

                for line_number, line in enumerate(f, start=1):

                    if keyword.lower() in line.lower():

                        matches.append({
                            "file": str(
                                Path(file).relative_to(REPO_PATH)
                            ),
                            "line": line_number,
                            "content": line.strip()[:200]  # Limit line length
                        })

                        if len(matches) >= max_results:
                            break
            
            if len(matches) >= max_results:
                break

        except OSError:
            continue

    if not matches:
        return f"No matches found for keyword: {keyword}"
    
    # Format as readable string
    result = f"Found {len(matches)} matches for '{keyword}':\n\n"
    
    for i, match in enumerate(matches, 1):
        result += f"{i}. {match['file']} (line {match['line']})\n"
        result += f"   {match['content']}\n\n"
    
    return result.strip()


if __name__ == "__main__":

    mcp.run(transport="stdio")
