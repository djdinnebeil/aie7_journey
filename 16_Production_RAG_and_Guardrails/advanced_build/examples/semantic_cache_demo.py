#!/usr/bin/env python3
"""
Semantic Cache Demo - Updated for Unified Cache

This script demonstrates the unified caching system that combines
E2E exact matching with semantic similarity fallback.
"""

import requests
import json
import time

# Configuration
BACKEND_URL = "http://localhost:8080"
QUESTIONS = [
    "What is this document about?",
    "Tell me about the main topic",
    "What's the primary subject?",
    "Can you summarize the content?",
    "What is the main focus of this text?",
    "Give me an overview of the document",
    "What are the key points?",
    "What is the central theme?"
]

def test_unified_cache():
    """Test the unified cache with various question formulations"""
    
    print("🚀 Testing Unified Cache System")
    print("=" * 50)
    
    # First, clear all caches
    print("\n🧹 Clearing all caches...")
    try:
        response = requests.post(f"{BACKEND_URL}/clear_cache")
        if response.status_code == 200:
            print("✅ Caches cleared successfully")
        else:
            print(f"❌ Failed to clear caches: {response.status_code}")
    except Exception as e:
        print(f"❌ Error clearing caches: {e}")
        return
    
    print(f"\n📊 Initial cache stats:")
    try:
        response = requests.get(f"{BACKEND_URL}/cache_stats")
        if response.status_code == 200:
            stats = response.json()
            print(json.dumps(stats, indent=2))
        else:
            print(f"❌ Failed to get cache stats: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting cache stats: {e}")
    
    print(f"\n🔍 Testing {len(QUESTIONS)} questions...")
    print("-" * 50)
    
    cache_hits = 0
    total_questions = len(QUESTIONS)
    
    for i, question in enumerate(QUESTIONS, 1):
        print(f"\n{i}/{total_questions}: {question}")
        
        # Ask the question with unified cache enabled
        payload = {
            "question": question,
            "use_cache": True,  # Unified cache flag
            "min_context_overlap": 0.34,
            "top_k": 3
        }
        
        try:
            start_time = time.time()
            response = requests.post(f"{BACKEND_URL}/ask", json=payload, timeout=30)
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                latency_ms = int((end_time - start_time) * 1000)
                
                if data.get("from_cache"):
                    cache_type = data.get("cache_type", "unknown")
                    print(f"   ✅ Cache HIT ({cache_type}) - {latency_ms}ms")
                    cache_hits += 1
                else:
                    print(f"   ❌ Cache MISS - {latency_ms}ms")
                
                # Show answer preview
                answer = data.get("answer", "")
                if answer:
                    preview = answer[:100] + "..." if len(answer) > 100 else answer
                    print(f"   📝 Answer: {preview}")
                
                # Show document IDs
                doc_ids = data.get("doc_ids", [])
                if doc_ids:
                    print(f"   📚 Doc IDs: {', '.join(map(str, doc_ids))}")
                    
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                print(f"   📄 Response: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    # Final statistics
    print("\n" + "=" * 50)
    print("📊 FINAL RESULTS")
    print(f"Total Questions: {total_questions}")
    print(f"Cache Hits: {cache_hits}")
    print(f"Cache Misses: {total_questions - cache_hits}")
    print(f"Hit Rate: {(cache_hits / total_questions) * 100:.1f}%")
    
    # Get final cache stats
    print(f"\n📈 Final cache stats:")
    try:
        response = requests.get(f"{BACKEND_URL}/cache_stats")
        if response.status_code == 200:
            stats = response.json()
            print(json.dumps(stats, indent=2))
        else:
            print(f"❌ Failed to get final cache stats: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting final cache stats: {e}")

def test_semantic_similarity():
    """Test semantic similarity between questions"""
    
    print("\n🔍 Testing Semantic Similarity")
    print("=" * 50)
    
    # Test pairs of similar questions
    question_pairs = [
        ("What is this document about?", "Tell me about the main topic"),
        ("What's the primary subject?", "Can you summarize the content?"),
        ("What is the main focus of this text?", "Give me an overview of the document"),
        ("What are the key points?", "What is the central theme?")
    ]
    
    for q1, q2 in question_pairs:
        print(f"\n📝 Question 1: {q1}")
        print(f"📝 Question 2: {q2}")
        
        try:
            response = requests.post(f"{BACKEND_URL}/test_semantic_similarity", 
                                   json={"question1": q1, "question2": q2})
            
            if response.status_code == 200:
                data = response.json()
                similarity = data.get("similarity_score", 0)
                threshold = data.get("threshold", 0.85)
                would_hit = data.get("would_cache_hit", False)
                
                print(f"   🔗 Similarity: {similarity:.4f}")
                print(f"   🎯 Threshold: {threshold:.4f}")
                print(f"   💾 Would Cache Hit: {'✅ Yes' if would_hit else '❌ No'}")
                
            else:
                print(f"   ❌ Request failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🎯 Unified Cache Demo - E2E + Semantic Caching")
    print("This demo shows how the unified cache combines exact matching with semantic similarity")
    print()
    
    # Test the unified cache
    test_unified_cache()
    
    # Test semantic similarity
    test_semantic_similarity()
    
    print("\n🎉 Demo completed!")
    print("\n💡 Key Benefits of Unified Cache:")
    print("   • E2E cache provides fast exact matches")
    print("   • Semantic cache catches rephrased questions")
    print("   • Context overlap ensures relevance")
    print("   • Single API flag simplifies usage")
    print("   • Better hit rates than either cache alone")
    print("   • Unified metrics: 'Cache Hits' vs 'Cache Misses'")
