"""Upload validation and safe storage. Uploaded files are never executed."""
import hashlib
import io
import uuid
import zipfile
from pathlib import Path

from app.core.config import get_settings
from app.core.exceptions import AppError

ALLOWED = {".pdf": "pdf", ".docx": "docx"}


class FileValidationError(AppError):
    status_code = 400
    code = "invalid_file"


def detect_type(filename: str, data: bytes) -> str:
    """Check extension AND file signature. Returns 'pdf' or 'docx'."""
    ext = Path(filename or "").suffix.lower()
    if ext not in ALLOWED:
        raise FileValidationError("Only PDF and DOCX files are allowed.", code="unsupported_type")
    if not data:
        raise FileValidationError("The file is empty.", code="empty_file")
    if len(data) > get_settings().max_upload_bytes:
        raise FileValidationError(
            f"File is larger than {get_settings().max_upload_size_mb} MB.", code="file_too_large", status_code=413
        )
    kind = ALLOWED[ext]
    if kind == "pdf":
        if not data[:1024].lstrip().startswith(b"%PDF-"):
            raise FileValidationError("This file is not a valid PDF.", code="bad_signature")
    else:
        if not data.startswith(b"PK\x03\x04"):
            raise FileValidationError("This file is not a valid DOCX.", code="bad_signature")
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as z:
                if "word/document.xml" not in z.namelist():
                    raise FileValidationError("This file is not a valid DOCX.", code="bad_signature")
        except zipfile.BadZipFile:
            raise FileValidationError("This DOCX file is corrupted.", code="corrupted_file") from None
    return kind


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def store_upload(data: bytes, kind: str) -> str:
    """Save under a random server-side name. Returns the path relative to UPLOAD_DIR."""
    root = get_settings().upload_path
    root.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{kind}"
    (root / name).write_bytes(data)
    return name


def resolve_stored(stored_path: str) -> Path:
    """Turn a stored relative name into an absolute path, refusing anything outside UPLOAD_DIR."""
    root = get_settings().upload_path.resolve()
    p = (root / stored_path).resolve()
    if root not in p.parents:
        raise AppError("Invalid file path.", code="invalid_path", status_code=400)
    return p


def safe_display_name(filename: str) -> str:
    name = Path(filename or "resume").name
    return "".join(ch for ch in name if ch.isprintable() and ch not in '\\/:*?"<>|')[:200] or "resume"
