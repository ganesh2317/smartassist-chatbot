# SmartAssist V2 — fixes and upgrades

## Critical issues fixed

### Production data loss
**Before:** users and conversations were JSON files on ephemeral Render disk.

**Now:** SQLAlchemy-backed persistence uses PostgreSQL in production and SQLite locally. The Render Blueprint provisions PostgreSQL for a demo deployment.

### No conversation memory
**Before:** only the latest user message was sent to the AI provider.

**Now:** recent user/assistant turns are reconstructed and supplied to the model.

### FAQ false positives
**Before:** broad keywords such as `help`, `contact`, and `what time` could hijack unrelated questions.

**Now:** predefined responses use narrow SmartAssist-specific patterns.

### Insecure JWT fallback
**Before:** missing `SECRET_KEY` silently used a known demo secret.

**Now:** the backend refuses to start without `SECRET_KEY`.

### Frontend localhost production fallback
**Before:** a misconfigured Vercel build could silently point real users at `localhost:8000`.

**Now:** production builds fail when `VITE_API_URL` is missing.

### Send-success/history-refresh failure
**Before:** a successful chat could be displayed as failed if the sidebar refresh failed afterwards.

**Now:** chat and history-refresh errors are handled separately.

### Empty chat spam
**Before:** clicking New Chat created empty server records.

**Now:** New Chat is local UI state; a conversation is created only when the first message is sent.

## SmartAssist V2 additions

- Private per-user Knowledge panel
- Native drag-and-drop uploads
- PDF text extraction with pypdf
- DOCX text extraction without requiring Microsoft Word
- TXT/MD/CSV/JSON ingestion
- Chunking with overlap
- Lightweight relevance retrieval
- RAG context isolation from instructions embedded in documents
- Source cards for knowledge-assisted answers
- Document list/delete API
- Document ownership enforcement
- Upload file-size/document-count/text-size limits
- Separate upload rate limit
- Security response headers
- Health response reports DB, AI configuration, and version
- OpenAI-compatible AI boundary ready for Groq/OpenAI/LiteLLM
- Root Vercel configuration for the monorepo
- Render Blueprint with PostgreSQL
- GitHub Actions CI

## Verification completed for this ZIP

- Python bytecode compilation passes.
- Backend regression suite: **14/14 tests passing**.
- All frontend `.js` and `.jsx` files pass a JavaScript/JSX parser syntax check.
- `render.yaml`, CI YAML, and JSON config files are parsed before packaging.
- ZIP integrity is checked after creation.

A full local Vite build requires downloading npm packages. The execution sandbox used to prepare this ZIP could not reliably reach npm, so the repository's GitHub Actions workflow performs the authoritative `npm install` + production `npm run build` gate on push/PR.
