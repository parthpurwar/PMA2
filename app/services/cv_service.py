from fastapi import UploadFile

from app.core.config import get_settings


def save_cv(resource_id: int, upload: UploadFile) -> str:
    if not upload.filename or not upload.filename.lower().endswith(".pdf"):
        raise ValueError("CV must be a PDF.")
    content = upload.file.read(5 * 1024 * 1024 + 1)
    if len(content) > 5 * 1024 * 1024 or not content.startswith(b"%PDF"):
        raise ValueError("CV must be a PDF no larger than 5 MB.")
    filename = f"resource_{resource_id}_cv.pdf"
    (get_settings().cv_dir / filename).write_bytes(content)
    return f"/static/cvs/{filename}"
