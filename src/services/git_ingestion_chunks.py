"""Context-aware chunking for structured Git repository documents.

This module owns Git/RAG-specific chunk preparation before embeddings are
created. It repeats source metadata on split chunks, keeps large code/config
units under the Milvus content limit, and chunks repo_dependency_graph.json by
logical graph sections so graph retrieval does not depend on arbitrary text
splits.
"""

import json
from collections import defaultdict

from src.services.embeddings import chunk_text
from src.utils.logger import get_logger

logger = get_logger(__name__)

_MILVUS_CONTENT_MAX_CHARS = 3900
_GRAPH_NODE_BATCH_SIZE = 40
_GRAPH_EDGE_BATCH_SIZE = 60


def _metadata_prefix(metadata: dict) -> str:
    """Build a compact, repeated header for source-code chunks."""
    fields = [
        ("Repository", metadata.get("repo_url")),
        ("Branch", metadata.get("branch")),
        ("File", metadata.get("file_path") or metadata.get("doc_name")),
        ("Language", metadata.get("language")),
        ("Unit type", metadata.get("unit_type")),
        ("Symbol", metadata.get("symbol_name")),
        ("Parent", metadata.get("parent_symbol")),
        ("Lines", _line_span(metadata)),
        ("Route", _route_span(metadata)),
    ]
    return "\n".join(f"{label}: {value}" for label, value in fields if value)


def _line_span(metadata: dict) -> str | None:
    """Format source start/end lines as a compact span."""
    if metadata.get("start_line") and metadata.get("end_line"):
        return f"{metadata['start_line']}-{metadata['end_line']}"
    return None


def _route_span(metadata: dict) -> str | None:
    """Format route metadata as METHOD path when available."""
    if metadata.get("route_path"):
        method = metadata.get("http_method") or ""
        return f"{method} {metadata['route_path']}".strip()
    return None


def _fit_prefixed_content(prefix: str, content: str) -> list[str]:
    """Split content to fit Milvus while repeating the unit header."""
    separator = "\n---\n" if prefix else ""
    overhead = len(prefix) + len(separator)
    body_limit = max(1000, _MILVUS_CONTENT_MAX_CHARS - overhead)
    if overhead + len(content) <= _MILVUS_CONTENT_MAX_CHARS:
        return [f"{prefix}{separator}{content}" if prefix else content]

    pieces = []
    for start in range(0, len(content), body_limit):
        body = content[start:start + body_limit]
        pieces.append(f"{prefix}{separator}{body}" if prefix else body)
    return pieces


def _json_dumps(value: dict) -> str:
    """Render compact, deterministic JSON for graph-aware chunks."""
    return json.dumps(value, indent=2, sort_keys=True)


def _batched(items: list, batch_size: int) -> list[list]:
    """Split list items into fixed-size batches."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def _graph_section_doc(
    metadata: dict,
    graph: dict,
    section: str,
    payload: dict,
    doc_index: int,
    batch_index: int = 0,
    batch_count: int = 1,
) -> list[dict]:
    """Create Milvus-sized chunks for one logical dependency graph section."""
    section_metadata = {
        **metadata,
        "graph_section": section,
        "graph_batch_index": batch_index,
        "graph_batch_count": batch_count,
    }
    section_content = _json_dumps({
        "repo_url": graph.get("repo_url"),
        "branch": graph.get("branch"),
        "schema_version": graph.get("schema_version"),
        "section": section,
        **payload,
    })
    prefix = _metadata_prefix(section_metadata)
    chunks = []
    for split_index, fitted_text in enumerate(_fit_prefixed_content(prefix, section_content)):
        chunks.append({
            "content": fitted_text,
            "metadata": {
                **section_metadata,
                "document_index": doc_index,
                "unit_chunk_index": batch_index,
                "unit_total_chunks": batch_count,
                "split_chunk_index": split_index,
            },
        })
    return chunks


def _chunk_dependency_graph_document(doc_index: int, metadata: dict, content: str) -> list[dict]:
    """Chunk repo_dependency_graph.json by summary, node type, and edge type."""
    try:
        graph = json.loads(content)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[git-chunks] graph-aware chunking failed, falling back: %s", exc)
        return []

    chunked_docs: list[dict] = []
    chunked_docs.extend(_graph_section_doc(
        metadata,
        graph,
        "summary",
        {"summary": graph.get("summary", {})},
        doc_index,
    ))

    nodes_by_type: dict[str, list] = defaultdict(list)
    for node in graph.get("nodes", []):
        nodes_by_type[node.get("type", "unknown")].append(node)
    for node_type, nodes in sorted(nodes_by_type.items()):
        batches = _batched(nodes, _GRAPH_NODE_BATCH_SIZE)
        for batch_index, batch in enumerate(batches):
            chunked_docs.extend(_graph_section_doc(
                metadata,
                graph,
                f"nodes:{node_type}",
                {"node_type": node_type, "nodes": batch},
                doc_index,
                batch_index,
                len(batches),
            ))

    edges_by_type: dict[str, list] = defaultdict(list)
    for edge in graph.get("edges", []):
        edges_by_type[edge.get("type", "unknown")].append(edge)
    for edge_type, edges in sorted(edges_by_type.items()):
        batches = _batched(edges, _GRAPH_EDGE_BATCH_SIZE)
        for batch_index, batch in enumerate(batches):
            chunked_docs.extend(_graph_section_doc(
                metadata,
                graph,
                f"edges:{edge_type}",
                {"edge_type": edge_type, "edges": batch},
                doc_index,
                batch_index,
                len(batches),
            ))

    logger.info(
        "[git-chunks] graph-aware chunking complete sections=%d nodes=%d edges=%d",
        len(chunked_docs),
        len(graph.get("nodes", [])),
        len(graph.get("edges", [])),
    )
    return chunked_docs


def chunk_git_documents(documents: list[dict]) -> list[dict]:
    """Chunk structured Git documents while preserving per-unit metadata context."""
    chunked_docs: list[dict] = []
    logger.info("[git-chunks] structured chunking started documents=%d", len(documents))
    for doc_index, doc in enumerate(documents):
        metadata = dict(doc.get("metadata") or {})
        content = doc.get("content") or ""
        doc_type = metadata.get("type") or "git"
        if metadata.get("unit_type") == "repo_dependency_graph":
            graph_chunks = _chunk_dependency_graph_document(doc_index, metadata, content)
            if graph_chunks:
                chunked_docs.extend(graph_chunks)
                continue

        prefix = _metadata_prefix(metadata)
        chunks = chunk_text(content, "git" if doc_type == "code" else doc_type)
        if not chunks:
            continue

        total_chunks = len(chunks)
        logger.debug(
            "[git-chunks] unit chunked file=%s unit=%s symbol=%s chunks=%d",
            metadata.get("file_path"),
            metadata.get("unit_type"),
            metadata.get("symbol_name"),
            total_chunks,
        )
        for unit_chunk_index, chunk in enumerate(chunks):
            for split_index, fitted_text in enumerate(_fit_prefixed_content(prefix, chunk)):
                chunked_docs.append({
                    "content": fitted_text,
                    "metadata": {
                        **metadata,
                        "document_index": doc_index,
                        "unit_chunk_index": unit_chunk_index,
                        "unit_total_chunks": total_chunks,
                        "split_chunk_index": split_index,
                    },
                })
    logger.info("[git-chunks] structured chunking complete chunks=%d", len(chunked_docs))
    return chunked_docs
