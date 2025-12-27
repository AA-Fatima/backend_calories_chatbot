from fastapi import APIRouter, HTTPException
from typing import List, Optional
from app.models.schemas import EvaluationResult
from app.services.fallback_service import FallbackService
from pydantic import BaseModel
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class EvaluationRequest(BaseModel):
    test_file_path: Optional[str] = "evaluation/test_cases.xlsx"
    include_gpt:  bool = True
    include_deepseek: bool = True

class EvaluationSummary(BaseModel):
    total_cases: int
    our_avg_error: float
    gpt_avg_error: Optional[float]
    deepseek_avg_error:  Optional[float]
    our_accuracy_within_10_percent: float
    gpt_accuracy_within_10_percent: Optional[float]
    deepseek_accuracy_within_10_percent: Optional[float]
    results: List[EvaluationResult]

@router.post("/run", response_model=EvaluationSummary)
async def run_evaluation(request: EvaluationRequest):
    """Run evaluation comparing our chatbot with GPT and DeepSeek"""
    
    if not os.path.exists(request.test_file_path):
        raise HTTPException(status_code=404, detail=f"Test file not found: {request.test_file_path}")
    
    # Load test cases
    try:
        df = pd.read_excel(request.test_file_path)
    except Exception as e: 
        raise HTTPException(status_code=400, detail=f"Error reading test file: {e}")
    
    # Import here to avoid circular imports
    from app.api.routes.chat import app_state, get_nlp_engine, get_calorie_calculator
    
    nlp_engine = get_nlp_engine()
    calorie_calculator = get_calorie_calculator()
    fallback_service = FallbackService()
    
    results = []
    
    for _, row in df.iterrows():
        query = str(row.get('query', row.get('food_name', '')))
        expected_calories = float(row.get('expected_calories', row.get('calories', 0)))
        country = str(row.get('country', 'lebanon')).lower()
        
        if not query or expected_calories == 0:
            continue
        
        # Get our response
        our_calories = None
        try:
            parsed = nlp_engine.parse_query(query)
            result = await calorie_calculator.calculate(parsed, country, {})
            our_calories = result.total_calories if result.total_calories > 0 else None
        except Exception as e:
            logger.error(f"Error calculating for {query}: {e}")
        
        # Get GPT response
        gpt_calories = None
        if request.include_gpt:
            try:
                gpt_result = await fallback_service.get_calories_from_gpt(query, country)
                if gpt_result: 
                    gpt_calories = gpt_result.get("calories")
            except Exception as e:
                logger.error(f"GPT error for {query}: {e}")
        
        # Get DeepSeek response
        deepseek_calories = None
        if request.include_deepseek: 
            try: 
                deepseek_result = await fallback_service.get_calories_from_deepseek(query, country)
                if deepseek_result:
                    deepseek_calories = deepseek_result.get("calories")
            except Exception as e:
                logger.error(f"DeepSeek error for {query}: {e}")
        
        # Calculate errors
        our_error = abs(our_calories - expected_calories) / expected_calories * 100 if our_calories else None
        gpt_error = abs(gpt_calories - expected_calories) / expected_calories * 100 if gpt_calories else None
        deepseek_error = abs(deepseek_calories - expected_calories) / expected_calories * 100 if deepseek_calories else None
        
        results.append(EvaluationResult(
            query=query,
            expected_calories=expected_calories,
            our_calories=our_calories,
            gpt_calories=gpt_calories,
            deepseek_calories=deepseek_calories,
            our_error_percent=round(our_error, 2) if our_error else None,
            gpt_error_percent=round(gpt_error, 2) if gpt_error else None,
            deepseek_error_percent=round(deepseek_error, 2) if deepseek_error else None
        ))
    
    # Calculate summary statistics
    our_errors = [r.our_error_percent for r in results if r.our_error_percent is not None]
    gpt_errors = [r.gpt_error_percent for r in results if r.gpt_error_percent is not None]
    deepseek_errors = [r.deepseek_error_percent for r in results if r.deepseek_error_percent is not None]
    
    return EvaluationSummary(
        total_cases=len(results),
        our_avg_error=round(sum(our_errors) / len(our_errors), 2) if our_errors else 0,
        gpt_avg_error=round(sum(gpt_errors) / len(gpt_errors), 2) if gpt_errors else None,
        deepseek_avg_error=round(sum(deepseek_errors) / len(deepseek_errors), 2) if deepseek_errors else None,
        our_accuracy_within_10_percent=round(len([e for e in our_errors if e <= 10]) / len(our_errors) * 100, 2) if our_errors else 0,
        gpt_accuracy_within_10_percent=round(len([e for e in gpt_errors if e <= 10]) / len(gpt_errors) * 100, 2) if gpt_errors else None,
        deepseek_accuracy_within_10_percent=round(len([e for e in deepseek_errors if e <= 10]) / len(deepseek_errors) * 100, 2) if deepseek_errors else None,
        results=results
    )

@router.get("/missing-dishes")
async def get_missing_dishes():
    """Get list of dishes that were not found"""
    from app.api.routes.chat import app_state
    missing_logger = app_state.get("missing_logger")
    if missing_logger: 
        return missing_logger.get_unresolved()
    return []