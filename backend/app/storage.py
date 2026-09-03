from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.database import Conversation, Document, DocumentChunk, Message, SessionLocal, User, utcnow


def _iso(value):
    return value.isoformat() if value else None


def _user_dict(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "password_hash": user.password_hash,
        "created_at": _iso(user.created_at),
    }


def _message_dict(message: Message) -> dict:
    return {"role": message.role, "content": message.content, "timestamp": _iso(message.created_at)}


def _conversation_dict(conversation: Conversation, include_messages: bool = True) -> dict:
    data = {
        "id": conversation.id,
        "user_id": conversation.user_id,
        "title": conversation.title or "New chat",
        "created_at": _iso(conversation.created_at),
        "updated_at": _iso(conversation.updated_at),
    }
    if include_messages:
        data["messages"] = [_message_dict(item) for item in conversation.messages]
    return data


def _document_dict(document: Document, chunk_count: Optional[int] = None) -> dict:
    return {
        "id": document.id,
        "name": document.name,
        "mime_type": document.mime_type,
        "size_bytes": document.size_bytes,
        "char_count": document.char_count,
        "chunk_count": len(document.chunks) if chunk_count is None else chunk_count,
        "created_at": _iso(document.created_at),
    }


def get_user_by_username(username: str) -> Optional[dict]:
    needle = username.strip().lower()
    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.username == needle))
        return _user_dict(user) if user else None


def get_user_by_id(user_id: str) -> Optional[dict]:
    with SessionLocal() as db:
        user = db.get(User, user_id)
        return _user_dict(user) if user else None


def create_user(username: str, password_hash: str) -> Optional[dict]:
    normalized = username.strip().lower()
    with SessionLocal() as db:
        user = User(username=normalized, password_hash=password_hash)
        db.add(user)
        try:
            db.commit()
            db.refresh(user)
            return _user_dict(user)
        except IntegrityError:
            db.rollback()
            return None


def list_conversations(user_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.scalars(
            select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc())
        ).all()
        return [_conversation_dict(item, include_messages=False) for item in rows]


def get_conversation(conversation_id: str, user_id: str) -> Optional[dict]:
    with SessionLocal() as db:
        conversation = db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        return _conversation_dict(conversation) if conversation else None


def create_conversation(user_id: str, title: str = "New chat") -> dict:
    with SessionLocal() as db:
        conversation = Conversation(user_id=user_id, title=title)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
        return _conversation_dict(conversation)


def append_messages(conversation_id: str, user_id: str, messages: list[dict], title: Optional[str] = None) -> Optional[dict]:
    with SessionLocal() as db:
        conversation = db.scalar(
            select(Conversation)
            .options(selectinload(Conversation.messages))
            .where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        if not conversation:
            return None
        for item in messages:
            conversation.messages.append(
                Message(role=item["role"], content=item["content"], created_at=item.get("created_at") or utcnow())
            )
        conversation.updated_at = utcnow()
        if title:
            conversation.title = title
        db.commit()
        refreshed = db.scalar(
            select(Conversation).options(selectinload(Conversation.messages)).where(Conversation.id == conversation_id)
        )
        return _conversation_dict(refreshed) if refreshed else None


def delete_conversation(conversation_id: str, user_id: str) -> bool:
    with SessionLocal() as db:
        conversation = db.scalar(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id)
        )
        if not conversation:
            return False
        db.delete(conversation)
        db.commit()
        return True


def count_documents(user_id: str) -> int:
    with SessionLocal() as db:
        return int(db.scalar(select(func.count(Document.id)).where(Document.user_id == user_id)) or 0)


def create_document(user_id: str, name: str, mime_type: str, size_bytes: int, text: str, chunks: list[str]) -> dict:
    with SessionLocal() as db:
        document = Document(
            user_id=user_id,
            name=name,
            mime_type=mime_type or "application/octet-stream",
            size_bytes=size_bytes,
            char_count=len(text),
        )
        document.chunks = [DocumentChunk(chunk_index=index, content=content) for index, content in enumerate(chunks)]
        db.add(document)
        db.commit()
        db.refresh(document)
        return _document_dict(document, len(chunks))


def list_documents(user_id: str) -> list[dict]:
    with SessionLocal() as db:
        rows = db.execute(
            select(Document, func.count(DocumentChunk.id))
            .outerjoin(DocumentChunk, DocumentChunk.document_id == Document.id)
            .where(Document.user_id == user_id)
            .group_by(Document.id)
            .order_by(Document.created_at.desc())
        ).all()
        return [_document_dict(document, int(count or 0)) for document, count in rows]


def delete_document(document_id: str, user_id: str) -> bool:
    with SessionLocal() as db:
        document = db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))
        if not document:
            return False
        db.delete(document)
        db.commit()
        return True


def search_chunks_for_user(user_id: str, terms: list[str], limit: int = 800) -> list[dict]:
    unique_terms = []
    for term in terms:
        lowered = term.lower().strip()
        if lowered and lowered not in unique_terms:
            unique_terms.append(lowered)
        if len(unique_terms) >= 10:
            break
    if not unique_terms:
        return []

    conditions = []
    for term in unique_terms:
        escaped = term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        conditions.append(DocumentChunk.content.ilike(f"%{escaped}%", escape="\\"))

    with SessionLocal() as db:
        rows = db.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.user_id == user_id, or_(*conditions))
            .order_by(Document.created_at.desc(), DocumentChunk.chunk_index.asc())
            .limit(limit)
        ).all()
        return [
            {
                "document_id": document.id,
                "name": document.name,
                "chunk_index": chunk.chunk_index,
                "content": chunk.content,
            }
            for chunk, document in rows
        ]
