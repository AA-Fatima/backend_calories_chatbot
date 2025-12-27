import pandas as pd
import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import json
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.nlp_engine import NLPEngine
from app.services.fallback_service import FallbackService
from app.services.food_search import FoodSearchService
from app.services.calorie_calculator import CalorieCalculatorService
from app.services.missing_dish_logger import MissingDishLogger
from app.data.loaders import USDALoader, DishesLoader
from app.config import settings


class ChatbotComparator:
    """Compare our chatbot with GPT and DeepSeek"""
    
    def __init__(self):
        self.nlp_engine = None
        self.food_search = None
        self.calorie_calculator = None
        self.fallback_service = FallbackService()
        self.results = []
    
    async def initialize(self):
        """Initialize all services"""
        print("🔄 Initializing services...")
        
        # Load data
        usda_foundation = USDALoader.load_foundation(settings.USDA_FOUNDATION_PATH)
        usda_sr_legacy = USDALoader.load_sr_legacy(settings.USDA_SR_LEGACY_PATH)
        dishes = DishesLoader.load(settings.DISHES_PATH)
        
        # Initialize NLP
        self.nlp_engine = NLPEngine()
        await self.nlp_engine.initialize()
        
        # Initialize services
        self.food_search = FoodSearchService(
            usda_foundation, usda_sr_legacy, dishes, self.nlp_engine
        )
        
        missing_logger = MissingDishLogger()
        self.calorie_calculator = CalorieCalculatorService(
            self.food_search, self.fallback_service, missing_logger
        )
        
        print("✅ Services initialized")
    
    async def get_our_response(self, query: str, country: str) -> Optional[float]:
        """Get calorie response from our chatbot"""
        try: 
            parsed = self.nlp_engine.parse_query(query)
            result = await self.calorie_calculator.calculate(parsed, country, {})
            return result.total_calories if result.total_calories > 0 else None
        except Exception as e:
            print(f"  ⚠️ Our chatbot error: {e}")
            return None
    
    async def get_gpt_response(self, query: str, country: str) -> Optional[float]: 
        """Get calorie response from GPT"""
        try: 
            result = await self.fallback_service.get_calories_from_gpt(query, country)
            return result.get("calories") if result else None
        except Exception as e:
            print(f"  ⚠️ GPT error:  {e}")
            return None
    
    async def get_deepseek_response(self, query:  str, country: str) -> Optional[float]:
        """Get calorie response from DeepSeek"""
        try:
            result = await self.fallback_service.get_calories_from_deepseek(query, country)
            return result.get("calories") if result else None
        except Exception as e: 
            print(f"  ⚠️ DeepSeek error: {e}")
            return None
    
    def calculate_error(self, predicted: Optional[float], actual:  float) -> Optional[float]:
        """Calculate percentage error"""
        if predicted is None or actual == 0:
            return None
        return abs(predicted - actual) / actual * 100
    
    async def run_comparison(
        self,
        test_file: str,
        include_gpt: bool = True,
        include_deepseek: bool = True,
        output_file: str = "evaluation_results.xlsx"
    ) -> Dict:
        """Run full comparison"""
        
        # Load test cases
        print(f"📂 Loading test cases from {test_file}...")
        df = pd.read_excel(test_file)
        
        results = []
        total = len(df)
        
        print(f"🧪 Running {total} test cases...\n")
        
        for idx, row in df.iterrows():
            query = str(row.get('query', row.get('food_name', '')))
            expected = float(row.get('expected_calories', row.get('calories', 0)))
            country = str(row.get('country', 'lebanon')).lower()
            
            if not query or expected == 0:
                continue
            
            print(f"[{idx + 1}/{total}] Testing: {query}")
            
            # Get responses
            our_cal = await self.get_our_response(query, country)
            gpt_cal = await self.get_gpt_response(query, country) if include_gpt else None
            deepseek_cal = await self.get_deepseek_response(query, country) if include_deepseek else None
            
            # Calculate errors
            our_error = self.calculate_error(our_cal, expected)
            gpt_error = self.calculate_error(gpt_cal, expected)
            deepseek_error = self.calculate_error(deepseek_cal, expected)
            
            result = {
                'query': query,
                'country': country,
                'expected_calories': expected,
                'our_calories': our_cal,
                'gpt_calories': gpt_cal,
                'deepseek_calories': deepseek_cal,
                'our_error_%': round(our_error, 2) if our_error else None,
                'gpt_error_%': round(gpt_error, 2) if gpt_error else None,
                'deepseek_error_%': round(deepseek_error, 2) if deepseek_error else None,
            }
            
            results.append(result)
            
            # Print progress
            print(f"  Expected: {expected} | Ours: {our_cal} | GPT: {gpt_cal} | DeepSeek: {deepseek_cal}")
        
        # Calculate summary statistics
        summary = self._calculate_summary(results)
        
        # Save results
        self._save_results(results, summary, output_file)
        
        return summary
    
    def _calculate_summary(self, results:  List[Dict]) -> Dict:
        """Calculate summary statistics"""
        our_errors = [r['our_error_%'] for r in results if r['our_error_%'] is not None]
        gpt_errors = [r['gpt_error_%'] for r in results if r['gpt_error_%'] is not None]
        deepseek_errors = [r['deepseek_error_%'] for r in results if r['deepseek_error_%'] is not None]
        
        def calc_stats(errors):
            if not errors:
                return {'avg':  None, 'within_10%': None, 'within_20%': None}
            return {
                'avg': round(sum(errors) / len(errors), 2),
                'within_10%': round(len([e for e in errors if e <= 10]) / len(errors) * 100, 2),
                'within_20%': round(len([e for e in errors if e <= 20]) / len(errors) * 100, 2),
            }
        
        return {
            'total_cases': len(results),
            'our_chatbot':  calc_stats(our_errors),
            'gpt':  calc_stats(gpt_errors),
            'deepseek': calc_stats(deepseek_errors),
            'timestamp': datetime.now().isoformat()
        }
    
    def _save_results(self, results: List[Dict], summary: Dict, output_file: str):
        """Save results to Excel"""
        # Results sheet
        df_results = pd.DataFrame(results)
        
        # Summary sheet
        summary_data = {
            'Metric': ['Total Cases', 'Average Error %', 'Accuracy (within 10%)', 'Accuracy (within 20%)'],
            'Our Chatbot': [
                summary['total_cases'],
                summary['our_chatbot']['avg'],
                summary['our_chatbot']['within_10%'],
                summary['our_chatbot']['within_20%']
            ],
            'ChatGPT': [
                summary['total_cases'],
                summary['gpt']['avg'] if summary['gpt']['avg'] else 'N/A',
                summary['gpt']['within_10%'] if summary['gpt']['within_10%'] else 'N/A',
                summary['gpt']['within_20%'] if summary['gpt']['within_20%'] else 'N/A'
            ],
            'DeepSeek': [
                summary['total_cases'],
                summary['deepseek']['avg'] if summary['deepseek']['avg'] else 'N/A',
                summary['deepseek']['within_10%'] if summary['deepseek']['within_10%'] else 'N/A',
                summary['deepseek']['within_20%'] if summary['deepseek']['within_20%'] else 'N/A'
            ]
        }
        df_summary = pd.DataFrame(summary_data)
        
        # Save to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            df_results.to_excel(writer, sheet_name='Detailed Results', index=False)
            df_summary.to_excel(writer, sheet_name='Summary', index=False)
        
        print(f"\n📊 Results saved to {output_file}")
        
        # Print summary
        print("\n" + "="*60)
        print("📈 EVALUATION SUMMARY")
        print("="*60)
        print(f"Total test cases: {summary['total_cases']}")
        print("\n--- Our Chatbot ---")
        print(f"  Average Error: {summary['our_chatbot']['avg']}%")
        print(f"  Accuracy (±10%): {summary['our_chatbot']['within_10%']}%")
        print(f"  Accuracy (±20%): {summary['our_chatbot']['within_20%']}%")
        
        if summary['gpt']['avg']:
            print("\n--- ChatGPT ---")
            print(f"  Average Error: {summary['gpt']['avg']}%")
            print(f"  Accuracy (±10%): {summary['gpt']['within_10%']}%")
            print(f"  Accuracy (±20%): {summary['gpt']['within_20%']}%")
        
        if summary['deepseek']['avg']:
            print("\n--- DeepSeek ---")
            print(f"  Average Error:  {summary['deepseek']['avg']}%")
            print(f"  Accuracy (±10%): {summary['deepseek']['within_10%']}%")
            print(f"  Accuracy (±20%): {summary['deepseek']['within_20%']}%")
        
        print("="*60)