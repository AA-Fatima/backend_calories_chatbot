#!/usr/bin/env python3
"""
Run evaluation comparison between our chatbot, ChatGPT, and DeepSeek
"""

import asyncio
import argparse
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from comparator import ChatbotComparator


async def main():
    parser = argparse.ArgumentParser(description='Run chatbot evaluation')
    parser.add_argument(
        '--test-file', 
        type=str, 
        default='test_cases.xlsx',
        help='Path to test cases Excel file'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default='evaluation_results.xlsx',
        help='Output file for results'
    )
    parser.add_argument(
        '--no-gpt', 
        action='store_true',
        help='Skip GPT comparison'
    )
    parser.add_argument(
        '--no-deepseek', 
        action='store_true',
        help='Skip DeepSeek comparison'
    )
    
    args = parser.parse_args()
    
    # Check if test file exists
    if not os.path.exists(args.test_file):
        print(f"❌ Test file not found: {args.test_file}")
        print("\nPlease create a test_cases.xlsx file with columns:")
        print("  - query (or food_name): The food to query")
        print("  - expected_calories (or calories): The correct calorie value")
        print("  - country: The country context (e.g., 'lebanon', 'egypt')")
        return
    
    # Initialize comparator
    comparator = ChatbotComparator()
    await comparator.initialize()
    
    # Run comparison
    summary = await comparator.run_comparison(
        test_file=args.test_file,
        include_gpt=not args.no_gpt,
        include_deepseek=not args.no_deepseek,
        output_file=args.output
    )
    
    print("\n✅ Evaluation complete!")


if __name__ == "__main__": 
    asyncio.run(main())