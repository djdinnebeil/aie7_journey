from __future__ import annotations
import os
from typing import List, Dict, Any, Optional

from fastapi import HTTPException
from pydantic import BaseModel

from .utils import e2e_cache_key, normalize_text
from .cache_backends import E2ECache, SemanticCache, UnifiedCache

# Import the user's provided library (assumed placed in PYTHONPATH at /app/lib)
from lib import rag, models, caching

class AskRequest(BaseModel):
    question: str
    use_cache: bool = True  # Unified cache flag
    min_context_overlap: float = 0.34  # fraction of retrieved doc_ids that must overlap for a semantic hit
    ttl_seconds: int | None = None  # TTL for E2E cache entries
    top_k: int = 3  # number of similar questions to search in semantic cache

class AskResponse(BaseModel):
    from_cache: bool
    cache_type: Optional[str]
    answer: str
    doc_ids: list[str]
    model: str

class AppService:
    def __init__(self):
        # Required envs
        data_dir = os.getenv('DATA_DIR', '').strip()
        if not data_dir:
            raise RuntimeError('DATA_DIR env var must point to a local directory containing text files to build the demo RAG retriever.')

        self.model_name = os.getenv('OPENAI_MODEL', 'gpt-4.1-nano')
        self.sim_threshold = float(os.getenv('CACHE_SIM_THRESHOLD', '0.85'))  # Lowered from 0.92
        self.qdrant_url = os.getenv('QDRANT_URL', 'http://qdrant:6333')
        self.namespace = os.getenv('CACHE_NAMESPACE', 'demo')
        self.e2e_db_path = os.getenv('CACHE_DB_PATH', './cache/e2e_cache.sqlite')
        self.debug_cache = os.getenv('DEBUG_CACHE', 'false').lower() == 'true'

        # Wire up user's caching primitives
        # Enable a global SQLite cache for LLM calls (LangChain's internal cache), optional
        cache_type = os.getenv('LLM_CACHE_TYPE', 'sqlite')  # 'memory' or 'sqlite'
        caching.setup_llm_cache(cache_type=cache_type, cache_path='./cache/llm_calls.sqlite')

        # Build the RAG chain using user's ProductionRAGChain
        self.rag_chain = rag.ProductionRAGChain(
            data_dir=data_dir,
            chunk_size=int(os.getenv('CHUNK_SIZE', '800')),
            chunk_overlap=int(os.getenv('CHUNK_OVERLAP', '100')),
            embedding_model=os.getenv('EMBED_MODEL', 'text-embedding-3-small'),
            llm_model=self.model_name,
            cache_dir='./cache'
        )

        # Initialize individual cache backends
        self.e2e_cache = E2ECache(db_path=self.e2e_db_path)
        self.semantic_cache = SemanticCache(
            collection='llm_cache',
            qdrant_url=self.qdrant_url,
            similarity_threshold=self.sim_threshold,
            namespace=self.namespace,
            embedding_model=os.getenv('EMBED_MODEL', 'text-embedding-3-small'),
            debug=self.debug_cache,
        )
        
        # Initialize unified cache that combines both strategies
        self.unified_cache = UnifiedCache(
            e2e_cache=self.e2e_cache,
            semantic_cache=self.semantic_cache,
            min_context_overlap=0.34,  # Default context overlap
            debug=self.debug_cache
        )

    def update_similarity_threshold(self, new_threshold: float):
        """Update the similarity threshold for the semantic cache"""
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        self.sim_threshold = new_threshold
        self.semantic_cache.update_similarity_threshold(new_threshold)
        self.unified_cache.update_similarity_threshold(new_threshold)
        
        # Update environment variable
        os.environ['CACHE_SIM_THRESHOLD'] = str(new_threshold)
        
        if self.debug_cache:
            print(f"Updated similarity threshold to: {new_threshold}")

    def get_similarity_threshold(self) -> float:
        """Get the current similarity threshold"""
        return self.sim_threshold

    def _retrieval_context_ids(self, question: str) -> list[str]:
        """Retrieve doc IDs for the question (without calling LLM)."""
        retriever = self.rag_chain.get_retriever()
        docs = retriever.invoke(question)
        # Extract lightweight stable IDs
        ids = []
        for d in docs:
            # prefer a source or an id from metadata
            sid = d.metadata.get('source') or d.metadata.get('doc_id') or d.page_content[:32]
            ids.append(str(sid))
        return ids

    def ask(self, req: AskRequest) -> AskResponse:
        q = req.question.strip()
        if not q:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail='question cannot be empty')

        # Step 1: Build retrieval context fingerprint
        doc_ids = self._retrieval_context_ids(q)

        # Step 2: Unified cache lookup (combines E2E + semantic strategies)
        if req.use_cache:
            cache_hit = self.unified_cache.get(q, self.model_name, doc_ids, top_k=req.top_k)
            if cache_hit:
                return AskResponse(
                    from_cache=True,
                    cache_type=cache_hit.get('meta', {}).get('cache_type', 'unified'),
                    answer=str(cache_hit['answer']),
                    doc_ids=doc_ids,
                    model=self.model_name
                )

        # Step 3: Call the user's production RAG chain (LLM)
        result = self.rag_chain.invoke(q)
        answer_text = getattr(result, 'content', None) or str(result)

        # Step 4: Write-through to unified cache (stores in both E2E and semantic)
        if req.use_cache:
            try:
                self.unified_cache.set(q, answer_text, self.model_name, doc_ids, req.ttl_seconds, meta={'doc_ids': doc_ids})
            except Exception as e:
                if self.debug_cache:
                    print(f"Failed to store in unified cache: {e}")

        return AskResponse(
            from_cache=False,
            cache_type=None,
            answer=answer_text,
            doc_ids=doc_ids,
            model=self.model_name
        )
