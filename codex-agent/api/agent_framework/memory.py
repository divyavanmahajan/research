from __future__ import annotations

import json
import uuid
from typing import Any


class MemoryManager:
    """Session memory (dict) + optional ChromaDB vector memory."""

    def __init__(self, collection_name: str = "agent_memory", use_vector: bool = True):
        self._session: dict[str, Any] = {}
        self._collection = None
        if use_vector:
            self._collection = self._init_chroma(collection_name)

    def _init_chroma(self, name: str):
        try:
            import chromadb

            client = chromadb.Client()
            return client.get_or_create_collection(name)
        except Exception:
            return None

    def store(self, state: Any) -> None:
        self._session[state.session_id] = {
            "task": state.task,
            "iteration": state.iteration,
            "plan": state.plan,
            "message_count": len(state.messages),
        }
        if self._collection and state.messages:
            last = state.messages[-1]
            content = last.get("content", "")
            if content and isinstance(content, str):
                self._collection.add(
                    documents=[content],
                    ids=[str(uuid.uuid4())],
                    metadatas=[{"session_id": state.session_id, "role": last.get("role", "")}],
                )

    def recall(self, query: str, n: int = 5) -> list[str]:
        if not self._collection:
            return []
        try:
            results = self._collection.query(query_texts=[query], n_results=n)
            return results.get("documents", [[]])[0]
        except Exception:
            return []

    def get_session(self, session_id: str) -> dict[str, Any]:
        return self._session.get(session_id, {})
