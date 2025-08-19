#!/usr/bin/env python3
"""
Top-K Testing Script

This script helps you understand how different top_k values affect
semantic cache performance and cache hit rates.
"""

import requests
import json
import time
from typing import List, Dict
import statistics

class TopKTest:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        
    def test_top_k_performance(self):
        """Test performance with different top_k values"""
        print("🔍 Top-K Performance Testing")
        print("=" * 50)
        
        # Test questions with varying similarity
        test_questions = [
            "What is this document about?",
            "Tell me about the main topic",
            "What is amatol?",
            "What are the components of amatol?",
            "How is amatol used?",
            "What are the safety considerations?",
            "Tell me about the history of amatol",
            "What are the chemical properties?",
            "How does amatol compare to TNT?",
            "What are the military applications?"
        ]
        
        # Test different top_k values
        top_k_values = [1, 3, 5, 10]
        
        print(f"📝 Test Questions: {len(test_questions)} questions")
        print(f"🎯 Top-K Values: {top_k_values}")
        print()
        
        results = {}
        
        for top_k in top_k_values:
            print(f"🔧 Testing top_k = {top_k}")
            print("-" * 30)
            
            # Clear cache first for fair testing
            self.clear_semantic_cache()
            time.sleep(2)
            
            # Test performance
            cache_hits = 0
            response_times = []
            
            for i, question in enumerate(test_questions):
                print(f"   Question {i+1}: {question[:40]}...")
                
                # Time the request
                start_time = time.time()
                response = self.ask_question(question, top_k)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000  # Convert to ms
                response_times.append(response_time)
                
                if response:
                    cache_type = response.get('cache_type', 'miss')
                    if cache_type == 'semantic':
                        cache_hits += 1
                        print(f"     ✅ Cache HIT ({response_time:.1f}ms)")
                    else:
                        print(f"     ❌ Cache MISS ({response_time:.1f}ms)")
                else:
                    print(f"     ❌ Error ({response_time:.1f}ms)")
                
                # Small delay between requests
                time.sleep(0.5)
            
            # Calculate statistics
            hit_rate = cache_hits / len(test_questions)
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            
            results[top_k] = {
                'hit_rate': hit_rate,
                'avg_response_time': avg_response_time,
                'min_response_time': min_response_time,
                'max_response_time': max_response_time,
                'cache_hits': cache_hits,
                'total_questions': len(test_questions)
            }
            
            print(f"   📊 Results:")
            print(f"     Cache Hit Rate: {hit_rate:.1%} ({cache_hits}/{len(test_questions)})")
            print(f"     Avg Response Time: {avg_response_time:.1f}ms")
            print(f"     Response Time Range: {min_response_time:.1f}ms - {max_response_time:.1f}ms")
            print()
        
        # Summary comparison
        print("📋 Performance Comparison Summary")
        print("=" * 50)
        
        print(f"{'Top-K':<6} {'Hit Rate':<12} {'Avg Time':<12} {'Min Time':<12} {'Max Time':<12}")
        print("-" * 60)
        
        for top_k in top_k_values:
            result = results[top_k]
            print(f"{top_k:<6} {result['hit_rate']:<12.1%} {result['avg_response_time']:<12.1f}ms "
                  f"{result['min_response_time']:<12.1f}ms {result['max_response_time']:<12.1f}ms")
        
        print()
        
        # Recommendations
        print("💡 Recommendations:")
        print("-" * 30)
        
        best_hit_rate = max(results.values(), key=lambda x: x['hit_rate'])
        best_performance = min(results.values(), key=lambda x: x['avg_response_time'])
        
        print(f"• Best Cache Hit Rate: top_k = {[k for k, v in results.items() if v == best_hit_rate][0]}")
        print(f"• Best Performance: top_k = {[k for k, v in results.items() if v == best_performance][0]}")
        
        print(f"\n🎯 Specific Recommendations:")
        if results[1]['hit_rate'] > 0.8:
            print("• top_k = 1: Excellent for simple, straightforward questions")
        if results[3]['hit_rate'] > 0.7:
            print("• top_k = 3: Good balance of performance and cache hits")
        if results[5]['hit_rate'] > 0.8:
            print("• top_k = 5: Great for complex domains with question variations")
        if results[10]['hit_rate'] > 0.9:
            print("• top_k = 10: Maximum cache utilization, best for research systems")
    
    def test_top_k_behavior(self):
        """Test how top_k affects cache behavior with specific questions"""
        print(f"\n🧪 Top-K Behavior Testing")
        print("=" * 50)
        
        # Test with a specific question pattern
        base_question = "What is this document about?"
        similar_questions = [
            "Tell me about the main topic",
            "What is the document about?",
            "Summarize the content",
            "What does this document discuss?"
        ]
        
        print(f"📝 Base Question: {base_question}")
        print(f"🔍 Similar Questions: {len(similar_questions)}")
        print()
        
        for top_k in [1, 3, 5]:
            print(f"🎯 Testing top_k = {top_k}")
            print("-" * 30)
            
            # Clear cache
            self.clear_semantic_cache()
            time.sleep(1)
            
            # Ask base question
            print("   📤 Base question...")
            base_response = self.ask_question(base_question, top_k)
            if base_response:
                print(f"     Cache: {base_response.get('cache_type', 'miss')}")
            
            # Test similar questions
            for i, similar_q in enumerate(similar_questions):
                print(f"   📤 Similar question {i+1}...")
                response = self.ask_question(similar_q, top_k)
                if response:
                    cache_type = response.get('cache_type', 'miss')
                    print(f"     Cache: {cache_type}")
                else:
                    print(f"     Error")
            
            print()
    
    def ask_question(self, question: str, top_k: int = 3) -> Dict:
        """Ask a question (note: top_k is not configurable via API in current implementation)"""
        try:
            payload = {
                "question": question,
                "use_semantic_cache": True,
                "use_e2e_cache": False,
                "min_context_overlap": 0.34
            }
            
            response = requests.post(f"{self.base_url}/ask", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"     Error asking question: {e}")
            return {}
    
    def clear_semantic_cache(self):
        """Clear the semantic cache for testing"""
        try:
            response = requests.post(f"{self.base_url}/clear_semantic_cache")
            if response.status_code == 200:
                print("   🗑️ Cache cleared")
            else:
                print("   ❌ Failed to clear cache")
        except Exception as e:
            print(f"   ❌ Error clearing cache: {e}")

def main():
    """Main function to run the tests"""
    try:
        tester = TopKTest()
        tester.test_top_k_performance()
        tester.test_top_k_behavior()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the FastAPI backend.")
        print("Make sure the backend is running on http://localhost:8080")
        print("Run: docker compose up --build")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
