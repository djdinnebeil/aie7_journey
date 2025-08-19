#!/usr/bin/env python3
"""
Semantic Cache Demo Script

This script demonstrates how to use the semantic cache effectively.
It shows different types of questions and their cache behavior.
"""

import requests
import json
import time
from typing import List, Dict

class SemanticCacheDemo:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        
    def ask_question(self, question: str, use_semantic: bool = True, use_e2e: bool = False) -> Dict:
        """Ask a question and return the response"""
        payload = {
            "question": question,
            "use_cache": True,  # Unified cache flag
            "min_context_overlap": 0.34,
            "top_k": 3
        }
        
        response = requests.post(f"{self.base_url}/ask", json=payload)
        response.raise_for_status()
        return response.json()
    
    def test_semantic_similarity(self, question1: str, question2: str) -> Dict:
        """Test semantic similarity between two questions"""
        payload = {
            "question1": question1,
            "question2": question2
        }
        
        response = requests.post(f"{self.base_url}/test_semantic_similarity", json=payload)
        response.raise_for_status()
        return response.json()
    
    def get_cache_stats(self) -> Dict:
        """Get current cache statistics"""
        response = requests.get(f"{self.base_url}/cache_stats")
        response.raise_for_status()
        return response.json()
    
    def clear_semantic_cache(self) -> Dict:
        """Clear the semantic cache"""
        response = requests.post(f"{self.base_url}/clear_semantic_cache")
        response.raise_for_status()
        return response.json()
    
    def run_demo(self):
        """Run the complete semantic cache demonstration"""
        print("🚀 Semantic Cache Demo")
        print("=" * 50)
        
        # Initial cache stats
        print("\n📊 Initial Cache Stats:")
        stats = self.get_cache_stats()
        print(json.dumps(stats, indent=2))
        
        # Test 1: First question (should miss cache)
        print("\n🔍 Test 1: First Question (Cache Miss)")
        print("-" * 40)
        question1 = "What is this document about?"
        print(f"Question: {question1}")
        
        response1 = self.ask_question(question1, use_semantic=True, use_e2e=False)
        print(f"Cache Result: {response1.get('cache_type', 'miss')}")
        print(f"Answer: {response1.get('answer', '')[:100]}...")
        
        # Test 2: Similar question (should hit semantic cache)
        print("\n🔍 Test 2: Similar Question (Should Hit Semantic Cache)")
        print("-" * 40)
        question2 = "Tell me about the main topic of this document"
        print(f"Question: {question2}")
        
        # Test similarity first
        similarity = self.test_semantic_similarity(question1, question2)
        print(f"Similarity Score: {similarity['similarity_score']:.4f}")
        print(f"Threshold: {similarity['threshold']:.4f}")
        print(f"Would Cache Hit: {similarity['would_cache_hit']}")
        
        response2 = self.ask_question(question2, use_semantic=True, use_e2e=False)
        print(f"Cache Result: {response2.get('cache_type', 'miss')}")
        print(f"Answer: {response2.get('answer', '')[:100]}...")
        
        # Test 3: Very similar question (should definitely hit)
        print("\n🔍 Test 3: Very Similar Question (Should Definitely Hit)")
        print("-" * 40)
        question3 = "What is this document about?"
        print(f"Question: {question3}")
        
        response3 = self.ask_question(question3, use_semantic=True, use_e2e=False)
        print(f"Cache Result: {response3.get('cache_type', 'miss')}")
        print(f"Answer: {response3.get('answer', '')[:100]}...")
        similarity3 = self.test_semantic_similarity(question1, question3)
        print(f"Similarity Score: {similarity['similarity_score']:.4f}")

        
        # Test 4: Different but related question
        print("\n🔍 Test 4: Different but Related Question")
        print("-" * 40)
        question4 = "What are the key components of amatol?"
        print(f"Question: {question4}")
        
        similarity4 = self.test_semantic_similarity(question1, question4)
        print(f"Similarity to original: {similarity4['similarity_score']:.4f}")
        
        response4 = self.ask_question(question4, use_semantic=True, use_e2e=False)
        print(f"Cache Result: {response4.get('cache_type', 'miss')}")
        print(f"Answer: {response4.get('answer', '')[:100]}...")
        
        # Test 5: Completely different question
        print("\n🔍 Test 5: Completely Different Question")
        print("-" * 40)
        question5 = "What is the weather like today?"
        print(f"Question: {question5}")
        
        similarity5 = self.test_semantic_similarity(question1, question5)
        print(f"Similarity Score: {similarity5['similarity_score']:.4f}")
        
        response5 = self.ask_question(question5, use_semantic=True, use_e2e=False)
        print(f"Cache Result: {response5.get('cache_type', 'miss')}")
        print(f"Answer: {response5.get('answer', '')[:100]}...")
        
        # Final cache stats
        print("\n📊 Final Cache Stats:")
        final_stats = self.get_cache_stats()
        print(json.dumps(final_stats, indent=2))
        
        # Summary
        print("\n📋 Summary:")
        print("-" * 40)
        print("• Test 1: First question - should miss cache")
        print("• Test 2: Similar question - may hit semantic cache depending on threshold")
        print("• Test 3: Identical question - should definitely hit semantic cache")
        print("• Test 4: Related question - may hit depending on similarity")
        print("• Test 5: Unrelated question - should miss cache")
        
        print(f"\n💡 Tips for better semantic cache performance:")
        print("• Lower similarity threshold (e.g., 0.85 instead of 0.92)")
        print("• Use similar phrasing for related questions")
        print("• Consider the context overlap requirement")
        print("• Monitor cache hit rates and adjust threshold accordingly")

    def compare_document_points_questions(self):
        """Compare similarity scores for different ways of asking about document points"""
        print("🔍 Document Points Question Similarity Comparison")
        print("=" * 60)
        
        # Define the questions to compare
        base_question = "What are the main points of this document?"
        comparison_questions = [
            "What are the essential points of this document?",
            "What are the key points of this document?",
            "What are the important points of this document?",
            "What are the major points of this document?"
        ]
        
        print(f"\n📝 Base Question: '{base_question}'")
        print("\n📊 Similarity Scores:")
        print("-" * 60)
        
        # Test similarity with each comparison question
        for i, question in enumerate(comparison_questions, 1):
            print(f"\n{i}. Comparison Question: '{question}'")
            
            try:
                similarity = self.test_semantic_similarity(base_question, question)
                print(f"   Similarity Score: {similarity['similarity_score']:.4f}")
                print(f"   Threshold: {similarity['threshold']:.4f}")
                print(f"   Would Cache Hit: {similarity['would_cache_hit']}")
                
                # Also test the reverse comparison
                reverse_similarity = self.test_semantic_similarity(question, base_question)
                print(f"   Reverse Similarity: {reverse_similarity['similarity_score']:.4f}")
                
            except Exception as e:
                print(f"   Error testing similarity: {e}")
        
        # Summary table
        print("\n📋 Summary Table:")
        print("-" * 60)
        print(f"{'Question':<50} {'Similarity':<12} {'Cache Hit':<10}")
        print("-" * 60)
        print(f"{base_question:<50} {'1.0000':<12} {'Yes':<10}")
        
        for question in comparison_questions:
            try:
                similarity = self.test_semantic_similarity(base_question, question)
                cache_hit = "Yes" if similarity['would_cache_hit'] else "No"
                print(f"{question:<50} {similarity['similarity_score']:.4f}     {cache_hit:<10}")
            except Exception as e:
                print(f"{question:<50} {'Error':<12} {'N/A':<10}")
        
        print("\n💡 Analysis:")
        print("• These questions are semantically very similar")
        print("• They should all have high similarity scores (>0.9)")
        print("• All should likely hit the semantic cache")
        print("• This demonstrates the power of semantic caching for rephrased questions")

def main():
    """Main function to run the demo"""
    try:
        demo = SemanticCacheDemo()
        # demo.run_demo()  # Commented out original demo
        demo.compare_document_points_questions()  # Run the new comparison
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the FastAPI backend.")
        print("Make sure the backend is running on http://localhost:8080")
        print("Run: docker compose up --build")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
