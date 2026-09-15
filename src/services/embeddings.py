"""Text chunking and embedding generation (NEW).

Matches the ai-data-ingestion-service configuration:
- OpenAI model: configured by EMBEDDING_MODEL
- local model: configured by LOCAL_EMBEDDING_MODEL
- token-based splitting via tiktoken
- L2 normalisation before storing
- batched embedding calls
"""

import math

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.config.settings import settings
from src.utils.logger import get_logger

logger = get_logger(__name__)


def _token_length_fn():
    """Return a length function using tiktoken for the configured embedding model."""
    import tiktoken
    try:
        enc = tiktoken.encoding_for_model(settings.embedding_model)
    except Exception:
        enc = tiktoken.get_encoding("cl100k_base")

    def _len(text: str) -> int:
        return len(enc.encode(text))

    return _len


def chunk_text(text: str, doc_type: str = "document") -> list[str]:
    """Split text into token-sized chunks using RecursiveCharacterTextSplitter.

    Falls back to the default splitter if a language-aware one cannot be built.
    Never raises — returns [] on error.
    """
    try:
        length_fn = _token_length_fn()

        if doc_type == "git":
            try:
                from langchain_text_splitters import Language
                splitter = RecursiveCharacterTextSplitter.from_language(
                    language=Language.PYTHON,
                    chunk_size=settings.chunk_size_tokens,
                    chunk_overlap=settings.chunk_overlap_tokens,
                    length_function=length_fn,
                )
            except Exception:
                splitter = RecursiveCharacterTextSplitter(
                    chunk_size=settings.chunk_size_tokens,
                    chunk_overlap=settings.chunk_overlap_tokens,
                    length_function=length_fn,
                )
        else:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size_tokens,
                chunk_overlap=settings.chunk_overlap_tokens,
                length_function=length_fn,
            )

        return splitter.split_text(text)
    except Exception as exc:  # noqa: BLE001
        logger.error("[chunk_text] failed doc_type=%s: %s", doc_type, exc)
        return []


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Generate embeddings via OpenAI, in batches, with optional L2 normalisation.

    Never raises — returns [] on error.
    """
    try:
        from langchain_openai import OpenAIEmbeddings

        embedder = OpenAIEmbeddings(
            model=settings.embedding_model,
            openai_api_key=settings.openai_api_key,
        )
        all_embeddings: list[list[float]] = []
        batch_size = settings.embedding_batch_size

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = embedder.embed_documents(batch)
            all_embeddings.extend(batch_embeddings)
            logger.debug("[embed_texts] batch %d/%d done", i // batch_size + 1,
                         (len(texts) + batch_size - 1) // batch_size)

        if settings.normalize_embeddings:
            normed: list[list[float]] = []
            for v in all_embeddings:
                mag = math.sqrt(sum(x * x for x in v)) or 1.0
                normed.append([x / mag for x in v])
            all_embeddings = normed

        return all_embeddings
    except Exception as exc:  # noqa: BLE001
        logger.error("[embed_texts] failed: %s", exc)
        return []


def embed_texts_local(texts: list[str]) -> list[list[float]]:
    """Generate embeddings using a local sentence-transformers model.

    Used for Knowledge Base document ingestion only (writes to the
    new ai_local_knowledge_base_embeddings Milvus collection). The
    original embed_texts() using OpenAI remains unchanged for all
    other callers (Vanna RAG, SQL auto-database-selection).

    Never raises — returns [] on any error, matching embed_texts()'s
    error-handling pattern.
    """
    if not texts:
        return []
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        embedder = HuggingFaceEmbeddings(
            model_name=settings.local_embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
        return embedder.embed_documents(texts)
    except Exception as exc:  # noqa: BLE001
        logger.error("[embed_texts_local] failed: %s", exc)
        return []


def embed_texts_vanna_local(texts: list[str]) -> list[list[float]]:
    """Generate local embeddings for Vanna/SQL-selection English metadata.

    This intentionally remains on the lighter English MiniLM model. Knowledge
    Base document ingestion uses embed_texts_local(), which is configurable for
    multilingual document retrieval.
    """
    if not texts:
        return []
    try:
        from langchain_huggingface import HuggingFaceEmbeddings

        embedder = HuggingFaceEmbeddings(
            model_name=settings.vanna_local_embedding_model,
            encode_kwargs={"normalize_embeddings": True},
        )
        return embedder.embed_documents(texts)
    except Exception as exc:  # noqa: BLE001
        logger.error("[embed_texts_vanna_local] failed: %s", exc)
        return []
