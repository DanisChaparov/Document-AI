# DocAI — распознавание счетов для бизнеса Казахстана

Upload a photo/scan of an invoice (счёт-фактура, накладная, акт, чек) — get structured data with validation and Excel export. Supports Russian and Kazakh documents.

> 📸 → 🤖 → ✅ → 📊 &nbsp; *Photo → LLM extraction → business-rule validation → Excel*

<!-- TODO: add demo GIF here -->

## Features

- Vision LLM extraction (Gemini Flash) — works with photos, scans, and PDFs
- Business-rule validation: БИН/ИИН checksum, VAT math, line-item totals, date sanity
- Per-field confidence scores — low-confidence fields flagged for manual review
- Excel export (summary + line items)
- Clean web UI, single Docker container, SQLite storage

## Quickstart

```bash
git clone https://github.com/YOUR_USERNAME/docai && cd docai
cp .env.example .env          # add your GEMINI_API_KEY (free at aistudio.google.com)
pip install -e ".[dev]"
uvicorn docai.api.app:app --reload
# open http://localhost:8000
```

Or with Docker:

```bash
docker build -t docai .
docker run -p 8000:8000 --env-file .env -v docai_data:/data docai
```

## Run tests

```bash
pytest -v
```

## Architecture

```
[Web UI] → [FastAPI] → preprocess (PDF→JPEG, resize)
                     → extractor  (Gemini Flash → JSON)
                     → validator  (БИН checksum, math, dates, confidence)
                     → SQLite     → Excel export
```

## Accuracy

<!-- TODO: measure on your fixture set and put real numbers here, e.g.:
| Field | Accuracy (n=500 real invoices) |
|-------|-------------------------------|
| total | 96.4% | -->

## Roadmap

- [ ] Telegram bot channel (same backend)
- [ ] Batch upload
- [ ] 1С export format
- [ ] User accounts + Kaspi payments

## Notes

- VAT rate is set in `src/docai/core/validator.py` — verify the current KZ rate.
- MVP processes only the first page of PDFs.
