import pandas as pd
import json
from typing import Dict, List, Any
import logging
import os

logger = logging.getLogger(__name__)

class DishesLoader: 
    """Load Arabic dishes database from Excel"""
    
    @staticmethod
    def load(filepath: str) -> Dict[str, Any]:
        """Load dishes from Excel file"""
        
        if not os.path.exists(filepath):
            logger.warning(f"Dishes file not found: {filepath}")
            return {"by_id": {}, "by_name": {}, "by_country": {}, "all_dishes":  [], "name_variations": {}}
        
        try:
            df = pd.read_excel(filepath)
        except Exception as e:
            logger.error(f"Error loading dishes: {e}")
            return {"by_id": {}, "by_name": {}, "by_country": {}, "all_dishes":  [], "name_variations": {}}
        
        indexed = {"by_id": {}, "by_name": {}, "by_country":  {}, "all_dishes": []}
        
        for _, row in df.iterrows():
            try:
                # Handle different column names
                dish_name = str(row.get('dish name', row.get('dish_name', ''))).lower().strip()
                country = str(row.get('Country', row.get('country', ''))).lower().strip()
                
                if not dish_name: 
                    continue
                
                # Parse ingredients
                ingredients = row.get('ingredients', '[]')
                if isinstance(ingredients, str):
                    try:
                        ingredients = json.loads(ingredients)
                    except: 
                        ingredients = []
                elif pd.isna(ingredients):
                    ingredients = []
                
                # Get weight and calories
                weight = row.get('weight (g)', row.get('weight_g', 0))
                calories = row.get('calories', 0)
                
                dish_entry = {
                    "dish_id": int(row.get('dish_id', 0)) if not pd.isna(row.get('dish_id', 0)) else 0,
                    "dish_name":  dish_name,
                    "weight_g": float(weight) if not pd.isna(weight) else 0,
                    "calories": float(calories) if not pd.isna(calories) else 0,
                    "ingredients": ingredients,
                    "country": country
                }
                
                indexed["by_id"][dish_entry["dish_id"]] = dish_entry
                
                if dish_name not in indexed["by_name"]:
                    indexed["by_name"][dish_name] = []
                indexed["by_name"][dish_name].append(dish_entry)
                
                if country not in indexed["by_country"]:
                    indexed["by_country"][country] = []
                indexed["by_country"][country].append(dish_entry)
                
                indexed["all_dishes"].append(dish_entry)
                
            except Exception as e: 
                logger.warning(f"Error processing dish row: {e}")
                continue
        
        indexed["name_variations"] = DishesLoader._create_name_variations()
        
        logger.info(f"Loaded {len(indexed['all_dishes'])} dishes from {len(indexed['by_country'])} countries")
        return indexed
    
    @staticmethod
    def _create_name_variations() -> Dict[str, str]:
        """Create common spelling variations for dish names"""
        variations = {}
        
        variation_map = {
 
        }
        
        for canonical, variants in variation_map.items():
            variations[canonical] = canonical
            for variant in variants:
                variations[variant.lower()] = canonical
        
        return variations