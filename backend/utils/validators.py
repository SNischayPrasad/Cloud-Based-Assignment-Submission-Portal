"""
Secure file-upload validation.

Three independent checks - never trust just one:
1. Extension whitelist (per assignment, bounded by the global whitelist)
2. Size limit (per assignment, bounded by the global MAX_UPLOAD_MB)
3. Content check ("magic bytes") - a virus.exe renamed to report.pdf
   still starts with "MZ", not "%PDF", and is rejected.
"""

import re
import unicodedata

from backend.utils.errors import PayloadTooLargeError, UnsupportedFileError, ValidationFailed

# Known file signatures. DOCX/XLSX/PPTX are ZIP containers.
MAGIC_SIGNATURES: dict[str, list[bytes]] = {
    "pdf": [b"%PDF-"],
    "docx": [b"PK\x03\x04"],
    "pptx": [b"PK\x03\x04"],
    "xlsx": [b"PK\x03\x04"],
    "zip": [b"PK\x03\x04", b"PK\x05\x06"],
    "png": [b"\x89PNG\r\n\x1a\n"],
    "jpg": [b"\xff\xd8\xff"],
    "jpeg": [b"\xff\xd8\xff"],
}

# Plain-text formats have no signature; we instead make sure they are text.
TEXT_TYPES = {"txt", "py", "java", "c", "cpp", "md", "csv", "ipynb"}

CONTENT_TYPES: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "zip": "application/zip",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "txt": "text/plain",
    "md": "text/markdown",
    "csv": "text/csv",
    "py": "text/x-python",
    "java": "text/x-java-source",
    "c": "text/x-c",
    "cpp": "text/x-c++",
    "ipynb": "application/x-ipynb+json",
}

SUPPORTED_TYPES = set(MAGIC_SIGNATURES) | TEXT_TYPES


def get_extension(filename: str) -> str:
    if "." not in filename:
        return ""
    return filename.rsplit(".", 1)[-1].lower().strip()


def sanitize_filename(filename: str, max_length: int = 150) -> str:
    """
    Make a user-supplied filename safe to display and to use in headers:
    strip directories, control characters and unusual symbols.
    (The object key never uses this name - it uses generated IDs.)
    """
    name = unicodedata.normalize("NFKC", filename or "")
    name = name.replace("\\", "/").split("/")[-1]  # drop any path component
    name = re.sub(r"[\x00-\x1f\x7f]", "", name)
    name = re.sub(r"[^\w.\- ()]", "_", name).strip(" .")
    if not name:
        name = "file"
    if len(name) > max_length:
        ext = get_extension(name)
        stem = name[: max_length - len(ext) - 1]
        name = f"{stem}.{ext}" if ext else stem
    return name


def normalize_file_types(value: str | list[str], global_whitelist: list[str]) -> list[str]:
    """Clean a teacher-supplied list like 'PDF, .docx' -> ['pdf', 'docx']."""
    items = value.split(",") if isinstance(value, str) else value
    cleaned: list[str] = []
    for item in items:
        ext = item.strip().lower().lstrip(".")
        if not ext:
            continue
        if ext not in global_whitelist:
            raise ValidationFailed(
                f"File type '.{ext}' is not permitted on this portal. Allowed: {', '.join(global_whitelist)}"
            )
        if ext not in cleaned:
            cleaned.append(ext)
    if not cleaned:
        raise ValidationFailed("At least one allowed file type is required.")
    return cleaned


def _looks_like_text(data: bytes) -> bool:
    if b"\x00" in data[:4096]:
        return False
    try:
        data[:4096].decode("utf-8")
        return True
    except UnicodeDecodeError:
        return False


def validate_upload(filename: str, data: bytes, allowed_types: list[str], max_size_mb: int) -> tuple[str, str]:
    """
    Validate an uploaded file. Returns (extension, content_type).
    Raises a 4xx AppError describing exactly what is wrong.
    """
    if not filename:
        raise ValidationFailed("The uploaded file has no name.")

    ext = get_extension(filename)
    if not ext or ext not in allowed_types:
        raise UnsupportedFileError(
            f"'.{ext or '?'}' files are not accepted for this assignment. Upload one of: "
            + ", ".join(f".{t}" for t in allowed_types)
        )

    if len(data) == 0:
        raise ValidationFailed("The uploaded file is empty.")

    max_bytes = max_size_mb * 1024 * 1024
    if len(data) > max_bytes:
        raise PayloadTooLargeError(f"File is larger than the {max_size_mb} MB limit for this assignment.")

    if ext in MAGIC_SIGNATURES:
        if not any(data.startswith(sig) for sig in MAGIC_SIGNATURES[ext]):
            raise UnsupportedFileError(
                f"The file content does not match a real .{ext} file. Re-export the file and upload it again."
            )
    elif ext in TEXT_TYPES:
        if not _looks_like_text(data):
            raise UnsupportedFileError(f"The .{ext} file does not contain readable text.")

    return ext, CONTENT_TYPES.get(ext, "application/octet-stream")


def scan_for_malware(data: bytes) -> bool:
    """
    Malware-scanning hook (concept).

    In production this would send the object to ClamAV, AWS GuardDuty
    Malware Protection for S3, or a cloud function triggered by the
    storage upload event, and quarantine infected files. Kept as a
    pass-through here so the portal runs without extra infrastructure.
    """
    return True
