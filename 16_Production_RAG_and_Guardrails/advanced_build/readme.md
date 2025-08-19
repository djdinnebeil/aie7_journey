# Advanced Caching FastAPI (Dockerized)

This demo adds **Unified LLM Caching** that combines **Semantic Caching** (Qdrant vector DB) and **E2E Caching** (SQLite) into a single intelligent system.

## Quickstart

1. Put a PDF in `./data/example.pdf` (relative to `docker-compose.yml`).
2. Export your OpenAI key in terminal:
   ```bash
   export OPENAI_API_KEY=sk-...   # Powers embeddings + LLM
   ```
3. Launch:
   ```bash
   cd /mnt/data/advanced_cache_app
   docker compose up --build
   ```

4. Health check:
   - http://localhost:8080/healthz

5. Ask:
   ```bash
   curl -X POST http://localhost:8080/ask \
     -H 'Content-Type: application/json' \
     -d '{"question":"What is this document about?","use_cache":true}'
   ```

6. Test the unified cache:
   ```bash
   python test_unified_cache.py
   ```

## How Unified Caching Works

The new **Unified Cache** intelligently combines two caching strategies:

1. **E2E Cache (SQLite)**: First tries exact matching using `(normalized_question, model, prompt_version, doc_ids)` hash
2. **Semantic Cache (Qdrant)**: Falls back to vector similarity search if no exact match, with context overlap validation

### Benefits:
- **Faster hits**: Exact matches are served immediately
- **Better coverage**: Semantic similarity catches rephrased questions
- **Context-aware**: Ensures cached answers are relevant to current retrieval context
- **Simplified API**: Single `use_cache` flag instead of separate flags

### Configuration:
- **Similarity Threshold**: `CACHE_SIM_THRESHOLD` (default: 0.85)
- **Context Overlap**: Minimum 34% document ID overlap for semantic cache hits
- **TTL**: Configurable per request or use default 7 days

## API Changes

### Before (Separate Caches):
```json
{
  "question": "What is AI?",
  "use_semantic_cache": true,
  "use_e2e_cache": true,
  "min_context_overlap": 0.34
}
```

### After (Unified Cache):
```json
{
  "question": "What is AI?",
  "use_cache": true,
  "min_context_overlap": 0.34,
  "ttl_seconds": 86400
}
```

## Cache Management

- **Clear All**: `POST /clear_cache`
- **Clear E2E Only**: `POST /clear_e2e_cache`  
- **Clear Semantic Only**: `POST /clear_semantic_cache`
- **Get Stats**: `GET /cache_stats`
- **Test Cache**: `POST /test_unified_cache`
- **Update Threshold**: `POST /update_similarity_threshold`

## Additional Features

- **LangChain LLM Cache**: Global SQLite cache for LangChain LLM calls via `setup_llm_cache(...)`
- **Embedding Cache**: Cache-backed embeddings using your `CacheBackedEmbeddings`
- **Production RAG**: Uses your `ProductionRAGChain` for retrieval + generation

This app maintains backward compatibility while providing a more intelligent and efficient caching experience.
