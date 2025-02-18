""" This module contains functions for cloning a Git repository to a local path. """

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

from gitingest.utils import async_timeout

TIMEOUT: int = 60


@dataclass
class CloneConfig:
    """
    Configuration for cloning a Git repository.

    This class holds the necessary parameters for cloning a repository to a local path, including
    the repository's URL, the target local path, and optional parameters for a specific commit or branch.

    Attributes
    ----------
    url : str
        The URL of the Git repository to clone.
    local_path : str
        The local directory where the repository will be cloned.
    commit : str, optional
        The specific commit hash to check out after cloning (default is None).
    branch : str, optional
        The branch to clone (default is None).
    repo_name : str, optional
        The name of the repository (default is None).
    subpath : str
        The subpath to clone from the repository (default is "/").
    """

    url: str
    local_path: str
    commit: Optional[str] = None
    branch: Optional[str] = None
    repo_name: Optional[str] = None
    subpath: str = "/"


@async_timeout(TIMEOUT)
async def clone_repo(config: CloneConfig) -> Tuple[bytes, bytes]:
    """
    Clone a repository to a local path based on the provided configuration.

    This function handles the process of cloning a Git repository to the local file system.
    It can clone a specific branch or commit if provided, and it raises exceptions if
    any errors occur during the cloning process.

    Parameters
    ----------
    config : CloneConfig
        The configuration for cloning the repository.

    Returns
    -------
    Tuple[bytes, bytes]
        A tuple containing the stdout and stderr of the Git commands executed.
    """
    if config.subpath != "/":
        return await partial_clone_repo(config)

    return await clone_repo(config)


async def full_clone_repo(config: CloneConfig) -> Tuple[bytes, bytes]:
    """
    Clone a repository to a local path based on the provided configuration.

    This function handles the process of cloning a Git repository to the local file system.
    It can clone a specific branch or commit if provided, and it raises exceptions if
    any errors occur during the cloning process.

    Parameters
    ----------
    config : CloneConfig
        The configuration for cloning the repository.

    Returns
    -------
    Tuple[bytes, bytes]
        A tuple containing the stdout and stderr of the Git commands executed.

    Raises
    ------
    ValueError
        If the 'url' or 'local_path' parameters are missing, or if the repository is not found.
    OSError
        If there is an error creating the parent directory structure.
    """
    # Extract and validate query parameters
    url: str = config.url
    local_path: str = config.local_path
    commit: Optional[str] = config.commit
    branch: Optional[str] = config.branch

    if not url:
        raise ValueError("The 'url' parameter is required.")

    if not local_path:
        raise ValueError("The 'local_path' parameter is required.")

    # Create parent directory if it doesn't exist
    parent_dir = Path(local_path).parent
    try:
        os.makedirs(parent_dir, exist_ok=True)
    except OSError as e:
        raise OSError(f"Failed to create parent directory {parent_dir}: {e}") from e

    # Check if the repository exists
    if not await _check_repo_exists(url):
        raise ValueError("Repository not found, make sure it is public")

    clone_cmd = ["git", "clone", "--recurse-submodules"]

    if commit:
        # Scenario 1: Clone and checkout a specific commit
        # Clone the repository without depth to ensure full history for checkout
        clone_commit_cmd = clone_cmd + ["--single-branch", url, local_path]
        await _run_git_command(*clone_commit_cmd)

        # Checkout the specific commit
        checkout_cmd = ["git", "-C", local_path, "checkout", commit]
        return await _run_git_command(*checkout_cmd)

    if branch and branch.lower() not in ("main", "master"):
        # Scenario 2: Clone a specific branch with shallow depth
        branch_cmd = clone_cmd + ["--depth=1", "--single-branch", "--branch", branch, url, local_path]
        return await _run_git_command(*branch_cmd)

    # Scenario 3: Clone the default branch with shallow depth
    clone_cmd += ["--depth=1", "--single-branch", url, local_path]
    return await _run_git_command(*clone_cmd)


async def partial_clone_repo(config: CloneConfig) -> Tuple[bytes, bytes]:
    """
    Perform a partial clone of a Git repository based on the provided configuration.

    Parameters
    ----------
    config : CloneConfig
        The configuration for cloning the repository.

    Returns
    -------
    Tuple[bytes, bytes]
        A tuple containing the stdout and stderr of the Git commands executed.

    Raises
    ------
    ValueError
        If the 'repo_name' parameter is missing.
    """
    partial_clone_cmd = [
        "git",
        "clone",
        "--filter=blob:none",
        "--sparse",
        config.url,
        config.local_path,
    ]
    await _run_git_command(*partial_clone_cmd)

    if not config.repo_name:
        raise ValueError("The 'repo_name' parameter is required.")

    sparse_checkout_cmd = [
        "git",
        "sparse-checkout",
        "set",
        config.subpath.lstrip("/"),
    ]
    return await _run_git_command(*sparse_checkout_cmd, cwd=config.local_path)


async def _check_repo_exists(url: str) -> bool:
    """
    Check if a Git repository exists at the provided URL.

    Parameters
    ----------
    url : str
        The URL of the Git repository to check.
    Returns
    -------
    bool
        True if the repository exists, False otherwise.

    Raises
    ------
    RuntimeError
        If the curl command returns an unexpected status code.
    """
    proc = await asyncio.create_subprocess_exec(
        "curl",
        "-I",
        url,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()

    if proc.returncode != 0:
        return False

    response = stdout.decode()
    status_code = _get_status_code(response)

    if status_code in (200, 301):
        return True

    if status_code in (404, 302):
        return False

    raise RuntimeError(f"Unexpected status code: {status_code}")


@async_timeout(TIMEOUT)
async def fetch_remote_branch_list(url: str) -> List[str]:
    """
    Fetch the list of branches from a remote Git repository.
    Parameters
    ----------
    url : str
        The URL of the Git repository to fetch branches from.
    Returns
    -------
    List[str]
        A list of branch names available in the remote repository.
    """
    fetch_branches_command = ["git", "ls-remote", "--heads", url]
    stdout, _ = await _run_git_command(*fetch_branches_command)
    stdout_decoded = stdout.decode()

    return [
        line.split("refs/heads/", 1)[1]
        for line in stdout_decoded.splitlines()
        if line.strip() and "refs/heads/" in line
    ]


async def _run_git_command(*args: str, cwd: Optional[str] = None) -> Tuple[bytes, bytes]:
    """
    Execute a Git command asynchronously and captures its output.

    Parameters
    ----------
    *args : str
        The Git command and its arguments to execute.
    cwd : str, optional
        The current working directory where the Git command should be executed.

    Returns
    -------
    Tuple[bytes, bytes]
        A tuple containing the stdout and stderr of the Git command.

    Raises
    ------
    RuntimeError
        If Git is not installed or if the Git command exits with a non-zero status.
    """
    # Check if Git is installed
    try:
        version_proc = await asyncio.create_subprocess_exec(
            "git",
            "--version",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await version_proc.communicate()
        if version_proc.returncode != 0:
            error_message = stderr.decode().strip() if stderr else "Git command not found"
            raise RuntimeError(f"Git is not installed or not accessible: {error_message}")
    except FileNotFoundError as exc:
        raise RuntimeError("Git is not installed. Please install Git before proceeding.") from exc

    # Execute the requested Git command
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        error_message = stderr.decode().strip()
        raise RuntimeError(f"Git command failed: {' '.join(args)}\nError: {error_message}")

    return stdout, stderr


def _get_status_code(response: str) -> int:
    """
    Extract the status code from an HTTP response.

    Parameters
    ----------
    response : str
        The HTTP response string.

    Returns
    -------
    int
        The status code of the response
    """
    status_line = response.splitlines()[0].strip()
    status_code = int(status_line.split(" ", 2)[1])
    return status_code
