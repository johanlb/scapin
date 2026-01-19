"""Media router for serving Apple Notes attachments.

This router serves media files (images, PDFs, audio) from Apple Notes
attachments stored in ~/Library/Group Containers/group.com.apple.notes/Media/
"""

import re
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

router = APIRouter(prefix="/api/media", tags=["media"])

# Apple Notes media directory
APPLE_NOTES_MEDIA = (
    Path.home() / "Library/Group Containers/group.com.apple.notes/Media"
)

# Fallback: Check for notes stored in our data directory
DATA_MEDIA_DIR = Path("data/media")

# MIME type mapping
MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".pdf": "application/pdf",
    ".m4a": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".wav": "audio/wav",
    ".mp4": "video/mp4",
    ".mov": "video/quicktime",
}

# UUID pattern for validation
UUID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def is_valid_uuid(value: str) -> bool:
    """Validate that a string is a valid UUID format."""
    return bool(UUID_PATTERN.match(value))


def find_media_file(attachment_id: str) -> Optional[Path]:
    """Find a media file by attachment ID.

    Searches in:
    1. Apple Notes Media directory
    2. Local data/media directory

    Returns the path to the first file found, or None.
    """
    # Try Apple Notes directory first
    if APPLE_NOTES_MEDIA.exists():
        media_dir = APPLE_NOTES_MEDIA / attachment_id
        if media_dir.exists() and media_dir.is_dir():
            files = [f for f in media_dir.iterdir() if f.is_file()]
            if files:
                return files[0]

    # Try local data directory
    if DATA_MEDIA_DIR.exists():
        media_dir = DATA_MEDIA_DIR / attachment_id
        if media_dir.exists() and media_dir.is_dir():
            files = [f for f in media_dir.iterdir() if f.is_file()]
            if files:
                return files[0]

        # Also try direct file match with extension
        for ext in MIME_TYPES:
            file_path = DATA_MEDIA_DIR / f"{attachment_id}{ext}"
            if file_path.exists():
                return file_path

    return None


@router.get("/{attachment_id}")
async def get_media(
    attachment_id: str,
    download: bool = Query(False, description="Force download instead of inline display"),
) -> FileResponse:
    """Serve a media file from Apple Notes or local storage.

    Args:
        attachment_id: UUID of the attachment
        download: If true, sets Content-Disposition to attachment

    Returns:
        The media file with appropriate Content-Type

    Raises:
        HTTPException 400: Invalid attachment ID format
        HTTPException 404: Media file not found
    """
    # Validate UUID format for security
    if not is_valid_uuid(attachment_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid attachment ID format. Must be a valid UUID."
        )

    # Find the file
    file_path = find_media_file(attachment_id)
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Media file not found: {attachment_id}"
        )

    # Determine MIME type
    mime_type = MIME_TYPES.get(
        file_path.suffix.lower(),
        "application/octet-stream"
    )

    # Set content disposition
    disposition = "attachment" if download else "inline"

    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name,
        headers={
            "Cache-Control": "max-age=86400",  # Cache for 24 hours
            "Content-Disposition": f'{disposition}; filename="{file_path.name}"',
        },
    )


@router.get("/info/{attachment_id}")
async def get_media_info(attachment_id: str) -> dict:
    """Get information about a media file without downloading it.

    Args:
        attachment_id: UUID of the attachment

    Returns:
        Dict with file metadata (name, size, type, etc.)

    Raises:
        HTTPException 400: Invalid attachment ID format
        HTTPException 404: Media file not found
    """
    if not is_valid_uuid(attachment_id):
        raise HTTPException(
            status_code=400,
            detail="Invalid attachment ID format. Must be a valid UUID."
        )

    file_path = find_media_file(attachment_id)
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Media file not found: {attachment_id}"
        )

    stat = file_path.stat()
    mime_type = MIME_TYPES.get(
        file_path.suffix.lower(),
        "application/octet-stream"
    )

    # Determine media category
    if mime_type.startswith("image/"):
        category = "image"
    elif mime_type.startswith("audio/"):
        category = "audio"
    elif mime_type.startswith("video/"):
        category = "video"
    elif mime_type == "application/pdf":
        category = "pdf"
    else:
        category = "file"

    return {
        "attachment_id": attachment_id,
        "filename": file_path.name,
        "size": stat.st_size,
        "mime_type": mime_type,
        "category": category,
        "extension": file_path.suffix.lower(),
        "url": f"/api/media/{attachment_id}",
    }
