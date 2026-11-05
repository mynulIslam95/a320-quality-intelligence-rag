# A320 Quality Intelligence RAG

An independent aircraft-quality question-answering application built with FastAPI, SQLite FTS5 and optional Google Gemini API. Uses fictional records only. Not affiliated with Airbus or connected to Skywise.

## Start
```bash
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Open http://127.0.0.1:8000.

The service automatically generates 120 synthetic aircraft documents on first start. Ask about `SIM-MSN-10042` or quality trends. Without an API key, the service provides retrieved evidence only. To enable generated answers set `GEMINI_API_KEY` in the environment. Never commit keys.

## Tests
```bash
python -m unittest discover -s tests -v
```

## Cross-project use
The synthetic IDs align with [A320 Quality Data Platform](https://github.com/mynulIslam95/a320-quality-data-platform) and [Quality Control Tower](https://github.com/mynulIslam95/a320-quality-control-tower). You can optionally set `QUALITY_DB` to a copy of Project 1's validated SQLite database, then restart the service to regenerate documents. The source database is read-only.

The retrieval method is **SQLite FTS5 lexical search**, not vector search or pgvector. Gemini is used for optional answer generation. Source filenames are returned as citations. Model output may be inaccurate and must not be used for airworthiness decisions. The service has no authentication and must be run locally.
