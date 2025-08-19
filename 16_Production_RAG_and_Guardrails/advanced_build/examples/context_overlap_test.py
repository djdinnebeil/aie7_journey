#!/usr/bin/env python3
"""
Context Overlap Test Script

This script helps you understand how different min_context_overlap values
affect cache behavior and performance.
"""

import requests
import json
import time
from typing import List, Dict

class ContextOverlapTester:
    def __init__(self, base_url: str = "http://localhost:8080"):
        self.base_url = base_url.rstrip('/')
        
    def test_overlap_values(self):
        """Test different overlap values with the same questions"""
        print("🔍 Context Overlap Testing")
        print("=" * 50)
        
        # Test questions that should have some context overlap
        question1 = "What is this document about?"
        question2 = "Tell me about the main topic of this document"
        
        print(f"📝 Test Questions:")
        print(f"Q1: {question1}")
        print(f"Q2: {question2}")
        print()
        
        # Test different overlap values
        overlap_values = [0.0, 0.20, 0.34, 0.50, 0.70, 0.90]
        
        print("📊 Testing Different Overlap Values:")
        print("-" * 50)
        
        for overlap in overlap_values:
            print(f"\n🎯 Overlap Threshold: {overlap:.2f}")
            
            # First, ask the original question to populate cache
            print("   📤 Asking original question...")
            response1 = self.ask_question(question1, overlap)
            if response1:
                cache_result1 = response1.get('cache_type', 'miss')
                doc_ids1 = response1.get('doc_ids', [])
                print(f"   Cache Result: {cache_result1}")
                print(f"   Doc IDs: {doc_ids1}")
            
            # Wait a moment
            time.sleep(1)
            
            # Now ask the similar question
            print("   📤 Asking similar question...")
            response2 = self.ask_question(question2, overlap)
            if response2:
                cache_result2 = response2.get('cache_type', 'miss')
                doc_ids2 = response2.get('doc_ids', [])
                print(f"   Cache Result: {cache_result2}")
                print(f"   Doc IDs: {doc_ids2}")
                
                # Calculate actual overlap
                if doc_ids1 and doc_ids2:
                    actual_overlap = len(set(doc_ids1) & set(doc_ids2)) / len(set(doc_ids1))
                    print(f"   Actual Overlap: {actual_overlap:.3f}")
                    print(f"   Would Hit Cache: {'✅ YES' if actual_overlap >= overlap else '❌ NO'}")
                    print(f"   Cache Behavior: {'✅ Matched' if cache_result2 == 'semantic' else '❌ Mismatch'}")
            
            print("   " + "-" * 40)
        
        # Summary
        print(f"\n📋 Summary:")
        print("-" * 30)
        print("• 0.00: No context requirement (most cache hits)")
        print("• 0.20: Very lenient context matching")
        print("• 0.34: Current setting (balanced)")
        print("• 0.50: Moderate context requirement")
        print("• 0.70: Strict context matching")
        print("• 0.90: Very strict context requirement")
        
        print(f"\n💡 Recommendations:")
        print("-" * 30)
        print("• Start with 0.34 (current) for balanced approach")
        print("• Lower to 0.20-0.30 if you need more cache hits")
        print("• Raise to 0.50-0.70 if answer quality is critical")
        print("• Monitor cache hit rates and adjust accordingly")
    
    def ask_question(self, question: str, min_overlap: float) -> Dict:
        """Ask a question with specific overlap setting"""
        try:
            payload = {
                "question": question,
                "use_cache": True,  # Unified cache flag
                "min_context_overlap": min_overlap,
                "top_k": 3
            }
            
            response = requests.post(f"{self.base_url}/ask", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"   Error asking question: {e}")
            return {}
    
    def test_specific_scenarios(self):
        """Test specific scenarios to understand overlap behavior"""
        print(f"\n🧪 Specific Scenario Testing")
        print("=" * 50)
        
        scenarios = [
            {
                "name": "Identical Questions",
                "q1": "What is this document about?",
                "q2": "What is this document about?",
                "expected_overlap": 1.0
            },
            {
                "name": "Very Similar Questions",
                "q1": "What is this document about?",
                "q2": "Tell me about the main topic",
                "expected_overlap": 0.6
            },
            {
                "name": "Related Questions",
                "q1": "What is amatol?",
                "q2": "What are the components of amatol?",
                "expected_overlap": 0.4
            },
            {
                "name": "Different Topics",
                "q1": "What is amatol?",
                "q2": "What are safety procedures?",
                "expected_overlap": 0.1
            }
        ]
        
        for scenario in scenarios:
            print(f"\n📋 Scenario: {scenario['name']}")
            print("-" * 40)
            print(f"Q1: {scenario['q1']}")
            print(f"Q2: {scenario['q2']}")
            print(f"Expected Overlap: {scenario['expected_overlap']:.1f}")
            
            # Test with different overlap thresholds
            thresholds = [0.0, 0.34, 0.70]
            
            for threshold in thresholds:
                print(f"   🎯 Threshold {threshold:.2f}: ", end="")
                
                # Ask first question
                response1 = self.ask_question(scenario['q1'], threshold)
                if response1:
                    doc_ids1 = response1.get('doc_ids', [])
                    
                    # Ask second question
                    response2 = self.ask_question(scenario['q2'], threshold)
                    if response2:
                        doc_ids2 = response2.get('doc_ids', [])
                        cache_result = response2.get('cache_type', 'miss')
                        
                        # Calculate actual overlap
                        if doc_ids1 and doc_ids2:
                            actual_overlap = len(set(doc_ids1) & set(doc_ids2)) / len(set(doc_ids1))
                            would_hit = actual_overlap >= threshold
                            cache_hit = cache_result == 'semantic'
                            
                            status = "✅" if would_hit == cache_hit else "❌"
                            print(f"{status} Overlap: {actual_overlap:.2f}, Cache: {cache_result}")
                        else:
                            print("❌ No doc IDs available")
                    else:
                        print("❌ Failed to get response")
                else:
                    print("❌ Failed to get response")

def main():
    """Main function to run the tests"""
    try:
        tester = ContextOverlapTester()
        tester.test_overlap_values()
        tester.test_specific_scenarios()
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the FastAPI backend.")
        print("Make sure the backend is running on http://localhost:8080")
        print("Run: docker compose up --build")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
