#!/usr/bin/env python3
"""
Create sample test cases for evaluation
"""

import pandas as pd

# Sample test cases with ground truth
test_cases = [
    {"query": "shawarma", "expected_calories": 550, "country": "lebanon"},
    {"query": "falafel sandwich", "expected_calories": 450, "country": "lebanon"},
    {"query": "hummus", "expected_calories": 180, "country": "lebanon"},
    {"query": "kushari", "expected_calories": 620, "country": "egypt"},
    {"query": "molokhia with rice", "expected_calories": 380, "country": "egypt"},
    {"query": "ful medames", "expected_calories": 220, "country": "egypt"},
    {"query": "kabsa", "expected_calories": 750, "country": "saudi"},
    {"query":  "mandi chicken", "expected_calories": 680, "country": "saudi"},
    {"query": "mansaf", "expected_calories": 850, "country": "jordan"},
    {"query": "maqluba", "expected_calories": 620, "country": "palestine"},
    {"query": "kibbeh", "expected_calories": 320, "country": "syria"},
    {"query": "tabbouleh", "expected_calories": 120, "country": "lebanon"},
    {"query": "fattoush", "expected_calories": 150, "country": "lebanon"},
    {"query": "baba ganoush", "expected_calories":  140, "country": "lebanon"},
    {"query": "grilled chicken breast", "expected_calories": 165, "country": "lebanon"},
    {"query": "baklava", "expected_calories": 340, "country": "lebanon"},
    {"query": "kunafa", "expected_calories": 450, "country": "palestine"},
    {"query": "apple", "expected_calories":  95, "country": "lebanon"},
    {"query": "rice 200g", "expected_calories": 260, "country": "saudi"},
    {"query": "pita bread", "expected_calories": 165, "country": "lebanon"},
]

# Create DataFrame
df = pd.DataFrame(test_cases)

# Save to Excel
output_file = "test_cases.xlsx"
df.to_excel(output_file, index=False)

print(f"✅ Created {output_file} with {len(test_cases)} test cases")
print("\nSample data:")
print(df.head(10))