import hashlib

def normalize_text(s: str) -> str:
    s = (s or '').strip()
    # simple normalization: collapse whitespace, lowercase
    s = ' '.join(s.split())
    return s.lower()

def e2e_cache_key(question: str, model: str, doc_ids: list[str] | None, prompt_version: str = 'v1') -> str:
    """End-to-end cache key that fingerprints both the input and retrieval context."""
    normalized_q = normalize_text(question)
    doc_part = ','.join(doc_ids or [])
    base = f'{normalized_q}||{model}||{prompt_version}||{doc_part}'
    return hashlib.sha256(base.encode('utf-8')).hexdigest()
