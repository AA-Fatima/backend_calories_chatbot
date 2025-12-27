from typing import Dict, List, Optional, Any
from app.models.schemas import ParsedQuery, CalorieResult, Ingredient, Intent
from app.services.food_search import FoodSearchService
from app.services.fallback_service import FallbackService
from app.services.missing_dish_logger import MissingDishLogger
import logging

logger = logging.getLogger(__name__)


class CalorieCalculatorService:
    """Service for calculating calories"""
    
    def __init__(
        self,
        food_search:  FoodSearchService,
        fallback_service: FallbackService,
        missing_logger: MissingDishLogger
    ):
        self.food_search = food_search
        self.fallback_service = fallback_service
        self.missing_logger = missing_logger
    
    async def calculate(
        self,
        parsed_query: ParsedQuery,
        country: str,
        context: Dict
    ) -> CalorieResult:
        """Calculate calories for a parsed query"""
        
        try:
            # Get food item from query
            if not parsed_query.food_items:
                return self._create_not_found_result(parsed_query.original_text)
            
            food_name = parsed_query.food_items[0]
            logger.info(f"Calculating calories for: {food_name}")
            
            # Handle modification of previous dish
            if parsed_query.intent in [Intent.MODIFY_REMOVE, Intent.MODIFY_ADD]:
                last_result = context.get("last_result")
                if last_result:
                    return await self._handle_modification(
                        parsed_query, last_result, country
                    )
            
            # Search for the food
            search_results = self.food_search.search(food_name, country)
            
            if not search_results: 
                logger.info(f"No results found for:  {food_name}")
                self.missing_logger.log(food_name, country, None)
                return self._create_not_found_result(food_name)
            
            # Get the best match
            best_match, source, confidence = search_results[0]
            logger.info(f"Best match: {best_match.get('dish_name') or best_match.get('description')}, confidence: {confidence}")
            
            # Calculate based on source
            if source == "dishes":
                result = self._calculate_dish_calories(best_match, parsed_query, confidence)
            else:
                result = self._calculate_ingredient_calories(best_match, parsed_query, confidence, source)
            
            # Apply modifications if any
            if parsed_query.modifications.get("remove") or parsed_query.modifications.get("add"):
                result = self._apply_modifications(result, parsed_query.modifications)
            
            # Apply quantity multiplier if specified
            if parsed_query.quantities.get("_multiplier"):
                result = self._apply_multiplier(result, parsed_query.quantities["_multiplier"])
            
            if parsed_query.quantities.get("_weight"):
                result = self._apply_custom_weight(result, parsed_query.quantities["_weight"])
            
            result.country = country
            return result
            
        except Exception as e: 
            logger.error(f"Error calculating calories: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return self._create_not_found_result(
                parsed_query.original_text if parsed_query else "unknown"
            )
    
    def _calculate_dish_calories(
        self,
        dish: Dict,
        parsed_query: ParsedQuery,
        confidence:  float
    ) -> CalorieResult: 
        """Calculate calories for a dish"""
        
        dish_name = dish.get("dish_name", "Unknown Dish")
        ingredients_data = dish.get("ingredients", [])
        
        ingredients = []
        total_calories = 0
        total_weight = 0
        
        for ing_data in ingredients_data:
            if isinstance(ing_data, dict):
                ing_name = ing_data.get("name", ing_data.get("ingredient", "Unknown"))
                ing_weight = float(ing_data.get("weight_g", ing_data.get("weight", 0)))
                ing_calories = float(ing_data.get("calories", ing_data.get("kcal", 0)))
                ing_fdc_id = ing_data.get("usda_fdc_id", ing_data.get("fdc_id", 0))
            else:
                continue
            
            ingredient = Ingredient(
                usda_fdc_id=int(ing_fdc_id) if ing_fdc_id else 0,
                name=str(ing_name),
                weight_g=float(ing_weight),
                calories=float(ing_calories)
            )
            ingredients.append(ingredient)
            total_calories += ing_calories
            total_weight += ing_weight
        
        # If no ingredients found, use dish-level data
        if not ingredients or total_calories == 0:
            total_calories = float(dish.get("total_calories", dish.get("calories", 0)))
            total_weight = float(dish.get("total_weight_g", dish.get("weight_g", dish.get("serving_size_g", 100))))
        
        return CalorieResult(
            food_name=dish_name,
            original_query=parsed_query.original_text,
            total_calories=total_calories,
            weight_g=total_weight,
            ingredients=ingredients,
            modifications=[],
            source="dishes",
            confidence=confidence,
            is_approximate=False,
            country=""
        )
    
    def _calculate_ingredient_calories(
        self,
        food:  Dict,
        parsed_query: ParsedQuery,
        confidence: float,
        source: str
    ) -> CalorieResult:
        """Calculate calories for a single ingredient"""
        
        food_name = food.get("description", "Unknown Food")
        fdc_id = food.get("fdcId", 0)
        
        # Get nutrients
        nutrients = food.get("foodNutrients", [])
        calories_per_100g = 0
        
        for nutrient in nutrients:
            if isinstance(nutrient, dict):
                nutrient_name = nutrient.get("nutrientName", nutrient.get("name", ""))
                if "Energy" in nutrient_name or "calorie" in nutrient_name.lower():
                    calories_per_100g = float(nutrient.get("value", nutrient.get("amount", 0)))
                    break
        
        # Default serving size
        weight_g = parsed_query.quantities.get("_weight", 100)
        
        # Calculate calories based on weight
        total_calories = (calories_per_100g * weight_g) / 100
        
        ingredient = Ingredient(
            usda_fdc_id=int(fdc_id) if fdc_id else 0,
            name=food_name,
            weight_g=float(weight_g),
            calories=float(total_calories)
        )
        
        return CalorieResult(
            food_name=food_name,
            original_query=parsed_query.original_text,
            total_calories=total_calories,
            weight_g=weight_g,
            ingredients=[ingredient],
            modifications=[],
            source=source,
            confidence=confidence,
            is_approximate=False,
            country=""
        )
    
    async def _handle_modification(
        self,
        parsed_query: ParsedQuery,
        last_result: Dict,
        country:  str
    ) -> CalorieResult: 
        """Handle modification of previous dish"""
        
        try:
            # Reconstruct the previous result
            ingredients = []
            for ing_data in last_result.get("ingredients", []):
                ingredients.append(Ingredient(
                    usda_fdc_id=ing_data.get("usda_fdc_id", 0),
                    name=ing_data.get("name", ""),
                    weight_g=float(ing_data.get("weight_g", 0)),
                    calories=float(ing_data.get("calories", 0))
                ))
            
            result = CalorieResult(
                food_name=last_result.get("food_name", "Modified Dish"),
                original_query=parsed_query.original_text,
                total_calories=float(last_result.get("total_calories", 0)),
                weight_g=float(last_result.get("weight_g", 0)),
                ingredients=ingredients,
                modifications=list(last_result.get("modifications", [])),
                source=last_result.get("source", "dishes"),
                confidence=float(last_result.get("confidence", 0.8)),
                is_approximate=last_result.get("is_approximate", False),
                country=country
            )
            
            # Apply new modifications
            result = self._apply_modifications(result, parsed_query.modifications)
            
            return result
            
        except Exception as e: 
            logger.error(f"Error handling modification: {str(e)}")
            # Fall back to regular search
            if parsed_query.food_items:
                search_results = self.food_search.search(parsed_query.food_items[0], country)
                if search_results: 
                    best_match, source, confidence = search_results[0]
                    if source == "dishes": 
                        result = self._calculate_dish_calories(best_match, parsed_query, confidence)
                    else:
                        result = self._calculate_ingredient_calories(best_match, parsed_query, confidence, source)
                    result = self._apply_modifications(result, parsed_query.modifications)
                    return result
            
            return self._create_not_found_result(parsed_query.original_text)
    
    def _apply_modifications(
        self,
        result: CalorieResult,
        modifications:  Dict[str, List[str]]
    ) -> CalorieResult:
        """Apply modifications to a calorie result"""
        
        new_ingredients = list(result.ingredients)
        new_modifications = list(result.modifications) if result.modifications else []
        
        # Handle removals
        for item_to_remove in modifications.get("remove", []):
            item_lower = item_to_remove.lower()
            removed = False
            
            for i, ing in enumerate(new_ingredients):
                ing_name_lower = ing.name.lower()
                # Check if the ingredient matches
                if item_lower in ing_name_lower or ing_name_lower in item_lower: 
                    new_ingredients.pop(i)
                    new_modifications.append(f"Removed:  {ing.name}")
                    removed = True
                    break
            
            if not removed:
                # Try partial match
                for i, ing in enumerate(new_ingredients):
                    ing_words = ing.name.lower().split()
                    if any(item_lower in word or word in item_lower for word in ing_words):
                        new_ingredients.pop(i)
                        new_modifications.append(f"Removed: {ing.name}")
                        break
        
        # Handle additions
        for item_to_add in modifications.get("add", []):
            # Search for the ingredient
            search_results = self.food_search.search(item_to_add, "")
            if search_results:
                food, source, _ = search_results[0]
                
                # Get calories
                if source == "dishes": 
                    add_calories = float(food.get("total_calories", 50))
                    add_weight = float(food.get("total_weight_g", 30))
                else: 
                    # USDA ingredient
                    nutrients = food.get("foodNutrients", [])
                    cal_per_100 = 0
                    for n in nutrients:
                        if "Energy" in n.get("nutrientName", ""):
                            cal_per_100 = float(n.get("value", 0))
                            break
                    add_weight = 30  # Default addition weight
                    add_calories = (cal_per_100 * add_weight) / 100
                
                new_ingredient = Ingredient(
                    usda_fdc_id=food.get("fdcId", 0),
                    name=item_to_add.title(),
                    weight_g=add_weight,
                    calories=add_calories
                )
                new_ingredients.append(new_ingredient)
                new_modifications.append(f"Added: {item_to_add}")
            else:
                # Add with estimated values
                new_ingredient = Ingredient(
                    usda_fdc_id=0,
                    name=item_to_add.title(),
                    weight_g=30,
                    calories=50  # Estimated
                )
                new_ingredients.append(new_ingredient)
                new_modifications.append(f"Added: {item_to_add} (estimated)")
        
        # Recalculate totals
        new_total_calories = sum(ing.calories for ing in new_ingredients)
        new_total_weight = sum(ing.weight_g for ing in new_ingredients)
        
        return CalorieResult(
            food_name=result.food_name,
            original_query=result.original_query,
            total_calories=new_total_calories,
            weight_g=new_total_weight,
            ingredients=new_ingredients,
            modifications=new_modifications,
            source=result.source,
            confidence=result.confidence,
            is_approximate=result.is_approximate,
            country=result.country
        )
    
    def _apply_multiplier(self, result: CalorieResult, multiplier: float) -> CalorieResult: 
        """Apply quantity multiplier"""
        
        new_ingredients = []
        for ing in result.ingredients:
            new_ing = Ingredient(
                usda_fdc_id=ing.usda_fdc_id,
                name=ing.name,
                weight_g=ing.weight_g * multiplier,
                calories=ing.calories * multiplier
            )
            new_ingredients.append(new_ing)
        
        multiplier_text = "double" if multiplier == 2 else "half" if multiplier == 0.5 else f"{multiplier}x"
        
        return CalorieResult(
            food_name=f"{result.food_name} ({multiplier_text} portion)",
            original_query=result.original_query,
            total_calories=result.total_calories * multiplier,
            weight_g=result.weight_g * multiplier,
            ingredients=new_ingredients,
            modifications=result.modifications + [f"Quantity:  {multiplier_text}"],
            source=result.source,
            confidence=result.confidence,
            is_approximate=result.is_approximate,
            country=result.country
        )
    
    def _apply_custom_weight(self, result: CalorieResult, target_weight:  float) -> CalorieResult:
        """Apply custom weight"""
        
        if result.weight_g == 0:
            return result
        
        ratio = target_weight / result.weight_g
        
        new_ingredients = []
        for ing in result.ingredients:
            new_ing = Ingredient(
                usda_fdc_id=ing.usda_fdc_id,
                name=ing.name,
                weight_g=ing.weight_g * ratio,
                calories=ing.calories * ratio
            )
            new_ingredients.append(new_ing)
        
        return CalorieResult(
            food_name=f"{result.food_name} ({int(target_weight)}g)",
            original_query=result.original_query,
            total_calories=result.total_calories * ratio,
            weight_g=target_weight,
            ingredients=new_ingredients,
            modifications=result.modifications + [f"Adjusted to {int(target_weight)}g"],
            source=result.source,
            confidence=result.confidence,
            is_approximate=True,
            country=result.country
        )
    
    def _create_not_found_result(self, query: str) -> CalorieResult: 
        """Create a not found result"""
        return CalorieResult(
            food_name=query,
            original_query=query,
            total_calories=0,
            weight_g=0,
            ingredients=[],
            modifications=[],
            source="not_found",
            confidence=0,
            is_approximate=True,
            country=""
        )