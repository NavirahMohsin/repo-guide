
import os
import json
import shutil
from pathlib import Path
from typing import Optional, Dict, Any
import git
from datetime import datetime


class RepositoryManager:
    """
    Manages repository selection, cloning, and metadata.
    """

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.repos_dir = base_dir / "repositories"
        self.repos_dir.mkdir(exist_ok=True)
        self.metadata_file = self.repos_dir / "repositories.json"
        self._ensure_metadata_file()

    def _ensure_metadata_file(self):
        """Create metadata file if it doesn't exist."""
        if not self.metadata_file.exists():
            self._save_metadata({})

    def _load_metadata(self) -> Dict[str, Any]:
        """Load repository metadata."""
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}

    def _save_metadata(self, metadata: Dict[str, Any]):
        """Save repository metadata."""
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)

    def _generate_repo_id(self, source: str) -> str:
        """Generate a unique repository ID."""
        if source.startswith(('http://', 'https://', 'git@')):
            # Extract repo name from URL
            name = source.rstrip('/').split('/')[-1].replace('.git', '')
        else:
            name = Path(source).name
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f"{name}_{timestamp}"

    def clone_github_repo(self, github_url: str) -> Dict[str, Any]:
        """
        Clone a GitHub repository.
        
        Returns:
            Dict with repo_id, path, and status
        """
        repo_id = self._generate_repo_id(github_url)
        target_path = self.repos_dir / repo_id

        try:
            # Clone the repository
            git.Repo.clone_from(github_url, target_path, depth=1)

            # Save metadata
            metadata = self._load_metadata()
            metadata[repo_id] = {
                'type': 'github',
                'source': github_url,
                'path': str(target_path),
                'created_at': datetime.now().isoformat(),
                'indexed': False
            }
            self._save_metadata(metadata)

            return {
                'success': True,
                'repo_id': repo_id,
                'path': str(target_path),
                'message': f"Successfully cloned {github_url}"
            }

        except Exception as error:
            # Clean up if cloning failed
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
            
            return {
                'success': False,
                'error': str(error),
                'message': f"Failed to clone repository: {str(error)}"
            }

    def register_local_repo(self, local_path: str) -> Dict[str, Any]:
        """
        Register an existing local repository without copying it.
        
        Returns:
            Dict with repo_id, path, and status
        """
        path = Path(local_path).resolve()

        if not path.exists():
            return {
                'success': False,
                'error': 'Path does not exist',
                'message': f"Directory not found: {local_path}"
            }

        if not path.is_dir():
            return {
                'success': False,
                'error': 'Not a directory',
                'message': f"Path is not a directory: {local_path}"
            }

        repo_id = self._generate_repo_id(str(path))

        # Save metadata
        metadata = self._load_metadata()
        metadata[repo_id] = {
            'type': 'local',
            'source': str(path),
            'path': str(path),
            'created_at': datetime.now().isoformat(),
            'indexed': False
        }
        self._save_metadata(metadata)

        return {
            'success': True,
            'repo_id': repo_id,
            'path': str(path),
            'message': f"Successfully registered {path.name}"
        }

    def get_repository(self, repo_id: str) -> Optional[Dict[str, Any]]:
        """Get repository information by ID."""
        metadata = self._load_metadata()
        return metadata.get(repo_id)

    def list_repositories(self) -> Dict[str, Any]:
        """List all registered repositories."""
        return self._load_metadata()

    def delete_repository(self, repo_id: str) -> Dict[str, Any]:
        """Delete a repository and its metadata."""
        metadata = self._load_metadata()
        repo_info = metadata.get(repo_id)

        if not repo_info:
            return {
                'success': False,
                'message': 'Repository not found'
            }

        # Only delete cloned repos, not local ones
        if repo_info['type'] == 'github':
            repo_path = Path(repo_info['path'])
            if repo_path.exists():
                shutil.rmtree(repo_path, ignore_errors=True)

        # Remove from metadata
        del metadata[repo_id]
        self._save_metadata(metadata)

        return {
            'success': True,
            'message': f"Repository {repo_id} deleted"
        }

    def mark_indexed(self, repo_id: str, indexed: bool = True):
        """Mark a repository as indexed."""
        metadata = self._load_metadata()
        if repo_id in metadata:
            metadata[repo_id]['indexed'] = indexed
            metadata[repo_id]['last_indexed'] = datetime.now().isoformat()
            self._save_metadata(metadata)
