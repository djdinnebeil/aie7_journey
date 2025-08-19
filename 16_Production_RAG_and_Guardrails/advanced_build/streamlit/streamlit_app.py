import os
import time
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd
import requests
import streamlit as st

# ---------- Config ----------
DEFAULT_BACKEND = os.getenv("BACKEND_URL", "http://localhost:8080")
E2E_DB_PATH = Path(os.getenv("E2E_DB_PATH", "/cache/e2e_cache.sqlite"))  # mounted read-only
QDRANT_URL = os.getenv("QDRANT_URL", "")  # optional, e.g. http://qdrant:6333

st.set_page_config(page_title="Advanced LLM Caching Demo", page_icon="⚡", layout="wide")

# ---------- Utilities (mirror backend utils.py) ----------
def _normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = " ".join(s.split())
    return s.lower()

def _e2e_cache_key(question: str, model: str, doc_ids: list[str] | None, prompt_version: str = "v1") -> str:
    # Same algorithm as app/utils.py:e2e_cache_key so our key matches backend.  (Ref) :contentReference[oaicite:4]{index=4}
    import hashlib
    normalized_q = _normalize_text(question)
    doc_part = ",".join(doc_ids or [])
    base = f"{normalized_q}||{model}||{prompt_version}||{doc_part}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

def _human(ts: int | float | None):
    if ts is None:
        return "—"
    return datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

# ---------- Session State ----------
if "stats" not in st.session_state:
    st.session_state.stats = {"miss": 0, "hit": 0, "total": 0}
if "history" not in st.session_state:
    st.session_state.history = []  # keep last runs

def _record_hit(cache_type: str | None, from_cache: bool):
    st.session_state.stats["total"] += 1
    if not from_cache:
        st.session_state.stats["miss"] += 1
    else:
        # Unified cache hit - regardless of whether it was E2E or semantic
        st.session_state.stats["hit"] += 1
    
    # Set flag to trigger rerun after response processing
    # st.session_state.needs_rerun = True

# ---------- Sidebar ----------
st.sidebar.header("Cache Settings")

# Backend URL
backend_url = st.sidebar.text_input("Backend URL", value=DEFAULT_BACKEND, help="FastAPI base URL")

# Unified cache toggle
use_cache = st.sidebar.checkbox("Enable Unified Cache", value=True, help="Enables the unified semantic E2E caching system")

# Cache strategy
cache_preset = st.sidebar.selectbox(
    "Cache Strategy",
    ["enabled", "disabled"],
    help="Enable or disable the unified semantic E2E cache"
)

# Update use_cache based on preset
use_cache = cache_preset == "enabled"

# Similarity threshold
sim_threshold = st.sidebar.slider(
    "Similarity Threshold",
    min_value=0.0,
    max_value=1.0,
    value=0.85,
    step=0.05,
    help="Minimum similarity score for semantic cache hits (0.85 = good balance)"
)

# Context overlap
min_overlap = st.sidebar.slider(
    "Min Context Overlap",
    min_value=0.0,
    max_value=1.0,
    value=0.34,
    step=0.05,
    help="Minimum document ID overlap for semantic cache hits"
)

# Top-K for semantic search
top_k = st.sidebar.slider(
    "Top-K Semantic Search",
    min_value=1,
    max_value=10,
    value=3,
    help="Number of similar questions to search in semantic cache"
)

# TTL for cache entries
ttl_seconds = st.sidebar.number_input(
    "Cache TTL (seconds)",
    min_value=0,
    max_value=7*24*3600,  # 7 days max
    value=7*24*3600,  # 7 days default
    step=3600,  # 1 hour steps
    help="Time-to-live for cache entries (0 = use default)"
)

# Dynamic similarity threshold control
st.sidebar.markdown("---")
st.sidebar.subheader("Advanced Settings")

# Get current threshold from backend
current_threshold = 0.85  # default
try:
    threshold_response = requests.get(f"{backend_url.rstrip('/')}/current_similarity_threshold", timeout=5)
    if threshold_response.status_code == 200:
        threshold_data = threshold_response.json()
        current_threshold = threshold_data.get("current_threshold", 0.85)
except Exception:
    pass

# Update threshold button
if st.sidebar.button("Update Threshold", key="update_threshold"):
    try:
        response = requests.post(
            f"{backend_url.rstrip('/')}/update_similarity_threshold",
            json={"threshold": sim_threshold},
            timeout=10
        )
        if response.status_code == 200:
            result = response.json()
            st.sidebar.success(f"Threshold updated to {sim_threshold:.3f}")
            st.rerun()
        else:
            st.sidebar.error("Failed to update threshold")
    except Exception as e:
        st.sidebar.error(f"Error: {e}")

# Show current threshold
st.sidebar.caption(f"Current threshold: **{current_threshold:.3f}**")
st.sidebar.caption(f"Top-K setting: **{top_k}**")

st.sidebar.markdown("---")
st.sidebar.subheader("Cache Management")

# Cache management
if st.sidebar.button("Clear All Caches", key="clear_all_caches"):
    try:
        response = requests.post(f"{backend_url.rstrip('/')}/clear_cache")
        if response.status_code == 200:
            st.success("All caches cleared!")
            st.rerun()
        else:
            st.error("Failed to clear caches")
    except Exception as e:
        st.error(f"Error: {e}")

st.sidebar.markdown("---")
if st.sidebar.button("Reset Session Stats"):
    st.session_state.stats = {"miss": 0, "hit": 0, "total": 0}
    st.session_state.history.clear()

# ---------- Main UI ----------
st.title("Advanced LLM Caching Demo")
st.caption("Unified Semantic E2E Cache: Intelligent caching with exact matching and semantic similarity. Powered by `/ask` in your FastAPI app.")

col1, col2 = st.columns([2, 1], gap="large")
with col1:
    q_default = "What is this document about?"
    if "question" not in st.session_state:
        st.session_state.question = q_default
    question = st.text_input("Question", value=st.session_state.question, placeholder="Ask about the PDF…")
    if st.button("Ask"):
        st.session_state.go = True
        st.session_state.preset_mode = None

with col2:
    # Create empty containers for initial metrics
    stats = st.session_state.stats
    total_metric = st.empty()
    hits_metric = st.empty()
    misses_metric = st.empty()

    total_metric.metric("Total requests", stats["total"])
    hits_metric.metric("Cache hits", stats["hit"])
    misses_metric.metric("Cache misses", stats["miss"])

# Blocks/containers
summary = st.empty()
badges = st.container()
raw_req = st.expander("Request Payload (raw JSON)", expanded=False)
raw_resp = st.expander("Response JSON (raw)", expanded=False)
ctx_box = st.container()
insight = st.container()
chart = st.container()
st.markdown("---")
st.subheader("Cache Browser — Recent Entries")

# ---------- Make request ----------
go = st.session_state.get("go", False)
if go and question.strip():
    # Build payload based on unified cache
    payload = {
        "question": question.strip(),
        "use_cache": use_cache,
        "min_context_overlap": float(min_overlap),
        "top_k": int(top_k),
    }
    
    # Add TTL if specified
    if ttl_seconds > 0:
        payload["ttl_seconds"] = int(ttl_seconds)



    url = f"{backend_url.rstrip('/')}/ask"
    t0 = time.time()
    err = None
    try:
        resp = requests.post(url, json=payload, timeout=120)
        t_ms = int((time.time() - t0) * 1000)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        err = str(e)
        data, t_ms = None, None

    with raw_req:
        st.code(json.dumps(payload, indent=2), language="json")

    if err:
        st.error(f"Request failed: {err}")
    elif data:
        # Record counters & append to history
        _record_hit(data.get("cache_type"), data.get("from_cache", False))
        snapshot = {
            "ts": int(time.time()),
            "payload": payload,
            "response": data,
            "latency_ms": t_ms,
        }
        st.session_state.history.append(snapshot)

        # 1) Run Summary — straightforward print-out
        model = data.get("model") or "—"
        doc_ids = data.get("doc_ids") or []
        cache_str = "hit" if data.get("from_cache") else "miss"
        with summary:
            summary_text = (
                "**Run Summary**\n"
                f"- cache: **{cache_str}**\n"
                f"- latency: **{t_ms} ms**\n"
                f"- model: `{model}`\n"
                f"- doc_ids ({len(doc_ids)}): "
                + (", ".join(map(str, doc_ids)) if doc_ids else "—")
            )
            st.markdown(summary_text)


        # 2) Badges (visual)
        with badges:
            b1, b2, b3 = st.columns([1, 1, 3])
            if data.get("from_cache"):
                b1.success(f"cache: {data.get('cache_type') or 'unknown'}")
            else:
                b1.warning("cache: miss")
            b2.info(f"latency: {t_ms} ms" if t_ms is not None else "latency: —")
            b3.caption("Tip: use presets or adjust min_context_overlap in the sidebar.")

        # 3) Response JSON (raw)
        with raw_resp:
            st.code(json.dumps(data, indent=2), language="json")

        # 4) Context & Answer
        with ctx_box:
            st.subheader("Answer")
            st.write(data.get("answer") or "(no answer)")
            st.caption(f"model: `{model}`")

            if doc_ids:
                st.caption("doc_ids:")
                st.write(", ".join(map(str, doc_ids)))

        # 5) Cache Insight — E2E row lookup + TTL remaining
        with insight:
            st.markdown("### Cache Insight")
            # Compute the exact E2E key the backend uses (same algo as backend).  (Ref) :contentReference[oaicite:5]{index=5}
            e2e_key = _e2e_cache_key(question.strip(), model, doc_ids)
            ttl_remaining = "—"
            row_present = False
            created_at_h = "—"
            expires_at_h = "—"

            if E2E_DB_PATH.exists():
                try:
                    con = sqlite3.connect(str(E2E_DB_PATH))
                    cur = con.cursor()
                    cur.execute(
                        "SELECT created_at, ttl_seconds FROM responses WHERE cache_key=?",
                        (e2e_key,),
                    )
                    row = cur.fetchone()
                    con.close()
                    if row:
                        row_present = True
                        created_at, ttl_seconds = row
                        now = int(time.time())
                        remaining = (created_at + ttl_seconds) - now
                        ttl_remaining = f"{max(0, remaining)} s"
                        created_at_h = _human(created_at)
                        expires_at_h = _human(created_at + ttl_seconds)
                except Exception as ex:
                    st.warning(f"Could not inspect E2E cache row: {ex}")

            left, right = st.columns(2)
            left_text = (
                f"- unified cache row present: **{row_present}**\n"
                f"- cache key (sha256): `{e2e_key[:16]}…`\n"
                f"- created_at: {created_at_h}\n"
                f"- expires_at: {expires_at_h}\n"
                f"- ttl_remaining: {ttl_remaining}"
            )
            left.write(left_text)

            right_text = (
                f"- final cache result: **{cache_str}**\n"
                "- unified cache strategy: Intelligent semantic E2E caching\n"
                "  *(similarity threshold & context overlap enforced server-side)*\n"
                "- Cache store: SQLite at `/app/cache/e2e_cache.sqlite`\n"
                "- Semantic search: Qdrant collection `llm_cache_<namespace>`"
            )
            right.write(right_text)


        # 6) Session mini-chart
        with chart:
            stats = st.session_state.stats
            df = pd.DataFrame({"count": [stats["miss"], stats["hit"]]},
                              index=["miss", "hit"])
            st.bar_chart(df)
        

        # Update each metric individually
        total_metric.metric("Total requests", stats["total"])
        hits_metric.metric("Cache hits", stats["hit"])
        misses_metric.metric("Cache misses", stats["miss"])
        
        # Clear request flag after processing
        if "go" in st.session_state:
            del st.session_state.go


# ---------- Unified Cache Browser (enriched) ----------
if E2E_DB_PATH.exists():
    try:
        con = sqlite3.connect(str(E2E_DB_PATH))
        df = pd.read_sql_query(
            """
            SELECT
              cache_key,
              substr(answer, 1, 120) AS answer_preview,
              created_at,
              ttl_seconds,
              COALESCE(meta_json, '') AS meta_json
            FROM responses
            ORDER BY created_at DESC
            LIMIT 50
            """,
            con,
        )
        con.close()
        # add computed fields
        now = int(time.time())
        df["expires_at"] = df["created_at"] + df["ttl_seconds"]
        df["ttl_remaining_s"] = (df["expires_at"] - now).clip(lower=0)
        df["created_at"] = pd.to_datetime(df["created_at"], unit="s", utc=True)
        df["expires_at"] = pd.to_datetime(df["expires_at"], unit="s", utc=True)
        st.dataframe(df, use_container_width=True, hide_index=True)
    except Exception as e:
        st.warning(f"Could not read cache: {e}")
else:
    st.info("No cache file found yet (run at least one request).")

# ---------- Optional: Qdrant stats ----------
if QDRANT_URL:
    try:
        r = requests.get(QDRANT_URL.rstrip("/") + "/collections", timeout=5)
        r.raise_for_status()
        collections = r.json()
        st.markdown("### Qdrant Collections")
        st.code(json.dumps(collections, indent=2), language="json")
    except Exception as e:
        st.caption(f"Qdrant stats unavailable: {e}")