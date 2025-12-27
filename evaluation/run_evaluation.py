"""
Evaluation Framework for Arabic Calorie Chatbot
Compares our system against GPT-4 and DeepSeek
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class EvaluationCase:
    """Single evaluation test case"""
    query: str
    country: str
    expected_calories: float
    expected_weight_g: float
    tolerance_percent: float = 15.0  # Acceptable error margin
    category: str = "dish"  # dish, ingredient, modification


@dataclass
class EvaluationResult:
    """Result of evaluating one test case"""
    test_case: EvaluationCase
    our_calories: Optional[float] = None
    our_weight_g: Optional[float] = None
    our_confidence: Optional[float] = None
    our_source: Optional[str] = None
    our_response_time_ms: Optional[float] = None
    
    gpt_calories: Optional[float] = None
    gpt_weight_g: Optional[float] = None
    gpt_response_time_ms:  Optional[float] = None
    
    deepseek_calories: Optional[float] = None
    deepseek_weight_g: Optional[float] = None
    deepseek_response_time_ms: Optional[float] = None
    
    @property
    def our_error_percent(self) -> Optional[float]:
        if self.our_calories is None: 
            return None
        expected = self.test_case.expected_calories
        if expected == 0:
            return 0 if self.our_calories == 0 else 100
        return abs(self.our_calories - expected) / expected * 100
    
    @property
    def gpt_error_percent(self) -> Optional[float]:
        if self.gpt_calories is None:
            return None
        expected = self.test_case.expected_calories
        if expected == 0:
            return 0 if self.gpt_calories == 0 else 100
        return abs(self.gpt_calories - expected) / expected * 100
    
    @property
    def deepseek_error_percent(self) -> Optional[float]:
        if self.deepseek_calories is None: 
            return None
        expected = self.test_case.expected_calories
        if expected == 0:
            return 0 if self.deepseek_calories == 0 else 100
        return abs(self.deepseek_calories - expected) / expected * 100
    
    @property
    def our_is_accurate(self) -> bool:
        if self.our_error_percent is None:
            return False
        return self.our_error_percent <= self.test_case.tolerance_percent
    
    @property
    def gpt_is_accurate(self) -> bool:
        if self.gpt_error_percent is None:
            return False
        return self.gpt_error_percent <= self.test_case.tolerance_percent
    
    @property
    def deepseek_is_accurate(self) -> bool:
        if self.deepseek_error_percent is None:
            return False
        return self.deepseek_error_percent <= self.test_case.tolerance_percent
    
    def to_dict(self) -> Dict:
        return {
            'query': self.test_case.query,
            'country': self.test_case.country,
            'category': self.test_case.category,
            'expected_calories': self.test_case.expected_calories,
            'expected_weight_g':  self.test_case.expected_weight_g,
            'tolerance_percent': self.test_case.tolerance_percent,
            
            'our_calories': self.our_calories,
            'our_weight_g': self.our_weight_g,
            'our_confidence': self.our_confidence,
            'our_source': self.our_source,
            'our_error_percent': self.our_error_percent,
            'our_response_time_ms': self.our_response_time_ms,
            'our_is_accurate':  self.our_is_accurate,
            
            'gpt_calories': self.gpt_calories,
            'gpt_error_percent': self.gpt_error_percent,
            'gpt_response_time_ms': self.gpt_response_time_ms,
            'gpt_is_accurate':  self.gpt_is_accurate,
            
            'deepseek_calories':  self.deepseek_calories,
            'deepseek_error_percent': self.deepseek_error_percent,
            'deepseek_response_time_ms': self.deepseek_response_time_ms,
            'deepseek_is_accurate':  self.deepseek_is_accurate,
        }


class CalorieChatbotEvaluator:
    """
    Comprehensive evaluation system for the Arabic Calorie Chatbot
    
    Metrics:
    1. Accuracy: How close to expected calories
    2. Precision: Consistency across multiple queries
    3. Recall: Ability to find dishes in database
    4. Response Time: Speed comparison
    5. Language Handling: Multi-language input accuracy
    """
    
    def __init__(
        self,
        calorie_calculator,
        nlp_engine,
        fallback_service
    ):
        self.calculator = calorie_calculator
        self.nlp = nlp_engine
        self.fallback = fallback_service
        self.results: List[EvaluationResult] = []
    
    def load_test_cases(self, filepath: str) -> List[EvaluationCase]:
        """Load test cases from Excel/CSV file"""
        df = pd.read_excel(filepath) if filepath.endswith('.xlsx') else pd.read_csv(filepath)
        
        cases = []
        for _, row in df.iterrows():
            case = EvaluationCase(
                query=row['query'],
                country=row.get('country', 'lebanon'),
                expected_calories=float(row['expected_calories']),
                expected_weight_g=float(row.get('expected_weight_g', 0)),
                tolerance_percent=float(row.get('tolerance_percent', 15)),
                category=row.get('category', 'dish')
            )
            cases.append(case)
        
        logger.info(f"Loaded {len(cases)} test cases")
        return cases
    
    async def evaluate_single(self, case: EvaluationCase) -> EvaluationResult: 
        """Evaluate a single test case against all systems"""
        
        result = EvaluationResult(test_case=case)
        
        # Evaluate our system
        try:
            import time
            start = time.time()
            
            parsed = self.nlp.parse_query(case.query)
            context = {'country': case.country}
            our_result = await self.calculator.calculate(parsed, case.country, context)
            
            result.our_response_time_ms = (time.time() - start) * 1000
            result.our_calories = our_result.total_calories
            result.our_weight_g = our_result.weight_g
            result.our_confidence = our_result.confidence
            result.our_source = our_result.source
            
        except Exception as e: 
            logger.error(f"Our system failed for '{case.query}':  {e}")
        
        # Evaluate GPT
        try:
            import time
            start = time.time()
            
            gpt_result, _ = await self.fallback.get_fallback_calories(
                case.query, case.country, provider="openai"
            )
            
            result.gpt_response_time_ms = (time.time() - start) * 1000
            if gpt_result: 
                result.gpt_calories = gpt_result.get('total_calories')
                result.gpt_weight_g = gpt_result.get('weight_g')
                
        except Exception as e:
            logger.error(f"GPT failed for '{case.query}': {e}")
        
        # Evaluate DeepSeek
        try: 
            import time
            start = time.time()
            
            ds_result, _ = await self.fallback.get_fallback_calories(
                case.query, case.country, provider="deepseek"
            )
            
            result.deepseek_response_time_ms = (time.time() - start) * 1000
            if ds_result:
                result.deepseek_calories = ds_result.get('total_calories')
                result.deepseek_weight_g = ds_result.get('weight_g')
                
        except Exception as e:
            logger.error(f"DeepSeek failed for '{case.query}': {e}")
        
        return result
    
    async def run_full_evaluation(
        self,
        test_cases: List[EvaluationCase],
        parallel:  bool = False
    ) -> List[EvaluationResult]:
        """Run evaluation on all test cases"""
        
        logger.info(f"Starting evaluation of {len(test_cases)} test cases")
        self.results = []
        
        if parallel:
            # Run in parallel (faster but may hit rate limits)
            tasks = [self.evaluate_single(case) for case in test_cases]
            self.results = await asyncio.gather(*tasks)
        else: 
            # Run sequentially (slower but more reliable)
            for i, case in enumerate(test_cases):
                logger.info(f"Evaluating {i+1}/{len(test_cases)}: {case.query}")
                result = await self.evaluate_single(case)
                self.results.append(result)
                await asyncio.sleep(0.5)  # Rate limiting
        
        return self.results
    
    def generate_statistics(self) -> Dict[str, Any]: 
        """Generate comprehensive statistics from evaluation results"""
        
        if not self.results:
            return {}
        
        stats = {
            'total_cases': len(self.results),
            'timestamp': datetime.utcnow().isoformat(),
            
            'our_system':  self._calculate_system_stats('our'),
            'gpt':  self._calculate_system_stats('gpt'),
            'deepseek': self._calculate_system_stats('deepseek'),
            
            'by_category': self._calculate_category_stats(),
            'by_country': self._calculate_country_stats(),
        }
    