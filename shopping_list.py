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

class ShoppingListManager:
    MEAL_PLAN_SELECTED, REMOVE_ELEMENT, SHOW_SHOPPING_LIST = range(3)

    def __init__(self, meal_planner, logger):
        self.meal_planner = meal_planner
        self.logger = logger
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
            [InlineKeyboardButton(f"{e['ingredient_name']} {e['quantity']} {e['measure']} \u274C", callback_data=i)] 
                for i, e in enumerate(shopping_list)
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

        ingredient = context.user_data['shopping_list'][int(query.data)]
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
        attributes = ['user_meal_plans', 'shopping_list']
        for attribute in attributes:
            if attribute in user_data:
                del user_data[attribute]

    def done(self, update: Update, context: CallbackContext) -> int:
        self.clear_context(context)
        update.message.reply_text("Uh-oh, it seems like you weren't able to complete the process. See you soon.")
        return ConversationHandler.END

    