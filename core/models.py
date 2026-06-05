"""SQLAlchemy models for ingested documents and their chunks (the metadata of record)."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source: Mapped[str] = mapped_column(String(1024))
    modality: Mapped[str] = mapped_column(String(32), default="text")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    chunks: Mapped[list[Chunk]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)  # == its Qdrant point id
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column()
    text: Mapped[str] = mapped_column(Text)

    document: Mapped[Document] = relationship(back_populates="chunks")


class EvalQuestion(Base):
    __tablename__ = "eval_questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_id: Mapped[str] = mapped_column(String(36))  # the relevant chunk (for recall@k)
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    is_gold: Mapped[bool] = mapped_column(default=False)  # hand-labeled vs generated


class Clarification(Base):
    """A file whose subject the ingest detector couldn't pin to a name, pending a user's answer.

    Answering it tags the document's chunks with the chosen entity so retrieval can tell two
    people's photos apart. Kept loose (no FK) so a clarification survives independent of the doc.
    """

    __tablename__ = "clarifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    bucket: Mapped[str] = mapped_column(String(255))
    document_id: Mapped[str] = mapped_column(String(36))
    source: Mapped[str] = mapped_column(String(1024))
    modality: Mapped[str] = mapped_column(String(32), default="text")
    subject: Mapped[str] = mapped_column(Text)  # "the person in this photo"
    question: Mapped[str] = mapped_column(Text)  # "Who is the person in this image?"
    candidates: Mapped[str] = mapped_column(Text, default="[]")  # JSON: bucket names that may fit
    status: Mapped[str] = mapped_column(String(16), default="pending")  # pending|answered|dismissed
    answer: Mapped[str] = mapped_column(Text, default="")  # the entity the user chose/typed
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
