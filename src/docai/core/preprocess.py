"""Input preprocessing: PDF→image, resize, basic checks."""
import io

from PIL import Image

MAX_SIDE = 2048  # px — plenty for LLM OCR, keeps cost/latency down
MAX_FILE_MB = 15


class PreprocessError(ValueError):
    pass


def prepare_image(data: bytes, filename: str) -> tuple[bytes, str]:
    """Return (jpeg_bytes, mime_type) ready for the extractor."""
    if len(data) > MAX_FILE_MB * 1024 * 1024:
        raise PreprocessError(f"Файл больше {MAX_FILE_MB} МБ")

    name = filename.lower()
    if name.endswith(".pdf"):
        try:
            import pypdfium2 as pdfium
        except ImportError as e:
            raise PreprocessError("PDF поддержка не установлена (pypdfium2)") from e
        pdf = pdfium.PdfDocument(data)
        if len(pdf) == 0:
            raise PreprocessError("Пустой PDF")
        page = pdf[0]  # MVP: first page only
        img = page.render(scale=2.0).to_pil()
    else:
        try:
            img = Image.open(io.BytesIO(data))
        except Exception as e:
            raise PreprocessError("Не удалось прочитать изображение") from e

    img = img.convert("RGB")
    if max(img.size) > MAX_SIDE:
        img.thumbnail((MAX_SIDE, MAX_SIDE))

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue(), "image/jpeg"
