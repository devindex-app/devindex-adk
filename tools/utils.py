
import os
import subprocess
from typing import List

from tools.logger import get_tool_logger as get_logger


def read_file(file_path: str) -> str:
    """
    Reads the content of a file.

    Args:
        file_path: The path to the file.

    Returns:
        The content of the file.
    """
    logger = get_logger("read_file")
    logger.info(f"Reading file: {file_path}")
    try:
        with open(file_path, "r") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file: {e}")
        return f"Error reading file: {e}"


def list_directory(path: str = ".") -> List[str]:
    """
    Lists the files and directories in a given path.

    Args:
        path: The path to the directory.

    Returns:
        A list of files and directories.
    """
    logger = get_logger("list_directory")
    logger.info(f"Listing directory: {path}")
    try:
        return os.listdir(path)
    except Exception as e:
        logger.error(f"Error listing directory: {e}")
        return [f"Error listing directory: {e}"]


def search_file_content(pattern: str, path: str = ".") -> List[str]:
    """
    Searches for a pattern in files in a given path.

    Args:
        pattern: The pattern to search for.
        path: The path to the directory.

    Returns:
        A list of files containing the pattern.
    """
    logger = get_logger("search_file_content")
    logger.info(f"Searching for pattern '{pattern}' in path '{path}'")
    try:
        matching_files = []
        for root, _, files in os.walk(path):
            for file in files:
                file_path = os.path.join(root, file)
                if read_file(file_path).find(pattern) != -1:
                    matching_files.append(file_path)
        return matching_files
    except Exception as e:
        logger.error(f"Error searching for pattern: {e}")
        return [f"Error searching for pattern: {e}"]


def run_shell_command(command: str) -> str:
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
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Error executing command: {e.stderr}")
        return f"Error executing command: {e.stderr}"


def git_tool(command: str) -> str:
    """
    A tool for running git commands.

    Args:
        command: The git command to execute.

    Returns:
        The output of the command.
    """
    logger = get_logger("git_tool")
    logger.info(f"Executing git command: {command}")
    return run_shell_command(f"git {command}")
