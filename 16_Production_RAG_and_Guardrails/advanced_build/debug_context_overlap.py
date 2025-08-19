#!/usr/bin/env python3
"""
Debug Context Overlap Script

This script helps debug why semantic cache hits are failing due to context overlap.
"""

import requests
import json

def debug_context_overlap():
    base_url = "http://localhost:8080"
    
    # Test questions
    question1 = "What are the main points of this document?"
    question2 = "What are the key points of this document?"
    
    print("🔍 Debugging Context Overlap Issue")
    print("=" * 50)
    
    # First, test semantic similarity
    print(f"\n📝 Question 1: '{question1}'")
    print(f"📝 Question 2: '{question2}'")
    
    try:
        # Test similarity
        similarity_response = requests.post(
            f"{base_url}/test_semantic_similarity",
            json={"question1": question1, "question2": question2}
        )
        similarity_data = similarity_response.json()
        
        print(f"\n🎯 Similarity Score: {similarity_data['similarity_score']:.4f}")
        print(f"🎯 Threshold: {similarity_data['threshold']:.4f}")
        print(f"🎯 Would Cache Hit (similarity only): {similarity_data['would_cache_hit']}")
        
        # Now test actual cache behavior with different overlap settings
        print(f"\n🔍 Testing Cache Behavior with Different Overlap Settings:")
        print("-" * 60)
        
        overlap_values = [0.0, 0.1, 0.2, 0.34, 0.5, 0.8]
        
        for overlap in overlap_values:
            print(f"\n📊 Testing with min_context_overlap = {overlap:.2f}")
            
            # Ask question 2 with the specified overlap
            payload = {
                "question": question2,
                "use_semantic_cache": True,
                "use_e2e_cache": False,
                "min_context_overlap": overlap,
                "top_k": 3
            }
            
            response = requests.post(f"{base_url}/ask", json=payload)
            response_data = response.json()
            
            cache_result = response_data.get('cache_type', 'miss')
            from_cache = response_data.get('from_cache', False)
            
            print(f"   Cache Result: {cache_result}")
            print(f"   From Cache: {from_cache}")
            
            if from_cache:
                print(f"   ✅ SUCCESS: Cache hit with overlap = {overlap}")
                break
            else:
                print(f"   ❌ FAILED: Cache miss with overlap = {overlap}")
        
        # Get cache stats to see what's in the semantic cache
        print(f"\n📊 Current Cache Stats:")
        stats_response = requests.get(f"{base_url}/cache_stats")
        stats_data = stats_response.json()
        print(json.dumps(stats_data, indent=2))
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    debug_context_overlap()
