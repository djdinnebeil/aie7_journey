#!/usr/bin/env python3
"""
CLI Tool for Managing Similarity Threshold

Quick command-line tool to view and update the similarity threshold.
"""

import argparse
import requests
import sys
from typing import Optional

def get_threshold(base_url: str) -> Optional[float]:
    """Get the current similarity threshold"""
    try:
        response = requests.get(f"{base_url}/current_similarity_threshold", timeout=5)
        response.raise_for_status()
        data = response.json()
        return data.get("current_threshold")
    except Exception as e:
        print(f"Error getting threshold: {e}")
        return None

def update_threshold(base_url: str, new_threshold: float) -> bool:
    """Update the similarity threshold"""
    try:
        response = requests.post(
            f"{base_url}/update_similarity_threshold",
            json={"threshold": new_threshold},
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
        print(f"✅ Threshold updated successfully!")
        print(f"   Old threshold: {data.get('old_threshold', 'unknown')}")
        print(f"   New threshold: {data.get('new_threshold', 'unknown')}")
        print(f"   Note: {data.get('note', '')}")
        return True
    except Exception as e:
        print(f"❌ Error updating threshold: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Manage similarity threshold for semantic cache",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # View current threshold
  python threshold_cli.py get
  
  # Update threshold to 0.80
  python threshold_cli.py set 0.80
  
  # Update threshold with custom backend URL
  python threshold_cli.py set 0.75 --url http://localhost:8080
        """
    )
    
    parser.add_argument(
        "action",
        choices=["get", "set"],
        help="Action to perform: 'get' to view current threshold, 'set' to update threshold"
    )
    
    parser.add_argument(
        "threshold",
        nargs="?",
        type=float,
        help="New threshold value (0.0 to 1.0) - required for 'set' action"
    )
    
    parser.add_argument(
        "--url",
        default="http://localhost:8080",
        help="Backend URL (default: http://localhost:8080)"
    )
    
    args = parser.parse_args()
    
    # Validate threshold range if setting
    if args.action == "set":
        if args.threshold is None:
            print("❌ Error: Threshold value is required for 'set' action")
            sys.exit(1)
        
        if not 0.0 <= args.threshold <= 1.0:
            print("❌ Error: Threshold must be between 0.0 and 1.0")
            sys.exit(1)
    
    # Perform action
    if args.action == "get":
        print(f"🔍 Getting current threshold from {args.url}...")
        current = get_threshold(args.url)
        if current is not None:
            print(f"📊 Current similarity threshold: {current:.3f}")
        else:
            print("❌ Failed to get threshold")
            sys.exit(1)
    
    elif args.action == "set":
        print(f"🔧 Updating threshold to {args.threshold:.3f} on {args.url}...")
        success = update_threshold(args.url, args.threshold)
        if not success:
            sys.exit(1)

if __name__ == "__main__":
    main()
