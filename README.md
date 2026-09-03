# SmartAssist V2

SmartAssist V2 is a deploy-ready full-stack AI assistant with persistent user accounts, conversation memory, private document knowledge/RAG, drag-and-drop file ingestion, source references, rate limiting, and production deployment configuration.

It keeps the repository intentionally small instead of embedding a full third-party AI platform. The provider boundary is OpenAI-compatible, so you can use OpenAI, Groq, or place LiteLLM in front later without changing the SmartAssist frontend.

## What works

- Register/login with PBKDF2 password hashing and signed JWT sessions
- Persistent PostgreSQL conversations in production; SQLite for local development
- Conversation memory is sent back to the AI for follow-up questions
- Narrow FAQ routing that does not hijack unrelated questions
- OpenAI-compatible AI provider integration
- Drag/drop private knowledge uploads
- PDF, DOCX, TXT, Markdown, CSV, and JSON text extraction
- Chunked knowledge storage per user
- Lightweight BM25-style retrieval before AI calls
- Uploaded content treated as **untrusted reference data** to reduce prompt-injection risk
- Knowledge-assisted replies return source cards
- Per-user conversation and document ownership checks
- Message/upload size limits and auth/chat/upload rate limiting
- Live backend health state in the UI
- Production CORS configuration
- Security response headers
- GitHub Actions backend tests + frontend production build gate
- Render Blueprint + Vercel configuration

## Architecture

```text
Browser / React + Vite
        |
        | JWT
        v
FastAPI / SmartAssist API
        |
        +---- Auth + ownership
        +---- Conversation memory
        +---- Knowledge ingestion
        |       PDF/DOCX/TXT/MD/CSV/JSON
        |               |
        |             chunks
        |               |
        |         lexical retrieval
        |               |
        +---------> AI context
        |
        +---- OpenAI-compatible AI API
        |       OpenAI / Groq / LiteLLM / similar
        |
        +---- PostgreSQL (production)
              users / conversations / messages
              documents / document_chunks
```

## Repository structure

```text
smartassist-chatbot/
├── backend/
│   ├── app/
│   │   ├── auth.py
│   │   ├── chatbot.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── knowledge.py
│   │   ├── main.py
│   │   ├── rate_limit.py
│   │   ├── responses.py
│   │   ├── schemas.py
│   │   └── storage.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatWindow.jsx
│   │   │   ├── ConversationList.jsx
│   │   │   ├── Header.jsx
│   │   │   ├── KnowledgePanel.jsx
│   │   │   ├── LoginPage.jsx
│   │   │   ├── Message.jsx
│   │   │   └── MessageInput.jsx
│   │   ├── services/chatbotApi.js
│   │   ├── App.jsx
│   │   └── index.css
│   ├── .env.example
│   └── package.json
├── .github/workflows/ci.yml
├── render.yaml
├── vercel.json
├── DEPLOY_CHECKLIST.md
├── FIXES.md
└── OPEN_SOURCE_STRATEGY.md
```

## Local setup

### Backend

```bash
cd backend
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

macOS/Linux:

```bash
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Set a real random `SECRET_KEY` in `backend/.env`:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Add an AI provider key. Example OpenAI:

```text
AI_API_KEY=...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
```

Or Groq:

```text
AI_API_KEY=...
AI_BASE_URL=https://api.groq.com/openai/v1
AI_MODEL=openai/gpt-oss-20b
```

Then run:

```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
```

Copy `.env.example` to `.env` and keep:

```text
VITE_API_URL=http://localhost:8000
```

Then:

```bash
npm run dev
```

## Knowledge workflow

1. Log in.
2. Open **Knowledge**.
3. Drag/drop a supported file.
4. SmartAssist extracts readable text, chunks it, and stores the chunks under the current user.
5. Ask a question related to the uploaded content.
6. Relevant chunks are added to the AI request as untrusted reference material.
7. When knowledge was used, the API returns `source: "rag"` and source cards appear under the answer.

The current retriever is intentionally local and dependency-light. It is isolated in `backend/app/knowledge.py`, so moving to embeddings + pgvector later does not require rewriting auth, storage APIs, or the frontend.

## API

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | No | DB/AI/version status |
| POST | `/auth/register` | No | Create account |
| POST | `/auth/login` | No | Login |
| GET | `/auth/me` | Yes | Current user |
| GET | `/conversations` | Yes | List chats |
| GET | `/conversations/{id}` | Yes | Load one chat |
| DELETE | `/conversations/{id}` | Yes | Delete chat |
| POST | `/chat` | Yes | Send message |
| GET | `/documents` | Yes | List private knowledge files |
| POST | `/documents` | Yes | Upload/index knowledge file |
| DELETE | `/documents/{id}` | Yes | Remove knowledge file |

Interactive backend docs are available at `/docs`.

## Important environment variables

```text
APP_ENV=development
DATABASE_URL=sqlite:///./data/smartassist.db
SECRET_KEY=...

AI_API_KEY=...
AI_BASE_URL=https://api.openai.com/v1
AI_MODEL=gpt-4o-mini
AI_TIMEOUT=30

CORS_ORIGINS=http://localhost:5173
MAX_MESSAGE_CHARS=8000
MAX_HISTORY_MESSAGES=16
AUTH_RATE_LIMIT_PER_MINUTE=10
CHAT_RATE_LIMIT_PER_MINUTE=30
UPLOAD_RATE_LIMIT_PER_MINUTE=8
MAX_UPLOAD_MB=10
MAX_DOCUMENT_CHARS=1500000
MAX_DOCUMENTS_PER_USER=50
RAG_TOP_K=5
RAG_MAX_CONTEXT_CHARS=8000
```

## Tests

```bash
cd backend
python -m pytest -q
```

The supplied suite covers auth, conversation ownership, memory, message limits, document ingestion, DOCX extraction, unsupported files, document isolation, RAG retrieval, health/security headers, and source references.

GitHub Actions also performs a frontend production build on every push/PR.

## Deploy

Use `DEPLOY_CHECKLIST.md` for the shortest path.

- **Render**: `render.yaml` provisions the API and PostgreSQL for a quick demo.
- **Vercel**: root `vercel.json` installs/builds `frontend/` from the same repository.
- Set `VITE_API_URL` in Vercel to the Render API URL.
- Set `CORS_ORIGINS` in Render to the exact Vercel production origin.

### Render Free Postgres warning

Render's Free Postgres is useful for demos but currently has a 1 GB limit and expires after 30 days. For a real persistent deployment, upgrade it or replace `DATABASE_URL` with a persistent PostgreSQL provider such as Neon or Supabase.

## Open-source design choices

See `OPEN_SOURCE_STRATEGY.md`. SmartAssist uses mature open-source libraries directly and adopts architecture patterns from larger AI projects without copying an entire platform into this small repository.
