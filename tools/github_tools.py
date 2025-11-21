
import os
import subprocess
import base64
from typing import List, Dict, Any, Optional
import json

from tools.logger import get_tool_logger as get_logger


class GithubTools:
    """Tools for interacting with Github repositories and API."""

    def __init__(self, working_dir: str = ".", github_token: Optional[str] = None):
        self.working_dir = working_dir
        self.github_token = github_token or os.environ.get("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"

    def get_tools(self):
        return [
            self.read_file,
            self.list_directory,
            self.search_file_content,
            self.run_shell_command,
            self.git_tool,
            self.fetch_user_repos,
            self.fetch_repo_languages,
            self.fetch_user_commits,
            self.fetch_commit_diff,
            self.fetch_user_pull_requests,
            self.fetch_repo_details,
            self.fetch_repo_file_paths,
            self.fetch_repo_file,
        ]

    def read_file(self, file_path: str) -> str:
        """
        Reads the content of a file.

        Args:
            file_path: The path to the file.

        Returns:
            The content of the file.
        """
        logger = get_logger("read_file")
        full_path = os.path.join(self.working_dir, file_path)
        logger.info(f"Reading file: {full_path}")
        try:
            with open(full_path, "r") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return f"Error reading file: {e}"

    def list_directory(self, path: str = ".") -> List[str]:
        """
        Lists the files and directories in a given path.

        Args:
            path: The path to the directory.

        Returns:
            A list of files and directories.
        """
        logger = get_logger("list_directory")
        full_path = os.path.join(self.working_dir, path)
        logger.info(f"Listing directory: {full_path}")
        try:
            return os.listdir(full_path)
        except Exception as e:
            logger.error(f"Error listing directory: {e}")
            return [f"Error listing directory: {e}"]

    def search_file_content(self, pattern: str, path: str = ".") -> List[str]:
        """
        Searches for a pattern in files in a given path.

        Args:
            pattern: The pattern to search for.
            path: The path to the directory.

        Returns:
            A list of files containing the pattern.
        """
        logger = get_logger("search_file_content")
        full_path = os.path.join(self.working_dir, path)
        logger.info(f"Searching for pattern '{pattern}' in path '{full_path}'")
        try:
            matching_files = []
            for root, _, files in os.walk(full_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    if self.read_file(file_path).find(pattern) != -1:
                        matching_files.append(file_path)
            return matching_files
        except Exception as e:
            logger.error(f"Error searching for pattern: {e}")
            return [f"Error searching for pattern: {e}"]

    def run_shell_command(self, command: str) -> str:
        """
        Executes a shell command.

        Args:
            command: The command to execute.

        Returns:
            The output of the command.
        """
        logger = get_logger("run_shell_command")
        logger.info(f"Executing command: {command}")
        try:
            result = subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=self.working_dir,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Error executing command: {e.stderr}")
            return f"Error executing command: {e.stderr}"

    def git_tool(self, command: str) -> str:
        """
        A tool for running git commands.

        Args:
            command: The git command to execute.

        Returns:
            The output of the command.
        """
        logger = get_logger("git_tool")
        logger.info(f"Executing git command: {command}")
        return self.run_shell_command(f"git {command}")

    def _make_api_request(self, endpoint: str) -> Dict[str, Any]:
        """
        Make a GitHub API request.
        
        Args:
            endpoint: API endpoint (e.g., '/users/username/repos')
            
        Returns:
            JSON response as dictionary.
        """
        logger = get_logger("github_api")
        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/vnd.github.v3+json"}
        
        if self.github_token:
            headers["Authorization"] = f"token {self.github_token}"
        
        logger.info(f"Making API request to: {url}")
        
        try:
            import urllib.request
            import urllib.error
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                return data
        except urllib.error.HTTPError as e:
            error_msg = f"GitHub API error: {e.code} - {e.reason}"
            if e.code == 404:
                error_msg += " (User or resource not found)"
            elif e.code == 403:
                error_msg += " (Rate limit exceeded or forbidden - consider using GITHUB_TOKEN)"
            logger.error(error_msg)
            return {"error": error_msg, "status_code": e.code}
        except Exception as e:
            logger.error(f"Error making API request: {e}")
            return {"error": str(e)}

    def fetch_user_repos(self, username: str, per_page: int = 100) -> Dict[str, Any]:
        """
        Fetch all public repositories for a GitHub user.
        
        Args:
            username: GitHub username
            per_page: Number of repos per page (max 100)
            
        Returns:
            Dictionary with repository data.
        """
        logger = get_logger("fetch_user_repos")
        logger.info(f"Fetching repositories for user: {username}")
        
        endpoint = f"/users/{username}/repos?per_page={per_page}&sort=updated"
        repos_data = self._make_api_request(endpoint)
        
        if "error" in repos_data:
            return repos_data
        
        # Extract relevant repo information
        repos_summary = []
        for repo in repos_data:
            repos_summary.append({
                "name": repo.get("name", ""),
                "full_name": repo.get("full_name", ""),
                "description": repo.get("description", ""),
                "language": repo.get("language", ""),
                "stars": repo.get("stargazers_count", 0),
                "forks": repo.get("forks_count", 0),
                "created_at": repo.get("created_at", ""),
                "updated_at": repo.get("updated_at", ""),
                "size": repo.get("size", 0),
                "default_branch": repo.get("default_branch", "main"),
            })
        
        return {
            "username": username,
            "total_repos": len(repos_summary),
            "repos": repos_summary
        }

    def fetch_repo_languages(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetch language breakdown for a specific repository.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            
        Returns:
            Dictionary with language statistics.
        """
        logger = get_logger("fetch_repo_languages")
        logger.info(f"Fetching languages for {owner}/{repo}")
        
        endpoint = f"/repos/{owner}/{repo}/languages"
        languages_data = self._make_api_request(endpoint)
        
        if "error" in languages_data:
            return languages_data
        
        total_bytes = sum(languages_data.values())
        languages_percentage = {}
        for lang, bytes_count in languages_data.items():
            languages_percentage[lang] = round((bytes_count / total_bytes) * 100, 2) if total_bytes > 0 else 0
        
        return {
            "repo": f"{owner}/{repo}",
            "languages_bytes": languages_data,
            "languages_percentage": languages_percentage,
            "total_bytes": total_bytes
        }

    def fetch_user_commits(self, username: str, repo: str, per_page: int = 5) -> Dict[str, Any]:
        """
        Fetch recent commits for a user in a specific repository.
        
        Args:
            username: GitHub username
            repo: Repository name (owner/repo or just repo if user owns it)
            per_page: Number of commits to fetch (default: 5 for most recent)
            
        Returns:
            Dictionary with commit data (messages only, no diffs).
        """
        logger = get_logger("fetch_user_commits")
        logger.info(f"Fetching commits for {username} in {repo}")
        
        # If repo doesn't include owner, assume it's owned by the user
        if "/" not in repo:
            repo = f"{username}/{repo}"
        
        endpoint = f"/repos/{repo}/commits?author={username}&per_page={per_page}"
        commits_data = self._make_api_request(endpoint)
        
        if "error" in commits_data:
            return commits_data
        
        commits_summary = []
        for commit in commits_data:
            commit_info = commit.get("commit", {})
            commits_summary.append({
                "sha": commit.get("sha", ""),
                "sha_short": commit.get("sha", "")[:7],
                "message": commit_info.get("message", ""),
                "author": commit_info.get("author", {}).get("name", ""),
                "date": commit_info.get("author", {}).get("date", ""),
                "url": commit.get("html_url", ""),
            })
        
        return {
            "username": username,
            "repo": repo,
            "total_commits": len(commits_summary),
            "commits": commits_summary
        }

    def fetch_commit_diff(self, owner: str, repo: str, commit_sha: str) -> Dict[str, Any]:
        """
        Fetch detailed commit information including code changes (diff) for a specific commit.
        
        Args:
            owner: Repository owner
            repo: Repository name
            commit_sha: Full commit SHA
            
        Returns:
            Dictionary with commit details including files changed and patches.
        """
        logger = get_logger("fetch_commit_diff")
        logger.info(f"Fetching commit diff for {owner}/{repo} commit {commit_sha[:7]}")
        
        endpoint = f"/repos/{owner}/{repo}/commits/{commit_sha}"
        commit_data = self._make_api_request(endpoint)
        
        if "error" in commit_data:
            return commit_data
        
        # Extract file changes and patches
        files_changed = []
        stats = commit_data.get("stats", {})
        
        for file_info in commit_data.get("files", []):
            file_data = {
                "filename": file_info.get("filename", ""),
                "status": file_info.get("status", ""),  # added, modified, removed, renamed
                "additions": file_info.get("additions", 0),
                "deletions": file_info.get("deletions", 0),
                "changes": file_info.get("changes", 0),
                "patch": file_info.get("patch", ""),  # The actual diff/patch
            }
            files_changed.append(file_data)
        
        commit_info = commit_data.get("commit", {})
        return {
            "sha": commit_data.get("sha", ""),
            "sha_short": commit_data.get("sha", "")[:7],
            "message": commit_info.get("message", ""),
            "author": commit_info.get("author", {}).get("name", ""),
            "date": commit_info.get("author", {}).get("date", ""),
            "url": commit_data.get("html_url", ""),
            "stats": {
                "total": stats.get("total", 0),
                "additions": stats.get("additions", 0),
                "deletions": stats.get("deletions", 0),
            },
            "files_changed": files_changed,
            "files_changed_count": len(files_changed),
        }

    def fetch_user_pull_requests(self, username: str, per_page: int = 30) -> Dict[str, Any]:
        """
        Fetch pull requests created by a user across all repositories.
        
        Args:
            username: GitHub username
            per_page: Number of PRs to fetch
            
        Returns:
            Dictionary with PR data.
        """
        logger = get_logger("fetch_user_pull_requests")
        logger.info(f"Fetching pull requests for user: {username}")
        
        endpoint = f"/search/issues?q=author:{username}+type:pr&per_page={per_page}&sort=updated"
        prs_data = self._make_api_request(endpoint)
        
        if "error" in prs_data:
            return prs_data
        
        items = prs_data.get("items", [])
        prs_summary = []
        for pr in items:
            prs_summary.append({
                "number": pr.get("number", 0),
                "title": pr.get("title", ""),
                "body": pr.get("body", ""),
                "state": pr.get("state", ""),
                "created_at": pr.get("created_at", ""),
                "updated_at": pr.get("updated_at", ""),
                "repo": pr.get("repository_url", "").replace(f"{self.base_url}/repos/", ""),
                "url": pr.get("html_url", ""),
            })
        
        return {
            "username": username,
            "total_prs": len(prs_summary),
            "pull_requests": prs_summary
        }

    def fetch_repo_details(self, owner: str, repo: str) -> Dict[str, Any]:
        """
        Fetch detailed information about a repository.
        
        Args:
            owner: Repository owner
            repo: Repository name
            
        Returns:
            Dictionary with detailed repo information.
        """
        logger = get_logger("fetch_repo_details")
        logger.info(f"Fetching details for {owner}/{repo}")
        
        endpoint = f"/repos/{owner}/{repo}"
        repo_data = self._make_api_request(endpoint)
        
        if "error" in repo_data:
            return repo_data
        
        return {
            "name": repo_data.get("name", ""),
            "full_name": repo_data.get("full_name", ""),
            "description": repo_data.get("description", ""),
            "language": repo_data.get("language", ""),
            "stars": repo_data.get("stargazers_count", 0),
            "forks": repo_data.get("forks_count", 0),
            "watchers": repo_data.get("watchers_count", 0),
            "open_issues": repo_data.get("open_issues_count", 0),
            "created_at": repo_data.get("created_at", ""),
            "updated_at": repo_data.get("updated_at", ""),
            "pushed_at": repo_data.get("pushed_at", ""),
            "size": repo_data.get("size", 0),
            "default_branch": repo_data.get("default_branch", "main"),
            "topics": repo_data.get("topics", []),
            "is_fork": repo_data.get("fork", False),
            "archived": repo_data.get("archived", False),
        }

    def fetch_repo_file_paths(
        self,
        owner: str,
        repo: str,
        path: str = "",
        branch: Optional[str] = None,
        file_extensions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Fetch a list of all file paths from a GitHub repository (just paths, no file contents).
        Recursively traverses the repository to get all file paths.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            path: Starting path in the repository (default: root "")
            branch: Branch name (defaults to default branch, usually "main")
            file_extensions: Optional list of file extensions to filter (e.g., [".py", ".js", ".ts"]).
                           If None, returns all files.
            
        Returns:
            Dictionary with list of file paths.
        """
        logger = get_logger("fetch_repo_file_paths")
        logger.info(f"Fetching file paths from {owner}/{repo} (path: {path}, branch: {branch or 'default'})")
        
        # Get default branch if not specified
        if not branch:
            repo_details = self.fetch_repo_details(owner, repo)
            if "error" in repo_details:
                return {"error": f"Failed to get repo details: {repo_details.get('error')}"}
            branch = repo_details.get("default_branch", "main")
        
        # Common directories and files to ignore
        IGNORED_PATTERNS = [
            "node_modules",
            ".git",
            ".svn",
            ".hg",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".venv",
            "venv",
            "env",
            ".env",
            "dist",
            "build",
            ".next",
            ".nuxt",
            ".cache",
            "coverage",
            ".nyc_output",
            ".idea",
            ".vscode",
            ".DS_Store",
            "*.pyc",
            "*.pyo",
            "*.pyd",
            ".classpath",
            ".project",
            ".settings",
            "target",
            "out",
            "bin",
            "obj",
            ".gradle",
            ".mvn",
            "vendor",
            "bower_components",
            ".sass-cache",
            ".parcel-cache",
        ]
        
        def _should_ignore_path(path: str) -> bool:
            """Check if a path should be ignored based on common patterns."""
            path_lower = path.lower()
            path_parts = path_lower.split("/")
            
            # Check if any part of the path matches ignored patterns
            for part in path_parts:
                for pattern in IGNORED_PATTERNS:
                    pattern_lower = pattern.lower()
                    # Handle wildcard patterns (e.g., "*.pyc")
                    if pattern_lower.startswith("*"):
                        if part.endswith(pattern_lower[1:]):
                            return True
                    # Exact match (directory or file name)
                    elif part == pattern_lower:
                        return True
                    # Check if part starts with pattern (for patterns like ".env" matching ".env.local")
                    elif part.startswith(pattern_lower):
                        return True
            return False
        
        file_paths = []
        
        def _recursive_fetch_paths(current_path: str):
            # Skip ignored directories
            if _should_ignore_path(current_path):
                logger.debug(f"Skipping ignored path: {current_path}")
                return
            
            endpoint = f"/repos/{owner}/{repo}/contents/{current_path}"
            if branch:
                endpoint += f"?ref={branch}"
            
            items = self._make_api_request(endpoint)
            
            if "error" in items:
                logger.warning(f"Error fetching path {current_path}: {items.get('error')}")
                return
            
            # Handle single file response
            if isinstance(items, dict) and items.get("type") == "file":
                file_path = items.get("path", "")
                # Skip ignored files
                if _should_ignore_path(file_path):
                    return
                # Check file extension filter
                if file_extensions:
                    if any(file_path.endswith(ext) for ext in file_extensions):
                        file_paths.append(file_path)
                else:
                    file_paths.append(file_path)
                return
            
            # Handle directory response (list of items)
            if not isinstance(items, list):
                return
            
            for item in items:
                item_type = item.get("type", "")
                item_path = item.get("path", "")
                
                # Skip ignored paths
                if _should_ignore_path(item_path):
                    continue
                
                if item_type == "file":
                    # Check file extension filter
                    if file_extensions:
                        if any(item_path.endswith(ext) for ext in file_extensions):
                            file_paths.append(item_path)
                    else:
                        file_paths.append(item_path)
                elif item_type == "dir":
                    # Recursively fetch directory contents
                    _recursive_fetch_paths(item_path)
        
        # Start recursive fetch
        _recursive_fetch_paths(path)
        
        return {
            "repo": f"{owner}/{repo}",
            "branch": branch,
            "path": path,
            "total_files": len(file_paths),
            "file_paths": sorted(file_paths),
        }

    def fetch_repo_file(
        self,
        owner: str,
        repo: str,
        file_path: str,
        branch: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch the complete content of a single file from a GitHub repository.
        Returns the full file content, not a diff.
        
        Args:
            owner: Repository owner username
            repo: Repository name
            file_path: Path to the file in the repository (e.g., "src/main.py")
            branch: Branch name (defaults to default branch, usually "main")
            
        Returns:
            Dictionary with file content and metadata.
        """
        logger = get_logger("fetch_repo_file")
        logger.info(f"Fetching file {file_path} from {owner}/{repo} (branch: {branch or 'default'})")
        
        # Get default branch if not specified
        if not branch:
            repo_details = self.fetch_repo_details(owner, repo)
            if "error" in repo_details:
                return {"error": f"Failed to get repo details: {repo_details.get('error')}"}
            branch = repo_details.get("default_branch", "main")
        
        endpoint = f"/repos/{owner}/{repo}/contents/{file_path}"
        if branch:
            endpoint += f"?ref={branch}"
        
        file_data = self._make_api_request(endpoint)
        
        if "error" in file_data:
            return file_data
        
        # Check if it's actually a file
        if file_data.get("type") != "file":
            return {"error": f"Path {file_path} is not a file (type: {file_data.get('type')})"}
        
        # Decode base64 content if present
        content = ""
        if file_data.get("encoding") == "base64":
            try:
                content = base64.b64decode(file_data.get("content", "")).decode("utf-8")
            except Exception as e:
                logger.error(f"Error decoding file content: {e}")
                return {"error": f"Error decoding file content: {e}"}
        else:
            content = file_data.get("content", "")
        
        return {
            "repo": f"{owner}/{repo}",
            "branch": branch,
            "path": file_data.get("path", ""),
            "name": file_data.get("name", ""),
            "size": file_data.get("size", 0),
            "sha": file_data.get("sha", ""),
            "content": content,
            "encoding": file_data.get("encoding", ""),
        }
