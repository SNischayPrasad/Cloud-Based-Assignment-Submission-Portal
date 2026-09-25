"""
Signed-file endpoint for the LOCAL storage provider.

With STORAGE_PROVIDER=s3 the browser downloads straight from the bucket
using a pre-signed URL and this route is never used. Locally, this route
plays the role of the bucket: it only serves a file when the URL's HMAC
signature is valid and not expired - no login needed, exactly like a
cloud pre-signed URL.
"""

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from backend.utils.errors import ForbiddenError, NotFoundError
from backend.utils.validators import CONTENT_TYPES, get_extension
from cloud.storage_service import LocalStorageService, StorageError, content_disposition, get_storage_service

router = APIRouter(prefix="/api/files", tags=["Files"])


@router.get("/signed", summary="Serve a file from local storage via a signed URL")
def signed_file(
    path: str = Query(...),
    expires: int = Query(...),
    name: str = Query(...),
    disposition: str = Query(default="attachment"),
    signature: str = Query(...),
):
    storage = get_storage_service()
    if not isinstance(storage, LocalStorageService):
        raise NotFoundError("Signed local files are only available with STORAGE_PROVIDER=local.")
    try:
        if not storage.verify_signed_request(path, expires, name, disposition, signature):
            raise ForbiddenError("This download link is invalid or has expired. Request a new link.", code="LINK_EXPIRED")
        file_path = storage.file_path(path)
    except StorageError as exc:
        raise NotFoundError("File not found.") from exc

    return FileResponse(
        file_path,
        media_type=CONTENT_TYPES.get(get_extension(path), "application/octet-stream"),
        headers={
            "Content-Disposition": content_disposition(disposition, name),
            "Cache-Control": "private, no-store",
        },
    )
