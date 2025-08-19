#!/usr/bin/env python3
"""
Test Unified Cache

Simple script to test the new unified caching system.
"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8080"

def test_unified_cache():
    """Test the unified cache functionality"""
    
    print("🧪 Testing Unified Cache System")
    print("=" * 40)
    
    # Test 1: Health check
    print("\n1️⃣ Health check...")
    try:
        response = requests.get(f"{BACKEND_URL}/healthz")
        if response.status_code == 200:
            print("   ✅ Backend is healthy")
        else:
            print(f"   ❌ Backend health check failed: {response.status_code}")
            return
    except Exception as e:
        print(f"   ❌ Cannot connect to backend: {e}")
        return
    
    # Test 2: Clear caches
    print("\n2️⃣ Clearing caches...")
    try:
        response = requests.post(f"{BACKEND_URL}/clear_cache")
        if response.status_code == 200:
            print("   ✅ Caches cleared")
        else:
            print(f"   ❌ Failed to clear caches: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error clearing caches: {e}")
    
    # Test 3: Get initial cache stats
    print("\n3️⃣ Getting initial cache stats...")
    try:
        response = requests.get(f"{BACKEND_URL}/cache_stats")
        if response.status_code == 200:
            stats = response.json()
            print("   ✅ Cache stats retrieved")
            print(f"   📊 Stats: {json.dumps(stats, indent=2)}")
        else:
            print(f"   ❌ Failed to get cache stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting cache stats: {e}")
    
    # Test 4: Ask first question (should miss cache)
    print("\n4️⃣ Asking first question (should miss cache)...")
    question1 = "What is this document about?"
    payload1 = {
        "question": question1,
        "use_cache": True,
        "min_context_overlap": 0.34,
        "top_k": 3
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BACKEND_URL}/ask", json=payload1, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            latency_ms = int((end_time - start_time) * 1000)
            
            if data.get("from_cache"):
                print(f"   ❌ Unexpected cache hit: {data.get('cache_type')}")
            else:
                print(f"   ✅ Cache miss as expected - {latency_ms}ms")
                print(f"   📝 Answer preview: {data.get('answer', '')[:100]}...")
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            print(f"   📄 Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 5: Ask same question (should hit E2E cache)
    print("\n5️⃣ Asking same question (should hit E2E cache)...")
    try:
        start_time = time.time()
        response = requests.post(f"{BACKEND_URL}/ask", json=payload1, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            latency_ms = int((end_time - start_time) * 1000)
            
            if data.get("from_cache"):
                cache_type = data.get("cache_type")
                print(f"   ✅ Cache hit ({cache_type}) - {latency_ms}ms")
                if cache_type == "e2e":
                    print("   🎯 Perfect! E2E cache working")
                else:
                    print(f"   ⚠️  Hit {cache_type} cache instead of E2E")
            else:
                print(f"   ❌ Cache miss - {latency_ms}ms")
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 6: Ask similar question (should hit semantic cache)
    print("\n6️⃣ Asking similar question (should hit semantic cache)...")
    question2 = "Tell me about the main topic"
    payload2 = {
        "question": question2,
        "use_cache": True,
        "min_context_overlap": 0.34,
        "top_k": 3
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BACKEND_URL}/ask", json=payload2, timeout=30)
        end_time = time.time()
        
        if response.status_code == 200:
            data = response.json()
            latency_ms = int((end_time - start_time) * 1000)
            
            if data.get("from_cache"):
                cache_type = data.get("cache_type")
                print(f"   ✅ Cache hit ({cache_type}) - {latency_ms}ms")
                if cache_type == "semantic":
                    print("   🎯 Perfect! Semantic cache working")
                else:
                    print(f"   ⚠️  Hit {cache_type} cache instead of semantic")
            else:
                print(f"   ❌ Cache miss - {latency_ms}ms")
        else:
            print(f"   ❌ Request failed: {response.status_code}")
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Test 7: Get final cache stats
    print("\n7️⃣ Getting final cache stats...")
    try:
        response = requests.get(f"{BACKEND_URL}/cache_stats")
        if response.status_code == 200:
            stats = response.json()
            print("   ✅ Final cache stats retrieved")
            print(f"   📊 Stats: {json.dumps(stats, indent=2)}")
        else:
            print(f"   ❌ Failed to get final cache stats: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Error getting final cache stats: {e}")
    
    print("\n🎉 Test completed!")
    print("\n💡 Expected behavior:")
    print("   • First question: Cache miss (generates new answer)")
    print("   • Same question: Cache hit via E2E exact matching")
    print("   • Similar question: Cache hit via semantic similarity")
    print("\n📊 Unified Cache Benefits:")
    print("   • Single 'use_cache' flag simplifies API")
    print("   • E2E cache provides fastest possible hits")
    print("   • Semantic cache catches rephrased questions")
    print("   • Context overlap ensures answer relevance")
    print("   • Better overall hit rates than either cache alone")

if __name__ == "__main__":
    test_unified_cache()
