"""
The file store.

Local disk by default, S3 or MinIO when the deployment has one. Local is the
default deliberately: this install has `STORAGE_MODE=local` and no object store
running, and a file store that only worked against unconfigured S3 would be one
more feature nobody could reach.

What arrives from a browser is treated as hostile:

* the client's filename never becomes a path - the key is the SHA-256 of the
  content, so a name like `../../etc/passwd` is only ever a label;
* the client's Content-Type is never believed - the first bytes are matched
  against a signature table, and a `.pdf` that is not a PDF is refused;
* only document and image types are accepted, so an executable or a script
  cannot be parked in the store and fetched back later;
* size is capped before anything is written.

Downloads always leave as attachments with `nosniff`, so a stored HTML file
could not execute against this origin even if one got in.
"""

import asyncio
import hashlib
import io
import os
import re
from pathlib import Path
from typing import Optional, Tuple

from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging_config import logger
from app.services.tenancy import self_serve_tenant
from app.models.files import StoredFile
from app.models.user import User

MAX_UPLOAD_MB = int(getattr(settings, "MAX_UPLOAD_MB", 25))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

# Read in chunks so an oversized upload is refused before it is all in memory.
CHUNK = 1024 * 1024

# Extension -> (mime, [magic prefixes]). An empty prefix list means the format
# has no reliable signature and is accepted on extension alone; every such
# entry here is a plain-text or text-derived format that cannot execute.
SIGNATURES = {
    "pdf": ("application/pdf", [b"%PDF-"]),
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", [b"PK\x03\x04"]),
    "pptx": ("application/vnd.openxmlformats-officedocument.presentationml.presentation", [b"PK\x03\x04"]),
    "xlsx": ("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", [b"PK\x03\x04"]),
    "doc": ("application/msword", [b"\xd0\xcf\x11\xe0"]),
    "ppt": ("application/vnd.ms-powerpoint", [b"\xd0\xcf\x11\xe0"]),
    "xls": ("application/vnd.ms-excel", [b"\xd0\xcf\x11\xe0"]),
    "png": ("image/png", [b"\x89PNG\r\n\x1a\n"]),
    "jpg": ("image/jpeg", [b"\xff\xd8\xff"]),
    "jpeg": ("image/jpeg", [b"\xff\xd8\xff"]),
    "webp": ("image/webp", [b"RIFF"]),
    "txt": ("text/plain", []),
    "csv": ("text/csv", []),
}

ALLOWED = sorted(SIGNATURES)


class FileStoreError(Exception):
    """A refusal the caller can show the user as-is."""


# ------------------------------------------------------------------ backends

def _mode() -> str:
    """Which backend to write NEW files to."""
    mode = (getattr(settings, "STORAGE_MODE", "local") or "local").lower()
    return "s3" if mode in {"s3", "minio"} else "local"


def _root() -> Path:
    """
    Where local files live.

    Under /app/uploads, which compose mounts as a named volume - inside the
    bind-mounted source tree the store would be wiped by a rebuild and would
    leak into the repository.
    """
    root = Path(getattr(settings, "FILE_STORE_ROOT", "/app/uploads/store"))
    root.mkdir(parents=True, exist_ok=True)
    return root


def _local_path(key: str) -> Path:
    return _root() / key


def _key_for(digest: str) -> str:
    """Sharded so no directory ends up holding a hundred thousand entries."""
    return f"{digest[:2]}/{digest[2:4]}/{digest}"


async def _write_local(key: str, content: bytes) -> None:
    path = _local_path(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size == len(content):
        return
    # Written beside the target and moved into place, so a crash mid-write
    # cannot leave a truncated file that hashes to a name promising more.
    temp = path.with_suffix(".part")
    await asyncio.to_thread(temp.write_bytes, content)
    await asyncio.to_thread(os.replace, temp, path)


async def _read_local(key: str) -> bytes:
    path = _local_path(key)
    if not path.exists():
        raise FileStoreError("That file is missing from storage.")
    return await asyncio.to_thread(path.read_bytes)


def _s3_client():
    from app.services.storage_service import StorageService
    return StorageService()


async def _write_s3(key: str, content: bytes, mime: str) -> None:
    service = _s3_client()
    client = await asyncio.to_thread(service._get_client)
    await asyncio.to_thread(
        client.put_object,
        Bucket=service._bucket_name, Key=key, Body=content, ContentType=mime,
    )


async def _read_s3(key: str) -> bytes:
    service = _s3_client()
    client = await asyncio.to_thread(service._get_client)
    obj = await asyncio.to_thread(client.get_object, Bucket=service._bucket_name, Key=key)
    return await asyncio.to_thread(obj["Body"].read)


# -------------------------------------------------------------- validation

def _extension(name: str) -> str:
    return (name or "").rsplit(".", 1)[-1].lower() if "." in (name or "") else ""


def safe_name(name: str) -> str:
    """
    The client's filename, reduced to something safe to store as a label and
    to echo back in a Content-Disposition header.
    """
    base = os.path.basename((name or "").replace("\\", "/")).strip()
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)
    base = re.sub(r'[<>:"/\\|?*]', "_", base)
    base = base.lstrip(".") or "upload"
    return base[:255]


def _sniff(content: bytes, extension: str) -> str:
    """
    Confirm the bytes match the extension, and return the mime to record.

    The browser's Content-Type is ignored entirely - it is chosen by whatever
    sent the request.
    """
    mime, prefixes = SIGNATURES[extension]
    if prefixes and not any(content.startswith(p) for p in prefixes):
        raise FileStoreError(
            f"That file does not look like a {extension.upper()}. "
            "Check you picked the right file and try again."
        )
    if extension == "webp" and not content[8:12] == b"WEBP":
        raise FileStoreError("That file does not look like a WEBP image.")
    return mime


def _page_count(content: bytes, mime: str) -> Optional[int]:
    """Page count for PDFs. A file that cannot be parsed is still stored."""
    if mime != "application/pdf":
        return None
    try:
        from PyPDF2 import PdfReader
        return len(PdfReader(io.BytesIO(content)).pages)
    except Exception:
        return None


async def _collect(upload: UploadFile) -> bytes:
    """Read the upload, refusing it the moment it goes over the cap."""
    chunks, total = [], 0
    while True:
        chunk = await upload.read(CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > MAX_UPLOAD_BYTES:
            raise FileStoreError(f"Files must be {MAX_UPLOAD_MB} MB or smaller.")
        chunks.append(chunk)
    if total == 0:
        raise FileStoreError("That file is empty.")
    return b"".join(chunks)


# ------------------------------------------------------------------- public

async def save(db: AsyncSession, upload: UploadFile, user: Optional[User],
               college_id=None) -> StoredFile:
    """
    Validate and store one upload, returning the row that describes it.

    Does not commit: the file belongs to the same transaction as whatever is
    being attached to it, so a failed attach cannot leave an orphan row
    claiming a document exists.

    `college_id` is for callers who know which institution the file belongs to
    better than the uploader's own profile does - a student attaching evidence
    to their batch's story files it under the batch's college, whether or not
    anyone ever filled in theirs.
    """
    # Blobs are per-college: the unique key is (college_id, sha256), so the
    # same PDF uploaded at two institutions is stored once for each rather
    # than shared. Sharing it would let one college detect that another holds
    # the same document, and hand over the first uploader's filename.
    if college_id is None:
        college_id = getattr(user, "college_id", None) if user else None
    if college_id is None:
        college_id = await self_serve_tenant(db)

    original = safe_name(upload.filename or "")
    extension = _extension(original)
    if extension not in SIGNATURES:
        raise FileStoreError(
            "That file type is not accepted. Upload one of: " + ", ".join(ALLOWED) + "."
        )

    content = await _collect(upload)
    mime = _sniff(content, extension)
    digest = hashlib.sha256(content).hexdigest()

    existing = (await db.execute(
        select(StoredFile)
        .where(StoredFile.sha256 == digest)
        .where(StoredFile.college_id == college_id)
    )).scalar_one_or_none()
    if existing is not None:
        # Same bytes already held. The blob keeps the first upload's record -
        # who stored it first is a fact - but THIS upload's filename travels
        # back with it, so attaching a shared PDF under your own name does not
        # silently rename it to whatever the first person called it.
        logger.info(f"[Files] Reusing stored blob {digest[:12]} for {original}")
        existing._upload_name = original
        return existing

    key = _key_for(digest)
    backend = _mode()
    if backend == "s3":
        await _write_s3(f"documents/{key}", content, mime)
        key = f"documents/{key}"
    else:
        await _write_local(key, content)

    stored = StoredFile(
        college_id=college_id,
        sha256=digest,
        backend=backend,
        storage_key=key,
        original_name=original,
        mime_type=mime,
        byte_size=len(content),
        page_count=_page_count(content, mime),
        uploaded_by_id=user.id if user else None,
    )
    db.add(stored)
    try:
        await db.flush()
    except IntegrityError:
        # Another request stored the identical file between the lookup and the
        # insert. The blob is already written and identical, so adopt theirs.
        await db.rollback()
        found = (await db.execute(
            select(StoredFile)
            .where(StoredFile.sha256 == digest)
            .where(StoredFile.college_id == college_id)
        )).scalar_one_or_none()
        if found is None:
            raise FileStoreError("That file could not be stored. Try again.")
        found._upload_name = original
        return found

    logger.info(f"[Files] Stored {original} ({len(content)} bytes) as {digest[:12]} on {backend}")
    stored._upload_name = original
    return stored


def upload_name(stored: StoredFile) -> str:
    """
    What the person who just uploaded called this file.

    Falls back to the stored record's name for a blob nobody uploaded in this
    request - reading an existing row, for instance.
    """
    return getattr(stored, "_upload_name", None) or stored.original_name


async def read(stored: StoredFile) -> bytes:
    """The bytes, from whichever backend held them when they were written."""
    if stored.backend == "s3":
        return await _read_s3(stored.storage_key)
    return await _read_local(stored.storage_key)


async def verify(stored: StoredFile) -> bool:
    """Re-hash the stored bytes and confirm they still match the address."""
    try:
        content = await read(stored)
    except FileStoreError:
        return False
    return hashlib.sha256(content).hexdigest() == stored.sha256


def download_headers(stored: StoredFile, filename: Optional[str] = None) -> dict:
    """
    Headers that make a download a download.

    Always an attachment, never inline: a stored SVG or HTML rendered inline
    would run with this origin's privileges. `nosniff` stops a browser
    second-guessing the recorded type.
    """
    name = safe_name(filename or stored.original_name)
    ascii_name = name.encode("ascii", "ignore").decode() or "download"
    quoted = ascii_name.replace('"', "")
    return {
        "Content-Disposition": f'attachment; filename="{quoted}"',
        "Content-Length": str(stored.byte_size),
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "private, max-age=0, no-store",
    }


def describe(stored: Optional[StoredFile]) -> Optional[dict]:
    """What a screen needs to show about a file it may offer for download."""
    if stored is None:
        return None
    return {
        "id": str(stored.id),
        # This upload's name when there is one, so a response never echoes
        # back a filename belonging to whoever stored the identical bytes
        # first.
        "name": upload_name(stored),
        "mime_type": stored.mime_type,
        "byte_size": stored.byte_size,
        "size_label": human_size(stored.byte_size),
        "page_count": stored.page_count,
        "sha256": stored.sha256[:16],
        "uploaded_at": stored.uploaded_at,
    }


def human_size(size: Optional[int]) -> str:
    value = float(size or 0)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def limits() -> dict:
    """Advertised to the UI so it can refuse before spending an upload."""
    return {
        "max_mb": MAX_UPLOAD_MB,
        "max_bytes": MAX_UPLOAD_BYTES,
        "extensions": ALLOWED,
        "accept": ",".join(f".{e}" for e in ALLOWED),
    }
