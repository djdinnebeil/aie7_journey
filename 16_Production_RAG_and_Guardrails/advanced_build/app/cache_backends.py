from __future__ import annotations
import os
import sqlite3
import time
import json
from typing import Optional, Tuple, List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain_openai.embeddings import OpenAIEmbeddings

# --- E2E Cache (SQLite) -------------------------------------------------------

class E2ECache:
    def __init__(self, db_path: str = './cache/e2e_cache.sqlite', default_ttl_seconds: int = 7 * 24 * 3600):
        self.db_path = db_path
        self.default_ttl = default_ttl_seconds
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                'CREATE TABLE IF NOT EXISTS responses ('
                '   cache_key TEXT PRIMARY KEY,'
                '   answer TEXT NOT NULL,'
                '   created_at INTEGER NOT NULL,'
                '   ttl_seconds INTEGER NOT NULL,'
                '   meta_json TEXT'
                ')'
            )
            con.commit()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute('SELECT answer, created_at, ttl_seconds, meta_json FROM responses WHERE cache_key=?', (cache_key,))
            row = cur.fetchone()
            if not row:
                return None
            answer, created_at, ttl_seconds, meta_json = row
            if int(time.time()) > created_at + ttl_seconds:
                # expired: drop entry
                cur.execute('DELETE FROM responses WHERE cache_key=?', (cache_key,))
                con.commit()
                return None
            
            # Parse meta_json back to dictionary if it exists
            meta = None
            if meta_json:
                try:
                    meta = json.loads(meta_json)
                except (json.JSONDecodeError, TypeError):
                    meta = {}
            
            return {'answer': answer, 'created_at': created_at, 'ttl_seconds': ttl_seconds, 'meta': meta}

    def set(self, cache_key: str, answer: str, ttl_seconds: Optional[int] = None, meta: Optional[dict] = None):
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        with sqlite3.connect(self.db_path) as con:
            cur = con.cursor()
            cur.execute(
                'REPLACE INTO responses(cache_key, answer, created_at, ttl_seconds, meta_json) VALUES(?,?,?,?,?)',
                (cache_key, answer, int(time.time()), ttl, (meta and json.dumps(meta)) or None)
            )
            con.commit()

    def get_stats(self) -> Dict[str, Any]:
        """Get E2E cache statistics"""
        try:
            with sqlite3.connect(self.db_path) as con:
                cur = con.cursor()
                cur.execute("SELECT COUNT(*) FROM responses")
                count = cur.fetchone()[0]
                return {
                    'count': count,
                    'db_path': self.db_path
                }
        except Exception as e:
            return {'error': str(e), 'db_path': self.db_path}

# --- Semantic Cache (Qdrant) --------------------------------------------------

class SemanticCache:
    """A prompt-level semantic cache backed by Qdrant.
    
    Each cache entry stores:
      - prompt embedding vector
      - payload: {'question': str, 'answer': str, 'doc_ids': list[str], 'model': str, 'created_at': int}
    """
    def __init__(
        self,
        collection: str = 'llm_cache',
        qdrant_url: str = 'http://qdrant:6333',
        vector_size: int = 1536,
        distance = Distance.COSINE,
        similarity_threshold: float = 0.85,  # Lowered from 0.92 for better cache hits
        namespace: str = 'default',
        embedding_model: str = 'text-embedding-3-small',
        debug: bool = False,
    ):
        self.collection = f'{collection}_{namespace}'
        self.similarity_threshold = similarity_threshold
        self.debug = debug
        self.client = QdrantClient(url=qdrant_url)
        self.embeddings = OpenAIEmbeddings(model=embedding_model)
        self._ensure_collection(vector_size, distance)
        self.qdrant_url = qdrant_url # Store the URL for get_stats

    def _ensure_collection(self, vector_size: int, distance):
        try:
            has = self.client.get_collection(self.collection)
        except Exception as e:
            if self.debug:
                print(f"Collection check failed: {e}")
            has = None
        if not has:
            try:
                self.client.recreate_collection(
                    collection_name=self.collection,
                    vectors_config=VectorParams(size=vector_size, distance=distance),
                )
                if self.debug:
                    print(f"Created collection: {self.collection}")
            except Exception as e:
                if self.debug:
                    print(f"Failed to create collection: {e}")
                raise

    def _embed(self, text: str) -> list[float]:
        try:
            vec = self.embeddings.embed_query(text)
            return vec
        except Exception as e:
            if self.debug:
                print(f"Embedding failed: {e}")
            raise

    def lookup(self, question: str, top_k: int = 3) -> Optional[Dict[str, Any]]:
        try:
            vec = self._embed(question)
            res = self.client.search(
                collection_name=self.collection,
                query_vector=vec,
                limit=top_k,
                with_payload=True,
            )
            if not res:
                if self.debug:
                    print(f"No search results for: {question[:50]}...")
                return None
            
            top = res[0]
            score = top.score
            if score is None:
                if self.debug:
                    print(f"No score for top result")
                return None
            
            if self.debug:
                print(f"Top similarity score: {score:.4f} (threshold: {self.similarity_threshold})")
                print(f"Top result question: {top.payload.get('question', 'N/A')[:50]}...")
            
            # Qdrant returns higher is better for cosine similarity (1.0 = exact). Use threshold.
            if score >= self.similarity_threshold:
                if self.debug:
                    print(f"Cache HIT! Score: {score:.4f}")
                return top.payload
            else:
                if self.debug:
                    print(f"Cache MISS! Score {score:.4f} < threshold {self.similarity_threshold}")
                return None
                
        except Exception as e:
            if self.debug:
                print(f"Semantic cache lookup failed: {e}")
            return None

    def upsert(self, question: str, answer: str, doc_ids: list[str], model: str):
        try:
            vec = self._embed(question)
            payload = {
                'question': question,
                'answer': answer,
                'doc_ids': doc_ids,
                'model': model,
                'created_at': int(time.time()),
            }
            self.client.upsert(
                collection_name=self.collection,
                points=[
                    {
                        'id': __import__('uuid').uuid4().hex,
                        'vector': vec,
                        'payload': payload,
                    }
                ]
            )
            if self.debug:
                print(f"Added to semantic cache: {question[:50]}...")
        except Exception as e:
            if self.debug:
                print(f"Failed to upsert to semantic cache: {e}")
            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics for monitoring"""
        try:
            info = self.client.get_collection(self.collection)
            return {
                'collection_name': self.collection,
                'vector_count': info.vectors_count,
                'similarity_threshold': self.similarity_threshold,
                'qdrant_url': str(self.qdrant_url),  # Use the stored URL instead
            }
        except Exception as e:
            return {'error': str(e)}

    def clear(self):
        """Clear the semantic cache collection"""
        try:
            self.client.delete_collection(self.collection)
            self._ensure_collection(1536, Distance.COSINE)
            if self.debug:
                print(f"Cleared semantic cache: {self.collection}")
        except Exception as e:
            if self.debug:
                print(f"Failed to clear semantic cache: {e}")
            raise

    def update_similarity_threshold(self, new_threshold: float):
        """Update the similarity threshold dynamically"""
        if not 0.0 <= new_threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        
        old_threshold = self.similarity_threshold
        self.similarity_threshold = new_threshold
        
        if self.debug:
            print(f"Updated similarity threshold from {old_threshold:.4f} to {new_threshold:.4f}")
        
        return old_threshold

# --- Unified Cache (Combines Both Strategies) ----------------------------------

class UnifiedCache:
    """Unified cache that combines E2E exact matching with semantic similarity fallback.
    
    Strategy:
    1. Try exact E2E match first (fastest, most accurate)
    2. Fall back to semantic similarity if no exact match
    3. Store results in both caches for maximum hit potential
    """
    
    def __init__(
        self,
        e2e_cache: E2ECache,
        semantic_cache: SemanticCache,
        min_context_overlap: float = 0.34,
        debug: bool = False
    ):
        self.e2e_cache = e2e_cache
        self.semantic_cache = semantic_cache
        self.min_context_overlap = min_context_overlap
        self.debug = debug

    def _context_overlap_ok(self, current_doc_ids: list[str], cached_doc_ids: list[str]) -> bool:
        """Check if context overlap meets minimum threshold"""
        if not current_doc_ids or not cached_doc_ids:
            return False
        
        current_set = set(current_doc_ids)
        cached_set = set(cached_doc_ids)
        
        if not current_set:
            return False
        
        overlap = len(current_set & cached_set) / len(current_set)
        return overlap >= self.min_context_overlap

    def get(self, question: str, model: str, doc_ids: list[str], top_k: int = 3) -> Optional[Dict[str, Any]]:
        """Get cached response using unified strategy"""
        
        # Strategy 1: Try exact E2E match first (fastest, most accurate)
        from .utils import e2e_cache_key
        exact_key = e2e_cache_key(question, model, doc_ids)
        exact_hit = self.e2e_cache.get(exact_key)
        
        if exact_hit:
            if self.debug:
                print(f"E2E cache HIT! Exact match found")
            return {
                **exact_hit,
                'meta': {
                    **exact_hit.get('meta', {}),
                    'cache_type': 'e2e'
                }
            }
        
        # Strategy 2: Fall back to semantic similarity
        if self.debug:
            print(f"E2E cache MISS, trying semantic similarity...")
        
        semantic_hit = self.semantic_cache.lookup(question, top_k=top_k)
        if semantic_hit and self._context_overlap_ok(doc_ids, semantic_hit.get('doc_ids', [])):
            if self.debug:
                print(f"Semantic cache HIT! Similarity: {semantic_hit.get('similarity_score', 'N/A')}")
            return {
                'answer': semantic_hit['answer'],
                'created_at': semantic_hit['created_at'],
                'ttl_seconds': 86400,  # 24 hours default for semantic hits
                'meta': {
                    'doc_ids': semantic_hit['doc_ids'],
                    'cache_type': 'semantic',
                    'similarity_score': semantic_hit.get('similarity_score', 'N/A'),
                    'original_question': semantic_hit.get('question', 'N/A')
                }
            }
        
        if self.debug:
            print(f"Unified cache MISS - no exact or semantic match found")
        return None

    def set(self, question: str, answer: str, model: str, doc_ids: list[str], ttl_seconds: int = None, meta: dict = None):
        """Store response in both caches for maximum hit potential"""
        
        # Store in E2E cache (exact match)
        from .utils import e2e_cache_key
        exact_key = e2e_cache_key(question, model, doc_ids)
        
        # Merge metadata
        e2e_meta = {
            'doc_ids': doc_ids,
            'cache_type': 'e2e',
            'original_question': question
        }
        if meta:
            e2e_meta.update(meta)
        
        try:
            self.e2e_cache.set(exact_key, answer, ttl_seconds, e2e_meta)
            if self.debug:
                print(f"Stored in E2E cache with key: {exact_key[:16]}...")
        except Exception as e:
            if self.debug:
                print(f"Failed to store in E2E cache: {e}")
        
        # Store in semantic cache (similarity matching)
        try:
            self.semantic_cache.upsert(question, answer, doc_ids, model)
            if self.debug:
                print(f"Stored in semantic cache")
        except Exception as e:
            if self.debug:
                print(f"Failed to store in semantic cache: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get unified cache statistics"""
        return {
            'e2e_cache': self.e2e_cache.get_stats(),
            'semantic_cache': self.semantic_cache.get_stats(),
            'min_context_overlap': self.min_context_overlap,
            'strategy': 'unified (e2e first, semantic fallback)'
        }

    def clear(self):
        """Clear both caches"""
        try:
            self.e2e_cache = E2ECache(self.e2e_cache.db_path)
            with sqlite3.connect(self.e2e_cache.db_path) as con:
                con.execute("DELETE FROM responses")
                con.commit()
            
            self.semantic_cache.clear()
            
            if self.debug:
                print("Cleared both E2E and semantic caches")
        except Exception as e:
            if self.debug:
                print(f"Failed to clear unified cache: {e}")
            raise

    def update_similarity_threshold(self, new_threshold: float):
        """Update semantic cache similarity threshold"""
        return self.semantic_cache.update_similarity_threshold(new_threshold)
