from __future__ import annotations
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .service import AppService, AskRequest, AskResponse
from .cache_backends import E2ECache, SemanticCache, UnifiedCache
from qdrant_client.http.models import Distance, VectorParams
import sqlite3

app = FastAPI(title='Advanced LLM Cache Demo')

SERVICE = AppService()

@app.get('/healthz')
def health() -> dict:
    return {'ok': True}

@app.post('/ask', response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    return SERVICE.ask(req)

@app.post("/clear_cache")
async def clear_cache():
    """Clear all caches safely"""
    try:
        # Use the unified cache to clear both
        SERVICE.unified_cache.clear()
        return {"message": "All caches cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")

@app.post("/clear_e2e_cache")
async def clear_e2e_cache():
    """Clear only E2E cache"""
    try:
        e2e_cache = E2ECache()
        with sqlite3.connect(e2e_cache.db_path) as con:
            con.execute("DELETE FROM responses")
            con.commit()
        return {"message": "E2E cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear E2E cache: {str(e)}")

@app.post("/clear_semantic_cache")
async def clear_semantic_cache():
    """Clear only semantic cache"""
    try:
        # Use same config as service
        semantic_cache = SemanticCache(
            collection='llm_cache',
            qdrant_url=os.getenv('QDRANT_URL', 'http://qdrant:6333'),
            similarity_threshold=float(os.getenv('CACHE_SIM_THRESHOLD', '0.85')),
            namespace=os.getenv('CACHE_NAMESPACE', 'demo'),
            embedding_model=os.getenv('EMBED_MODEL', 'text-embedding-3-small'),
        )
        semantic_cache.clear()
        return {"message": "Semantic cache cleared successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear semantic cache: {str(e)}")

@app.get("/cache_stats")
async def get_cache_stats():
    """Get statistics about all caches"""
    try:
        # Get unified cache stats (includes both E2E and semantic)
        unified_stats = SERVICE.unified_cache.get_stats()
        
        return {
            "unified_cache": unified_stats,
            "settings": {
                "similarity_threshold": float(os.getenv('CACHE_SIM_THRESHOLD', '0.85')),
                "namespace": os.getenv('CACHE_NAMESPACE', 'demo'),
                "qdrant_url": os.getenv('QDRANT_URL', 'http://qdrant:6333'),
                "min_context_overlap": 0.34
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get cache stats: {str(e)}")

@app.post("/test_semantic_similarity")
async def test_semantic_similarity(request: dict):
    """Test semantic similarity between two questions"""
    try:
        question1 = request.get("question1", "")
        question2 = request.get("question2", "")
        
        if not question1 or not question2:
            raise HTTPException(status_code=400, detail="Both question1 and question2 are required")
        
        semantic_cache = SemanticCache(
            collection='llm_cache',
            qdrant_url=os.getenv('QDRANT_URL', 'http://qdrant:6333'),
            similarity_threshold=float(os.getenv('CACHE_SIM_THRESHOLD', '0.85')),
            namespace=os.getenv('CACHE_NAMESPACE', 'demo'),
            embedding_model=os.getenv('EMBED_MODEL', 'text-embedding-3-small'),
            debug=True,  # Enable debug for this test
        )
        
        # Get embeddings for both questions
        vec1 = semantic_cache._embed(question1)
        vec2 = semantic_cache._embed(question2)
        
        # Calculate cosine similarity manually
        import numpy as np
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        # Normalize vectors
        vec1_norm = vec1_np / np.linalg.norm(vec1_np)
        vec2_norm = vec2_np / np.linalg.norm(vec2_np)
        
        # Cosine similarity
        similarity = float(np.dot(vec1_norm, vec2_np))  # Convert to Python float
        
        return {
            "question1": question1,
            "question2": question2,
            "similarity_score": similarity,
            "threshold": float(os.getenv('CACHE_SIM_THRESHOLD', '0.85')),
            "would_cache_hit": bool(similarity >= float(os.getenv('CACHE_SIM_THRESHOLD', '0.85')))  # Convert to Python bool
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test similarity: {str(e)}")

@app.post("/update_similarity_threshold")
async def update_similarity_threshold(request: dict):
    """Update the similarity threshold dynamically"""
    try:
        new_threshold = request.get("threshold")
        if new_threshold is None:
            raise HTTPException(status_code=400, detail="threshold parameter is required")
        
        # Validate threshold range
        try:
            threshold_float = float(new_threshold)
            if not 0.0 <= threshold_float <= 1.0:
                raise HTTPException(status_code=400, detail="threshold must be between 0.0 and 1.0")
        except ValueError:
            raise HTTPException(status_code=400, detail="threshold must be a valid number")
        
        # Update environment variable (this will affect new requests)
        os.environ['CACHE_SIM_THRESHOLD'] = str(threshold_float)
        
        # Update the service's unified cache instance
        SERVICE.update_similarity_threshold(threshold_float)
        
        return {
            "message": "Similarity threshold updated successfully",
            "old_threshold": float(os.getenv('CACHE_SIM_THRESHOLD', '0.85')),
            "new_threshold": threshold_float,
            "note": "Changes apply to new requests. Existing cached items remain unchanged."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update threshold: {str(e)}")

@app.get("/current_similarity_threshold")
async def get_current_similarity_threshold():
    """Get the current similarity threshold"""
    try:
        current_threshold = float(os.getenv('CACHE_SIM_THRESHOLD', '0.85'))
        return {
            "current_threshold": current_threshold,
            "service_threshold": SERVICE.get_similarity_threshold()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get threshold: {str(e)}")

@app.post("/test_unified_cache")
async def test_unified_cache(request: dict):
    """Test the unified cache with a question"""
    try:
        question = request.get("question", "")
        if not question:
            raise HTTPException(status_code=400, detail="question parameter is required")
        
        # Get retrieval context
        doc_ids = SERVICE._retrieval_context_ids(question)
        
        # Test unified cache lookup
        cache_hit = SERVICE.unified_cache.get(question, SERVICE.model_name, doc_ids, top_k=3)
        
        return {
            "question": question,
            "doc_ids": doc_ids,
            "cache_hit": cache_hit is not None,
            "cache_type": cache_hit.get('meta', {}).get('cache_type', 'none') if cache_hit else 'none',
            "answer_preview": cache_hit['answer'][:100] + "..." if cache_hit and cache_hit.get('answer') else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to test unified cache: {str(e)}")