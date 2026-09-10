"""Read digital text directly and OCR scanned pages locally with Tesseract."""

import json
import re
import threading
import zipfile
from contextlib import closing
from pathlib import Path
from xml.etree import ElementTree

from ..errors import APIError

MAX_TEXT = 60000
MAX_PAGES = 30
MAX_PIXELS = 20_000_000
PDF_LOCK = threading.Lock()  # PDFium calls must not overlap across threads.
FORMATS = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".txt": "text/plain",
    ".csv": "text/csv",
    ".json": "application/json",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def ocr_image(image, language):
    import pytesseract

    if image.width * image.height > MAX_PIXELS:
        raise APIError("Image is too large for OCR. Use a smaller image.", 400)
    try:
        return pytesseract.image_to_string(image, lang=language, timeout=30)
    except pytesseract.TesseractNotFoundError:
        raise APIError("Install Tesseract on the server, then retry processing.", 503) from None
    except (pytesseract.TesseractError, RuntimeError):
        raise APIError(
            "OCR failed or timed out. Check OCR_LANGUAGE and the source image.", 422
        ) from None


def bounded_text(parts):
    text = "\n\n".join(parts).strip().replace("\x00", "")
    if len(text) > MAX_TEXT:
        raise APIError("Extracted text exceeds 60,000 characters. Split the document.", 413)
    return text


def extract_text(path, language="eng"):
    from PIL import Image, ImageOps

    suffix = Path(path).suffix.lower()
    parts = []
    try:
        if suffix in (".txt", ".csv", ".json"):
            text = Path(path).read_text(encoding="utf-8-sig")
            if suffix == ".json":
                json.loads(text)
            parts = [text]
        elif suffix == ".docx":
            with zipfile.ZipFile(path) as archive:
                if sum(item.file_size for item in archive.infolist()) > 30 * 1024 * 1024:
                    raise APIError("Expanded Word document is too large.", 413)
                xml = archive.read("word/document.xml")
            root = ElementTree.fromstring(xml)
            ns = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
            parts = [" ".join(node.itertext()) for node in root.iter(ns + "p")]
        elif suffix == ".pdf":
            import pypdfium2 as pdfium

            with PDF_LOCK, pdfium.PdfDocument(str(path)) as pdf:
                if len(pdf) > MAX_PAGES:
                    raise APIError("PDF exceeds 30 pages. Split the document.", 413)
                for number in range(len(pdf)):
                    with closing(pdf[number]) as page:
                        with closing(page.get_textpage()) as textpage:
                            text = textpage.get_text_range()
                        if not text.strip():
                            if page.get_width() * page.get_height() * 4 > MAX_PIXELS:
                                raise APIError("PDF page is too large for OCR.", 413)
                            bitmap = page.render(scale=2)
                            try:
                                text = ocr_image(bitmap.to_pil(), language)
                            finally:
                                bitmap.close()
                        parts.append(f"[Page {number + 1}]\n{text}")
                        bounded_text(parts)
        elif suffix in FORMATS:
            with Image.open(path) as picture:
                if getattr(picture, "n_frames", 1) > MAX_PAGES:
                    raise APIError("Image exceeds 30 frames. Split the document.", 413)
                for number in range(getattr(picture, "n_frames", 1)):
                    picture.seek(number)
                    if picture.width * picture.height > MAX_PIXELS:
                        raise APIError("Image is too large for OCR.", 413)
                    frame = ImageOps.exif_transpose(picture).convert("RGB")
                    try:
                        parts.append(ocr_image(frame, language))
                    finally:
                        frame.close()
                    bounded_text(parts)
        else:
            raise APIError("Unsupported document format.", 400)
        text = bounded_text(parts)
        if not text or not any(char.isalnum() for char in re.sub(r"\[Page \d+\]", "", text)):
            raise APIError("No readable text found in the document.", 422)
        return text
    except APIError:
        raise
    except ImportError:
        raise APIError(
            "Install the backend OCR dependencies, then retry processing.", 503
        ) from None
    except Exception:
        raise APIError("Cannot read this document. Check its format and contents.", 422) from None
