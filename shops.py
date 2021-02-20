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
from markdownify import markdownify
import utils

class ShopsManager:
    CHOOSE_SHOP_CATEGORY, CHOOSE_CATEGORY_SHOP = range(2)
   
    def __init__(self, meal_planner, logger):
        self.meal_planner = meal_planner
        self.logger = logger

        self.conv_handler = ConversationHandler(
            entry_points=[CommandHandler('shops', self.shops)],
            states={
                ShopsManager.CHOOSE_SHOP_CATEGORY: [
                    CallbackQueryHandler(self.choose_shop_category, pattern='^((?!exit|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
                ShopsManager.CHOOSE_CATEGORY_SHOP: [
                    CallbackQueryHandler(self.choose_category_shop, pattern='^((?!exit|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )

    def get_categories_keyboard(self, update, context):
        if not 'categories' in context.user_data:
            user = context.user_data['user']
            user_shopping_list = self.meal_planner.get_user_shopping_list(user)
            print("shopping list:", user_shopping_list)
            categories = self.meal_planner.group_ingredients(user_shopping_list)
            print("categories: ", categories)
            context.user_data['categories'] = categories
        else:
            categories = context.user_data['categories']
        print("Categories:", categories)

        keyboard = [
            [InlineKeyboardButton(text=f"{category['category'].capitalize()}", callback_data=category['category'])]
            for category in categories
        ]
        keyboard.append([InlineKeyboardButton(text="Exit", callback_data="exit")])
        return InlineKeyboardMarkup(keyboard)

    def shops(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return
        context.user_data['new_meal_plan'] = {}
        update.message.reply_text(
            """Yo-ho-ho, is it already time to do the shopping?
Here are the categories of ingredients in you shopping list, choose \
one to see which ingredients are there and where you can purchase 'em.
            """,
            reply_markup=self.get_categories_keyboard(update, context),
        )
        return ShopsManager.CHOOSE_SHOP_CATEGORY

    def get_shops_keyboard(self, update, context, category):
        query = update.callback_query
        query.edit_message_text("Just a moment, I'm working on it...")
        if not 'shops' in context.user_data:
            user = context.user_data['user']
            print('user:', user)
            categories = context.user_data['categories']
            shops = self.meal_planner.get_nearby_shops_by_categories(user, categories)
            context.user_data['shops'] = shops
        else:
            shops = context.user_data['shops']
        print(shops)
        for shop in shops:
            if shop['category'] == category:
                category_shops = shop
                break
        else:
            return InlineKeyboardMarkup([])

        keyboard = [
            [InlineKeyboardButton(text=f"{shop['name'] if 'name' in shop else shop['shop']}", callback_data=i)]
            for i,shop in enumerate(category_shops)
        ]

        keyboard.append([InlineKeyboardButton(text="Back", callback_data="exit")])
        keyboard.append([InlineKeyboardButton(text="Exit", callback_data="exit")])
        return InlineKeyboardMarkup(keyboard)
   
    def choose_shop_category(self, update, context):
        user = context.user_data['user']

        if not user['address']:
            user['lat'] = 46.0664228
            user['lon'] = 11.1257601

        query = update.callback_query
        category_name = query.data
        categories = context.user_data['categories']
        for c in categories:
            if c['category'] == category_name:
                    category = c
                    break
        else:
            query.edit_message_text(f"Ups, no items appear to be found in this category,\
I'm sorry for the inconvenient")
            return ConversationHandler.END
        # category = list(filter(lambda x : x['category'] == category_name, categories))[0]
        ingredients = category['ingredients']
        ingredients_list = '\n'.join(f"\- {ingredient['name']}" for ingredient in ingredients)
        markup = self.get_shops_keyboard(update, context, category_name)
        query.edit_message_text(f"""
These are the items of category '{category_name}' in your shopping list:
{ingredients_list}

I found the following shops where I think you could buy them, check 'em out\.
        """, reply_markup = markup, parse_mode = ParseMode.MARKDOWN_V2)

        return ConversationHandler.END


    def choose_category_shop(self, update, context):
        query = update.callback_query
        query.answer()
        meal_plan_i = int(query.data)
        context.user_data['user_meal_plan_chosen'] = meal_plan_i
        meal_plan = context.user_data['user_meal_plans'][meal_plan_i]
        daily_plans = meal_plan['daily_plans']
        keyboard = [
            [InlineKeyboardButton(f"#{daily_plan['daily_plan_number'] + 1:2d}", callback_data=i)] 
                for i, daily_plan in enumerate(daily_plans)
        ]
        keyboard.extend([
            [InlineKeyboardButton("Back", callback_data=f"back_mp_0")],
            [InlineKeyboardButton("Exit", callback_data="exit")]
        ])
        markup = InlineKeyboardMarkup(keyboard)

        query.edit_message_text(
            text=f"""These are the daily plans of the meal number #{meal_plan_i + 1}.
Daily calories: {meal_plan['daily_calories']} - Diet: {meal_plan['diet_type']}    
            """, reply_markup=markup
        )
        return ShopsManager.CHOOSE_RECIPE

    
    def back_exit(self, update, context):
        query = update.callback_query
        query.answer()
        action = query.data
        if action == 'exit':
            return self.menu_exit(update, context)
        _, action, data = action.split('_')
        query.data = data
        if action == 'mp':
            return self.choose_meal_plan(update, context)
        if action == 'dp':
            return self.choose_daily_plan(update, context)
        if action == 'rp':
            return self.choose_recipe(update, context)

    def done(self, update: Update, context: CallbackContext) -> int:
        user_data = context.user_data
        attributes = ['new_meal_plan', 'user_meal_plans', 'user_meal_plan_chosen', 'user_daily_plan_chosen', 'user_recipes']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]

        update.message.reply_text(
            f"Uh-oh, it seems like you weren't able to complete the process. See you soon."
        )

        return ConversationHandler.END

    def menu_exit(self, update, context):
        user_data = context.user_data
        attributes = ['shops', 'categories']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]
        query = update.callback_query
        query.answer()
        query.edit_message_text("Whoopee, see you later!", reply_markup = None)
        return ConversationHandler.END