from pathlib import Path  # Filesystem path handling
from typing import Any, Dict, List  # Type hints for structured metadata results

# exifread is robust for JPEG EXIF; Pillow can provide PNG info dictionaries
import exifread  # Extracts EXIF tags (e.g., camera model, timestamps, GPS)
from PIL import Image  # General image handling; exposes PNG text chunks via .info
from PyPDF2 import PdfReader  # Reads PDF document info (author, title, creation)
from docx import Document  # Reads DOCX core properties (author, created/modified)


def _safe_open_image(path: Path) -> Image.Image | None:
    """Open an image with Pillow, returning None on errors.

    Pillow supports a wide range of formats; this is primarily used for PNG
    metadata via the .info dictionary, since PNG typically does not have EXIF.
    Returning None on failures keeps the pipeline robust if an image file is
    corrupted or unsupported.
    """
    try:
        return Image.open(path)
    except Exception:
        return None


def _extract_exif_with_exifread(path: Path) -> Dict[str, Any]:
    """Extract a subset of EXIF tags from a JPEG using exifread.

    The function returns a simple dictionary with common keys (camera make/model,
    timestamp, GPS if available). Non-obvious EXIF keys are omitted for clarity.
    """
    meta: Dict[str, Any] = {}
    try:
        with path.open("rb") as f:
            # details=False avoids deep parsing of less relevant tags, speeding up processing
            tags = exifread.process_file(f, details=False)
        # Commonly useful EXIF tags
        for key in [
            "EXIF DateTimeOriginal",
            "Image Model",
            "Image Make",
            "EXIF LensModel",
            "GPS GPSLatitude",
            "GPS GPSLongitude",
        ]:
            if key in tags:
                meta[key] = str(tags[key])
    except Exception:
        return {}
    return meta


def _extract_png_info(path: Path) -> Dict[str, Any]:
    """Extract PNG metadata via Pillow's info dict.

    PNGs do not typically contain EXIF; Pillow exposes text chunks in Image.info.
    These may include creation tools, comments, or custom application data.
    """
    meta: Dict[str, Any] = {}
    img = _safe_open_image(path)
    if img and hasattr(img, "info") and isinstance(img.info, dict):
        # Copy info keys into a simple metadata dict
        for k, v in img.info.items():
            meta[str(k)] = str(v)
    return meta


def _extract_pdf_metadata(path: Path) -> Dict[str, Any]:
    """Extract document metadata from a PDF via PyPDF2.PdfReader.

    PDF metadata often includes author, title, producer, and creation/mod times.
    """
    meta: Dict[str, Any] = {}
    try:
        reader = PdfReader(path)
        info = reader.metadata  # returns a DocumentInformation-like mapping
        if info:
            # Normalize keys to simple strings; PyPDF2 may prefix keys with '/' characters
            for k, v in dict(info).items():
                meta[str(k).lstrip("/")] = str(v)
    except Exception:
        return {}
    return meta


def _extract_docx_metadata(path: Path) -> Dict[str, Any]:
    """Extract core properties from a DOCX using python-docx.

    Many organizations rely on these properties for document management; they
    are useful in DFIR to understand authorship and modification timelines.
    """
    meta: Dict[str, Any] = {}
    try:
        doc = Document(path)
        props = doc.core_properties
        # Collect a subset of useful properties
        meta["author"] = props.author
        meta["last_modified_by"] = props.last_modified_by
        meta["created"] = str(props.created)
        meta["modified"] = str(props.modified)
        meta["title"] = props.title
        meta["subject"] = props.subject
        meta["category"] = props.category
        meta["comments"] = props.comments
        meta["keywords"] = props.keywords
    except Exception:
        return {}
    return meta


def extract_metadata_for_case(case_path: Path) -> List[Dict[str, Any]]:
    """Walk the case directory and extract metadata for supported file types.

    Supported:
    - Images: .jpg/.jpeg via EXIF (exifread), .png via Pillow .info
    - PDFs: PyPDF2 reader metadata
    - DOCX: python-docx core properties

    Returns a list of entries: {path, metadata: {key: value, ...}}.
    """
    results: List[Dict[str, Any]] = []
    for path in case_path.rglob("*"):
        if not path.is_file():
            continue

        suffix = path.suffix.lower()
        metadata: Dict[str, Any] | None = None

        if suffix in {".jpg", ".jpeg"}:
            metadata = _extract_exif_with_exifread(path)
        elif suffix == ".png":
            metadata = _extract_png_info(path)
        elif suffix == ".pdf":
            metadata = _extract_pdf_metadata(path)
        elif suffix == ".docx":
            metadata = _extract_docx_metadata(path)
        else:
            metadata = None

        if metadata is not None and metadata:
            results.append({"path": str(path), "metadata": metadata})

    return results