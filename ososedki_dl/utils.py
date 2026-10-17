"""Utility functions for the application."""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import validators  # type: ignore
from core_helpers.logs import logger
from rich import print
from rich.prompt import Prompt

from .consts import CACHE_PATH, DEFAULT_DEST_PATH, EXIT_FAILURE, LOG_PATH

if TYPE_CHECKING:
    from typing import NoReturn


def get_valid_url() -> list[str]:
    """
    Get a valid URL from user input.

    Returns:
        list[str]: A list of valid URLs.
    """
    logger.debug("Getting a valid URL from user")

    while True:
        result: list[str] = []
        urls: str = Prompt.ask("Enter the URL to download from")
        url_list: list[str] = urls.split(" ")
        for u in url_list:
            logger.debug(f"Validating URL: {u}")
            url: str = u.strip()
            if validators.url(url):
                result.append(url)

        if result:
            logger.debug(f"Valid URL(s) entered: {result}")
            return result

        logger.error("Invalid URL(s) entered")
        print("[bold red]Error:[/] Please enter a valid URL.")


def get_valid_path(default_path: str = DEFAULT_DEST_PATH.name) -> Path:
    """
    Get a valid download path from user input.

    Args:
        default_path (str): The default path to suggest to the user. Defaults
            to DEFAULT_DEST_PATH.

    Returns:
        Path: The valid download path.
    """
    logger.debug("Getting a valid download path from user")

    while True:
        path: str = Prompt.ask("Enter the download path", default=default_path)
        real_path: Path = Path(path).resolve()

        try:
            real_path.mkdir(parents=True, exist_ok=True)
            return real_path
        except Exception as e:
            logger.exception(f"Invalid path entered: {path}")
            print(f"[red]Cannot use this path:[/red] {e}")


def get_user_input(path: Path) -> tuple[list[str], Path]:
    """
    Get URL and download path from user input.

    Args:
        path (Path): The default download path.

    Returns:
        tuple[list[str], Path]: A tuple containing the list of URLs and the
            download path.
    """
    logger.debug("Getting user input for URL and path")

    print("\n", end="")
    url: list[str] = get_valid_url()
    if not path:
        path = get_valid_path()
    print("\n", end="")

    logger.debug(f"User provided URL: {url} and path: {path}")

    return url, path


def sanitize_title(title: str) -> str:
    """
    Sanitize a single filesystem path segment (a file or directory name).

    Strips characters that are invalid on common filesystems, along with
    leading/trailing spaces and dots (trailing dots/spaces are invalid on
    Windows).

    Args:
        title (str): The segment to be sanitized.

    Returns:
        str: The sanitized segment. Falls back to "Unknown" if nothing valid
            remains (e.g. the title was only invalid characters, or "..").
    """
    # Define a regular expression pattern to match invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    # Replace invalid characters with an underscore or another safe character
    sanitized_title: str = re.sub(invalid_chars, "_", title)
    # Remove leading and trailing spaces and dots
    sanitized_title = sanitized_title.strip(" .")
    if sanitized_title.startswith("_"):
        sanitized_title = sanitized_title[1:]

    return sanitized_title or "Unknown"


def sanitize_path(path: Path, title: str) -> Path:
    """
    Sanitize the given title to create a valid filesystem path.

    Args:
        path (Path): The base path where the title will be appended.
        title (str): The title to be sanitized.

    Returns:
        Path: The sanitized path.
    """
    logger.debug(f"Sanitizing path for title: {title}")

    final_path: Path = (path / sanitize_title(title)).resolve()
    logger.debug(f"Sanitized path: {final_path}")

    return final_path


def get_final_path(download_path: Path, *titles: str) -> Path:
    """
    Get the final sanitized path for downloading content.

    Each title is sanitized independently and joined as nested directory
    segments (e.g. `get_final_path(download_path, "subject", "set")` ->
    `download_path/subject/set`), so a title can never "escape" into its
    sibling's segment via a slash or path separator of its own.

    Args:
        download_path (Path): The base download path.
        *titles (str): One or more path segments to nest the final path
            under, in order.

    Returns:
        Path: The final sanitized download path.

    Raises:
        ValueError: If the final path is invalid (e.g. it would resolve
            outside of `download_path`).
    """
    logger.debug(f"Getting final path for titles: {titles}")

    resolved_download_path: Path = download_path.resolve()
    final_path: Path = resolved_download_path
    for title in titles:
        final_path = final_path / sanitize_title(title)
    final_path = final_path.resolve()

    # Sanitize the path: it must stay inside download_path
    if final_path != resolved_download_path and (
        resolved_download_path not in final_path.parents
    ):
        raise ValueError("Invalid path", final_path)

    final_path.mkdir(parents=True, exist_ok=True)
    logger.debug(f"Final path: {final_path}")

    return final_path


def get_url_hashfile(url: str) -> Path:
    """
    Generate a unique hash filename for the given URL.

    Args:
        url (str): The URL to generate a hash for.

    Returns:
        Path: The path to the hash file in the cache directory.
    """
    logger.debug(f"Generating cache filename for URL: {url}")

    url_hash: str = hashlib.sha256(url.encode("utf-8")).hexdigest()
    hash_path: Path = CACHE_PATH / url_hash
    logger.debug(f"Generated hash path: {hash_path}")

    return hash_path


def write_to_cache(url: str) -> None:
    """
    Write a cache file for the given URL.

    Args:
        url (str): The URL to cache.
    """
    logger.debug(f"Writing to cache for URL: {url}")

    cache_filename: Path = get_url_hashfile(url)
    logger.debug(f"Cache filename: {cache_filename}")
    with open(cache_filename, "w", encoding="utf-8"):
        pass


def get_unique_filename(base_path: Path) -> Path:
    """
    Generate a unique filename by appending a suffix if the file already exists.

    Args:
        base_path (Path): The initial file path.

    Returns:
        Path: A unique file path.
    """
    logger.debug(f"Generating unique filename for base path: {base_path}")

    suffix: int = 0
    new_path: Path = base_path
    while new_path.exists():
        suffix += 1
        new_path = base_path.with_stem(f"{base_path.stem}_{suffix}")

    logger.debug(f"Unique filename generated: {new_path}")

    return new_path


def exit_session(exit_value: int) -> NoReturn:
    """
    Exit the program with the given exit value.

    Args:
        exit_value (int): The POSIX exit value to exit with.
    """
    logger.info("End of session")
    # Check if the exit_value is a valid POSIX exit value
    if not 0 <= exit_value <= 255:
        exit_value = EXIT_FAILURE

    if exit_value == EXIT_FAILURE:
        print(
            "\n[red]There were errors during the execution of the script. "
            f"Check the logs at '{LOG_PATH}' for more information.[/]"
        )

    # Exit the program with the given exit value
    sys.exit(exit_value)
