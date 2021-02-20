from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    CallbackQueryHandler,
)

import utils
from markdownify import markdownify

class ShoppingListManager:
    MEAL_PLAN_SELECTED, REMOVE_ELEMENT, SHOW_SHOPPING_LIST, GET_QUERY, GET_NUMBER, VIEW_RECIPE = range(6)

    def __init__(self, meal_planner, logger):
        self.meal_planner = meal_planner
        self.logger = logger

        MAX_RECIPES = 5
        self.number_keyboard = [
            list(range(1, MAX_RECIPES + 1))
        ]
        self.number_markup = ReplyKeyboardMarkup(self.number_keyboard, one_time_keyboard=True,  resize_keyboard=True)

        self.conv_handler_meal_plan_to_shopping_list = ConversationHandler(
            entry_points=[CommandHandler('mptosl', self.meal_plan_to_shopping_list)],
            states={
                ShoppingListManager.MEAL_PLAN_SELECTED: [
                    CallbackQueryHandler(self.add_meal_plan_to_shopping_list),
                ],
                ShoppingListManager.SHOW_SHOPPING_LIST: [
                    CallbackQueryHandler(self.show_shopping_list),
                ],
                ShoppingListManager.REMOVE_ELEMENT: [
                    CallbackQueryHandler(self.remove_element),
                ]
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )
        self.conv_handler_show_shopping_list = ConversationHandler(
            entry_points=[CommandHandler('shoppinglist', self.show_shopping_list)],
            states={
                ShoppingListManager.REMOVE_ELEMENT: [
                    CallbackQueryHandler(self.remove_element),
                ]
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )
        self.conv_handler_search_recipes = ConversationHandler(
            entry_points=[CommandHandler('searchrecipes', self.start_search_recipes)],
            states={
                ShoppingListManager.GET_QUERY: [
                    MessageHandler(
                        ~(Filters.command | Filters.regex('^Done$')),
                        self.get_query,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.done,
                    )
                ],
                ShoppingListManager.GET_NUMBER: [
                    MessageHandler(
                        Filters.regex('^\d$') & ~(Filters.command | Filters.regex('^Done$')),
                        self.get_number,
                    ),
                    MessageHandler(
                        Filters.text & ~(Filters.command | Filters.regex('^Done$')),
                        self.done,
                    )
                ],
                ShoppingListManager.VIEW_RECIPE: [
                    CallbackQueryHandler(self.save_recipe, pattern='^(save_.*)$'),
                    CallbackQueryHandler(self.view_recipe, pattern='^((?!exit|save_.*|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )
        self.conv_handler_show_user_recipes = ConversationHandler(
            entry_points=[CommandHandler('recipes', self.start_show_user_recipes)],
            states={
                ShoppingListManager.VIEW_RECIPE: [
                    CallbackQueryHandler(self.add_recipe_ingredients_to_sl, pattern='^(add_.*)$'),
                    CallbackQueryHandler(self.remove_user_recipe, pattern='^(remove_.*)$'),
                    CallbackQueryHandler(self.view_user_recipe, pattern='^((?!exit|add_.*|remove_.*|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )

    

    def start_search_recipes(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return
        update.message.reply_text(
            """It seems like you want to become a chef.
Let's find out which recipes will be in your menu then!
            """,
        )

        return ShoppingListManager.GET_QUERY

    def get_query(self, update, context):
        query = update.message.text
        context.user_data['search_query'] = query
        update.message.reply_text('Alright. How many recipes would you like to browse?',
            reply_markup=self.number_markup)
        return ShoppingListManager.GET_NUMBER
        
    def get_number(self, update, context):
        text = update.message.text
        number = int(text)
        context.user_data['number'] = number

        update.message.reply_text('I\'m looking for the recipes of your dreams...',
            reply_markup=None)

        return self.show_collected_recipes(update, context)

    def show_collected_recipes(self, update, context):
        if not 'collected_recipes' in context.user_data:
            number = context.user_data['number']
            query = context.user_data['search_query']
            recipes = self.meal_planner.search_recipes(context.user_data['user'], number, query)
            context.user_data['collected_recipes'] = recipes
            message_fn = update.message.reply_text
        else:
            query = update.callback_query
            recipes = context.user_data['collected_recipes']
            message_fn = query.edit_message_text

        keyboard = [
            [InlineKeyboardButton(f"{recipe['title']}", callback_data=recipe['recipe_id'])]
                for recipe in recipes
        ]
        keyboard.extend([
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)

        message_fn(f"""These are the recipes I found. They sound tasty, huh?
        """, reply_markup=markup)

        return ShoppingListManager.VIEW_RECIPE

    def add_recipe_ingredients_to_sl(self, update, context):
        query = update.callback_query
        query.answer()
        user = context.user_data['user']
        recipe = context.user_data['selected_recipe']

        added_ingredients = self.meal_planner.add_recipe_ingredients_to_shopping_list(user, recipe)

        keyboard = []
        keyboard.extend([
            [InlineKeyboardButton("Back", callback_data=f"back_sur")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text=f"""Ya-hoo. Ingredients added! Don't forget to buy them.
            """, reply_markup=markup
        )

        return 
        
    def remove_user_recipe(self, update, context):
        query = update.callback_query
        query.answer()
        user = context.user_data['user']
        recipe = context.user_data['selected_recipe']
        deleted_recipe = self.meal_planner.delete_user_recipe(user, recipe)

        del context.user_data['user_recipes'][recipe['recipe_id']]

        keyboard = []
        keyboard.extend([
            [InlineKeyboardButton("Back", callback_data=f"back_sur")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text=f"""Who needs that recipe!
            """, reply_markup=markup
        )

        return 

    def save_recipe(self, update, context):
        query = update.callback_query
        query.answer()
        user = context.user_data['user']
        recipe = context.user_data['selected_recipe']
        saved_recipes = self.meal_planner.save_recipes(user, [{
            "recipe_id": recipe['recipe_id']
        }])

        keyboard = []
        keyboard.extend([
            [InlineKeyboardButton("Back", callback_data=f"back_scr")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text=f"""Recipe saved!
            """, reply_markup=markup
        )

        return 

    def start_show_user_recipes(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return

        return self.show_user_recipes(update, context)

    def show_user_recipes(self, update, context):
        if not 'user_recipes' in context.user_data:
            user_recipes = self.meal_planner.get_user_recipes(context.user_data['user'])
            context.user_data['user_recipes'] = user_recipes
            message_fn = update.message.reply_text
        else:
            query = update.callback_query
            user_recipes = context.user_data['user_recipes']
            message_fn = query.edit_message_text
        
        keyboard = [
            [InlineKeyboardButton(f"{recipe['title']}", callback_data=recipe['recipe_id'])]
                for recipe in user_recipes.values()
        ]
        keyboard.extend([
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)

        message_fn(f"""Here are your favorite recipes.
        """, reply_markup=markup)

        return ShoppingListManager.VIEW_RECIPE


    def view_user_recipe(self, update, context):
        query = update.callback_query
        query.answer()
        recipe_id = int(query.data)
        user_recipes = context.user_data['user_recipes']
        keyboard = []
        keyboard.extend([
            [InlineKeyboardButton("Add ingredients to the shopping list", callback_data=f"add_{recipe_id}")],
            [InlineKeyboardButton("Remove recipe from favorites", callback_data=f"remove_{recipe_id}")],
            [InlineKeyboardButton("Back", callback_data=f"back_sur")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)

        recipe = user_recipes[recipe_id]

        context.user_data['selected_recipe'] = recipe

        instructions = "I wasn't able to find any instructions for this recipe. You'll have to be creative I guess."
        image = ""
        if recipe['instructions']:
            instructions = recipe['instructions']
        if 'image' in recipe:
            if recipe['image']:
                image = f"[​​​​​​​​​​​]({recipe['image']})"
        query.edit_message_text(
            text=f"""Let's have a look at {recipe['title']}:
            {image}
{markdownify(instructions)}
            """, reply_markup=markup, parse_mode=ParseMode.MARKDOWN
        )
        return 


    def view_recipe(self, update, context):
        query = update.callback_query
        query.answer()
        recipe_id = int(query.data)
        keyboard = []
        keyboard.extend([
            [InlineKeyboardButton("Save recipe", callback_data=f"save_{recipe_id}")],
            [InlineKeyboardButton("Back", callback_data=f"back_scr")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)

        recipes_info = self.meal_planner.get_recipes_info([{
            'recipe_id': recipe_id
        }])

        recipe = recipes_info[recipe_id]
        context.user_data['selected_recipe'] = recipe

        instructions = "I wasn't able to find any instructions for this recipe. You'll have to be creative I guess."
        image = ""
        if recipe['instructions']:
            instructions = recipe['instructions']
        if 'image' in recipe:
            if recipe['image']:
                image = f"[​​​​​​​​​​​]({recipe['image']})"
        query.edit_message_text(
            text=f"""Let's have a look at {recipe['title']}:
            {image}
{markdownify(instructions)}
            """, reply_markup=markup, parse_mode=ParseMode.MARKDOWN
        )
        return 

    def meal_plan_to_shopping_list(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return
        markup = InlineKeyboardMarkup(self.get_meal_plans_keyboard(context))
        update.message.reply_text(
            """Someone told me that you'd like to get all the ingredients of your meal plan in a shopping list.
What meal plan is it?
            """,
            reply_markup=markup,
        )

        return ShoppingListManager.MEAL_PLAN_SELECTED

    def get_meal_plans_keyboard(self, context):
        user = context.user_data['user']
        meal_plans = self.meal_planner.get_meal_plans(user)
        context.user_data['user_meal_plans'] = meal_plans
        keyboard = [
            [InlineKeyboardButton(f"#{i+1:2d}:{meal_plan['daily_calories']} calories - {meal_plan['diet_type']}", callback_data=i)] 
                for i, meal_plan in enumerate(meal_plans)
        ]
        return keyboard

    def get_shopping_list_keyboard(self, shopping_list):
        keyboard = [
            [InlineKeyboardButton(f"{e['ingredient_name']} {e['quantity']} {e['measure']} \u274C", callback_data=e['ingredient_id'])] 
                for e in shopping_list
        ]
        keyboard.append([
            InlineKeyboardButton(f"Exit", callback_data="exit")
        ])
        return keyboard

    def add_meal_plan_to_shopping_list(self, update, context):
        query = update.callback_query
        query.answer()
        user = context.user_data['user']
        meal_plan = context.user_data['user_meal_plans'][int(query.data)]

        query.edit_message_text(
            text="""Alright, this will take a while. 
Sit back and relax...
            """
        )

        shopping_list = self.meal_planner.add_meal_plan_to_shopping_list(user, meal_plan)
        shopping_list = self.meal_planner.get_user_shopping_list(user)
        context.user_data['shopping_list'] = shopping_list
        markup = InlineKeyboardMarkup(self.get_shopping_list_keyboard(shopping_list))

        query.edit_message_text(
            text=f"""We're finally done! Your shining new shopping list is ready.
            """,
            reply_markup=markup
        )
        return ShoppingListManager.REMOVE_ELEMENT

    def show_shopping_list(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return
        user = context.user_data['user']
        shopping_list = self.meal_planner.get_user_shopping_list(user)
        context.user_data['shopping_list'] = shopping_list
        markup = InlineKeyboardMarkup(self.get_shopping_list_keyboard(shopping_list))
        update.message.reply_text(text="Click on a button to remove the ingredient from the shopping list!", reply_markup=markup)

        return ShoppingListManager.REMOVE_ELEMENT

    def remove_element(self, update, context):
        query = update.callback_query
        query.answer()
        if(query.data == "exit"):
            query.edit_message_text("It has been nice talking to you. Farewell.", reply_markup=None)
            self.clear_context(context)
            return ConversationHandler.END

        
        for i in context.user_data['shopping_list']:
            if i['ingredient_id'] == int(query.data):
                ingredient = i
                break
        else:
            return ShoppingListManager.REMOVE_ELEMENT
        

        user = context.user_data['user']

        ingredient_to_remove = {
            "ingredient_id": ingredient['ingredient_id'],
            "ingredient_name": ingredient['ingredient_name'],
            "quantity": -ingredient['quantity'],
            "measure": ingredient['measure'] 
        }

        removed_ingredient = self.meal_planner.remove_ingredient_from_shopping_list(user, [ingredient_to_remove])
        shopping_list = self.meal_planner.get_user_shopping_list(user)
        context.user_data['shopping_list'] = shopping_list
        markup = InlineKeyboardMarkup(self.get_shopping_list_keyboard(shopping_list))
        query.edit_message_reply_markup(reply_markup=markup)

        return ShoppingListManager.REMOVE_ELEMENT

    def clear_context(self, context):
        user_data = context.user_data
        attributes = ['user_meal_plans', 'shopping_list', 'search_query', 'collected_recipes', 'number', 'selected_recipe', 'user_recipes']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]

    def done(self, update: Update, context: CallbackContext) -> int:
        self.clear_context(context)
        update.message.reply_text("Uh-oh, it seems like you weren't able to complete the process. See you soon.")
        return ConversationHandler.END

    def back_exit(self, update, context):
        query = update.callback_query
        query.answer()
        action = query.data
        if action == 'exit':
            return self.menu_exit(update, context)
        command, data = action.split('_')
        if command == 'save':
            return self.save_recipe(update, context)
        if command == 'remove':
            return self.remove_user_recipe(update, context)
        if command == 'add':
            return self.add_recipe_ingredients_to_sl(update, context)
        if data == 'scr':
            return self.show_collected_recipes(update, context)
        if data == 'sur':
            return self.show_user_recipes(update, context)


    def menu_exit(self, update, context):
        self.clear_context(context)
        query = update.callback_query
        query.answer()
        query.edit_message_text("Whoopee, see you later!", reply_markup = None)
        return ConversationHandler.END

    