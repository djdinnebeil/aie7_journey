# Unified Cache Guide

This guide explains how to use and troubleshoot the **Unified Cache** in your LLM application, which combines E2E exact matching with semantic similarity fallback.

## What is Unified Caching?

The Unified Cache intelligently combines two caching strategies:

1. **E2E Cache (SQLite)**: First tries exact matching using `(normalized_question, model, prompt_version, doc_ids)` hash
2. **Semantic Cache (Qdrant)**: Falls back to vector similarity search if no exact match, with context overlap validation

### Strategy Flow:
1. **Exact Match First**: Fastest, most accurate cache hits
2. **Semantic Fallback**: Catches rephrased questions when exact match fails
3. **Context Validation**: Ensures cached answers are relevant to current retrieval context

## Key Components

### 1. Similarity Threshold
- **Default**: 0.85 (lowered from 0.92 for better cache hits)
- **Range**: 0.0 to 1.0
- **Higher values**: More strict, fewer cache hits, higher quality matches
- **Lower values**: More lenient, more cache hits, potentially lower quality matches

### 2. Context Overlap
- **Default**: 0.34 (34% of document IDs must overlap)
- **Purpose**: Ensures cached answers are relevant to the current context
- **Example**: If question A retrieved docs [1,2,3] and question B retrieves docs [2,3,4], overlap is 2/3 = 0.67

### 3. Cache Types
- **E2E Cache**: Exact matches with full context fingerprinting
- **Semantic Cache**: Similar questions with context overlap validation
- **Unified Strategy**: Combines both for maximum hit potential

## Configuration

### Environment Variables
```bash
# Cache settings
CACHE_SIM_THRESHOLD=0.85          # Similarity threshold (0.0-1.0)
CACHE_NAMESPACE=demo              # Cache namespace
QDRANT_URL=http://qdrant:6333     # Qdrant vector database URL
CACHE_DB_PATH=./cache/e2e_cache.sqlite  # E2E cache database path

# Debug mode
DEBUG_CACHE=false                  # Enable debug logging
```

### Docker Compose
```yaml
environment:
  - CACHE_SIM_THRESHOLD=0.85
  - DEBUG_CACHE=false
  - CACHE_NAMESPACE=demo
  - QDRANT_URL=http://qdrant:6333
  - CACHE_DB_PATH=./cache/e2e_cache.sqlite
```

## Usage Examples

### 1. Basic Unified Cache Usage
```python
import requests

# Ask a question with unified cache enabled
response = requests.post("http://localhost:8080/ask", json={
    "question": "What is this document about?",
    "use_cache": True,  # Single flag for both strategies
    "min_context_overlap": 0.34,
    "ttl_seconds": 86400  # 24 hours
})

print(f"Cache result: {response.json()['cache_type']}")
```

### 2. Test Unified Cache
```python
# Test the unified cache with a question
test_result = requests.post("http://localhost:8080/test_unified_cache", json={
    "question": "Tell me about the main topic"
})

print(f"Cache hit: {test_result.json()['cache_hit']}")
print(f"Cache type: {test_result.json()['cache_type']}")
```

### 3. Get Unified Cache Statistics
```python
# Monitor unified cache performance
stats = requests.get("http://localhost:8080/cache_stats")
print(json.dumps(stats.json(), indent=2))
```

### 4. Test Semantic Similarity
```python
# Test how similar two questions are
similarity = requests.post("http://localhost:8080/test_semantic_similarity", json={
    "question1": "What is this document about?",
    "question2": "Tell me about the main topic"
})

print(f"Similarity: {similarity.json()['similarity_score']:.4f}")
```

## API Changes

### Before (Separate Caches):
```json
{
  "question": "What is AI?",
  "use_semantic_cache": true,
  "use_e2e_cache": true,
  "min_context_overlap": 0.34,
  "e2e_ttl_seconds": 86400
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

## Troubleshooting

### Common Issues

#### 1. No Cache Hits
**Symptoms**: All questions return `cache_type: null` or `from_cache: false`

**Solutions**:
- Lower the similarity threshold (try 0.80 or 0.75)
- Check if Qdrant is running: `docker ps | grep qdrant`
- Verify QDRANT_URL is correct
- Check backend logs: `docker logs session16_advanced_build`
- Test the unified cache: `POST /test_unified_cache`

#### 2. High Similarity Threshold
**Problem**: Threshold of 0.92 is too strict for most use cases

**Solution**: Lower to 0.85 or 0.80
```bash
curl -X POST http://localhost:8080/update_similarity_threshold \
  -H 'Content-Type: application/json' \
  -d '{"threshold": 0.80}'
```

#### 3. Context Overlap Too Strict
**Problem**: 34% overlap requirement is too strict

**Solution**: Lower the overlap requirement in the service configuration
```python
# In app/service.py, update the UnifiedCache initialization
self.unified_cache = UnifiedCache(
    e2e_cache=self.e2e_cache,
    semantic_cache=self.semantic_cache,
    min_context_overlap=0.20,  # Lower from 0.34
    debug=self.debug_cache
)
```

### Debug Mode

Enable debug logging to see cache behavior:
```bash
export DEBUG_CACHE=true
docker compose up --build
```

This will show:
- E2E cache hits/misses
- Semantic similarity scores
- Context overlap calculations
- Cache storage operations

## Performance Tips

1. **Start with 0.85 threshold**: Good balance of quality and hit rate
2. **Monitor cache stats**: Use `/cache_stats` to track performance
3. **Test with similar questions**: Use `/test_semantic_similarity` to tune thresholds
4. **Clear caches periodically**: Use `/clear_cache` to refresh stale data
5. **Use appropriate TTL**: Balance between freshness and cache efficiency

## Migration from Separate Caches

If you're upgrading from the old separate cache system:

1. **Update API calls**: Change `use_semantic_cache` + `use_e2e_cache` to `use_cache`
2. **Update TTL**: Change `e2e_ttl_seconds` to `ttl_seconds`
3. **Test functionality**: Use `/test_unified_cache` to verify behavior
4. **Monitor performance**: Check `/cache_stats` for improved hit rates

The unified system maintains backward compatibility while providing better performance and simpler configuration.
