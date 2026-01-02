"""
File Utility Functions

Helper functions for file operations.
"""

import hashlib
import shutil
import tempfile
from pathlib import Path
from typing import Optional


def ensure_dir(path: Path) -> Path:
    """
    Ensure directory exists, create if it doesn't

    Args:
        path: Directory path

    Returns:
        Path object
    """
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_read_file(file_path: Path, encoding: str = "utf-8") -> Optional[str]:
    """
    Safely read file contents

    Args:
        file_path: Path to file
        encoding: File encoding

    Returns:
        File contents or None if error
    """
    try:
        return Path(file_path).read_text(encoding=encoding)
    except (FileNotFoundError, PermissionError, UnicodeDecodeError):
        return None


def safe_write_file(
    file_path: Path,
    content: str,
    encoding: str = "utf-8",
    create_parents: bool = True
) -> bool:
    """
    Safely write content to file

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding
        create_parents: Create parent directories if needed

    Returns:
        True if successful, False otherwise
    """
    try:
        file_path = Path(file_path)
        if create_parents:
            file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding=encoding)
        return True
    except (PermissionError, OSError):
        return False


def atomic_write(file_path: Path, content: str, encoding: str = "utf-8") -> bool:
    """
    Atomically write content to file

    Writes to temporary file first, then renames to target.
    This ensures the file is never in a partially-written state.

    Args:
        file_path: Path to file
        content: Content to write
        encoding: File encoding

    Returns:
        True if successful, False otherwise
    """
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Write to temporary file
        with tempfile.NamedTemporaryFile(
            mode='w',
            encoding=encoding,
            dir=file_path.parent,
            delete=False,
            prefix=f".{file_path.name}.",
            suffix=".tmp"
        ) as tmp_file:
            tmp_file.write(content)
            tmp_path = Path(tmp_file.name)

        # Atomic rename
        tmp_path.replace(file_path)
        return True

    except (PermissionError, OSError):
        # Clean up temp file if it exists
        if 'tmp_path' in locals():
            tmp_path.unlink(missing_ok=True)
        return False


def list_files(
    directory: Path,
    pattern: str = "*",
    recursive: bool = False
) -> list[Path]:
    """
    List files in directory matching pattern

    Args:
        directory: Directory to search
        pattern: Glob pattern
        recursive: Search recursively

    Returns:
        List of matching file paths
    """
    directory = Path(directory)
    if not directory.exists():
        return []

    if recursive:
        return sorted(directory.rglob(pattern))
    else:
        return sorted(directory.glob(pattern))


def get_file_hash(file_path: Path, algorithm: str = "sha256") -> Optional[str]:
    """
    Get hash of file contents

    Args:
        file_path: Path to file
        algorithm: Hash algorithm (sha256, md5, etc.)

    Returns:
        Hex digest of file hash, or None if error
    """
    try:
        hasher = hashlib.new(algorithm)
        with open(file_path, 'rb') as f:
            # Read in chunks to handle large files
            for chunk in iter(lambda: f.read(8192), b''):
                hasher.update(chunk)
        return hasher.hexdigest()
    except (FileNotFoundError, PermissionError, ValueError):
        return None


def copy_file(src: Path, dst: Path, overwrite: bool = False) -> bool:
    """
    Copy file from source to destination

    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing file

    Returns:
        True if successful, False otherwise
    """
    try:
        src = Path(src)
        dst = Path(dst)

        if not src.exists():
            return False

        if dst.exists() and not overwrite:
            return False

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        return True

    except (PermissionError, OSError):
        return False


def move_file(src: Path, dst: Path, overwrite: bool = False) -> bool:
    """
    Move file from source to destination

    Args:
        src: Source file path
        dst: Destination file path
        overwrite: Whether to overwrite existing file

    Returns:
        True if successful, False otherwise
    """
    try:
        src = Path(src)
        dst = Path(dst)

        if not src.exists():
            return False

        if dst.exists() and not overwrite:
            return False

        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))
        return True

    except (PermissionError, OSError):
        return False


def get_file_size(file_path: Path) -> Optional[int]:
    """
    Get file size in bytes

    Args:
        file_path: Path to file

    Returns:
        File size in bytes, or None if error
    """
    try:
        return Path(file_path).stat().st_size
    except (FileNotFoundError, PermissionError):
        return None
