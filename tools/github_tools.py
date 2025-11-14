
import os
import subprocess
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
