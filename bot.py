import logging
import os, sys
import profile, meal_plan, shopping_list, shops
import requests
from typing import Dict
from datetime import date

from telegram import ReplyKeyboardMarkup, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
)
# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

TOKEN = "1585535684:AAFj6jKfe6Nud4unaRZwS5HXi5VrzbHFSrs"

# Class that handle all the database functions
class MealPlanner:
    def __init__(self):
        self.meal_planner_url = "https://meal-plan-sde-meal-plan.herokuapp.com/"
        self.shopping_list_url = "https://meal-plan-sde-shopping-list.herokuapp.com/"

    # Function to retrieve user by id from db
    def get_user(self, username):
        r = requests.get(f"{self.meal_planner_url}users/{username}")
        return r.json()

    # Function to insert and update user in db
    def update_user(self, user):
        r = requests.get(f"{self.meal_planner_url}users/{user['username']}")
        if (self.is_error(r.json())):
            #post
            r = requests.post(f"{self.meal_planner_url}users/", json=user)
        else:
            #patch
            r = requests.patch(f"{self.meal_planner_url}users/{r.json()['mp_user_id']}", json=user)
        return r.json()

    def get_needed_calories(self, user):
        payload = {
            'height' : user['height'],
            'weight' : user['weight'],
            'age' : date.today().year - user['birth_year'],
            'sex' : user['sex'],
            'activityFactor' : user['activity_factor']
        }
        r = requests.get(f"{self.meal_planner_url}calories", params=payload).json()
        return r['neededCalories']

    def create_meal_plan(self, user, days, meals_per_day):
        payload = {
            'calories' : self.get_needed_calories(user),
            'n' : days,
            'm' : meals_per_day,
            'diet' : user['diet_type']
        }
        print(payload)
        new_meal_plan = requests.get(f"{self.meal_planner_url}mealPlans", params=payload).json()
        print(new_meal_plan)
        saved_meal_plan = requests.post(f"{self.meal_planner_url}mealPlans/{user['mp_user_id']}", json=new_meal_plan).json()
        print(saved_meal_plan)
        return saved_meal_plan

    def get_meal_plans(self, user):
        meal_plans_list = requests.get(f"{self.meal_planner_url}users/{user['mp_user_id']}/mealPlans").json()
        return meal_plans_list

# MEAL PLAN FORMAT
# {'meal_plan_id': 16, 
# 'mp_user_id': 3, 
# 'is_current': True, 
# 'daily_calories': 2365, 
# 'diet_type': 'vegan', 
# 'daily_plans': [
#     {'daily_plan_id': 41, 
#     'daily_plan_number': 0, 
#     'meal_plan_id': 16, 
#     'recipes': [{'recipe_id': 716426}]
#     }, 
#     {'daily_plan_id': 40, 
#     'daily_plan_number': 1, 
#     'meal_plan_id': 16, 
#     'recipes': [{'recipe_id': 715594}]
#     }
#   ]
# }
#
# RECIPE FORMAT
# { id: number;
#   title: string;
#   image: string;
#   imageType: string;
#   ingredients: [{
    #     id: number;
    #     name: string;
    #     measures: {
    #         metric: {
            #       amount: number;
            #       unitLong: string;
            #       unitShort: string;
            #   }
    
    #     };
    # };
    # ]
#   summary: string;
#   sourceUrl: string;
#   servings: number;
#   readyInMinutes: number;
#   pricePerServing: number;
#   glutenFree: boolean;
#   vegan: boolean;
#   vegetarian: boolean;
#   instructions: string;
# }

# SHOPPING_LIST_ENTRY
# {
#     ingredient_id: number,
#     quantity: number,
#     measure: string
# }
    def add_meal_plan_to_shopping_list(self, user, meal_plan):
        recipes = []
        for daily_plan in meal_plan['daily_plans']:
            for recipe in daily_plan['recipes']:
                recipes.append(recipe)

        recipes_info = self.get_recipes_info(recipes)
        recipes = list(recipes_info.values())
        print("Recipes:", recipes)
        shopping_list_entries = []

        for recipe in recipes:
            shopping_list_entries.extend(self.get_shopping_list_entries_from_recipe(recipe))
        print("Entries:", shopping_list_entries)
        

        final_shopping_list = requests.patch(f"{self.shopping_list_url}users/{user['mp_user_id']}/shoppingList", json=shopping_list_entries).json()
        return final_shopping_list

    def get_shopping_list_entries_from_recipe(self, recipe):
        shopping_list_entries = []
        for ingredient in recipe['ingredients']:
            if ingredient['id'] and ingredient['id']:
                shopping_list_entries.append({
                    "ingredient_id": ingredient['id'],
                    "ingredient_name": ingredient['name'],
                    "quantity": ingredient['measures']['metric']['amount'],
                    "measure": ingredient['measures']['metric']['unitLong']
                })
        return shopping_list_entries

    def add_recipe_ingredients_to_shopping_list(self, user, recipe):
        shopping_list_entries = self.get_shopping_list_entries_from_recipe(recipe)
        new_ingredients = requests.patch(f"{self.shopping_list_url}users/{user['mp_user_id']}/shoppingList", json=shopping_list_entries).json()
        return new_ingredients
        

    def get_user_shopping_list(self, user):
        return requests.get(f"{self.shopping_list_url}users/{user['mp_user_id']}/shoppingList").json()

    def remove_ingredient_from_shopping_list(self, user, ingredient):
        return requests.patch(f"{self.shopping_list_url}users/{user['mp_user_id']}/shoppingList", json=ingredient).json()
        

    def get_recipes_info(self, recipes):
        recipes_info = {}
        for recipe in recipes:
            rid = recipe['recipe_id']
            if not rid in recipe:
                rinfo = requests.get(f"{self.shopping_list_url}recipes/{recipe['recipe_id']}").json()
                recipes_info[rid] = rinfo
        return recipes_info

    def search_recipes(self, user, number, query):
        payload = {
            'q' : query,
            'n' : number,
            'diet' : user['diet_type']
        }
        recipes = requests.get(f"{self.shopping_list_url}recipes", params=payload).json()
        return recipes

    def get_user_recipes(self, user):
        recipes = requests.get(f"{self.shopping_list_url}users/{user['mp_user_id']}/recipes").json()
        recipes_info = self.get_recipes_info(recipes)
        return recipes_info

    def delete_user_recipe(self, user, recipe):
        deleted_recipe = requests.delete(f"{self.shopping_list_url}users/{user['mp_user_id']}/recipes/{recipe['recipe_id']}").json()
        return deleted_recipe

    def save_recipes(self, user, recipes):
        saved_recipes = requests.post(f"{self.shopping_list_url}users/{user['mp_user_id']}/recipes", json=recipes).json()
        return saved_recipes

    def group_ingredients(self, ingredients_list):
        r = requests.post(f"{self.shopping_list_url}groupIngredients/", json=ingredients_list)
        return sorted(r.json(), key = self.sort_categories) 
    
    def get_nearby_shops_by_categories(self, user, categories):
        params = {
            'lat' : user['lat'],
            'lon' : user['lon']
        }
        r = requests.post(f"{self.shopping_list_url}shopsByCategories/", json=categories, params=params)
        return sorted(r.json(), key = self.sort_categories) 

    def sort_categories(self, category):
        return 'z' if category['category'] == "other" else category['category']

    def is_error(self, obj):
        return "error" in obj



class Bot:
    def __init__(self):
        self.meal_planner = MealPlanner()
        self.logger = logging.getLogger(__name__)
        self.profile_manager = profile.ProfileManager(self.meal_planner, self.logger)
        self.meal_plan_manager = meal_plan.MealPlanManager(self.meal_planner, self.logger)
        self.shopping_list_manager = shopping_list.ShoppingListManager(self.meal_planner, self.logger)
        self.shops_manager = shops.ShopsManager(self.meal_planner, self.logger)


    def start(self) -> None:
        # Create the Updater and pass it your bot's token.
        updater = Updater(TOKEN)
        
        # Get the dispatcher to register handlers
        dispatcher = updater.dispatcher
        # Add conversation handler with the states CHOOSING, TYPING_CHOICE and TYPING_REPLY
        edit_profile_handler = self.profile_manager.conv_handler_edit
        show_profile_handler = self.profile_manager.conv_handler_show
        create_meal_plan_handler = self.meal_plan_manager.conv_handler_create
        view_meal_plans_handler = self.meal_plan_manager.conv_handler_view
        mp_to_sl_handler = self.shopping_list_manager.conv_handler_meal_plan_to_shopping_list
        show_shopping_list_handler = self.shopping_list_manager.conv_handler_show_shopping_list
        search_recipes_handler = self.shopping_list_manager.conv_handler_search_recipes
        show_user_recipes_handler = self.shopping_list_manager.conv_handler_show_user_recipes
        shops_handler = self.shops_manager.conv_handler
        handlers = [
            edit_profile_handler,
            show_profile_handler,
            create_meal_plan_handler,
            view_meal_plans_handler,
            mp_to_sl_handler,
            show_shopping_list_handler,
            search_recipes_handler,
            show_user_recipes_handler,
            shops_handler,
        ]
        for i, handler in enumerate(handlers):
            dispatcher.add_handler(handler, i+1)
        
        PORT = int(os.environ.get("PORT", "8443"))

        # Starting bot
        if len(sys.argv) == 2 and sys.argv[1] == "DEV":
            # Developer mode with local instance
            self.logger.info("Start polling")
            updater.start_polling()
        else:
            # Deployed version with heroku instance
            self.logger.info("Start webhook")
            updater.start_webhook(listen="0.0.0.0",
                                port=PORT,
                                url_path=TOKEN)
            updater.bot.set_webhook("https://meal-plan-sde-bot.herokuapp.com/" + TOKEN)
        updater.idle()


    



# reply_keyboard = [
#     ['Age', 'Favourite colour'],
#     ['Number of siblings', 'Something else...'],
#     ['Done'],
# ]
# markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)



# def facts_to_str(user_data: Dict[str, str]) -> str:
#     facts = list()

#     for key, value in user_data.items():
#         facts.append(f'{key} - {value}')

#     return "\n".join(facts).join(['\n', '\n'])







if __name__ == '__main__':
    bot = Bot()
    bot.start()