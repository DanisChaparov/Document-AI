"""LLM-based document extraction. Gemini Flash primary, easy to add fallbacks."""
import json
import os
import time

from google import genai
from google.genai import types

from docai.models.schemas import ExtractionResult, Invoice

MODEL = os.getenv("EXTRACTION_MODEL", "gemini-2.0-flash")

PROMPT = """Ты — система извлечения данных из бухгалтерских документов Казахстана
(счета-фактуры, накладные, акты, чеки). Документы могут быть на русском
или казахском языке.

Извлеки данные из изображения документа и верни СТРОГО валидный JSON:
{
  "doc_type": "счёт-фактура | накладная | акт | чек | unknown",
  "doc_number": "строка или null",
  "doc_date": "YYYY-MM-DD или null",
  "supplier_name": "строка",
  "supplier_bin": "12 цифр или null",
  "buyer_name": "строка или null",
  "buyer_bin": "12 цифр или null",
  "line_items": [{"name": "...", "quantity": число, "unit": "...", "price": число, "total": число}],
  "subtotal": число или null,
  "vat_amount": число или null,
  "total": число,
  "currency": "KZT",
  "confidence": {"supplier_bin": 0.99, "total": 0.85}
}

Правила:
- БИН/ИИН — ровно 12 цифр. Если не уверен — null.
- Суммы — числа без пробелов и символов валюты.
- Если поле отсутствует или нечитаемо — null, НЕ выдумывай.
- Для каждого извлечённого поля укажи confidence от 0 до 1.
- Если документ не бухгалтерский — верни {"doc_type": "unknown"}.
Верни ТОЛЬКО JSON, без пояснений и markdown."""


def _parse_response(text: str) -> Invoice:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return Invoice.model_validate(json.loads(text))


def extract(image_bytes: bytes, mime_type: str = "image/jpeg") -> ExtractionResult:
    """Extract structured invoice data from a document image."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    start = time.monotonic()

    last_error: Exception | None = None
    for attempt in range(2):  # one retry on invalid JSON
        response = client.models.generate_content(
            model=MODEL,
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                PROMPT,
            ],
        )
        try:
            invoice = _parse_response(response.text)
            break
        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
    else:
        raise ValueError(f"Model returned invalid JSON twice: {last_error}")

    return ExtractionResult(
        invoice=invoice,
        model_used=MODEL,
        latency_ms=int((time.monotonic() - start) * 1000),
    )
