"""FastAPI app: web frontend + extraction API."""
import io
import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse

load_dotenv()  # reads .env from the project root

from docai.core.exporter import invoices_to_xlsx
from docai.core.preprocess import PreprocessError, prepare_image
from docai.core.validator import validate_invoice
from docai.db import repository

app = FastAPI(title="DocAI KZ", version="0.1.0")

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "..", "static")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    with open(os.path.join(_STATIC_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/extract")
async def extract_document(file: UploadFile = File(...)) -> dict:
    from docai.core.extractor import extract  # imported here so app runs without API key

    data = await file.read()
    try:
        image_bytes, mime = prepare_image(data, file.filename or "upload.jpg")
    except PreprocessError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = extract(image_bytes, mime)
    except KeyError:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY не настроен на сервере")
    except ValueError as e:
        raise HTTPException(status_code=502, detail=f"Ошибка распознавания: {e}")

    result.issues = validate_invoice(result.invoice)
    row_id = repository.save(result, file.filename or "")

    return {
        "id": row_id,
        "invoice": result.invoice.model_dump(mode="json"),
        "issues": [i.model_dump() for i in result.issues],
        "model_used": result.model_used,
        "latency_ms": result.latency_ms,
    }


@app.get("/api/export.xlsx")
def export_xlsx() -> StreamingResponse:
    invoices = repository.list_invoices()
    if not invoices:
        raise HTTPException(status_code=404, detail="Нет документов для экспорта")
    data = invoices_to_xlsx(invoices)
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=docai_export.xlsx"},
    )
