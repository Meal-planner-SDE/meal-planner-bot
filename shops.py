from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, KeyboardButton, ReplyKeyboardMarkup, ParseMode
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
    SHOPS, CHOOSE_SHOP_CATEGORY, CHOOSE_CATEGORY_SHOP = range(3)
   
    def __init__(self, meal_planner, logger):
        self.meal_planner = meal_planner
        self.logger = logger

        self.conv_handler = ConversationHandler(
            entry_points=[CommandHandler('shops', self.location)],
            states={
                ShopsManager.SHOPS: [
                    MessageHandler(Filters.location & ~(Filters.command | Filters.regex('^Done$')), self.shops),
                    # CallbackQueryHandler(, pattern='^((?!exit|back_.*).)*$'),
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                ],
                ShopsManager.CHOOSE_SHOP_CATEGORY: [
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                    CallbackQueryHandler(self.choose_shop_category, pattern='^((?!exit|back_.*).)*$'),
                ],
                ShopsManager.CHOOSE_CATEGORY_SHOP: [
                    CallbackQueryHandler(self.back_exit, pattern='^(exit|back_.*)$'),
                    CallbackQueryHandler(self.choose_category_shop, pattern='^((?!exit|back_.*).)*$'),
                ],
            },
            fallbacks=[MessageHandler(Filters.command | Filters.regex('^Done$'), self.done)],
        )

    def get_categories_keyboard(self, update, context):
        if not 'categories' in context.user_data:
            user = context.user_data['user']
            print(user)
            user_shopping_list = self.meal_planner.get_user_shopping_list(user)
            print("shopping list:", user_shopping_list)
            categories = self.meal_planner.group_ingredients(user_shopping_list)
            print("categories: ", categories)
            context.user_data['categories'] = categories
        else:
            categories = context.user_data['categories']
        print("Categories:", categories)

        keyboard = [
            [InlineKeyboardButton(text=f"{category['category'].capitalize()}", callback_data=i)]
            for i, category in enumerate(categories)
        ]
        keyboard.append([InlineKeyboardButton(text="Exit", callback_data="exit")])
        return InlineKeyboardMarkup(keyboard)
    
    def location(self, update, context):
        print('location called')
        if not utils.authenticate(self.meal_planner, update, context):
            return
        keyboard = [
            [KeyboardButton(text="Share location", request_location=True)],
            # [ReplyKeyboardButton(text="Exit", callback_data="exit")],
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
        update.message.reply_text("""Yo-ho-ho, is it already time to do the shopping?
To help you find the shops, I need to know you location.""", reply_markup=reply_markup)
        return ShopsManager.SHOPS

    def shops(self, update, context):
        print('shops called')
        
        user = context.user_data['user']
        if update.message:
            user['lat'] = update.message.location.latitude
            user['lon'] = update.message.location.longitude
            message_fn = update.message.reply_text
        else:
            query = update.callback_query
            query.answer()
            message_fn = query.edit_message_text
        message_fn(
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
        for shop_category in shops:
            if shop_category['category'] == category:
                category_shops = shop_category['shops'];
                break
        else:
            keyboard = []
            keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_categories_0")])
            keyboard.append([InlineKeyboardButton(text="Exit", callback_data="exit")])
            return InlineKeyboardMarkup(keyboard)

        keyboard = [
            [InlineKeyboardButton(text=f"{shop['name'] if 'name' in shop else shop['shop']}", callback_data=i)]
            for i, shop in enumerate(category_shops)
        ]

        keyboard.append([InlineKeyboardButton(text="Back", callback_data="back_categories_0")])
        keyboard.append([InlineKeyboardButton(text="Exit", callback_data="exit")])
        
        return InlineKeyboardMarkup(keyboard)
   
    def choose_shop_category(self, update, context):
        print('shops category called')

        user = context.user_data['user']

        query = update.callback_query
        category_i = int(query.data)
        categories = context.user_data['categories']
        category = categories[category_i]
        context.user_data['category_chosen'] = category_i

        # category = list(filter(lambda x : x['category'] == category_name, categories))[0]
        ingredients = category['ingredients']
        ingredients_list = '\n'.join(f"- {ingredient['name']}" for ingredient in ingredients if 'name' in ingredient and ingredient['name'])
        markup = self.get_shops_keyboard(update, context, category['category'])
        query.edit_message_text(f"""
These are the items of category '{category['category']}' in your shopping list:
{ingredients_list}

I found the following shops where I think you could buy them, check 'em out\.
        """, reply_markup = markup)

        return ShopsManager.CHOOSE_CATEGORY_SHOP


    def choose_category_shop(self, update, context):
        print('category shops called')

        query = update.callback_query
        query.answer()
        shop_i = int(query.data)
        category_i = int(context.user_data['category_chosen'])
        print(f"Chosen shop {shop_i} of category nr. {category_i}")
        shop_categories = context.user_data['shops']
        print(shop_categories)
        shop = shop_categories[category_i]['shops'][shop_i]
        lat = shop['lat']
        lon = shop['lon']
        name = shop['name']

        # query.data = category_i
        category_name = shop_categories[category_i]['category']
        query.message.reply_text(f"{name} is here!")
        query.message.reply_location(latitude = lat, longitude = lon)
        query.reply_text(f"""
These are the items of category '{category['category']}' in your shopping list:
{ingredients_list}

I found the following shops where I think you could buy them, check 'em out\.
        """, reply_markup = self.get_shops_keyboard(update, context, category_name))

        return ShopsManager.CHOOSE_CATEGORY_SHOP

    
    def back_exit(self, update, context):
        print('back exit called')

        query = update.callback_query
        query.answer()
        action = query.data
        if action == 'exit':
            return self.menu_exit(update, context)
        _, action, data = action.split('_')
        query.data = data
        # if action == 'mp':
        #     return self.choose_meal_plan(update, context)
        # if action == 'dp':
        #     return self.choose_daily_plan(update, context)
        # if action == 'rp':
        #     return self.choose_recipe(update, context)
        if action == 'categories':
            return self.shops(update, context)
    def done(self, update: Update, context: CallbackContext) -> int:
        print('done called')

        user_data = context.user_data
        attributes = ['shops', 'categories', 'category_chosen']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]

        update.message.reply_text(
            f"Uh-oh, it seems like you weren't able to complete the process. See you soon."
        )

        return ConversationHandler.END

    def menu_exit(self, update, context):
        print('exit called')

        user_data = context.user_data
        attributes = ['shops', 'categories', 'category_chosen']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]
        query = update.callback_query
        query.answer()
        query.edit_message_text("Whoopee, see you later!", reply_markup = None)
        return ConversationHandler.END