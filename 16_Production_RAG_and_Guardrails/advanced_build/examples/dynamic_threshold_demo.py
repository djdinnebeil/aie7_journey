#!/usr/bin/env python3
"""
Dynamic Similarity Threshold Demo

This script demonstrates how to change the similarity threshold dynamically
and see its effects on cache behavior.
"""

import requests
import json
import time
from typing import List, Dict

class DynamicThresholdDemo:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        
    def get_current_threshold(self) -> float:
        """Get the current similarity threshold"""
        try:
            response = requests.get(f"{self.base_url}/current_similarity_threshold")
            response.raise_for_status()
            data = response.json()
            return data.get("current_threshold", 0.85)
        except Exception as e:
            print(f"Error getting current threshold: {e}")
            return 0.85
    
    def update_threshold(self, new_threshold: float) -> Dict:
        """Update the similarity threshold"""
        try:
            response = requests.post(
                f"{self.base_url}/update_similarity_threshold",
                json={"threshold": new_threshold}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error updating threshold: {e}")
            return {}
    
    def test_similarity(self, question1: str, question2: str) -> Dict:
        """Test semantic similarity between two questions"""
        try:
            response = requests.post(
                f"{self.base_url}/test_semantic_similarity",
                json={"question1": question1, "question2": question2}
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error testing similarity: {e}")
            return {}
    
    def ask_question(self, question: str, min_overlap: float = 0.34, top_k: int = 3) -> Dict:
        """Ask a question and return the response"""
        try:
            # Ask the question with unified cache
            payload = {
                "question": question,
                "use_cache": True,  # Unified cache flag
                "min_context_overlap": min_overlap,
                "top_k": top_k
            }
            
            response = requests.post(f"{self.base_url}/ask", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error asking question: {e}")
            return {}
    
    def run_threshold_comparison(self):
        """Run a comparison of different threshold values"""
        print("🔧 Dynamic Similarity Threshold Demo")
        print("=" * 50)
        
        # Test questions
        question1 = "What is this document about?"
        question2 = "Tell me about the main topic of this document"
        
        print(f"\n📝 Test Questions:")
        print(f"Q1: {question1}")
        print(f"Q2: {question2}")
        
        # Test with different thresholds
        thresholds = [0.75, 0.80, 0.85, 0.90, 0.95]
        
        print(f"\n🔍 Testing Different Thresholds:")
        print("-" * 50)
        
        for threshold in thresholds:
            print(f"\n📊 Threshold: {threshold:.2f}")
            
            # Update threshold
            update_result = self.update_threshold(threshold)
            if update_result:
                print(f"✅ Updated threshold to {threshold:.2f}")
                
                # Wait a moment for the change to take effect
                time.sleep(1)
                
                # Test similarity
                similarity_result = self.test_similarity(question1, question2)
                if similarity_result:
                    score = similarity_result.get('similarity_score', 0)
                    would_hit = similarity_result.get('would_cache_hit', False)
                    print(f"   Similarity Score: {score:.4f}")
                    print(f"   Would Cache Hit: {'✅ YES' if would_hit else '❌ NO'}")
                    
                    # Test actual cache behavior
                    if would_hit:
                        print("   🧪 Testing cache hit...")
                        response = self.ask_question(question2, min_overlap=0.34, top_k=3)
                        if response:
                            cache_type = response.get('cache_type', 'miss')
                            print(f"   Cache Result: {cache_type}")
                    else:
                        print("   🧪 Testing cache miss...")
                        response = self.ask_question(question2, min_overlap=0.34, top_k=3)
                        if response:
                            cache_type = response.get('cache_type', 'miss')
                            print(f"   Cache Result: {cache_type}")
            else:
                print(f"❌ Failed to update threshold to {threshold:.2f}")
        
        # Reset to default threshold
        print(f"\n🔄 Resetting to default threshold (0.85)...")
        self.update_threshold(0.85)
        print("✅ Reset complete")
        
        # Final comparison
        print(f"\n📋 Summary:")
        print("-" * 30)
        print("• Lower thresholds (0.75-0.80): More cache hits, potentially lower quality")
        print("• Medium thresholds (0.80-0.90): Balanced approach")
        print("• Higher thresholds (0.90-0.95): Fewer cache hits, higher quality")
        print("• Dynamic updates allow real-time tuning without restarts")

def main():
    """Main function to run the demo"""
    try:
        demo = DynamicThresholdDemo()
        demo.run_threshold_comparison()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the FastAPI backend.")
        print("Make sure the backend is running on http://localhost:8080")
        print("Run: docker compose up --build")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
