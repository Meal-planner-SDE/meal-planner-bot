from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ReplyKeyboardMarkup
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
    MEAL_PLAN_SELECTED = 0

    def __init__(self, meal_planner, logger):
        self.meal_planner = meal_planner
        self.logger = logger
        self.conv_handler_meal_plan_to_shopping_list = ConversationHandler(
            entry_points=[CommandHandler('mptosl', self.meal_plan_to_shopping_list)],
            states={
                ShoppingListManager.MEAL_PLAN_SELECTED: [
                    CallbackQueryHandler(self.add_meal_plan_to_shopping_list),
                ]
            },
            fallbacks=[MessageHandler(Filters.regex('^Done$'), self.done)],
        )

    def meal_plan_to_shopping_list(self, update, context):
        if not utils.authenticate(self.meal_planner, update, context):
            return
        markup = InlineKeyboardMarkup(self.get_meal_plans_keyboard(context))
        update.message.reply_text(
            """Someone told me that you'd like to get all the ingredients of your meal plan in a shopping list.
What's the ID of the meal plan?
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

    def format_entries(self, shopping_list):
        return "\n".join(f"{e['ingredient_name']} {e['quantity']} {e['measure']}" for e in shopping_list)


    def add_meal_plan_to_shopping_list(self, update, context):
        query = update.callback_query
        query.answer()
        context.user_data['user_meal_plan_chosen'] = int(query.data)
        meal_plan = context.user_data['user_meal_plans'][int(query.data)]
        print(meal_plan)
        query.edit_message_text(
            text="""Alright, this will take a while. 
Sit back and relax...
            """
        )
        shopping_list = self.meal_planner.add_meal_plan_to_shopping_list(context.user_data['user'], meal_plan)

        query.edit_message_text(
            text=f"""We're finally done! Here is your shining new shopping list:
            """
        )
        
        messages = self.format_entries(shopping_list)
        for message in messages:
            pass

        return ConversationHandler.END

    def done(self, update, context):
        user_data = context.user_data
        if 'choice' in user_data:
            del user_data['choice']

        update.message.reply_text(
            f"I learned these facts about you: {(user_data)} Until next time!"
        )

        user_data.clear()
        return ConversationHandler.END