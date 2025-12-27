from typing import Optional, List
from app.models.schemas import CalorieResult
import logging

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate responses in multiple languages with better formatting"""
    
    def __init__(self):
        self.translations = self._build_translations()
    
    def _build_translations(self):
        """Build translation dictionary for common phrases"""
        return {
            "greeting": {
                "english": "Hello! Welcome to the Arabic Food Calorie Calculator!",
                "arabic": "مرحبا! أهلا بك في حاسبة السعرات الحرارية للطعام العربي!"
            },
            "total_calories": {
                "english": "Total Calories",
                "arabic": "السعرات الحرارية الإجمالية"
            },
            "total_weight": {
                "english": "Total Weight",
                "arabic": "الوزن الإجمالي"
            },
            "ingredients": {
                "english": "Ingredients breakdown",
                "arabic": "تفصيل المكونات"
            },
            "modifications": {
                "english": "Modifications",
                "arabic": "التعديلات"
            },
            "approximate": {
                "english": "(This is an approximate estimate)",
                "arabic": "(هذا تقدير تقريبي)"
            },
            "not_found": {
                "english": "I couldn't find",
                "arabic": "لم أتمكن من العثور على"
            }
        }
    
    def generate_greeting(self, country: str, language: str = "english") -> str:
        """Generate greeting response"""
        country_greetings = {
            "lebanon": {"english": "Marhaba! 🇱🇧", "arabic": "مرحبا! 🇱🇧"},
            "syria": {"english": "Ahlan wa sahlan! 🇸🇾", "arabic": "أهلا وسهلا! 🇸🇾"},
            "egypt": {"english": "Ahlan! 🇪🇬", "arabic": "أهلا! 🇪🇬"},
            "saudi": {"english": "Marhaba! 🇸🇦", "arabic": "مرحبا! 🇸🇦"},
            "iraq": {"english": "Ahlan bik! 🇮🇶", "arabic": "أهلا بك! 🇮🇶"},
        }
        
        greeting = country_greetings.get(country.lower(), {"english": "Hello!", "arabic": "مرحبا!"})
        greeting_text = greeting.get(language, greeting["english"])
        
        if language == "arabic":
            return f"""{greeting_text}
            
يمكنني مساعدتك في العثور على معلومات السعرات الحرارية لـ:
- المكونات الفردية (مثل "تفاح"، "أرز"، "دجاج")
- الأطباق التقليدية (مثل "شاورما"، "كشري"، "كبسة")

يمكنك أيضا:
- تعديل الأطباق: "شاورما بدون بطاطس"
- إضافة مكونات: "فلافل مع طحينة إضافية"
- تحديد الكميات: "200 جرام صدر دجاج"

ما الذي تريد معرفته؟"""
        else:
            return f"""{greeting_text} Welcome to the Arabic Food Calorie Calculator!

I can help you find calorie information for:
- Single ingredients (e.g., "apple", "rice", "chicken")
- Traditional dishes (e.g., "shawarma", "kushari", "kabsa")

You can also:
- Modify dishes: "shawarma without fries"
- Add ingredients: "falafel with extra tahini"
- Specify quantities: "200g chicken breast"

What would you like to know about?"""
    
    def generate_help(self, language: str = "english") -> str:
        """Generate help response"""
        if language == "arabic":
            return """كيفية استخدام حاسبة السعرات الحرارية:

1. اسأل عن أي طعام:
   - "كم سعرة حرارية في الشاورما؟"
   - "سعرات الكشري"
   - "سعرات التفاح"

2. تعديل الأطباق:
   - "فاهيتا بدون بطاطس"
   - "كبسة بدون أرز"

3. إضافة مكونات:
   - "شاورما مع صلصة الثوم الإضافية"
   - "فلافل مع المخلل"

4. تحديد الكميات:
   - "200 جرام دجاج مشوي"
   - "حصة مزدوجة من الأرز"

فقط اكتب سؤالك وسأساعدك!"""
        else:
            return """How to use the Calorie Calculator:

1. Ask about any food:
   - "How many calories in shawarma?"
   - "Calories in kushari"
   - "Apple calories"

2. Modify dishes:
   - "Fajita without fries"
   - "Kabsa without rice"

3. Add ingredients:
   - "Shawarma with extra garlic sauce"
   - "Falafel with pickles"

4. Specify quantities:
   - "200g grilled chicken"
   - "Double portion of rice"

Just type your question and I'll help you!"""
    
    def generate_calorie_response(self, result: CalorieResult, language: str = "english") -> str:
        """Generate response for calorie result"""
        food_name = result.food_name.title() if result.food_name else "Unknown"
        total_cal = int(result.total_calories) if result.total_calories else 0
        total_weight = int(result.weight_g) if result.weight_g else 0
        
        if language == "arabic":
            accuracy_note = "\n(هذا تقدير تقريبي)" if result.is_approximate else ""
            
            response = f"""{food_name}

معلومات التغذية:
- السعرات الحرارية الإجمالية: {total_cal} سعرة
- الوزن الإجمالي: {total_weight} جرام
"""
            
            if result.ingredients and len(result.ingredients) > 0:
                response += "\nتفصيل المكونات:\n"
                for ing in result.ingredients[:10]:
                    ing_cal = int(ing.calories) if ing.calories else 0
                    ing_weight = int(ing.weight_g) if ing.weight_g else 0
                    response += f"  - {ing.name}: {ing_cal} سعرة ({ing_weight} جرام)\n"
            
            if result.modifications:
                response += "\nالتعديلات:\n"
                for mod in result.modifications:
                    response += f"  - {mod}\n"
            
            response += accuracy_note
            response += "\n\nيمكنك تعديل هذا الطبق بقول 'بدون [مكون]' أو 'أضف [مكون]'"
        else:
            accuracy_note = "\n(This is an approximate estimate)" if result.is_approximate else ""
            
            response = f"""{food_name}

Nutrition Information:
- Total Calories: {total_cal} kcal
- Total Weight: {total_weight}g
"""
            
            if result.ingredients and len(result.ingredients) > 0:
                response += "\nIngredients breakdown:\n"
                for ing in result.ingredients[:10]:
                    ing_cal = int(ing.calories) if ing.calories else 0
                    ing_weight = int(ing.weight_g) if ing.weight_g else 0
                    response += f"  - {ing.name}: {ing_cal} kcal ({ing_weight}g)\n"
            
            if result.modifications:
                response += "\nModifications:\n"
                for mod in result.modifications:
                    response += f"  - {mod}\n"
            
            response += accuracy_note
            response += "\n\nYou can modify this dish by saying 'without [ingredient]' or 'add [ingredient]'"
        
        return response
    
    def generate_not_found(self, food_name: str, language: str = "english") -> str:
        """Generate response when food is not found"""
        if language == "arabic":
            return f"""لم أتمكن من العثور على "{food_name}" في قاعدة البيانات الخاصة بي.

قد يكون هذا بسبب:
- كتابته بشكل مختلف عما أتوقع
- إنه طبق إقليمي ليس لدي بعد

هل يمكنك مساعدتي؟ من فضلك أخبرني:
1. ما هي المكونات الرئيسية في هذا الطبق؟
2. تقريبا كم من كل مكون؟

على سبيل المثال: "دجاج 200 جرام، أرز 150 جرام، بصل 50 جرام"

سيساعدني هذا في حساب السعرات الحرارية!"""
        else:
            return f"""I couldn't find "{food_name}" in my database.

This could be because:
- It's spelled differently than I expect
- It's a regional dish I don't have yet

Can you help me? Please tell me:
1. What are the main ingredients in this dish?
2. Approximately how much of each ingredient?

For example: "chicken 200g, rice 150g, onion 50g"

This will help me calculate the calories!"""
    
    def generate_clarification(self, food_name: str, suggestions: List[str], language: str = "english") -> str:
        """Generate clarification request with suggestions"""
        if language == "arabic":
            response = f"""لست متأكدا تماما مما تعنيه بـ "{food_name}".

هل تقصد أحد هذه؟
"""
            for i, suggestion in enumerate(suggestions, 1):
                response += f"{i}. {suggestion}\n"
            
            response += "\nأو يمكنك إعطائي المزيد من التفاصيل."
        else:
            response = f"""I'm not quite sure what you mean by "{food_name}".

Did you mean one of these?
"""
            for i, suggestion in enumerate(suggestions, 1):
                response += f"{i}. {suggestion}\n"
            
            response += "\nOr you can give me more details."
        
        return response
