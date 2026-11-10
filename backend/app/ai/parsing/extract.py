"""Text extraction from PDF (PyMuPDF) and DOCX (python-docx)."""
import io


class ExtractionError(Exception):
    pass


def extract_pdf(data: bytes) -> tuple[str, dict]:
    import pymupdf as fitz

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:  # corrupted file
        raise ExtractionError("The PDF could not be opened (it may be corrupted).") from e
    if doc.needs_pass:
        raise ExtractionError("The PDF is password-protected.")
    pages = []
    image_count = 0
    for page in doc:
        pages.append(page.get_text("text", sort=True))
        image_count += len(page.get_images(full=False))
    text = "\n".join(pages)
    meta = {"pages": doc.page_count, "images": image_count}
    doc.close()
    if len(text.strip()) < 30:
        if image_count:
            raise ExtractionError(
                "No text found. This looks like a scanned (image-only) PDF; OCR is not supported."
            )
        raise ExtractionError("No text found in this PDF.")
    return text, meta


def extract_docx(data: bytes) -> tuple[str, dict]:
    import docx

    try:
        d = docx.Document(io.BytesIO(data))
    except Exception as e:
        raise ExtractionError("The DOCX could not be opened (it may be corrupted).") from e
    lines: list[str] = []
    for p in d.paragraphs:
        lines.append(p.text)
    for table in d.tables:
        for row in table.rows:
            seen = []
            for cell in row.cells:
                t = cell.text.strip()
                if t and t not in seen:
                    seen.append(t)
            if seen:
                lines.append(" | ".join(seen))
    text = "\n".join(lines)
    if len(text.strip()) < 30:
        raise ExtractionError("No text found in this DOCX.")
    return text, {"paragraphs": len(d.paragraphs), "tables": len(d.tables)}


def extract_text(data: bytes, kind: str) -> tuple[str, dict]:
    if kind == "pdf":
        return extract_pdf(data)
    if kind == "docx":
        return extract_docx(data)
    raise ExtractionError(f"Unsupported file type: {kind}")
