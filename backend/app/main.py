import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app import storage
from app.auth import create_access_token, get_current_user, hash_password, verify_password
from app.chatbot import process_message
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.knowledge import chunk_text, extract_text, retrieve_knowledge, safe_filename
from app.rate_limit import rate_limit_middleware
from app.schemas import (
    AuthRequest, ChatRequest, ChatResponse, ConversationDetail, ConversationSummary, DeleteResponse,
    DocumentSummary, HealthResponse, SourceReference, TokenResponse, UserResponse,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
settings = get_settings()
VERSION = "3.0.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="SmartAssist API",
    description="Production-ready SmartAssist API with persistent chat memory and a private document knowledge base.",
    version=VERSION,
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.middleware("http")(rate_limit_middleware)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    return response


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    first = exc.errors()[0] if exc.errors() else {}
    message = str(first.get("msg", "Invalid request."))
    if message.startswith("Value error, "):
        message = message[len("Value error, ") :]
    return JSONResponse(status_code=422, content={"detail": message})


def _title_from_message(message: str, limit: int = 48) -> str:
    value = " ".join(message.split())
    return value if len(value) <= limit else value[: limit - 1].rstrip() + "..."


def _token_response(user: dict) -> TokenResponse:
    return TokenResponse(access_token=create_access_token(user["id"], user["username"]), username=user["username"])


def _owned_conversation(conversation_id: str, user: dict) -> dict:
    conversation = storage.get_conversation(conversation_id, user["id"])
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return conversation


@app.get("/")
async def root():
    return {"service": "SmartAssist API", "status": "ok", "version": VERSION, "health": "/health", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse)
async def health():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        logger.exception("Database health check failed")
        raise HTTPException(status_code=503, detail="Database unavailable.")
    return {
        "status": "ok",
        "service": "SmartAssist API",
        "database": "ok",
        "ai_configured": bool(settings.ai_api_key),
        "version": VERSION,
    }


@app.post("/auth/register", response_model=TokenResponse)
async def register(request: AuthRequest):
    user = storage.create_user(request.username, hash_password(request.password))
    if user is None:
        raise HTTPException(status_code=409, detail="That username is already taken.")
    return _token_response(user)


@app.post("/auth/login", response_model=TokenResponse)
async def login(request: AuthRequest):
    user = storage.get_user_by_username(request.username)
    if not user or not verify_password(request.password, user.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Incorrect username or password.")
    return _token_response(user)


@app.get("/auth/me", response_model=UserResponse)
async def me(user: dict = Depends(get_current_user)):
    return UserResponse(username=user["username"])


@app.get("/conversations", response_model=list[ConversationSummary])
async def conversations(user: dict = Depends(get_current_user)):
    return storage.list_conversations(user["id"])


@app.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    conversation = _owned_conversation(conversation_id, user)
    return ConversationDetail(
        id=conversation["id"], title=conversation["title"], created_at=conversation["created_at"],
        updated_at=conversation["updated_at"], messages=conversation.get("messages", []),
    )


@app.delete("/conversations/{conversation_id}", response_model=DeleteResponse)
async def remove_conversation(conversation_id: str, user: dict = Depends(get_current_user)):
    if not storage.delete_conversation(conversation_id, user["id"]):
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return DeleteResponse(ok=True)


@app.get("/documents", response_model=list[DocumentSummary])
async def documents(user: dict = Depends(get_current_user)):
    return storage.list_documents(user["id"])


@app.post("/documents", response_model=DocumentSummary, status_code=201)
async def upload_document(file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    if storage.count_documents(user["id"]) >= settings.max_documents_per_user:
        raise HTTPException(status_code=409, detail=f"Document limit reached ({settings.max_documents_per_user}). Delete one first.")

    name = safe_filename(file.filename or "document")
    max_bytes = settings.max_upload_mb * 1024 * 1024
    data = await file.read(max_bytes + 1)
    await file.close()
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=f"File is too large. Maximum upload size is {settings.max_upload_mb} MB.")
    if not data:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")

    try:
        extracted = extract_text(name, data)
        chunks = chunk_text(extracted)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if not chunks:
        raise HTTPException(status_code=422, detail="No usable text chunks were found in this document.")

    saved = storage.create_document(
        user["id"], name=name, mime_type=file.content_type or "application/octet-stream",
        size_bytes=len(data), text=extracted, chunks=chunks,
    )
    return DocumentSummary(**saved)


@app.delete("/documents/{document_id}", response_model=DeleteResponse)
async def remove_document(document_id: str, user: dict = Depends(get_current_user)):
    if not storage.delete_document(document_id, user["id"]):
        raise HTTPException(status_code=404, detail="Document not found.")
    return DeleteResponse(ok=True)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, user: dict = Depends(get_current_user)):
    try:
        conversation = _owned_conversation(request.conversation_id, user) if request.conversation_id else storage.create_conversation(user["id"])
        history = conversation.get("messages", [])
        knowledge = retrieve_knowledge(user["id"], request.message)
        result = await process_message(request.message, history, knowledge)
        now = datetime.now(timezone.utc)
        title = None if any(item.get("role") == "user" for item in history) else _title_from_message(request.message)
        saved = storage.append_messages(
            conversation["id"], user["id"],
            [
                {"role": "user", "content": request.message, "created_at": now},
                {"role": "bot", "content": result.reply, "created_at": now},
            ],
            title=title,
        )
        if saved is None:
            raise HTTPException(status_code=404, detail="Conversation not found.")

        references = []
        seen_docs = set()
        if result.source == "rag":
            for item in knowledge:
                if item["document_id"] in seen_docs:
                    continue
                seen_docs.add(item["document_id"])
                excerpt = " ".join(item["content"].split())[:220]
                references.append(SourceReference(document_id=item["document_id"], name=item["name"], excerpt=excerpt))
        return ChatResponse(reply=result.reply, source=result.source, conversation_id=conversation["id"], sources=references)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to process chat message")
        raise HTTPException(status_code=500, detail="Something went wrong. Please try again.")
