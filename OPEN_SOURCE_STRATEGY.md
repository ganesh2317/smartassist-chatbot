# Open-source strategy used for SmartAssist V2

SmartAssist V2 deliberately reuses mature open-source infrastructure instead of turning the repository into a giant framework fork.

## Used directly

- **FastAPI** — API framework (MIT)
- **SQLAlchemy** — database ORM (MIT)
- **PyJWT** — JWT implementation (MIT)
- **pypdf** — PDF text extraction (BSD-3-Clause)
- **React** — frontend component system (MIT)
- **Vite** — frontend build tooling (MIT)
- **PostgreSQL / psycopg** — persistent production database

## Architecture patterns adopted

The design was checked against maintained projects such as Langflow, LibreChat, AnythingLLM, LiteLLM, Supabase, pgvector, and Langfuse. We intentionally do **not** vendor their entire codebases. Doing so would make this internship/portfolio repository much larger, harder to audit, and much harder to deploy on Render/Vercel.

The useful patterns we adopted are:

- document knowledge/RAG separated from chat UI;
- OpenAI-compatible provider boundary so LiteLLM can be inserted later without rewriting SmartAssist;
- persistent SQL conversations instead of JSON files;
- private per-user document ownership;
- drag/drop knowledge ingestion;
- untrusted-document prompt isolation;
- source references on knowledge-assisted responses;
- observable health/config state;
- CI as a deploy gate.

## Why SmartAssist does not bundle Langflow/LibreChat/AnythingLLM

Those are full platforms. Bundling one would replace SmartAssist rather than strengthen it. SmartAssist keeps a small product surface and can integrate with them later through APIs if the project grows.

## Upgrade path

The current knowledge search is a lightweight BM25-style lexical retriever stored in PostgreSQL/SQLite. It has zero external vector-service dependency and is appropriate for a small deployment. The retrieval module is isolated in `backend/app/knowledge.py`, so it can later be swapped for pgvector/embeddings without changing the frontend or auth model.
